#!/usr/bin/env python3
"""
wc_player_boxscore.py — World Cup player-level boxscore capture & grading.

Captures actual outcomes per player per WC game from ESPN boxscore,
maps against TC projections in soccer_player_projs.json / soccer_player_picks.csv,
and grades each pick: HIT / MISS / PUSH / PENDING.

Usage:
  python3 wc_player_boxscore.py --date 2026-07-13
  python3 wc_player_boxscore.py --grade-only --date 2026-07-13
  python3 wc_player_boxscore.py --date 2026-07-13 --output graded_wc.csv
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, date
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
DAILY_LOG = os.path.join(os.path.dirname(ROOT), "Daily_Log")

ESPN_MAP_SUMMARY = {
    "Goals":          "goals",
    "Assists":        "assists",
    "Shots":          "sots",
    "Shots on Goal":  "sots",
    "Fouls Committed":"foulsCommitted",
    "Fouls Suffered": "foulsSuffered",
    "Offsides":       "offsides",
    "Corners":        "corners",
    "Saves":          "saves",
    "Yellow Cards":   "yellowCards",
    "Red Cards":      "redCards",
    "Passes":         "PAS",
    "Tackles":        "TKL",
    "Clearances":     "CLR",
    "Interceptions":  "INT",
    "Duels Won":      "DWL",
    "Aerials Won":    "AER",
}

ESPN_MAP_DETAIL = {
    "goals":          "goals",
    "assists":        "assists",
    "shots":          "shots",
    "shots_on_target":"shotsOnTarget",
    "fouls_committed":"foulsCommitted",
    "fouls_suffered": "foulsSuffered",
    "offsides":       "offsides",
    "corners":        "corners",
    "saves":          "saves",
    "yellow_cards":   "yellowCards",
    "red_cards":      "redCards",
    "passes":         "PAS",
    "tackles":        "TKL",
    "clearances":     "CLR",
    "interceptions":  "INT",
    "duels_won":      "DWL",
    "aerials_won":    "AER",
    "minutes":        "minutes",
}


def grade_pick(direction: str, actual: float, line: float) -> str:
    """Grade a single pick: HIT / MISS / PUSH / PENDING."""
    if actual is None or actual == "":
        return "PENDING"
    actual = float(actual)
    line = float(line)
    if abs(actual - line) < 0.01:
        return "PUSH"
    if direction == "OVER":
        return "HIT" if actual > line else "MISS"
    elif direction == "UNDER":
        return "HIT" if actual < line else "MISS"
    return "PENDING"


def _load_soccer_picks(log_dir: str) -> List[Dict[str, str]]:
    """Load soccer_player_picks.csv from the log directory."""
    picks_path = os.path.join(log_dir, "soccer_player_picks.csv")
    if not os.path.exists(picks_path):
        print(f" WARN: {picks_path} not found")
        return []
    with open(picks_path, newline="") as f:
        return list(csv.DictReader(f))


def _load_soccer_projs(log_dir: str) -> List[Dict[str, Any]]:
    """Load soccer_player_projs.json from the log directory."""
    projs_path = os.path.join(log_dir, "soccer_player_projs.json")
    if not os.path.exists(projs_path):
        print(f" WARN: {projs_path} not found")
        return []
    with open(projs_path) as f:
        return json.load(f)


def _load_espn_boxscore(matchup: str) -> Optional[Dict[str, Any]]:
    """Load ESPN WC boxscore summary JSON if available."""
    box_path = os.path.join(DAILY_LOG, f"boxscore_WC_{matchup}.json")
    if not os.path.exists(box_path):
        return None
    with open(box_path) as f:
        return json.load(f)


def capture_player_boxscore(matchup: str, date_str: str) -> Dict[str, Dict[str, float]]:
    """
    Capture player-level boxscore for a WC game.
    Returns: {player_name: {stat: actual_value, ...}}
    """
    box = _load_espn_boxscore(matchup)
    if not box:
        print(f"WARN: No boxscore file for {matchup}")
        return {}

    player_stats = {}
    for team_key in ("away", "home"):
        team_data = box.get(team_key, {})
        players = team_data.get("players", []) or team_data.get("playerStats", [])

        for player in players:
            name = player.get("name", player.get("athlete", {}).get("displayName", "UNKNOWN"))
            stats_entry: Dict[str, float] = {}

            stats_raw = player.get("statistics", player.get("stats", {}))
            for espn_label, tc_key in ESPN_MAP_SUMMARY.items():
                val = stats_raw.get(espn_label, stats_raw.get(tc_key, 0))
                try:
                    stats_entry[tc_key] = float(val)
                except (ValueError, TypeError):
                    stats_entry[tc_key] = 0.0

            player_stats[name] = stats_entry

    return player_stats


def grade_picks(picks: List[Dict[str, str]], projs: List[Dict[str, Any]],
                date_str: str) -> List[Dict[str, str]]:
    """Grade existing picks against captured boxscores."""
    graded = []
    matchups_done: set = set()

    for pick in picks:
        matchup = pick.get("matchup", "")
        player = pick.get("player", "")
        stat = pick.get("stat", "")
        direction = pick.get("signal", pick.get("direction", "OVER"))
        line_str = pick.get("tc_line", pick.get("market_line", "0"))

        try:
            line = float(line_str)
        except (ValueError, TypeError):
            line = 0.0

        if matchup not in matchups_done:
            box = capture_player_boxscore(matchup, date_str)
            matchups_done.add(matchup)
        else:
            box = {}

        player_box = box.get(player, {})
        actual = player_box.get(stat, player_box.get(stat.lower(), None))

        result = grade_pick(direction, actual if actual is not None else None, line)
        pick["actual"] = str(actual) if actual is not None else ""
        pick["result"] = result
        graded.append(pick)

    return graded


def run_grade(date_str: str) -> Dict[str, int]:
    """Main grading entry point."""
    log_dir = os.path.join(DAILY_LOG, date_str)
    if not os.path.isdir(log_dir):
        print(f"ERROR: {log_dir} not found")
        return {"error": 1}

    picks = _load_soccer_picks(log_dir)
    projs = _load_soccer_projs(log_dir)

    if not picks:
        print("No WC picks to grade")
        return {"total": 0}

    graded = grade_picks(picks, projs, date_str)

    out_path = os.path.join(log_dir, "soccer_player_picks_graded.csv")
    if graded:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=graded[0].keys())
            writer.writeheader()
            writer.writerows(graded)

    counts = {"total": len(graded), "HIT": 0, "MISS": 0, "PUSH": 0, "PENDING": 0}
    for g in graded:
        r = g.get("result", "PENDING")
        counts[r] = counts.get(r, 0) + 1

    graded_count = counts["HIT"] + counts["MISS"] + counts["PUSH"]
    hit_rate = (counts["HIT"] / graded_count * 100) if graded_count > 0 else 0.0

    print(f"WC Grading — {date_str}")
    print(f"  Total picks: {counts['total']}")
    print(f"  Graded: {graded_count} (HIT={counts['HIT']} MISS={counts['MISS']} PUSH={counts['PUSH']})")
    print(f"  Hit rate: {hit_rate:.1f}%")
    print(f"  PENDING: {counts['PENDING']}")
    print(f"Saved: {out_path}")

    return counts


def main():
    ap = argparse.ArgumentParser(description="WC Player Boxscore Capture & Grading")
    ap.add_argument("--date", default=date.today().isoformat(),
                    help="Date to grade (YYYY-MM-DD)")
    ap.add_argument("--grade-only", action="store_true",
                    help="Only grade existing picks (skip capture)")
    ap.add_argument("--output", default="",
                    help="Output CSV path for graded picks")
    args = ap.parse_args()

    result = run_grade(args.date)
    if args.output and result.get("total", 0) > 0:
        src = os.path.join(DAILY_LOG, args.date, "soccer_player_picks_graded.csv")
        if os.path.exists(src):
            import shutil
            shutil.copy(src, args.output)
            print(f"Copied to: {args.output}")


if __name__ == "__main__":
    main()
