#!/usr/bin/env python3
"""
gen_mlb_today.py — MLB Self-Edge Projection Generator
Builds per-player projections using season stats + home/away adjustments.
Mirrors gen_wnba_today.py structure.

Output: Daily_Log/YYYY-MM-DD/proj_MLB_{away}_at_{home}.json
"""

import json
import os
import time
import hashlib
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, '/home/workspace/Projects')
from tc_math import sport_over_under_signal

ET = ZoneInfo("America/New_York")

try:
    import statsapi
except ImportError:
    statsapi = None

# ── Configuration ──────────────────────────────────────────────
MIN_GAMES = 5
DEFAULT_LINE_MARGIN = {
    "H": 0.5,
    "R": 0.3,
    "RBI": 0.3,
    "HR": 0.2,
    "2B": 0.2,
    "3B": 0.1,
    "BB": 0.4,
    "SB": 0.2,
    "AVG": 0.020,
    "OBP": 0.020,
    "SLG": 0.030,
    "OPS": 0.030,
}

HOME_BOOST = 1.02
AWAY_PENALTY = 0.98
REGRESSION_FACTOR = 0.85

LOG_DIR = Path("/home/workspace/Daily_Log")
CACHE_DIR = Path("/home/workspace/Daily_Log/mlb_cache")


def get_today_str() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def ensure_dirs(date_str: str):
    (LOG_DIR / date_str).mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def clean_team_name(name: str) -> str:
    return name.replace(" ", "_").replace("'", "").replace(".", "")


def get_todays_games() -> list:
    return statsapi.schedule(date=get_today_str())


def get_team_roster(team_name: str) -> list:
    cache_file = CACHE_DIR / f"roster_{clean_team_name(team_name)}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            if data.get("_fetch_date") == get_today_str():
                return data["players"]

    try:
        teams = statsapi.lookup_team(team_name)
        if not teams:
            return []
        team_id = teams[0]["id"]
        roster = statsapi.roster(team_id)
    except Exception as e:
        print(f"  [WARN] Roster failed for {team_name}: {e}")
        return []

    players = []
    for entry in roster.split("\n"):
        parts = entry.strip().split(maxsplit=1)
        if len(parts) >= 2:
            num = parts[0]
            name = parts[1].strip()
            players.append({"name": name, "roster_num": num})

    if players:
        with open(cache_file, "w") as f:
            json.dump({"_fetch_date": get_today_str(), "players": players}, f)

    return players


def find_player_id(name: str) -> int:
    cache_file = CACHE_DIR / f"lookup_{name.replace(' ', '_')}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            if data.get("_fetch_date") == get_today_str():
                return data.get("player_id", 0)

    try:
        results = statsapi.lookup_player(name)
        if results:
            pid = results[0]["id"]
            with open(cache_file, "w") as f:
                json.dump({"_fetch_date": get_today_str(), "player_id": pid}, f)
            return pid
    except Exception:
        pass
    return 0


def get_player_stats(player_name: str, player_id: int) -> dict:
    cache_file = CACHE_DIR / f"pid_{player_name.replace(' ', '_')}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            cached = json.load(f)
            if cached.get("_fetch_date") == get_today_str():
                return cached.get("stats", {})

    try:
        stats = statsapi.player_stat_data(player_id, group="hitting", type="season")
    except Exception:
        return {}

    if not stats or "stats" not in stats or not stats["stats"]:
        return {}

    s = stats["stats"][0]["stats"]
    g = s.get("gamesPlayed", 1) or 1

    result = {
        "G": g,
        "AVG": float(s.get("avg", ".000") or ".000"),
        "OBP": float(s.get("obp", ".000") or ".000"),
        "SLG": float(s.get("slg", ".000") or ".000"),
        "OPS": float(s.get("ops", ".000") or ".000"),
        "H": float(s.get("hits", 0) or 0),
        "R": float(s.get("runs", 0) or 0),
        "RBI": float(s.get("rbi", 0) or 0),
        "HR": float(s.get("homeRuns", 0) or 0),
        "2B": float(s.get("doubles", 0) or 0),
        "3B": float(s.get("triples", 0) or 0),
        "BB": float(s.get("baseOnBalls", 0) or 0),
        "SB": float(s.get("stolenBases", 0) or 0),
    }

    with open(cache_file, "w") as f:
        json.dump({"_fetch_date": get_today_str(), "stats": result}, f)

    return result


def build_projections_for_game(game: dict) -> dict:
    away = game["away_name"]
    home = game["home_name"]
    game_id = game["game_id"]

    result = {
        "game_id": game_id,
        "away": away,
        "home": home,
        "start_time": game.get("game_datetime", ""),
        "generated_at": datetime.now(ET).isoformat(),
        "players": [],
    }

    for team_name, venue_bonus in [(away, AWAY_PENALTY), (home, HOME_BOOST)]:
        print(f"  Loading roster: {team_name}")
        players = get_team_roster(team_name)
        print(f"    {len(players)} players on roster")

        for p in players[:40]:
            name = p["name"]
            pid = find_player_id(name)
            if not pid:
                continue

            stats = get_player_stats(name, pid)
            games = stats.get("G", 0)
            if games < MIN_GAMES:
                continue

            projs = {}
            for stat in ["H", "R", "RBI", "HR", "2B", "3B", "BB", "SB"]:
                raw = (stats[stat] / games) * REGRESSION_FACTOR * venue_bonus
                proj_val = round(raw, 2)
                key = f"{name}_{stat}_{game_id}"
                hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
                line = round(proj_val * 0.98, 3) if hash_val % 2 == 0 else round(proj_val * 1.02, 3)
                direction, edge = sport_over_under_signal(projection=proj_val, market_line=line, sport="MLB", min_edge=0.0)
                if direction in ("INVALID", "FLAT"):
                    direction = "OVER" if proj_val > line else "UNDER"
                    edge = round(abs(proj_val - line), 3)
                projs[stat] = {"projection": proj_val, "line": line, "edge": round(edge, 3), "direction": direction}
            for stat in ["AVG", "OBP", "SLG", "OPS"]:
                raw = stats[stat] * REGRESSION_FACTOR * venue_bonus
                proj_val = round(raw, 3)
                key = f"{name}_{stat}_{game_id}"
                hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
                line = round(proj_val * 0.98, 4) if hash_val % 2 == 0 else round(proj_val * 1.02, 4)
                direction, edge = sport_over_under_signal(projection=proj_val, market_line=line, sport="MLB", min_edge=0.0)
                if direction in ("INVALID", "FLAT"):
                    direction = "OVER" if proj_val > line else "UNDER"
                    edge = round(abs(proj_val - line), 4)
                projs[stat] = {"projection": proj_val, "line": line, "edge": round(edge, 4), "direction": direction}

            result["players"].append({
                "name": name,
                "player_id": pid,
                "team": team_name,
                "venue": "home" if venue_bonus == HOME_BOOST else "away",
                "games_played": games,
                "season_stats": stats,
                "projections": projs,
            })
            time.sleep(0.3)

    return result


def generate() -> dict:
    if not statsapi:
        return {"error": "statsapi not installed"}

    date_str = get_today_str()
    ensure_dirs(date_str)

    print(f"[gen_mlb_today] Date: {date_str} ET")
    games = get_todays_games()
    print(f"[gen_mlb_today] {len(games)} games scheduled")

    output = {"date": date_str, "sport": "MLB", "games": []}

    for game in games:
        away = game["away_name"]
        home = game["home_name"]
        status = game["status"]
        print(f"\n{'='*60}")
        print(f"  {away} @ {home} [{status}]")
        print(f"{'='*60}")

        if status in ("Final", "Game Over"):
            print("  Skipping completed game")
            continue

        proj = build_projections_for_game(game)
        output["games"].append(proj)

        fname = f"proj_MLB_{clean_team_name(away)}_at_{clean_team_name(home)}.json"
        fpath = LOG_DIR / date_str / fname
        with open(fpath, "w") as f:
            json.dump(proj, f, indent=2)
        print(f"  Saved: {fpath}")

    summary_path = LOG_DIR / date_str / "proj_MLB_summary.json"
    with open(summary_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSummary saved: {summary_path}")
    print(f"Total player projections: {sum(len(g['players']) for g in output['games'])}")

    return output


if __name__ == "__main__":
    generate()
