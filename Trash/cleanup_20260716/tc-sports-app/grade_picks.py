#!/usr/bin/env python3
"""grade_picks.py — Auto-grade TC picks against real ESPN boxscores.

Works for WNBA, MLB, and soccer (World Cup). Reads picks from
data/picks/{sport}_{date}.csv and grades them against ESPN boxscores.

Usage:
    python grade_picks.py --sport wnba --date 2026-07-15
    python grade_picks.py --sport all --date 2026-07-15
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "picks"
GRADED_DIR = BASE / "data" / "graded"
GRADED_DIR.mkdir(parents=True, exist_ok=True)

ET = timedelta(hours=-4)
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

SPORT_LEAGUES = {
    "wnba": "basketball/wnba",
    "mlb": "baseball/mlb",
    "wc": "soccer/usa.1",  # fallback; World Cup uses FIFA endpoint
    "soccer": "soccer/fifa.world",
}

STAT_MAP = {
    "wnba": {"PTS": "PTS", "REB": "REB", "AST": "AST", "STL": "STL", "BLK": "BLK", "3PM": "3PT"},
    "mlb": {"H": "H", "HR": "HR", "RBI": "RBI", "R": "R", "SB": "SB", "K": "SO", "ER": "ER", "BB": "BB"},
    "soccer": {"G": "G", "A": "A", "SOT": "SOT", "SH": "SH"},
    "wc": {"G": "G", "A": "A", "SOT": "SOT", "SH": "SH"},
}


def fetch_espn_boxscore(sport: str, game_id: str) -> Optional[Dict[str, Any]]:
    """Fetch boxscore from ESPN API."""
    league = SPORT_LEAGUES.get(sport, SPORT_LEAGUES["soccer"])
    url = f"{ESPN_BASE}/{league}/summary?event={game_id}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def extract_player_stats(sport: str, boxscore: Dict) -> Dict[str, Dict[str, float]]:
    """Extract per-player actual stats from ESPN boxscore."""
    stats: Dict[str, Dict[str, float]] = {}
    stat_keys = STAT_MAP.get(sport, STAT_MAP["wnba"])

    for team_side in ("home", "away"):
        team_data = boxscore.get("boxscore", {}).get("players", [])
        for entry in team_data:
            if entry.get("team", {}).get("homeAway", "").lower() == team_side:
                for stat_entry in entry.get("statistics", []):
                    if stat_entry.get("name") == "player":
                        athlete_data = stat_entry.get("athletes", [])
                        for athlete in athlete_data:
                            name = athlete.get("athlete", {}).get("displayName", "")
                            if not name:
                                continue
                            player_stats: Dict[str, float] = {}
                            for s in stat_entry.get("labels", []):
                                player_stats[s] = float(athlete.get("stats", [])[stat_entry["labels"].index(s)] or 0)
                            stats[name] = player_stats
    return stats


def grade_picks(sport: str, pick_date: str) -> List[Dict[str, Any]]:
    """Grade all picks for a sport on a given date."""
    csv_path = DATA_DIR / f"{sport}_{pick_date}.csv"
    if not csv_path.exists():
        print(f"No picks file: {csv_path}")
        return []

    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"Empty picks file: {csv_path}")
        return []

    graded: List[Dict[str, Any]] = []
    for row in rows:
        player = row.get("player", "")
        team = row.get("team", "")
        stat = row.get("stat", "PTS")
        line = float(row.get("line", 0))
        projection = float(row.get("projection", 0))
        over_under = row.get("over_under", "OVER")

        actual = -1.0
        result = "UNKNOWN"

        # Try to find actual for this player from cached boxscore
        cache_path = BASE / "data" / "cache" / f"espn_box_{sport}_{pick_date}.json"
        if cache_path.exists():
            with open(cache_path) as f:
                box_data = json.load(f)
            stat_map = STAT_MAP.get(sport, STAT_MAP["wnba"])
            mapped_stat = stat_map.get(stat, stat)
            for game_id, boxscore in box_data.items():
                player_stats = extract_player_stats(sport, boxscore)
                if player in player_stats:
                    actual = player_stats[player].get(mapped_stat, -1.0)
                    break

        if actual >= 0:
            if over_under == "OVER":
                result = "WIN" if actual > line else ("PUSH" if actual == line else "LOSS")
            else:
                result = "WIN" if actual < line else ("PUSH" if actual == line else "LOSS")

        graded.append({
            "player": player,
            "team": team,
            "stat": stat,
            "line": line,
            "projection": projection,
            "actual": actual if actual >= 0 else "N/A",
            "over_under": over_under,
            "result": result,
        })

    out_path = GRADED_DIR / f"graded_{sport}_{pick_date}.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=graded[0].keys())
        writer.writeheader()
        writer.writerows(graded)

    wins = sum(1 for g in graded if g["result"] == "WIN")
    losses = sum(1 for g in graded if g["result"] == "LOSS")
    pushes = sum(1 for g in graded if g["result"] == "PUSH")
    total = wins + losses + pushes

    print(f"\n{sport.upper()} — {pick_date} — {len(rows)} picks graded")
    print(f"  Wins: {wins} | Losses: {losses} | Pushes: {pushes}")
    if total > 0:
        print(f"  Hit Rate: {wins/total*100:.1f}%")
    print(f"  Saved to: {out_path}")

    return graded


def main():
    parser = argparse.ArgumentParser(description="Grade TC picks against ESPN boxscores")
    parser.add_argument("--sport", choices=["mlb", "wnba", "wc", "soccer", "all"], default="all")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    sports = ["mlb", "wnba", "wc"] if args.sport == "all" else [args.sport]
    all_graded = []
    for s in sports:
        graded = grade_picks(s, args.date)
        all_graded.extend(graded)

    if all_graded:
        print(f"\nTotal: {len(all_graded)} picks graded across {len(sports)} sports")


if __name__ == "__main__":
    main()
