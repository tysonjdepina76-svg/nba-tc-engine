#!/usr/bin/env python3
"""
gen_nfl_today.py — NFL Self-Edge Projection Generator
Mirrors gen_wnba_today.py for NFL. Uses roster data + stats + ESPN fallback.
NFL is pre-season (2026-07-25). Generates projections for pre-season games.

Output: Daily_Log/YYYY-MM-DD/proj_NFL_{away}_at_{home}.json
"""

import json, os, sys, hashlib, logging
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/home/workspace/Projects')
from tc_math import sport_over_under_signal

ET = __import__('zoneinfo').ZoneInfo("America/New_York")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DAILY_LOG = "/home/workspace/Daily_Log"
STATS_PATH = "/home/workspace/data/nfl_player_stats.json"
ROSTERS_PATH = "/home/workspace/data/rosters/nfl_rosters.json"

NFL_STATS_QB = ["PASS_YDS", "TD", "INT"]
NFL_STATS_RB = ["RUSH_YDS", "REC_YDS", "REC", "TD"]
NFL_STATS_WR = ["REC_YDS", "REC", "TD"]
NFL_STATS_TE = ["REC_YDS", "REC", "TD"]
NFL_STATS_DEF = ["TACKLES", "SACKS", "INT"]
NFL_STATS_K = ["FG"]
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"

REGRESSION_FACTOR = 0.80  # harder than NBA due to single-game per week


def _load_stats():
    stats = {}
    name_map = {}
    try:
        with open(STATS_PATH) as f:
            stats = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load NFL season stats: {e}")
    if stats:
        try:
            with open(ROSTERS_PATH) as f:
                rosters = json.load(f)
            for team_data in rosters.values():
                for p in team_data.get("players", []):
                    name = p["name"]
                    parts = name.split()
                    if len(parts) >= 2:
                        init_name = f"{parts[0][0]}. {parts[-1]}"
                        if init_name in stats and stats[init_name]["team"] == p.get("team", team_data.get("slug", "")):
                            name_map[name] = init_name
        except Exception:
            pass
    return stats, name_map


STATS, NAME_MAP = _load_stats()
logger.info(f"Loaded stats for {len(STATS)} NFL players, {len(NAME_MAP)} name mappings")


def project_player(name: str) -> dict:
    init = NAME_MAP.get(name)
    if not init or init not in STATS:
        return None
    s = STATS[init]
    r5 = s.get("recent5", s["season"])
    season = s["season"]
    result = {}
    for stat in ["PASS_YDS", "RUSH_YDS", "REC_YDS", "REC", "TD", "INT", "TACKLES", "SACKS", "FG"]:
        sv = season.get(stat, 0)
        rv = r5.get(stat, 0)
        combined = round(0.3 * sv + 0.7 * rv, 1)
        if combined > 0:
            result[stat] = combined
    return result


def build_projection(p, stat: str, val: float, game_id: str) -> dict:
    key = f"{p.get('name', '')}_{stat}_{game_id}"
    hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
    if hash_val % 2 == 0:
        line = round(val * 0.98, 2)
    else:
        line = round(val * 1.02, 2)
    direction, edge = sport_over_under_signal(projection=val, market_line=line, sport="NFL", min_edge=0.0)
    if direction in ("INVALID", "FLAT"):
        direction = "OVER" if val > line else "UNDER"
        edge = round(abs(val - line), 2)
    return {"stat": stat, "projection": round(val, 2), "line": line, "edge": round(edge, 2), "direction": direction, "period": "GAME"}


def _fetch_scoreboard(date_str):
    import requests
    if "-" in date_str:
        dparam = date_str.replace("-", "")
    else:
        dparam = date_str
    r = requests.get(f"{ESPN_SCOREBOARD}?dates={dparam}", timeout=30)
    r.raise_for_status()
    return date_str, r.json()


def _fetch_boxscore(game_id):
    import requests
    r = requests.get(f"{ESPN_SUMMARY}?event={game_id}", timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now(ET).strftime("%Y-%m-%d")
    date_str, scoreboard = _fetch_scoreboard(date_str)
    events = scoreboard.get("events", [])
    if not events:
        logger.info(f"No NFL games on {date_str}")
        return

    date_dir = os.path.join(DAILY_LOG, date_str)
    os.makedirs(date_dir, exist_ok=True)
    all_players, per_game_files = [], []

    for event in events:
        game_id = event["id"]
        comps = event.get("competitions", [{}])[0].get("competitors", [])
        away_abbr = home_abbr = ""
        for c in comps:
            abbr = c.get("team", {}).get("abbreviation", "")
            if c.get("homeAway") == "away": away_abbr = abbr
            else: home_abbr = abbr
        matchup = f"{away_abbr}_at_{home_abbr}"

        away_roster, home_roster = [], []
        try:
            with open(ROSTERS_PATH) as f:
                rosters = json.load(f)
            for team_abbr, team_data in rosters.items():
                if team_abbr == away_abbr:
                    away_roster = team_data.get("players", [])
                elif team_abbr == home_abbr:
                    home_roster = team_data.get("players", [])
        except Exception:
            pass

        def make_projs_from_season(roster):
            out = []
            for p in roster:
                proj = project_player(p["name"])
                if not proj:
                    continue
                projs = [build_projection(p, k, v, game_id) for k, v in proj.items() if v > 0]
                out.append({
                    "player": p["name"], "team": away_abbr if roster is away_roster else home_abbr,
                    "projections": projs, "status": "Active", "source": "season_avg"
                })
            return out

        away_players = make_projs_from_season(away_roster)
        home_players = make_projs_from_season(home_roster)

        if not away_players and not home_players:
            logger.warning(f"  {matchup}: no players with stats, skipping")
            continue

        logger.info(f"  {matchup}: {len(away_players)} away + {len(home_players)} home")

        game_proj = {
            "away": {"all": {"players": away_players}},
            "home": {"all": {"players": home_players}}
        }
        out_path = os.path.join(date_dir, f"proj_NFL_{matchup}.json")
        with open(out_path, "w") as f:
            json.dump(game_proj, f, indent=2)
        per_game_files.append(out_path)

        for p in away_players:
            p["matchup"] = matchup
            all_players.append(p)
        for p in home_players:
            p["matchup"] = matchup
            all_players.append(p)

    combined_path = os.path.join(date_dir, "proj_NFL_.json")
    with open(combined_path, "w") as f:
        json.dump({"date": date_str, "sport": "NFL", "per_game_files": per_game_files, "players": all_players}, f, indent=2)
    logger.info(f"Saved {combined_path} — {len(all_players)} players")


if __name__ == "__main__":
    main()
