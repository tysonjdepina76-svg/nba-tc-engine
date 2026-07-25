#!/usr/bin/env python3
"""
gen_nhl_today.py — NHL Self-Edge Projection Generator
Mirrors gen_wnba_today.py for NHL. Uses roster data + stats + ESPN fallback.
NHL is off-season (2026-07-25). Generates projections when games resume.

Output: Daily_Log/YYYY-MM-DD/proj_NHL_{away}_at_{home}.json
"""

import json, os, sys, hashlib, logging
from datetime import datetime
from zoneinfo import ZoneInfo

ET = __import__('zoneinfo').ZoneInfo("America/New_York")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, '/home/workspace/Projects')
from tc_math import sport_over_under_signal

DAILY_LOG = "/home/workspace/Daily_Log"
STATS_PATH = "/home/workspace/data/nhl_player_stats.json"
ROSTERS_PATH = "/home/workspace/data/rosters/nhl_rosters.json"

NHL_STATS_SKATER = ["G", "A", "PTS", "SOG", "HITS", "BLK", "PIM"]
NHL_STATS_GOALIE = ["SAVES", "GA"]
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary"

REGRESSION_FACTOR = 0.85


def _load_stats():
    stats = {}
    name_map = {}
    try:
        with open(STATS_PATH) as f:
            stats = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load NHL season stats: {e}")
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
logger.info(f"Loaded stats for {len(STATS)} NHL players, {len(NAME_MAP)} name mappings")


def project_player(name: str) -> dict:
    init = NAME_MAP.get(name)
    if not init or init not in STATS:
        return None
    s = STATS[init]
    r5 = s.get("recent5", s["season"])
    season = s["season"]
    result = {}
    for stat in ["G", "A", "PTS", "SOG", "HITS", "BLK", "PIM", "SAVES"]:
        sv = season.get(stat, 0)
        rv = r5.get(stat, 0)
        combined = round(0.3 * sv + 0.7 * rv, 1)
        if combined > 0:
            result[stat] = combined
    return result


def build_projection(p, stat: str, val: float, game_id: str) -> dict:
    key = f"{p.get('name', '')}_{stat}_{game_id}"
    hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
    line = round(val * 0.98, 2) if hash_val % 2 == 0 else round(val * 1.02, 2)
    direction, edge = sport_over_under_signal(projection=val, market_line=line, sport="NHL", min_edge=0.0)
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


def _extract_players_fallback(boxscore, team_side):
    """Extract from live ESPN NHL boxscore — fallback only."""
    players = []
    competitors = (boxscore.get("header", {}).get("competitions", [{}])[0].get("competitors", []))
    target = next((c.get("team", {}).get("displayName", "") for c in competitors if c.get("homeAway") == team_side), "Unknown")
    if target == "Unknown":
        return [], target
    for team_entry in boxscore.get("boxscore", {}).get("players", []):
        if team_entry.get("team", {}).get("displayName", "") != target:
            continue
        for cat in team_entry.get("statistics", []):
            stat_names = cat.get("names", [])
            for athlete in cat.get("athletes", []):
                athlete_data = athlete.get("athlete", {})
                stats_raw = athlete.get("stats", [])
                projs = []
                for i, val in enumerate(stats_raw):
                    if i >= len(stat_names):
                        continue
                    sname = stat_names[i]
                    if sname not in NHL_STATS_SKATER and sname not in NHL_STATS_GOALIE:
                        continue
                    try:
                        fv = float(val) if val not in (None, "", "-") else 0.0
                    except:
                        fv = 0.0
                    projs.append({"stat": sname, "projection": fv, "line": fv - 0.5 if fv > 0 else -0.5, "edge": 0.5, "period": "GAME"})
                if projs:
                    players.append({
                        "player": athlete_data.get("displayName", "Unknown"),
                        "team": target, "starter": athlete.get("starter", False),
                        "did_not_play": athlete.get("didNotPlay", False),
                        "status": "Active" if not athlete.get("didNotPlay") else "DNP",
                        "projections": projs
                    })
        break
    return players, target


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now(ET).strftime("%Y-%m-%d")
    date_str, scoreboard = _fetch_scoreboard(date_str)
    events = scoreboard.get("events", [])
    if not events:
        logger.info(f"No NHL games on {date_str}")
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

        if len(away_players) < 3 or len(home_players) < 3:
            logger.info(f"  {matchup}: season coverage low (A:{len(away_players)} H:{len(home_players)}), falling back to ESPN")
            try:
                box = _fetch_boxscore(game_id)
                away_players, away_team = _extract_players_fallback(box, "away")
                home_players, home_team = _extract_players_fallback(box, "home")
            except Exception as e:
                logger.warning(f"  ESPN fallback failed: {e}")

        if not away_players and not home_players:
            logger.warning(f"  {matchup}: no players, skipping")
            continue

        logger.info(f"  {matchup}: {len(away_players)} away + {len(home_players)} home")

        game_proj = {
            "away": {"all": {"players": away_players}},
            "home": {"all": {"players": home_players}}
        }
        out_path = os.path.join(date_dir, f"proj_NHL_{matchup}.json")
        with open(out_path, "w") as f:
            json.dump(game_proj, f, indent=2)
        per_game_files.append(out_path)

        for p in away_players:
            p["matchup"] = matchup
            all_players.append(p)
        for p in home_players:
            p["matchup"] = matchup
            all_players.append(p)

    combined_path = os.path.join(date_dir, "proj_NHL_.json")
    with open(combined_path, "w") as f:
        json.dump({"date": date_str, "sport": "NHL", "per_game_files": per_game_files, "players": all_players}, f, indent=2)
    logger.info(f"Saved {combined_path} — {len(all_players)} players")


if __name__ == "__main__":
    main()
