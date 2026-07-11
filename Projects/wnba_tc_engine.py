#!/usr/bin/env python3
# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
WNBA TC Engine v2.0 — Core API-only projections.
ESPN Core API (sports.core.api.espn.com) — reliable, no auth.
Site API (site.api.espn.com) — skipped due to intermittent timeouts.
"""
import json, os, sys, argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import socket; socket.setdefaulttimeout(8)  # prevent per-athlete API calls from hanging
from tc_math import sport_over_under_signal

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"

EDGE_THRESH = 0.5
LINE_FACTOR = 0.88
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
DEFAULT_MINUTES = 25.0

STAT_ESPN_MAP = {
    "PTS": "avgPoints", "REB": "avgRebounds", "AST": "avgAssists",
    "3PM": "avgThreePointFieldGoalsMade", "STL": "avgSteals",
    "BLK": "avgBlocks", "MIN": "avgMinutes",
}

WNBA_TEAMS = {
    "ATL": 20, "CHI": 19, "CON": 18, "DAL": 3, "GS": 129689,
    "IND": 5, "LV": 17, "LA": 6, "MIN": 8, "NY": 9,
    "PHX": 11, "POR": 132052, "SEA": 14, "TOR": 131935, "WSH": 16,
}

WNBA_ABBREV = {
    "ATL": "Atlanta Dream", "CHI": "Chicago Sky", "CON": "Connecticut Sun",
    "DAL": "Dallas Wings", "GS": "Golden State Valkyries", "IND": "Indiana Fever",
    "LV": "Las Vegas Aces", "LA": "Los Angeles Sparks", "MIN": "Minnesota Lynx",
    "NY": "New York Liberty", "PHX": "Phoenix Mercury", "POR": "Portland Fire",
    "SEA": "Seattle Storm", "TOR": "Toronto Tempo", "WSH": "Washington Mystics",
}

WNBA_TEAM_IDS_REVERSE = {v: k for k, v in WNBA_TEAMS.items()}

SEASON_CACHE = {}

# ---------------------------------------------------------------------------
# INJURY FEED — single source of truth for OUT/QUESTIONABLE/ACTIVE per player.
# Loaded from ESPN site API per-slate + on-disk cache for the day.
# Cached for 1 hour per slate to avoid hammering during a run.
# ---------------------------------------------------------------------------
INJURY_CACHE = {}      # {date_str: {name_lower: "ACTIVE"|"OUT"|"QUESTIONABLE"|"PROBABLE"}}
INJURY_TTL = 3600      # seconds

def _injury_cache_path(date_str: str) -> Path:
    d = LOG_DIR / date_str
    d.mkdir(parents=True, exist_ok=True)
    return d / "wnba_injuries.json"


def _fetch_team_roster_injuries(team_abbr: str, timeout: int = 5) -> dict:
    """Pull injury/roster status for one WNBA team via ESPN site API.
    Returns {name_lower: status_str}. Returns {} on any error."""
    import urllib.request
    team_id = WNBA_TEAMS.get(team_abbr)
    if not team_id:
        return {}
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{team_id}/roster"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return {}
    out = {}
    # Roster endpoint doesn't always include status — fall back to default ACTIVE
    for grp in (data.get("athlete") or []):
        for ath in (grp.get("items") or []):
            name = ath.get("displayName") or ath.get("fullName") or ""
            if not name:
                continue
            inj = ath.get("injuries") or []
            status = "ACTIVE"
            if inj:
                # ESPN shape: injuries[0].status (e.g., "Out", "Questionable", "Probable")
                s = (inj[0].get("status") or "").strip().lower()
                if s in ("out", "injured", "doubtful"):
                    status = "OUT"
                elif s in ("questionable", "day-to-day", "day to day"):
                    status = "QUESTIONABLE"
                elif s in ("probable",):
                    status = "PROBABLE"
            out[name.lower()] = status
    return out


def load_injury_report(date_str: str = None, force: bool = False) -> dict:
    """Return {name_lower: status} for every WNBA player on the current slate.
    Merges per-team rosters; cached on disk for INJURY_TTL seconds.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    if not force and date_str in INJURY_CACHE:
        return INJURY_CACHE[date_str]

    cache_file = _injury_cache_path(date_str)
    if not force and cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < INJURY_TTL:
            try:
                merged = json.loads(cache_file.read_text())
                INJURY_CACHE[date_str] = merged
                return merged
            except Exception:
                pass

    merged = {}
    for abbr in WNBA_TEAMS.keys():
        try:
            merged.update(_fetch_team_roster_injuries(abbr))
        except Exception:
            continue
    # Also load a manual override file if it exists (used for late scratches the
    # ESPN feed doesn't yet show — Costanza Verona (DAL) was the original case).
    override_file = LOG_DIR / date_str / "wnba_injury_overrides.json"
    if override_file.exists():
        try:
            for name, status in json.loads(override_file.read_text()).items():
                merged[name.lower()] = status
        except Exception:
            pass

    try:
        cache_file.write_text(json.dumps(merged, indent=2, sort_keys=True))
    except Exception:
        pass
    INJURY_CACHE[date_str] = merged
    return merged


def status_for(name: str, injuries: dict) -> str:
    """Lookup a player's status from the injury report. Default ACTIVE."""
    if not name or not injuries:
        return "ACTIVE"
    return injuries.get(name.lower(), "ACTIVE")


# ---------------------------------------------------------------------------
# INJURY FEED — single source of truth for OUT/QUESTIONABLE/ACTIVE per player.
# Loaded from ESPN site API per-slate + on-disk cache for the day.
# Without this, every player was hardcoded ACTIVE and OUT picks leaked through
# (Verona bug — fixed 2026-07-02). Keys are lowercased full names.
# ---------------------------------------------------------------------------
INJURY_CACHE: dict = {}


def load_secrets():
    sf = Path("/root/.zo/secrets.env")
    if sf.exists():
        for line in sf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

def _fetch(url: str, timeout: int = 10) -> dict:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}

def fetch_all_season_stats(limit: int = 150) -> dict:
    """Fetch season stats for top players via Core API leaders. Returns {name_lower: {stats...}}."""
    cache_key = f"all_leaders_{limit}"
    now_ts = datetime.now().timestamp()
    if cache_key in SEASON_CACHE:
        entry = SEASON_CACHE[cache_key]
        if now_ts - entry.get("_ts", 0) < 18000:
            return entry

    result = {"_ts": now_ts}
    categories = [
        {"name": "pointsPerGame", "stats": ["avgPoints", "avgMinutes", "avgRebounds",
            "avgAssists", "avgThreePointFieldGoalsMade", "avgSteals", "avgBlocks"]},
        {"name": "reboundsPerGame", "stats": ["avgRebounds", "avgMinutes"]},
        {"name": "assistsPerGame", "stats": ["avgAssists", "avgMinutes"]},
        {"name": "stealsPerGame", "stats": ["avgSteals", "avgMinutes"]},
        {"name": "blocksPerGame", "stats": ["avgBlocks", "avgMinutes"]},
    ]

    leader_url = (f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/"
                  f"seasons/2026/types/2/leaders?limit={limit}")
    
    try:
        data = _fetch(leader_url, timeout=12)
        if data.get("_error"):
            return result

        # Phase 1: collect unique athlete IDs across all categories
        athlete_refs = {}  # athlete_id -> (ath_ref, team_abbr)
        for cat in data.get("categories", []):
            for leader in cat.get("leaders", []):
                ath_ref = leader.get("athlete", {}).get("$ref", "")
                athlete_id = int(ath_ref.split("/")[-1].split("?")[0]) if ath_ref else None
                if not athlete_id:
                    continue
                team_ref = leader.get("team", {}).get("$ref", "")
                team_id = int(team_ref.split("/")[-1].split("?")[0]) if team_ref else None
                team_abbr = WNBA_TEAM_IDS_REVERSE.get(team_id, "")
                if athlete_id not in athlete_refs:
                    athlete_refs[athlete_id] = (ath_ref, team_abbr)

        # Phase 2: fetch stats + name for each unique athlete in parallel
        import threading
        _result_lock = threading.Lock()
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_one(athlete_id, ath_ref, team_abbr):
            stats_url = (f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/"
                         f"seasons/2026/types/2/athletes/{athlete_id}/statistics/0?lang=en&region=us")
            stats_data = _fetch(stats_url, timeout=4)
            if stats_data.get("_error"):
                return None
            ath_data = _fetch(ath_ref, timeout=4) if ath_ref else {}
            name = ath_data.get("displayName", ath_data.get("fullName", f"id_{athlete_id}"))
            name_lower = name.lower()

            if name_lower not in result:
                result[name_lower] = {"name": name, "team": team_abbr, "team_id": WNBA_TEAMS.get(team_abbr)}

            splits = stats_data.get("splits", {}).get("categories", [])
            for sc in splits:
                for s in sc.get("stats", []):
                    sname = s.get("name", "")
                    sval = s.get("value", 0)
                    if isinstance(sval, (int, float)) and sval > 0:
                        result[name_lower][sname] = float(sval)

            return result[name_lower]

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_one, athlete_id, ath_ref, team_abbr): athlete_id for athlete_id, (ath_ref, team_abbr) in athlete_refs.items()}
            for future in as_completed(futures):
                pass  # results are mutated in-place

        SEASON_CACHE[cache_key] = result
        return result
    except Exception as e:
        return {"_ts": now_ts, "_error": str(e)}


def compute_tc_projection(season_stats: dict, stat_key: str, player_minutes: float, status: str) -> float:
    espn_key = STAT_ESPN_MAP.get(stat_key, "")
    mpg_key = STAT_ESPN_MAP.get("MIN", "avgMinutes")
    
    season_avg = season_stats.get(espn_key, 0.0)
    season_mpg = season_stats.get(mpg_key, DEFAULT_MINUTES)
    
    if season_avg == 0.0 and stat_key == "PTS":
        season_avg = season_stats.get("avgPoints", 0.0)
    
    if season_mpg > 0 and season_avg > 0:
        per_36 = season_avg * (36.0 / season_mpg)
    else:
        per_36 = season_avg
    
    exp_minutes = min(player_minutes if player_minutes > 0 else season_mpg, 40.0)
    minutes_factor = exp_minutes / 36.0
    
    status_upper = (status or "ACTIVE").upper()
    if status_upper == "ACTIVE":
        status_factor = 1.0
    elif status_upper in ("QUESTIONABLE", "Q", "DOUBTFUL"):
        status_factor = Q_FACTOR
    elif status_upper in ("OUT", "INJURED", "DNP"):
        status_factor = OUT_FACTOR
    else:
        status_factor = 1.0
    
    tc = per_36 * minutes_factor * status_factor
    return round(tc, 1)


def _fetch_dk_lines_with_fallback(away: str, home: str) -> tuple:
    """Fetch DraftKings lines: ESPN site API first, OddsAPI as fallback.

    Returns: (dk_total, dk_spread, dk_ml_home, dk_ml_away, ml_source)
    """
    # 1. ESPN site API — embedded DK odds (provider.id == "100")
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
        data = _fetch(url, timeout=4)
        if not data.get("_error"):
            for ev in data.get("events", []):
                comp = (ev.get("competitions") or [{}])[0]
                comps = comp.get("competitors", [])
                a_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "away"), "")
                h_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "home"), "")
                if a_team != away.upper() and h_team != home.upper():
                    continue
                odds_list = comp.get("odds", []) or []
                dk_odds = next((o for o in odds_list if (o.get("provider", {}) or {}).get("id") == "100" or (o.get("provider", {}) or {}).get("name") == "DraftKings"), None)
                if dk_odds:
                    ml = dk_odds.get("moneyline", {}) or {}
                    return (
                        dk_odds.get("overUnder"),
                        dk_odds.get("spread"),
                        ml.get("home", {}).get("close", {}).get("odds"),
                        ml.get("away", {}).get("close", {}).get("odds"),
                        "ESPN DraftKings embedded",
                    )
    except Exception:
        pass

    # 2. OddsAPI fallback (events with book=draftkings)
    try:
        key = os.environ.get("ODDS_API_KEY", "")
        if not key:
            return (None, None, None, None, "ESPN Core API (self-edge)")
        url = f"https://api.theoddsapi.com/odds/?sport_key=basketball_wnba&regions=us&markets=h2h,spreads,totals&bookmakers=draftkings&apiKey={key}"
        data = _fetch(url, timeout=4)
        if data.get("_error"):
            return (None, None, None, None, "ESPN Core API (self-edge)")
        # Map full team names to ESPN abbreviations
        # "Atlanta Dream" -> "ATL", "Washington Mystics" -> "WSH"
        def team_to_abbr(full: str) -> str:
            if not full: return ""
            for abbr, name in WNBA_ABBREV.items():
                if full.lower() == name.lower() or full.lower().startswith(name.lower().split()[-1].lower()):
                    return abbr
            return ""
        for ev in data.get("data", []):
            at_abbr = team_to_abbr(ev.get("away_team") or "")
            ht_abbr = team_to_abbr(ev.get("home_team") or "")
            if at_abbr != away.upper() and ht_abbr != home.upper():
                continue
            dk_total = dk_spread = dk_ml_home = dk_ml_away = None
            for book in ev.get("books", []):
                if book.get("book") != "draftkings":
                    continue
                market = book.get("market")
                for oc in book.get("outcomes", []):
                    price = oc.get("price")
                    point = oc.get("point")
                    if market == "totals":
                        if price is not None and (oc.get("name") or "").lower() == "over":
                            dk_total = point
                    elif market == "spreads":
                        if price is not None:
                            n = (oc.get("name") or "").lower()
                            if home.lower() in n or ht_abbr.lower() in n or away.lower() in n:
                                dk_spread = point
                    elif market == "h2h":
                        n = (oc.get("name") or "").lower()
                        # Check by last word of team name OR abbr — must match HOME exactly
                        if WNBA_ABBREV.get(home).lower() in n or ht_abbr.lower() in n:
                            dk_ml_home = price
                        elif away.lower() in n or at_abbr.lower() in n:
                            dk_ml_away = price
            return (dk_total, dk_spread, dk_ml_home, dk_ml_away, "OddsAPI DraftKings")
    except Exception:
        pass

    return (None, None, None, None, "ESPN Core API (self-edge)")


def compute_line_and_edge(tc_projection: float) -> Tuple[float, float, str, float]:
    line = max(0.5, round(tc_projection * 0.88, 1))
    direction, edge_pct = sport_over_under_signal(
        projection=tc_projection,
        market_line=line,
        sport="WNBA",
    )
    edge_abs = round(tc_projection - line, 1)
    return line, edge_abs, direction, edge_pct


def project_game(away: str, home: str) -> dict:
    """Full TC projection using Core API season stats only (no site API dependency)."""
    load_secrets()
    away = away.upper()
    home = home.upper()

    # Fetch season stats for all players
    all_stats = fetch_all_season_stats(150)

    # Fetch injury report — single source of truth for ACTIVE/OUT/QUESTIONABLE
    injuries = load_injury_report()

    # Filter players by team
    away_players = []
    home_players = []
    for name_lower, sinfo in all_stats.items():
        if name_lower.startswith("_"):
            continue
        team = sinfo.get("team", "")
        if team == away:
            pname = sinfo.get("name", name_lower.title())
            away_players.append({
                "name": pname,
                "player": pname,
                "team": team,
                "role": "BENCH",
                "status": status_for(pname, injuries),
                "pos": "",
                "min": DEFAULT_MINUTES,
                "avgMinutes": float(sinfo.get("avgMinutes") or 0),
                "season_stats": sinfo,
            })
        elif team == home:
            pname = sinfo.get("name", name_lower.title())
            home_players.append({
                "name": pname,
                "player": pname,
                "team": team,
                "role": "BENCH",
                "status": status_for(pname, injuries),
                "pos": "",
                "min": DEFAULT_MINUTES,
                "avgMinutes": float(sinfo.get("avgMinutes") or 0),
                "season_stats": sinfo,
            })

    # Real starter detection: ESPN lineup data first, minutes-based fallback otherwise.
    from starter_detector import detect_starters
    detect_starters(away_players, away, event_id=None, sport="basketball/wnba", starter_cap=5)
    detect_starters(home_players, home, event_id=None, sport="basketball/wnba", starter_cap=5)

    # Compute projections
    away_proj, home_proj = [], []
    valid_props = []
    
    for p in away_players:
        proj = _project_one(p)
        away_proj.append(proj)
        valid_props.extend(_extract_valid(proj, away))
    
    for p in home_players:
        proj = _project_one(p)
        home_proj.append(proj)
        valid_props.extend(_extract_valid(proj, home))
    
    total_props = len(valid_props)
    over_count = sum(1 for vp in valid_props if vp.get("direction") == "OVER")
    signal = "OVER" if over_count > total_props / 2 else ("UNDER" if total_props > 0 else "ROSTER LOADED")

    # DK lines — ESPN site API first, OddsAPI fallback
    dk_total, dk_spread, dk_ml_home, dk_ml_away, ml_source = _fetch_dk_lines_with_fallback(away, home)

    return {
        "mode": "live", "sport": "WNBA",
        "matchup": f"{away}@{home}",
        "away_team": away, "home_team": home,
        "source": "ESPN Core API (self-edge)" if ml_source == "ESPN Core API (self-edge)" else f"ESPN + OddsAPI fallback ({ml_source})",
        "signal": signal,
        "dk_total": dk_total,
        "odds": {"total": dk_total, "spread": dk_spread, "ml_home": dk_ml_home, "ml_away": dk_ml_away, "ml_source": ml_source},
        "away": {
            "all": {"players": away_proj},
            "starters": {"players": [p for p in away_proj if p.get("role") == "START"]},
            "bench": {"players": [p for p in away_proj if p.get("role") != "START"]},
        },
        "home": {
            "all": {"players": home_proj},
            "starters": {"players": [p for p in home_proj if p.get("role") == "START"]},
            "bench": {"players": [p for p in home_proj if p.get("role") != "START"]},
        },
        "roster_counts": {"away": len(away_proj), "home": len(home_proj)},
        "valid_props": valid_props,
    }


def _project_one(player_info: dict) -> dict:
    season = player_info.get("season_stats", {})
    proj = {
        "player": player_info["name"],
        "team": player_info.get("team", ""),
        "role": player_info.get("role", "BENCH"),
        "status": player_info.get("status", "ACTIVE"),
        "pos": player_info.get("pos", ""),
        "projections": {},
    }

    # OUT players: zero projections, no valid props. The injury report is the
    # source of truth; compute_tc_projection's OUT logic is a backstop but we
    # also short-circuit here so the player never enters valid_props.
    if (proj["status"] or "ACTIVE").upper() == "OUT":
        for stat_key in ("PTS", "REB", "AST", "3PM", "STL", "BLK"):
            proj["projections"][stat_key] = {
                "tc_projection": 0.0, "line": 0.0, "edge": 0.0,
                "direction": "PASS", "dk_line": None, "valid": False,
            }
        return proj

    for stat_key in ("PTS", "REB", "AST", "3PM", "STL", "BLK"):
        tc = compute_tc_projection(season, stat_key, player_info.get("min", DEFAULT_MINUTES), player_info.get("status", "ACTIVE"))
        line, edge, direction, edge_pct = compute_line_and_edge(tc)
        proj["projections"][stat_key] = {
            "tc_projection": tc, "line": line, "edge": edge,
            "direction": direction, "dk_line": None,
            "valid": abs(edge) >= EDGE_THRESH,
        }
    return proj


def _extract_valid(proj: dict, team: str) -> list:
    """Filter to valid props. OUT players produce no entries (proj.valid=False)."""
    props = []
    # Defense-in-depth: never let an OUT player produce a pick, even if the
    # caller forgot to skip them. (Was the Costanza Verona (DAL) bug.)
    if (proj.get("status") or "ACTIVE").upper() == "OUT":
        return props
    for sk, pd in proj.get("projections", {}).items():
        if pd.get("valid"):
            props.append({
                "player": proj["player"], "team": team, "stat": sk,
                "direction": pd["direction"], "market_line": pd["line"],
                "tc_projection": pd["tc_projection"], "tc_target": pd["line"],
                "edge": pd["edge"], "threshold": EDGE_THRESH,
                "raw_average": pd["tc_projection"],
                "source": "ESPN Core API (self-edge)",
                "status": proj.get("status", "ACTIVE"),
                "role": proj.get("role", "BENCH"),
            })
    return props


def _fetch_espn_odds_for_event(event_id: str) -> dict:
    """Fetch DraftKings moneyline/spread/total from ESPN's dedicated odds endpoint.

    URL shape: /v2/sports/{sport}/leagues/{league}/events/{id}/competitions/{id}/odds
    Returns: {items: [{provider, overUnder, spread, homeTeamOdds, awayTeamOdds, ...}]}
    We pick DraftKings (provider.id=100), extract ml_home, ml_away, spread, total.
    """
    if not event_id:
        return {"ml_home": None, "ml_away": None, "dk_spread": None, "dk_total": None, "source": "none"}
    url = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/events/{event_id}/competitions/{event_id}/odds"
    data = _fetch(url, timeout=4)
    if data.get("_error"):
        return {"ml_home": None, "ml_away": None, "dk_spread": None, "dk_total": None, "source": "none"}
    items = (data.get("items") or [])
    if not items:
        return {"ml_home": None, "ml_away": None, "dk_spread": None, "dk_total": None, "source": "none"}
    pick = next((o for o in items if (o.get("provider") or {}).get("name", "").lower() == "draftkings"), items[0])
    provider_name = (pick.get("provider") or {}).get("name", "")
    out = {"ml_home": None, "ml_away": None, "dk_spread": None, "dk_total": None, "source": provider_name}
    for side_key, ml_key in (("homeTeamOdds", "ml_home"), ("awayTeamOdds", "ml_away")):
        side = pick.get(side_key) or {}
        ml = side.get("moneyLine")
        if ml is not None:
            try: out[ml_key] = int(ml)
            except (TypeError, ValueError): pass
    sp = pick.get("spread")
    if sp is not None:
        try: out["dk_spread"] = float(sp)
        except (TypeError, ValueError): pass
    tot = pick.get("overUnder")
    if tot is not None:
        try: out["dk_total"] = float(tot)
        except (TypeError, ValueError): pass
    return out


def get_today_slate() -> list:
    """Get today's WNBA slate. Uses Core API if site API times out."""
    data = _fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard", timeout=4)
    if data.get("_error"):
        return []
    games = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions", []) or [{}])[0]
        teams = comp.get("competitors", [])
        a = next((t for t in teams if t.get("homeAway") == "away"), {})
        h = next((t for t in teams if t.get("homeAway") == "home"), {})
        a_abbr = (a.get("team") or {}).get("abbreviation", "")
        h_abbr = (h.get("team") or {}).get("abbreviation", "")
        status = (ev.get("status") or {}).get("type", {}).get("description", "")
        completed = (ev.get("status") or {}).get("type", {}).get("completed", False)
        odds = _fetch_espn_odds_for_event(ev.get("id"))
        games.append({
            "away": a_abbr, "home": h_abbr, "status": status,
            "completed": completed, "event_id": ev.get("id"),
            "ml_home": odds.get("ml_home"), "ml_away": odds.get("ml_away"),
            "dk_spread": odds.get("dk_spread"), "dk_total": odds.get("dk_total"),
        })
    return games


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WNBA TC Engine")
    parser.add_argument("--game", help="Matchup like NY@GS")
    parser.add_argument("--slate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    if args.game:
        parts = args.game.replace("@", " ").split()
        if len(parts) >= 2:
            result = project_game(parts[0].upper(), parts[1].upper())
            print(json.dumps(result, indent=2, default=str))
    elif args.slate:
        games = get_today_slate()
        print(f"WNBA Slate: {len(games)} games")
        for g in games:
            print(f"  {g['away']}@{g['home']} [{g['status']}]")