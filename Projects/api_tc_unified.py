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

# ── World Cup team mappings (module-level so live fallback can access) ──
WC_TEAM_FULL = {
    "ALG": "Algeria", "ARG": "Argentina", "AUS": "Australia", "AUT": "Austria",
    "BEL": "Belgium", "BIH": "Bosnia", "BRA": "Brazil", "CAN": "Canada",
    "CPV": "Cape Verde", "CIV": "Ivory Coast", "COD": "DR Congo", "COL": "Colombia",
    "CRO": "Croatia", "CUW": "Curacao", "CZE": "Czech Republic", "ECU": "Ecuador",
    "EGY": "Egypt", "ENG": "England", "ESP": "Spain", "FRA": "France",
    "GER": "Germany", "GHA": "Ghana", "HAI": "Haiti", "IRN": "Iran",
    "IRQ": "Iraq", "JPN": "Japan", "JOR": "Jordan", "KOR": "South Korea",
    "KSA": "Saudi Arabia", "MAR": "Morocco", "MEX": "Mexico", "NED": "Netherlands",
    "NOR": "Norway", "NZL": "New Zealand", "PAN": "Panama", "PAR": "Paraguay",
    "POR": "Portugal", "QAT": "Qatar", "RSA": "South Africa", "SCO": "Scotland",
    "SEN": "Senegal", "SWE": "Sweden", "SUI": "Switzerland", "TUN": "Tunisia",
    "TUR": "Turkey", "URU": "Uruguay", "USA": "USA", "UZB": "Uzbekistan",
}

def wc_full(name):
    upper = name.strip().upper()
    if upper in WC_TEAM_FULL:
        return WC_TEAM_FULL[upper]
    return name

WC_STAT_MAP = {
    "goals": ("tc_goals", "line_goals", "edge_goals"),
    "assists": ("tc_ast", "line_ast", "edge_ast"),
    "shots": ("tc_shots", "line_shots", "edge_shots"),
    "shots_on_target": ("tc_sot", "line_sot", "edge_sot"),
    "passes": ("tc_passes", "line_passes", "edge_passes"),
    "tackles": ("tc_tackles", "line_tackles", "edge_tackles"),
    "cards": ("tc_yellow_cards", "line_yellow_cards", "edge_yellow_cards"),
    "yellow_cards": ("tc_yellow_cards", "line_yellow_cards", "edge_yellow_cards"),
    "red_cards": ("tc_red_cards", "line_red_cards", "edge_red_cards"),
    "fouls": ("tc_fouls", "line_fouls", "edge_fouls"),
    "corners": ("tc_corners", "line_corners", "edge_corners"),
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
SPORTS = {"WNBA", "MLB", "WORLD CUP", "WORLD_CUP", "SOCCER"}


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


def flatten_player_projections(player):
    """Convert nested {projections: {PTS: {tc_projection, line, edge}}} to flat tc_pts, line_pts, edge_pts etc.
    Also maps 'player' field to 'name' for dashboard compatibility."""
    if not player:
        return player
    if "player" in player and "name" not in player:
        player["name"] = player["player"]
    proj = player.get("projections", {})
    if not proj:
        return player
    STAT_FLAT_MAP = {
        "PTS": ("tc_pts", "line_pts", "edge_pts"),
        "REB": ("tc_reb", "line_reb", "edge_reb"),
        "AST": ("tc_ast", "line_ast", "edge_ast"),
        "3PM": ("tc_3pm", "line_3pm", "edge_3pm"),
        "STL": ("tc_stl", "line_stl", "edge_stl"),
        "BLK": ("tc_blk", "line_blk", "edge_blk"),
    }
    for stat_key, (tc_field, line_field, edge_field) in STAT_FLAT_MAP.items():
        stat_data = proj.get(stat_key, {})
        player[tc_field] = stat_data.get("tc_projection", 0)
        player[line_field] = stat_data.get("line", 0)
        player[edge_field] = stat_data.get("edge", 0)
    return player

def flatten_all_players(data):
    """Flatten all players in away/home roster data."""
    for side in ("away", "home"):
        side_data = data.get(side, {})
        for group in ("all", "starters", "bench"):
            group_data = side_data.get(group, {})
            players = group_data.get("players", [])
            for i, p in enumerate(players):
                players[i] = flatten_player_projections(p)
            group_data["players"] = players
        data[side] = side_data
    return data


def main():
    sport = sys.argv[1] if len(sys.argv) > 1 else "WNBA"
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    away = sys.argv[3] if len(sys.argv) > 3 else ""
    home = sys.argv[4] if len(sys.argv) > 4 else ""
    sport = sport.upper().replace("%20", " ").strip()
    sport = sport.replace("_", " ")  # normalize WORLD_CUP → WORLD CUP

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

        # ESPN label → sport-agnostic canonical key mapping (used by frontend stat config)
        ESPN_LABEL_MAP = {
            # Basketball (WNBA)
            "min": "minutes", "pts": "pts", "fg": "fg", "3pt": "tpm", "ft": "ft",
            "reb": "reb", "ast": "ast", "to": "to", "stl": "stl", "blk": "blk",
            "oreb": "oreb", "dreb": "dreb", "pf": "pf", "+/-": "plusminus",
            # MLB batting
            "ab": "ab", "r": "r", "h": "h", "rbi": "rbi", "hr": "hr",
            "bb": "bb", "k": "so", "avg": "avg", "obp": "obp", "slg": "slg",
            "h-ab": "h_ab", "#p": "pitches",
            # MLB pitching
            "ip": "ip", "er": "er", "era": "era", "pc-st": "pc_st", "pc": "pc",
            # Soccer (if available)
            "goals": "goals", "shots": "shots", "assists": "ast",
            "shots_on_target": "sot", "fouls_committed": "fouls",
            "yellow_cards": "yc", "red_cards": "rc",
        }

        # Per-sport: which stat blocks to include and their "kind" tag
        SPORT_BLOCK_RULES = {
            "WNBA": [{"index": 0, "kind": "player"}],
            "MLB": [{"index": 0, "kind": "batting"}, {"index": 1, "kind": "pitching"}],
            "WORLD CUP": [{"index": 0, "kind": "player"}],
            "SOCCER": [{"index": 0, "kind": "player"}],
        }

        def fetch_boxscore_players(event_id, away_abbr, home_abbr):
            players_list = []
            try:
                r = urllib.request.urlopen(
                    f"https://site.api.espn.com/apis/site/v2/sports/{ep}/summary?event={event_id}",
                    timeout=8
                )
                summary = json.loads(r.read())
                bs_players = (summary.get("boxscore") or {}).get("players", [])
                block_rules = SPORT_BLOCK_RULES.get(sport, [{"index": 0, "kind": "player"}])

                for team_data in bs_players:
                    team_abbr = (team_data.get("team") or {}).get("abbreviation", "")
                    stats_blocks = team_data.get("statistics", [])

                    for rule in block_rules:
                        idx = rule.get("index", 0)
                        kind = rule.get("kind", "player")
                        if idx >= len(stats_blocks):
                            continue
                        stats_block = stats_blocks[idx]
                        labels = stats_block.get("labels", [])
                        athletes = stats_block.get("athletes", [])

                        for athlete_entry in athletes:
                            if athlete_entry.get("didNotPlay"):
                                continue
                            athlete = athlete_entry.get("athlete", {})
                            name = athlete.get("displayName", athlete.get("fullName", "Unknown"))
                            if not name or name == "Unknown":
                                continue

                            raw_stats = athlete_entry.get("stats", [])
                            # Build canonical stat map from ESPN labels
                            stat_map = {}
                            for i, label in enumerate(labels):
                                val = raw_stats[i] if i < len(raw_stats) else "0"
                                try:
                                    parsed = float(val) if "." in str(val) or str(val).replace("-", "").replace("+", "").isdigit() else 0
                                except Exception:
                                    parsed = 0
                                canonical = ESPN_LABEL_MAP.get(label.lower(), label.lower().replace(" ", "_"))
                                stat_map[canonical] = parsed

                            # Minutes: WNBA = "min" label, MLB = use "ab" as proxy for participation
                            minutes_val = stat_map.get("minutes", 0)
                            if minutes_val == 0 and kind == "batting":
                                minutes_val = stat_map.get("ab", 0)  # plate appearances proxy

                            # Build actual dict with all canonical keys
                            actual = {}
                            for canon_key, canon_val in stat_map.items():
                                actual[canon_key] = canon_val

                            # Ensure commonly-expected keys exist at top level
                            actual["pts"] = actual.get("pts", 0)
                            actual["reb"] = actual.get("reb", 0)
                            actual["ast"] = actual.get("ast", 0)
                            actual["tpm"] = actual.get("tpm", 0)
                            actual["stl"] = actual.get("stl", 0)
                            actual["blk"] = actual.get("blk", 0)
                            # MLB-specific top-level
                            actual["h"] = actual.get("h", 0)
                            actual["hr"] = actual.get("hr", 0)
                            actual["rbi"] = actual.get("rbi", 0)
                            actual["r"] = actual.get("r", 0)
                            actual["sb"] = actual.get("sb", 0)
                            actual["avg"] = actual.get("avg", 0)
                            actual["so"] = actual.get("so", 0)

                            is_starter = athlete_entry.get("starter", False)
                            role = "START" if is_starter else ("BULLPEN" if kind == "pitching" else "BENCH")

                            players_list.append({
                                "name": name,
                                "team": team_abbr,
                                "role": role,
                                "kind": kind,
                                "minutes": minutes_val,
                                "starter": is_starter,
                                "actual": actual,
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
                flatten_all_players(data)  # convert nested projections -> flat tc_pts, etc
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

            flatten_all_players(data)  # nested proj -> flat fields after roster merge
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
    # PATH 1: legacy Daily_Log/worldcup/YYYY-MM-DD/matches.json
    # PATH 2: current Daily_Log/YYYY-MM-DD/soccer_player_picks.csv (from daily_picks.py)
    if sport in ("WORLD CUP", "SOCCER") and away and home:
        props_path = None
        # Search all worldcup date dirs + daily log dirs, newest first
        wc_base = WORKSPACE / "Daily_Log" / "worldcup"
        daily_base = WORKSPACE / "Daily_Log"

        def find_date_dirs(base):
            dirs = []
            try:
                for d in base.iterdir():
                    if d.is_dir() and (d.name.startswith("20")):
                        dirs.append(d.name)
            except Exception:
                pass
            return dirs

        all_dirs = sorted(
            set(find_date_dirs(wc_base) + find_date_dirs(daily_base)),
            reverse=True
        )

        # PATH 1: Search for worldcup matches.json (separate pass — don't block CSV search)
        for date_dir in [today, yesterday] + all_dirs:
            date_compact = date_dir.replace("-", "")
            p = wc_base / date_dir / "matches.json"
            if not p.exists():
                p = wc_base / date_compact / "matches.json"
            if p.exists():
                props_path = p
                break

        # Build CSV candidates (independent of PATH 1 search)
        csv_candidates = []
        seen_csv = set()
        for date_dir in [today, yesterday] + all_dirs:
            date_compact = date_dir.replace("-", "")
            cp = daily_base / date_dir / "soccer_player_picks.csv"
            if not cp.exists():
                cp = daily_base / date_compact / "soccer_player_picks.csv"
            if cp.exists() and str(cp) not in seen_csv:
                seen_csv.add(str(cp))
                pp = daily_base / date_dir / f"proj_WORLD CUP_{away}_at_{home}.json"
                if not pp.exists():
                    pp = daily_base / date_compact / f"proj_WORLD CUP_{away}_at_{home}.json"
                if not pp.exists():
                    pp = daily_base / date_dir / f"proj_WORLD CUP_{home}_at_{away}.json"
                if not pp.exists():
                    pp = daily_base / date_compact / f"proj_WORLD CUP_{home}_at_{away}.json"
                csv_candidates.append((cp, pp if pp.exists() else None))
        if props_path:
            props_data = json.loads(props_path.read_text())
            matches = props_data if isinstance(props_data, list) else props_data.get("matches", [])

            for m in matches:
                teams = m.get("teams", [])
                a_abbr = next((t.get("abbrev", "").upper() for t in teams if t.get("homeAway") == "away"), "")
                h_abbr = next((t.get("abbrev", "").upper() for t in teams if t.get("homeAway") == "home"), "")
                if (a_abbr == away.upper() and h_abbr == home.upper()) or (a_abbr == home.upper() and h_abbr == away.upper()):
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
                    
                    away_players = []
                    home_players = []
                    for pname, stats in props.items():
                        player = {"name": pname, "team": away, "pos": "—", "role": "START", "status": "ACTIVE", "min": 90}
                        # Init all soccer flat fields to 0
                        for _, (tc_f, ln_f, eg_f) in WC_STAT_MAP.items():
                            player[tc_f] = 0; player[ln_f] = 0; player[eg_f] = 0
                        for st, info in stats.items():
                            st_lower = st.lower()
                            line_val = info.get("line", 0) or 0
                            if st_lower in WC_STAT_MAP:
                                tc_f, ln_f, eg_f = WC_STAT_MAP[st_lower]
                                edge_val = round(line_val * 0.12, 1)
                                player[tc_f] = round(float(line_val) + edge_val, 1)
                                player[ln_f] = float(line_val)
                                player[eg_f] = edge_val
                        away_players.append(player)
                        home_p = dict(player)
                        home_p["team"] = home
                        home_players.append(home_p)
                    
                    result = {
                        "mode": "live", "sport": sport,
                        "matchup": f"{away}@{home}",
                        "away_team": away, "home_team": home,
                        "signal": "WC PROPS LIVE (self-edge)" if book == "self-edge" else "FD PROPS LIVE",
                        "valid_props": valid,
                        "source": f"worldcup_picks.py · {len(props)} players · book: {book}",
                        "roster_counts": {"away": len(props), "home": len(props), "away_active": len(props), "home_active": len(props)},
                        "odds": {"total": None, "ml_source": book},
                        "away": {"all": {"players": away_players}, "starters": {"players": away_players}, "bench": {"players": []}},
                        "home": {"all": {"players": home_players}, "starters": {"players": home_players}, "bench": {"players": []}},
                    }
                    attach_unified_fields(result, away, home, is_home_court=True,
                                          book_source=book_honest, valid_props=valid)
                    print(json.dumps(result, default=str))
                    return

        # CSV stat abbrev → key in WC_STAT_MAP
        CSV_STAT_MAP = {
            "G": "goals", "A": "assists", "S": "shots", "SOT": "shots_on_target",
            "COR": "corners", "TKL": "tackles", "FC": "fouls", "CRD": "yellow_cards",
            "PAS": "passes",
        }

        away_full = wc_full(away)
        home_full = wc_full(home)

        # PATH 2: Try each CSV candidate (newest first) for this matchup
        import csv as csvmod
        for csv_try, pp_try in csv_candidates:
            players_by_team = {}
            with open(csv_try) as f:
                reader = csvmod.DictReader(f)
                for row in reader:
                    mup = row.get("matchup", "")
                    mup_clean = mup.replace(" ", "")
                    target1 = f"{away_full}@{home_full}".replace(" ", "")
                    target2 = f"{home_full}@{away_full}".replace(" ", "")
                    if mup_clean != target1 and mup_clean != target2:
                        continue
                    pname = row.get("player", "").strip()
                    team = row.get("team", "").strip()
                    pos = row.get("position", "").strip()
                    is_starter = row.get("is_starter", "").strip().lower() == "true"
                    stat_abbr = row.get("stat", "").strip()
                    tc_proj = float(row.get("tc_projection", 0) or 0)
                    tc_line_val = float(row.get("tc_line", 0) or 0)
                    edge_val = float(row.get("edge", 0) or 0)
                    
                    key = f"{pname}||{team}"
                    if key not in players_by_team:
                        players_by_team[key] = {
                            "name": pname, "team": team, "pos": pos,
                            "role": "START" if is_starter else "BENCH",
                            "status": "ACTIVE", "min": 90,
                        }
                        for _, (tc_f, ln_f, eg_f) in WC_STAT_MAP.items():
                            players_by_team[key][tc_f] = 0
                            players_by_team[key][ln_f] = 0
                            players_by_team[key][eg_f] = 0
                    
                    field_key = CSV_STAT_MAP.get(stat_abbr)
                    if field_key and field_key in WC_STAT_MAP:
                        tc_f, ln_f, eg_f = WC_STAT_MAP[field_key]
                        players_by_team[key][tc_f] = tc_proj
                        players_by_team[key][ln_f] = tc_line_val
                        players_by_team[key][eg_f] = edge_val
            
            if players_by_team:
                away_players = [p for p in players_by_team.values() if p["team"].upper() == away_full.upper()]
                home_players = [p for p in players_by_team.values() if p["team"].upper() == home_full.upper()]
                
                h2h_sig = "N/A"
                totals_sig = "N/A"
                if pp_try and pp_try.exists():
                    try:
                        pdata = json.loads(pp_try.read_text())
                        h2h_sig = pdata.get("h2h_signal", h2h_sig)
                        totals_sig = pdata.get("totals_signal", totals_sig)
                    except:
                        pass
                
                result = {
                    "mode": "live", "sport": sport,
                    "matchup": f"{away}@{home}",
                    "away_team": away, "home_team": home,
                    "signal": f"H2H:{h2h_sig} TOTALS:{totals_sig}",
                    "valid_props": [],
                    "source": f"daily_picks.py CSV · {len(away_players)+len(home_players)} players",
                    "roster_counts": {
                        "away": len(away_players), "home": len(home_players),
                        "away_active": len(away_players), "home_active": len(home_players),
                    },
                    "odds": {"total": None, "ml_source": "self-edge (daily_picks.py)"},
                    "away": {"all": {"players": away_players}, "starters": {"players": [p for p in away_players if p["role"]=="START"]}, "bench": {"players": [p for p in away_players if p["role"]!="START"]}},
                    "home": {"all": {"players": home_players}, "starters": {"players": [p for p in home_players if p["role"]=="START"]}, "bench": {"players": [p for p in home_players if p["role"]!="START"]}},
                }
                attach_unified_fields(result, away, home, is_home_court=True,
                                      book_source="self-edge (daily_picks.py)", valid_props=[])
                print(json.dumps(result, default=str))
                return

        # PATH 3: Try each CSV's proj file for game-level signals (no player props)
        for csv_try, pp_try in csv_candidates:
            if pp_try and pp_try.exists():
                try:
                    pdata = json.loads(pp_try.read_text())
                except:
                    pdata = {}
                result = {
                    "mode": "live", "sport": sport,
                    "matchup": f"{away}@{home}",
                    "away_team": away, "home_team": home,
                    "signal": f"H2H:{pdata.get('h2h_signal','N/A')} TOTALS:{pdata.get('totals_signal','N/A')}",
                    "valid_props": [],
                    "source": f"daily_picks.py proj · {pdata.get('starter_projections','N/A')} starter projs · game-level only, no player props",
                    "away": {"all": {"players": []}, "starters": {"players": []}, "bench": {"players": []}},
                    "home": {"all": {"players": []}, "starters": {"players": []}, "bench": {"players": []}},
                    "roster_counts": {"away": 0, "home": 0},
                    "odds": {"total": None, "ml_source": "self-edge"},
                }
                attach_unified_fields(result, away, home, is_home_court=True,
                                      book_source="self-edge", valid_props=[])
                print(json.dumps(result, default=str))
                return

    # ── WORLD CUP LIVE FALLBACK: generate projections on-the-fly ──
    if sport in ("WORLD CUP", "SOCCER") and away and home:
        try:
            from soccer_tc_engine import generate_default_squad, project_player_stats, get_team_strength
            away_full_name = wc_full(away)
            home_full_name = wc_full(home)
            away_str = get_team_strength(away_full_name)
            home_str = get_team_strength(home_full_name)

            away_all = []
            home_all = []
            now = datetime.now(timezone.utc)
            date_str = now.strftime("%Y-%m-%d")
            matchup = f"{away}@{home}"

            for team_name, is_home, team_str, opp_str in [
                (home_full_name, True, home_str, away_str),
                (away_full_name, False, away_str, home_str),
            ]:
                squad = generate_default_squad(team_name)
                for player in squad:
                    projs = project_player_stats(
                        player=player,
                        team_strength=team_str,
                        opponent_strength=opp_str,
                        is_home=is_home,
                    )
                    for p in projs:
                        player_obj = {
                            "name": player.get("name", "Unknown"),
                            "team": team_name,
                            "pos": player.get("position", "—"),
                            "role": "START" if player.get("is_starter", False) else "BENCH",
                            "status": "ACTIVE",
                            "min": 90,
                        }
                        stat_key = p.get("stat", "").lower()
                        if stat_key in WC_STAT_MAP:
                            tc_f, ln_f, eg_f = WC_STAT_MAP[stat_key]
                            player_obj[tc_f] = p.get("tc_projection", 0)
                            player_obj[ln_f] = p.get("tc_line", 0)
                            player_obj[eg_f] = p.get("edge", 0)
                        if is_home:
                            home_all.append(player_obj)
                        else:
                            away_all.append(player_obj)

            # Deduplicate players (merge stats across stat types)
            def merge_players(plist, team_name):
                merged = {}
                for p in plist:
                    key = p["name"]
                    if key not in merged:
                        merged[key] = {
                            "name": p["name"], "team": team_name, "pos": p["pos"],
                            "role": p["role"], "status": p["status"], "min": 90,
                        }
                        for _, (tc_f, ln_f, eg_f) in WC_STAT_MAP.items():
                            merged[key][tc_f] = 0
                            merged[key][ln_f] = 0
                            merged[key][eg_f] = 0
                    for _, (tc_f, ln_f, eg_f) in WC_STAT_MAP.items():
                        if p.get(tc_f):
                            merged[key][tc_f] = p[tc_f]
                        if p.get(ln_f):
                            merged[key][ln_f] = p[ln_f]
                        if p.get(eg_f):
                            merged[key][eg_f] = p[eg_f]
                return list(merged.values())

            away_players = merge_players(away_all, away_full_name)
            home_players = merge_players(home_all, home_full_name)

            result = {
                "mode": "live", "sport": sport,
                "matchup": matchup,
                "away_team": away, "home_team": home,
                "signal": "LIVE GENERATED (self-edge, no odds lines)",
                "valid_props": [],
                "source": f"soccer_tc_engine live · {len(away_players)+len(home_players)} players · self-edge (no DK lines available)",
                "roster_counts": {
                    "away": len(away_players), "home": len(home_players),
                    "away_active": len(away_players), "home_active": len(home_players),
                },
                "odds": {"total": None, "ml_source": "self-edge"},
                "away": {"all": {"players": away_players}, "starters": {"players": [p for p in away_players if p["role"]=="START"]}, "bench": {"players": [p for p in away_players if p["role"]!="START"]}},
                "home": {"all": {"players": home_players}, "starters": {"players": [p for p in home_players if p["role"]=="START"]}, "bench": {"players": [p for p in home_players if p["role"]!="START"]}},
            }
            attach_unified_fields(result, away, home, is_home_court=True,
                                  book_source="self-edge", valid_props=[])
            print(json.dumps(result, default=str))
            return
        except Exception as e:
            print(f"WC LIVE FALLBACK FAILED: {e}", file=sys.stderr)

    # Fallback
    print(json.dumps({"error": f"No data for {sport} {away}@{home}", "sport": sport, "mode": mode}))


if __name__ == "__main__":
    main()
