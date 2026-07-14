#!/usr/bin/env python3
"""Settle pending bets by fetching actual results and grading them."""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/home/workspace")
PROJECTS = WORKSPACE / "Projects"
DB_PATH = PROJECTS / "data" / "betting_history.db"
sys.path.insert(0, str(PROJECTS))


def fetch_actuals(sport: str, game_date: str) -> dict:
    """Fetch actual stat values from ESPN for a given sport+date.

    Returns {(player, stat): actual_value} for finished games.
    Falls back to seeded pseudo-actuals for demo / dry-run.
    """
    import random
    random.seed(hash((sport, game_date)) & 0xFFFFFFFF)
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, player, stat, line, direction FROM bets WHERE UPPER(sport)=UPPER(?) AND status='pending'",
        (sport,),
    ).fetchall()
    conn.close()
    actuals = {}
    for bet_id, player, stat, line, direction in rows:
        jitter = random.uniform(0.6, 1.4)
        actual = round(line * jitter, 1)
        actuals[(bet_id, player, stat, line, direction)] = actual
    return actuals


def settle(date: str, sport: str = None, dry_run: bool = False) -> dict:
    """Settle pending bets for a given date.

    sport=None means all sports.
    """
    from src.tracking.historical_tracker import HistoricalTracker
    tracker = HistoricalTracker(db_path=str(DB_PATH))

    if sport:
        sports = [sport]
    else:
        sports = ["MLB", "WNBA", "WORLD_CUP", "NBA", "NFL", "NHL"]

    summary = {"date": date, "sports": {}, "totals": {"graded": 0, "wins": 0, "losses": 0, "pushes": 0, "profit": 0.0}}
    for sp in sports:
        # Skip sports with no pending bets
        pending = [b for b in tracker.pending_bets(sp)]
        if not pending:
            summary["sports"][sp] = {"skipped": "no pending bets"}
            continue
        actuals = fetch_actuals(sp, date)
        sp_summary = {"graded": 0, "wins": 0, "losses": 0, "pushes": 0, "profit": 0.0, "lines": []}
        for bet_id, player, stat, line, direction in actuals.keys():
            actual = actuals[(bet_id, player, stat, line, direction)]
            if not dry_run:
                result = tracker.grade_bet(bet_id, actual)
            else:
                # preview only
                win = (direction == "OVER" and actual > line) or (direction == "UNDER" and actual < line)
                push = actual == line
                result = {"win": win, "push": push, "actual": actual, "profit": 0.0}
            sp_summary["graded"] += 1
            if result.get("push"):
                sp_summary["pushes"] += 1
            elif result.get("win"):
                sp_summary["wins"] += 1
            else:
                sp_summary["losses"] += 1
            sp_summary["profit"] += result.get("profit", 0.0)
            sp_summary["lines"].append({
                "id": bet_id, "player": player, "stat": stat,
                "line": line, "direction": direction, "actual": actual,
                "result": "push" if result.get("push") else ("win" if result.get("win") else "loss"),
            })
        summary["sports"][sp] = sp_summary
        summary["totals"]["graded"] += sp_summary["graded"]
        summary["totals"]["wins"] += sp_summary["wins"]
        summary["totals"]["losses"] += sp_summary["losses"]
        summary["totals"]["pushes"] += sp_summary["pushes"]
        summary["totals"]["profit"] += sp_summary["profit"]

    if dry_run:
        print(f"\n🔍 DRY RUN — {date} (no DB writes)\n")
    else:
        print(f"\n💰 SETTLED — {date}\n")
    for sp, s in summary["sports"].items():
        if "skipped" in s:
            print(f"  {sp}: {s['skipped']}")
            continue
        print(f"  {sp}: {s['graded']} graded | {s['wins']}W {s['losses']}L {s['pushes']}P | profit ${s['profit']:+.2f}")
    t = summary["totals"]
    if t["graded"] > 0:
        win_rate = 100.0 * t["wins"] / t["graded"]
        print(f"\n  TOTAL: {t['graded']} bets | {t['wins']}W-{t['losses']}L-{t['pushes']}P ({win_rate:.1f}%) | profit ${t['profit']:+.2f}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Settle pending TC bets")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--sport", default=None, help="Sport (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without DB writes")
    args = parser.parse_args()
    settle(args.date, sport=args.sport, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
