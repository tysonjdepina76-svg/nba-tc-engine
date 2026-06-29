#!/usr/bin/env python3
"""Unified TC API handler — WNBA, MLB, WORLD CUP.
All sports return the same fields: team_to_win, ml_pick, spread_pick, total_lean, book_source_honest, valid_props.
"""
import json, os, sys, subprocess, glob as globmod, socket
from datetime import datetime, timezone, timedelta
from pathlib import Path

socket.setdefaulttimeout(8)  # prevent any HTTP/SSL hang from taking down the endpoint

sys.path.insert(0, "/home/workspace/Projects")
from api_cache import cached_get, log_call

SPORT_TO_ESPN = {
    "NBA": "basketball/nba", "WNBA": "basketball/wnba",
    "MLB": "baseball/mlb", "NHL": "hockey/nhl",
    "NFL": "football/nfl", "SOCCER": "soccer/usa.1",
    "WORLD CUP": "soccer/fifa.world",
}

_ESPN_SCOREBOARD_CACHE = {}

def fetch_espn_scoreboard(espn_path: str) -> list:
    """ONCE per slate — returns all events for the sport."""
    if espn_path in _ESPN_SCOREBOARD_CACHE:
        return _ESPN_SCOREBOARD_CACHE[espn_path]
    url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard"
    data = cached_get(url, ttl_seconds=1800)
    if not data:
        log_call("ESPN", f"scoreboard:{espn_path}")
        _ESPN_SCOREBOARD_CACHE[espn_path] = []
        return []
    log_call("ESPN", f"scoreboard:{espn_path}")
    _ESPN_SCOREBOARD_CACHE[espn_path] = data.get("events", [])
    return _ESPN_SCOREBOARD_CACHE[espn_path]

def fetch_espn_event(espn_path: str, event_id: str) -> dict:
    """ONCE per event_id — used for boxscore/summary."""
    if not event_id:
        return {}
    url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/summary"
    data = cached_get(url, params={"event": event_id}, ttl_seconds=1800)
    log_call("ESPN", f"event:{event_id}")
    return data or {}

WORKSPACE = Path("/home/workspace")
SPORTS = {"WNBA", "MLB", "WORLD CUP", "SOCCER"}


def compute_team_pick(away_score, home_score, away_abbr, home_abbr, dk_ml_away, dk_ml_home, spread, is_home_court):
    """Returns (team_to_win, reason, ml_pick, spread_pick)."""
    team_to_win = None
    reason = ""
    ml_pick = None
    spread_pick = None

    # If live score exists
    if away_score is not None and home_score is not None:
        try:
            as_ = int(away_score) if away_score else 0
            hs_ = int(home_score) if home_score else 0
        except (ValueError, TypeError):
            as_ = 0
            hs_ = 0
        if as_ > hs_:
            team_to_win = away_abbr
            reason = f"leading {as_}-{hs_}"
        elif hs_ > as_:
            team_to_win = home_abbr
            reason = f"leading {hs_}-{as_}"
        else:
            team_to_win = home_abbr if is_home_court else away_abbr
            reason = "tied — home advantage"
    else:
        team_to_win = home_abbr if is_home_court else away_abbr
        reason = "home court/field advantage"

    # ML pick: use DK ML if available, else lean toward team_to_win
    if dk_ml_away is not None and dk_ml_home is not None:
        if dk_ml_away < dk_ml_home:
            ml_pick = away_abbr
        else:
            ml_pick = home_abbr
    else:
        ml_pick = team_to_win

    # Spread pick: cover if DK spread is available
    if spread is not None:
        try:
            sp_val = float(spread)
        except (ValueError, TypeError):
            sp_val = 0
        if sp_val <= 0:
            spread_pick = home_abbr  # home is favorite or pickem
        else:
            spread_pick = away_abbr  # away is getting points
    else:
        spread_pick = team_to_win

    return team_to_win, reason, ml_pick, spread_pick


def _fetch_espn_dk_lines(espn_path: str, away_abbr: str, home_abbr: str):
    """Fetch DraftKings lines (total/spread/ML) from ESPN scoreboard for a specific game."""
    import urllib.request, urllib.error
    result = {"total": None, "spread": None, "ml_away": None, "ml_home": None}
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        for ev in data.get("events", []):
            comp = (ev.get("competitions", []) or [{}])[0]
            comps = comp.get("competitors", [])
            a_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "away"), "")
            h_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "home"), "")
            if a_team != away_abbr.upper() and h_team != home_abbr.upper():
                continue
            odds_list = comp.get("odds", []) or []
            dk_odds = next((o for o in odds_list if o.get("provider", {}).get("id") == "100" or o.get("provider", {}).get("name") == "DraftKings"), None)
            if not dk_odds:
                dk_odds = odds_list[0] if odds_list else None
            if dk_odds:
                result["total"] = dk_odds.get("overUnder")
                result["spread"] = dk_odds.get("spread")
                ml = dk_odds.get("moneyline", {})
                result["ml_home"] = _parse_ml(ml.get("home", {}).get("close", {}).get("odds"))
                result["ml_away"] = _parse_ml(ml.get("away", {}).get("close", {}).get("odds"))
            break
    except Exception:
        pass
    return result


def _fetch_espn_game_roster(espn_path, away_abbr, home_abbr):
    """Fetch ESPN boxscore roster + DK lines for a specific game. Returns {away_players, home_players, dk_lines, event_id}."""
    import urllib.request, urllib.error
    result = {"away_players": [], "home_players": [], "dk_lines": {"total": None, "spread": None, "ml_away": None, "ml_home": None}, "event_id": None}
    WNBA_LABELS = ["MIN", "PTS", "FG", "3PT", "FT", "REB", "AST", "TO", "STL", "BLK", "OREB", "DREB", "PF", "+/-"]
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        for ev in data.get("events", []):
            comp = (ev.get("competitions", []) or [{}])[0]
            comps = comp.get("competitors", [])
            a_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "away"), "")
            h_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "home"), "")
            if a_team != away_abbr.upper() and h_team != home_abbr.upper():
                continue
            ev_id = ev.get("id")
            result["event_id"] = ev_id
            
            # Get DK lines from odds
            odds_list = comp.get("odds", []) or []
            dk_odds = next((o for o in odds_list if o.get("provider", {}).get("id") == "100" or o.get("provider", {}).get("name") == "DraftKings"), None)
            if not dk_odds:
                dk_odds = odds_list[0] if odds_list else None
            if dk_odds:
                result["dk_lines"]["total"] = dk_odds.get("overUnder")
                result["dk_lines"]["spread"] = dk_odds.get("spread")
                ml = dk_odds.get("moneyline", {})
                result["dk_lines"]["ml_home"] = _parse_ml(ml.get("home", {}).get("close", {}).get("odds"))
                result["dk_lines"]["ml_away"] = _parse_ml(ml.get("away", {}).get("close", {}).get("odds"))
            
            # Fetch boxscore roster
            if ev_id:
                try:
                    sum_url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/summary?event={ev_id}"
                    with urllib.request.urlopen(sum_url, timeout=8) as sum_resp:
                        summary = json.loads(sum_resp.read().decode())
                    bs_players = (summary.get("boxscore") or {}).get("players", [])
                    for team_data in bs_players:
                        team_abbr = (team_data.get("team") or {}).get("abbreviation", "")
                        stats_block = (team_data.get("statistics") or [{}])[0]
                        labels = stats_block.get("labels", WNBA_LABELS)
                        athletes = stats_block.get("athletes", [])
                        for athlete_entry in athletes:
                            if athlete_entry.get("didNotPlay"):
                                continue
                            athlete = athlete_entry.get("athlete", {})
                            name = athlete.get("displayName", athlete.get("fullName", "Unknown"))
                            pos = athlete.get("position", {}).get("abbreviation", "")
                            raw_stats = athlete_entry.get("stats", [])
                            stat_map = {}
                            for i, label in enumerate(labels):
                                val = raw_stats[i] if i < len(raw_stats) else "0"
                                try:
                                    stat_map[label.lower()] = float(val) if "." in str(val) or val.replace("-", "").isdigit() else 0
                                except:
                                    stat_map[label.lower()] = 0
                            player = {
                                "name": name,
                                "team": team_abbr,
                                "role": "START" if athlete_entry.get("starter") else "BENCH",
                                "status": "ACTIVE",
                                "pos": pos,
                                "min": 0,
                                "tc_pts": 0, "tc_reb": 0, "tc_ast": 0, "tc_3pm": 0, "tc_stl": 0, "tc_blk": 0,
                                "line_pts": 0, "line_reb": 0, "line_ast": 0, "line_3pm": 0, "line_stl": 0, "line_blk": 0,
                                "edge_pts": 0, "edge_reb": 0, "edge_ast": 0, "edge_3pm": 0, "edge_stl": 0, "edge_blk": 0,
                            }
                            if team_abbr == a_team:
                                result["away_players"].append(player)
                            elif team_abbr == h_team:
                                result["home_players"].append(player)
                except Exception:
                    pass
            break
    except Exception:
        pass
    return result


def _fetch_odds_api_game_lines(espn_path, away_abbr, home_abbr):
    """Fetch game totals/ML/spread from The Odds API as fallback when ESPN DK lines are empty."""
    import urllib.request, urllib.error
    result = {"total": None, "spread": None, "ml_away": None, "ml_home": None, "source": "none"}
    try:
        key = os.environ.get("ODDS_API_KEY", "") or os.environ.get("THEODDSAPI_KEY", "")
        if not key:
            return result
        sport_key = espn_path.replace("/", "_")  # basketball/wnba -> basketball_wnba
        print(f"DEBUG: Using key for {espn_path}")
        url = f"https://api.theoddsapi.com/odds/?sport_key={sport_key}&regions=us&apiKey={key}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        
        if not data.get("success"):
            return result
        
        # WNBA team abbreviations to full names for matching
        WNBA_NAMES = {
            "ATL": "atlanta", "CHI": "chicago", "CON": "connecticut", "DAL": "dallas",
            "GS": "golden state", "IND": "indiana", "LV": "las vegas", "LA": "los angeles",
            "MIN": "minnesota", "NY": "new york", "PHX": "phoenix", "POR": "portland",
            "SEA": "seattle", "TOR": "toronto", "WSH": "washington",
        }
        aw = WNBA_NAMES.get(away_abbr.upper(), away_abbr.lower())
        hw = WNBA_NAMES.get(home_abbr.upper(), home_abbr.lower())
        
        for ev in data.get("data", []):
            ht = (ev.get("home_team", "") or "").lower()
            at = (ev.get("away_team", "") or "").lower()
            if aw not in at and hw not in ht:
                continue
            
            # Find best book: prefer DraftKings, then BetMGM, then first available
            books = ev.get("books", [])
            dk_books = [b for b in books if "draftkings" in (b.get("book", "") or "").lower()]
            mgm_books = [b for b in books if "betmgm" in (b.get("book", "") or "").lower()]
            fd_books = [b for b in books if "fanduel" in (b.get("book", "") or "").lower()]
            preferred = dk_books or mgm_books or fd_books or books
            
            # Collect all markets across preferred books
            all_markets = []
            for b in preferred[:3]:
                all_markets.append(b)
            
            # Extract totals
            totals_mkts = [m for m in all_markets if m.get("market") == "totals"]
            for tm in totals_mkts:
                outcomes = tm.get("outcomes", [])
                if outcomes:
                    result["total"] = outcomes[0].get("point")
                    result["source"] = "odds_api"
                    break
            
            # Extract spread
            spread_mkts = [m for m in all_markets if m.get("market") == "spreads"]
            for sm in spread_mkts:
                outcomes = sm.get("outcomes", [])
                for o in outcomes:
                    name = (o.get("name", "") or "").lower()
                    if hw in name:
                        result["spread"] = o.get("point")
                        result["source"] = "odds_api"
                        break
            
            # Extract ML from h2h market
            h2h_mkts = [m for m in all_markets if m.get("market") == "h2h"]
            for hm in h2h_mkts:
                outcomes = hm.get("outcomes", [])
                for o in outcomes:
                    name = (o.get("name", "") or "").lower()
                    price = o.get("price")
                    if hw in name:
                        result["ml_home"] = price
                    elif aw in name:
                        result["ml_away"] = price
            
            if result["total"]:
                break
    except Exception:
        pass
    return result


def _parse_ml(v):
    if v is None:
        return None
    try:
        return int(str(v).replace("+", ""))
    except (ValueError, TypeError):
        return None


def compute_total_lean(actual_total, dk_total, valid_props):
    """Return total_lean string based on score vs DK total."""
    if actual_total is not None and dk_total is not None and dk_total > 0:
        return "OVER" if actual_total > dk_total else "UNDER" if actual_total < dk_total else "NEUTRAL"
    over_count = sum(1 for p in valid_props if p.get("direction") == "OVER")
    under_count = len(valid_props) - over_count
    if under_count > over_count:
        return "UNDER"
    elif over_count > under_count:
        return "OVER"
    return "NO MARKET"


def main():
    sport = sys.argv[1] if len(sys.argv) > 1 else "WNBA"
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    away = sys.argv[3] if len(sys.argv) > 3 else ""
    home = sys.argv[4] if len(sys.argv) > 4 else ""
    sport = sport.upper().replace("%20", " ").strip()

    if sport in ("NBA", "NHL"):
        print(json.dumps({"error": f"{sport} disabled", "disabled": True}))
        return

    if sport not in SPORTS:
        print(json.dumps({"error": f"Unknown sport: {sport}"}))
        return

    today = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=5) - timedelta(days=1)).strftime("%Y-%m-%d")

    # --- LIVE STATS MODE ---
    if mode == "live-stats":
        espn_paths = {"WNBA": "basketball/wnba", "MLB": "baseball/mlb", "WORLD CUP": "soccer/fifa.world", "SOCCER": "soccer/fifa.world"}
        ep = espn_paths.get(sport, "basketball/wnba")
        import urllib.request, concurrent.futures

        WNBA_LABELS = ["MIN", "PTS", "FG", "3PT", "FT", "REB", "AST", "TO", "STL", "BLK", "OREB", "DREB", "PF", "+/-"]

        def fetch_boxscore_players(event_id, away_abbr, home_abbr):
            players_list = []
            try:
                r = urllib.request.urlopen(
                    f"https://site.api.espn.com/apis/site/v2/sports/{ep}/summary?event={event_id}",
                    timeout=8
                )
                summary = json.loads(r.read())
                bs_players = (summary.get("boxscore") or {}).get("players", [])
                for team_data in bs_players:
                    team_abbr = (team_data.get("team") or {}).get("abbreviation", "")
                    stats_block = (team_data.get("statistics") or [{}])[0]
                    labels = stats_block.get("labels", WNBA_LABELS)
                    athletes = stats_block.get("athletes", [])
                    for athlete_entry in athletes:
                        if athlete_entry.get("didNotPlay"):
                            continue
                        athlete = athlete_entry.get("athlete", {})
                        name = athlete.get("displayName", athlete.get("fullName", "Unknown"))
                        raw_stats = athlete_entry.get("stats", [])
                        stat_map = {}
                        for i, label in enumerate(labels):
                            val = raw_stats[i] if i < len(raw_stats) else "0"
                            try:
                                stat_map[label.lower()] = float(val) if "." in str(val) or val.replace("-","").isdigit() else 0
                            except:
                                stat_map[label.lower()] = 0
                        players_list.append({
                            "name": name,
                            "team": team_abbr,
                            "role": "START" if athlete_entry.get("starter") else "BENCH",
                            "minutes": stat_map.get("min", 0),
                            "actual": {
                                "pts": stat_map.get("pts", 0),
                                "reb": stat_map.get("reb", 0),
                                "ast": stat_map.get("ast", 0),
                                "tpm": stat_map.get("3pt", 0),
                                "stl": stat_map.get("stl", 0),
                                "blk": stat_map.get("blk", 0),
                            },
                        })
            except Exception:
                pass
            return players_list

        try:
            r = urllib.request.urlopen(f"https://site.api.espn.com/apis/site/v2/sports/{ep}/scoreboard", timeout=10)
            data = json.loads(r.read())
            games = []
            live_event_ids = []
            for ev in data.get("events", []):
                comp = (ev.get("competitions") or [{}])[0]
                teams = comp.get("competitors", [])
                a = next((t for t in teams if t.get("homeAway") == "away"), {})
                h = next((t for t in teams if t.get("homeAway") == "home"), {})
                ev_id = ev.get("id")
                status_desc = (ev.get("status") or {}).get("type", {}).get("description", "")
                completed = (ev.get("status") or {}).get("type", {}).get("completed", False)
                game = {
                    "id": ev_id,
                    "name": ev.get("name", ""),
                    "date": ev.get("date"),
                    "status": status_desc,
                    "completed": completed,
                    "clock": (ev.get("status") or {}).get("displayClock", ""),
                    "period": (ev.get("status") or {}).get("period", 0),
                    "detail": ev.get("shortName", ""),
                    "away": {"team": (a.get("team") or {}).get("abbreviation", ""), "score": str(a.get("score", "0"))},
                    "home": {"team": (h.get("team") or {}).get("abbreviation", ""), "score": str(h.get("score", "0"))},
                    "players": [],
                }
                games.append(game)
                if status_desc in ("In Progress", "Final") or completed:
                    live_event_ids.append((ev_id, game))

            if live_event_ids:
                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                    futures = {
                        executor.submit(fetch_boxscore_players, ev_id, g["away"]["team"], g["home"]["team"]): g
                        for ev_id, g in live_event_ids
                    }
                    for future in concurrent.futures.as_completed(futures):
                        game_ref = futures[future]
                        try:
                            game_ref["players"] = future.result(timeout=10)
                        except Exception:
                            pass

            print(json.dumps({"mode": "live_stats", "sport": sport, "games": games, "timestamp": datetime.now().isoformat()}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        return

    # --- PROJECTION MODE ---

    # Common helpers for unified fields
    def attach_unified_fields(result, away_abbr, home_abbr, is_home_court=True,
                               dk_total=None, dk_ml_away=None, dk_ml_home=None,
                               spread=None, away_score=None, home_score=None,
                               book_source="unknown", valid_props=None):
        tw, reason, ml, sp = compute_team_pick(away_score, home_score, away_abbr, home_abbr, dk_ml_away, dk_ml_home, spread, is_home_court)
        total_lean = compute_total_lean(
            (int(away_score or 0) + int(home_score or 0)) if away_score is not None and home_score is not None else None,
            dk_total, valid_props or []
        )
        result["team_to_win"] = tw
        result["team_to_win_reason"] = reason
        result["ml_pick"] = ml
        result["spread_pick"] = sp
        result["total_lean"] = total_lean
        result["book_source_honest"] = book_source

    # MLB: delegate to mlb_tc_engine.py
    if sport == "MLB" and away and home:
        out = f"/tmp/tc_MLB_{away}_{home}.json"
        try:
            subprocess.run(
                ["python3", str(WORKSPACE / "Projects" / "mlb_tc_engine.py"),
                 "--game", f"{away}@{home}", "--output", out],
                capture_output=True, timeout=45, cwd=str(WORKSPACE))
            if Path(out).exists():
                result = json.loads(Path(out).read_text())

                def reshape_mlb_players(flat_list):
                    players = []
                    for p in flat_list:
                        pos = (p.get("pos") or "").upper()
                        is_pitcher = pos in ("SP", "RP", "P")
                        batting = p.get("tc_batting", {})
                        lines = p.get("lines", {})
                        edges = p.get("edges", {})
                        player = {
                            "name": p.get("name", ""),
                            "pos": p.get("pos", ""),
                            "team": p.get("team", ""),
                            "status": p.get("status", "ACTIVE"),
                            "role": "PITCHER" if is_pitcher else "BATTER",
                            "min": p.get("min", 0),
                            "tc_h": batting.get("hits", 0),
                            "tc_hr": batting.get("hr", 0),
                            "tc_rbi": batting.get("rbi", 0),
                            "tc_r": batting.get("runs", 0),
                            "tc_sb": batting.get("sb", 0),
                            "tc_avg": round(batting.get("avg", 0), 3) if batting.get("avg") else 0,
                            "line_h": lines.get("hits", 0),
                            "line_hr": lines.get("hr", 0),
                            "line_rbi": lines.get("rbi", 0),
                            "line_r": lines.get("runs", 0),
                            "line_sb": lines.get("sb", 0),
                            "edge_h": edges.get("hits", 0),
                            "edge_hr": edges.get("hr", 0),
                            "edge_rbi": edges.get("rbi", 0),
                            "edge_r": edges.get("runs", 0),
                            "edge_sb": edges.get("sb", 0),
                            "edge_avg": 0,
                            "batting": batting,
                            "pitching": p.get("pitching"),
                            "tc_batting": batting,
                            "tc_pitching": p.get("tc_pitching"),
                            "lines_raw": lines,
                            "edges_raw": edges,
                        }
                        players.append(player)
                    players.sort(key=lambda x: (0 if x["role"] == "BATTER" else 1, x.get("pos", "")))
                    return players

                away_flat = result.pop("away_players", [])
                home_flat = result.pop("home_players", [])
                away_players = reshape_mlb_players(away_flat)
                home_players = reshape_mlb_players(home_flat)

                away_active = [p for p in away_players if p["status"] == "ACTIVE"]
                home_active = [p for p in home_players if p["status"] == "ACTIVE"]

                result["away"] = {"all": {"players": away_players}, "starters": {"players": away_active[:9]}, "bench": {"players": away_active[9:]}}
                result["home"] = {"all": {"players": home_players}, "starters": {"players": home_active[:9]}, "bench": {"players": home_active[9:]}}
                result["away_team"] = away
                result["home_team"] = home
                result["sport"] = "MLB"
                result["mode"] = "live"
                result["roster_counts"] = {
                    "away": len(away_players), "home": len(home_players),
                    "away_active": len(away_active), "home_active": len(home_active),
                }

                vp = result.get("valid_props", [])
                tc_combined = sum(p.get("tc_projection", 0) for p in vp) / max(len(vp), 1) if vp else 0
                tc_line = sum(p.get("market_line", 0) for p in vp) / max(len(vp), 1) if vp else 0
                edge = sum(p.get("edge", 0) for p in vp) / max(len(vp), 1) if vp else 0
                over_count = sum(1 for p in vp if p.get("direction") == "OVER")
                signal = "OVER" if over_count > len(vp) / 2 else "UNDER" if vp else "NO MARKET"
                odds = {"total": result.get("dk_total"), "ml_source": "DraftKings via SportsDataIO"}

                result["tc_combined"] = None
                result["tc_line"] = None
                result["edge"] = None
                result["signal"] = None
                result["odds"] = odds

                attach_unified_fields(result, away, home, is_home_court=True,
                                      dk_total=result.get("dk_total"),
                                      book_source="DraftKings via SportsDataIO",
                                      valid_props=vp)
                print(json.dumps(result, default=str))
                return
        except Exception as e:
            pass

    # WNBA: read from daily pipeline output
    if sport == "WNBA" and away and home:
        # ── Load or create projection from WNBA TC engine ──
        from wnba_tc_engine import project_game, fetch_all_season_stats
        proj_path = None
        for date_dir in [today, yesterday]:
            exact = WORKSPACE / "Daily_Log" / date_dir / f"proj_{sport}_{away}_at_{home}.json"
            if exact.exists():
                proj_path = exact
                break
            candidates = globmod.glob(
                str(WORKSPACE / "Daily_Log" / date_dir / f"proj_{sport}_*.json"))
            for cp in candidates:
                fn = os.path.basename(cp)
                if away.upper() in fn.upper() and home.upper() in fn.upper():
                    proj_path = Path(cp)
                    break
            if proj_path:
                break

        # ── Fetch ESPN DK lines + roster for this game ──
        dk_lines = _fetch_espn_dk_lines("basketball/wnba", away, home)
        roster = _fetch_espn_game_roster("basketball/wnba", away, home)
        
        # Merge roster DK lines if _fetch_espn_dk_lines missed them
        if not dk_lines.get("total"):
            dk_lines = roster.get("dk_lines", dk_lines)
        
        # Merge Odds API fallback if still no lines
        if not dk_lines.get("total"):
            print(f"DEBUG: No DK lines found for {away}@{home}", file=sys.stderr)
            odds_lines = _fetch_odds_api_game_lines("basketball/wnba", away, home)
            if odds_lines.get("total"):
                dk_lines = odds_lines

        # ── If no saved proj, generate fresh from engine ──
        if not proj_path:
            try:
                data = project_game(away, home)
                # Merge ESPN DK lines into engine output
                if dk_lines.get("total"):
                    data["odds"]["total"] = dk_lines["total"]
                    data["odds"]["ml_away"] = dk_lines.get("ml_away")
                    data["odds"]["ml_home"] = dk_lines.get("ml_home")
                    data["odds"]["spread"] = dk_lines.get("spread")
                    data["odds"]["ml_source"] = "ESPN DraftKings embedded"
                    data["dk_total"] = dk_lines["total"]
                # Merge roster if engine missing players
                if roster.get("away_players") and (not data.get("away", {}).get("all", {}).get("players")):
                    away_all = roster["away_players"]
                    home_all = roster["home_players"]
                    data["away"] = {"all": {"players": away_all}, "starters": {"players": [p for p in away_all if p.get("role")=="START"]}, "bench": {"players": [p for p in away_all if p.get("role")!="START"]}}
                    data["home"] = {"all": {"players": home_all}, "starters": {"players": [p for p in home_all if p.get("role")=="START"]}, "bench": {"players": [p for p in home_all if p.get("role")!="START"]}}
                    data["roster_counts"] = {"away": len(away_all), "home": len(home_all)}
                    data["source"] = "ESPN Core API + ESPN roster (live)"
                book = "DK/ESPN embedded" if dk_lines.get("total") else "self-edge"
                attach_unified_fields(data, away, home, is_home_court=True,
                                      dk_total=dk_lines.get("total"),
                                      book_source=book,
                                      valid_props=data.get("valid_props", []))
                print(json.dumps(data, default=str))
                return
            except Exception as e:
                print(f"ENGINE FALLBACK FAILED: {e}", file=sys.stderr)

        if proj_path and proj_path.exists():
            data = json.loads(proj_path.read_text())
            vp = data.get("valid_props", [])
            dk_total = dk_lines.get("total") or data.get("dk_total")
            
            # If proj file has empty roster, fill from ESPN
            away_players = (data.get("away") or {}).get("all", {}).get("players", [])
            home_players = (data.get("home") or {}).get("all", {}).get("players", [])
            if not away_players and not home_players and roster.get("away_players"):
                away_all = roster["away_players"]
                home_all = roster["home_players"]
                away_starters = [p for p in away_all if p.get("role") == "START"]
                home_starters = [p for p in home_all if p.get("role") == "START"]
                away_bench = [p for p in away_all if p.get("role") != "START"]
                home_bench = [p for p in home_all if p.get("role") != "START"]
                data["away"] = {"all": {"players": away_all}, "starters": {"players": away_starters}, "bench": {"players": away_bench}}
                data["home"] = {"all": {"players": home_all}, "starters": {"players": home_starters}, "bench": {"players": home_bench}}
                data["roster_counts"] = {
                    "away": len(away_all), "home": len(home_all),
                    "away_active": len(away_all), "home_active": len(home_all),
                }
                data["source"] = "ESPN roster (live) + saved proj"

            # Merge DK lines into odds field if they exist
            if dk_lines.get("total"):
                data.setdefault("odds", {})
                data["odds"]["total"] = dk_lines["total"]
                data["odds"]["ml_away"] = dk_lines.get("ml_away")
                data["odds"]["ml_home"] = dk_lines.get("ml_home")
                data["odds"]["spread"] = dk_lines.get("spread")
                data["odds"]["ml_source"] = "ESPN DraftKings embedded"
                data["dk_total"] = dk_lines["total"]

            book = "DK/ESPN embedded" if dk_total else "self-edge"
            attach_unified_fields(data, away, home, is_home_court=True,
                                  dk_total=dk_total, book_source=book, valid_props=vp)
            print(json.dumps(data, default=str))
            return

        # Fallback: build response from ESPN roster + DK lines
        away_players = roster.get("away_players", [])
        home_players = roster.get("home_players", [])
        away_starters = [p for p in away_players if p.get("role") == "START"]
        home_starters = [p for p in home_players if p.get("role") == "START"]
        away_bench = [p for p in away_players if p.get("role") != "START"]
        home_bench = [p for p in home_players if p.get("role") != "START"]
        
        has_roster = len(away_players) > 0 or len(home_players) > 0
        source = "ESPN roster (live)" if has_roster else "ESPN DK embedded (no player props available yet)"
        
        result = {
            "mode": "live", "sport": sport,
            "matchup": f"{away}@{home}",
            "away_team": away, "home_team": home,
            "source": source,
            "valid_props": [],
            "signal": "ROSTER LOADED" if has_roster else "NO PROPS — game lines only",
            "away": {"all": {"players": away_players}, "starters": {"players": away_starters}, "bench": {"players": away_bench}},
            "home": {"all": {"players": home_players}, "starters": {"players": home_starters}, "bench": {"players": home_bench}},
            "roster_counts": {
                "away": len(away_players), "home": len(home_players),
                "away_active": len(away_players), "home_active": len(home_players),
            },
            "odds": {
                "total": dk_lines.get("total"),
                "ml_away": dk_lines.get("ml_away"),
                "ml_home": dk_lines.get("ml_home"),
                "spread": dk_lines.get("spread"),
                "ml_source": "ESPN DraftKings embedded",
            },
            "dk_total": dk_lines.get("total"),
        }
        attach_unified_fields(result, away, home, is_home_court=True,
                              dk_total=dk_lines.get("total"),
                              book_source="ESPN DK embedded",
                              valid_props=[])
        print(json.dumps(result, default=str))
        return

    # WORLD CUP: load from worldcup_picks.py output (check today + yesterday)
    if sport in ("WORLD CUP", "SOCCER") and away and home:
        props_path = None
        for date_dir in [today, yesterday]:
            date_compact = date_dir.replace("-", "")
            p = WORKSPACE / "Daily_Log" / "worldcup" / date_compact / "matches.json"
            if p.exists():
                props_path = p
                break
        if props_path:
            props_data = json.loads(props_path.read_text())
            matches = props_data if isinstance(props_data, list) else props_data.get("matches", [])

            for m in matches:
                teams = m.get("teams", [])
                a_abbr = next((t.get("abbrev", "").upper() for t in teams if t.get("homeAway") == "away"), "")
                h_abbr = next((t.get("abbrev", "").upper() for t in teams if t.get("homeAway") == "home"), "")
                if a_abbr == away.upper() and h_abbr == home.upper():
                    props = m.get("player_props", {})
                    valid = []
                    for pname, stats in props.items():
                        for st, info in stats.items():
                            line = info.get("line")
                            if line:
                                edge = round(line * 0.12, 1)
                                valid.append({
                                    "player": pname, "stat": st.upper(),
                                    "market_line": line, "tc_projection": round(line + edge, 1),
                                    "edge": edge, "direction": "OVER" if edge > 0 else "UNDER",
                                    "source": info.get("source", m.get("book", "self-edge")),
                                    "status": "ACTIVE"
                                })
                    book = m.get("book", "self-edge")
                    book_honest = "FanDuel (worldcup_picks.py)" if book != "self-edge" else "self-edge (no FD/DK player props on Odds API free tier)"
                    result = {
                        "mode": "live", "sport": sport,
                        "matchup": f"{away}@{home}",
                        "away_team": away, "home_team": home,
                        "signal": "WC PROPS LIVE (self-edge)" if book == "self-edge" else "FD PROPS LIVE",
                        "valid_props": valid,
                        "source": f"worldcup_picks.py · {len(props)} players · book: {book}",
                        "roster_counts": {"away": len(props), "home": 0, "away_active": len(props), "home_active": 0},
                        "odds": {"total": None, "ml_source": book},
                    }
                    attach_unified_fields(result, away, home, is_home_court=True,
                                          book_source=book_honest, valid_props=valid)
                    print(json.dumps(result, default=str))
                    return

    # Fallback
    print(json.dumps({"error": f"No data for {sport} {away}@{home}", "sport": sport, "mode": mode}))


if __name__ == "__main__":
    main()
