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

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"

EDGE_THRESH = 2.0
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
    "ATL": 7, "CHI": 12, "CON": 14, "DAL": 3, "GS": 22,
    "IND": 11, "LV": 17, "LA": 5, "MIN": 8, "NY": 9,
    "PHX": 19, "POR": 26, "SEA": 16, "TOR": 29, "WSH": 20,
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


def compute_line_and_edge(tc_projection: float) -> Tuple[float, float, str]:
    raw = tc_projection * LINE_FACTOR
    line = round(raw * 2) / 2
    edge = round(tc_projection - line, 1)
    direction = "OVER" if edge >= EDGE_THRESH else ("UNDER" if edge <= -EDGE_THRESH else "PASS")
    return line, edge, direction


def project_game(away: str, home: str) -> dict:
    """Full TC projection using Core API season stats only (no site API dependency)."""
    load_secrets()
    away = away.upper()
    home = home.upper()
    
    # Fetch season stats for all players
    all_stats = fetch_all_season_stats(150)
    
    # Filter players by team
    away_players = []
    home_players = []
    for name_lower, sinfo in all_stats.items():
        if name_lower.startswith("_"):
            continue
        team = sinfo.get("team", "")
        if team == away:
            away_players.append({
                "name": sinfo.get("name", name_lower.title()),
                "team": team,
                "role": "BENCH",
                "status": "ACTIVE",
                "pos": "",
                "min": DEFAULT_MINUTES,
                "season_stats": sinfo,
            })
        elif team == home:
            home_players.append({
                "name": sinfo.get("name", name_lower.title()),
                "team": team,
                "role": "BENCH",
                "status": "ACTIVE",
                "pos": "",
                "min": DEFAULT_MINUTES,
                "season_stats": sinfo,
            })
    
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
    
    return {
        "mode": "live", "sport": "WNBA",
        "matchup": f"{away}@{home}",
        "away_team": away, "home_team": home,
        "source": "ESPN Core API (self-edge)",
        "signal": signal,
        "dk_total": None,
        "odds": {"total": None, "ml_source": "ESPN Core API (self-edge)"},
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
    
    for stat_key in ("PTS", "REB", "AST", "3PM", "STL", "BLK"):
        tc = compute_tc_projection(season, stat_key, player_info.get("min", DEFAULT_MINUTES), player_info.get("status", "ACTIVE"))
        line, edge, direction = compute_line_and_edge(tc)
        proj["projections"][stat_key] = {
            "tc_projection": tc, "line": line, "edge": edge,
            "direction": direction, "dk_line": None,
            "valid": abs(edge) >= EDGE_THRESH,
        }
    return proj


def _extract_valid(proj: dict, team: str) -> list:
    props = []
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
        games.append({
            "away": a_abbr, "home": h_abbr, "status": status,
            "completed": completed, "event_id": ev.get("id"),
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
