#!/usr/bin/env python3
"""
Run Settlement — v1.0.0

Reads the latest picks from /home/workspace/Projects/data/picks/ and
grades them against final box scores saved by boxscore_saver.

Output: data/picks/settled_<sport>_<YYYY-MM-DD>.json
        logs/daily.log is appended with the run summary
"""

from __future__ import annotations
import json
import os
import sys
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECTS = Path("/home/workspace/Projects")
PICKS_DIR = PROJECTS / "data" / "picks"
LOGS_DIR  = PROJECTS / "logs"
DAILY_LOG = LOGS_DIR / "daily.log"

LOG_HEADER = "timestamp\tsport\tdate\tpicks_total\thits\tmisses\tpushes\thit_rate\tsource\n"


def _log_line(sport: str, pick_date: str, picks_total: int,
              hits: int, misses: int, pushes: int) -> None:
    """Append a settlement summary to logs/daily.log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not DAILY_LOG.exists() or DAILY_LOG.stat().st_size == 0:
        DAILY_LOG.write_text(LOG_HEADER)
    hit_rate = (hits / picks_total * 100.0) if picks_total else 0.0
    with DAILY_LOG.open("a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t"
                f"{sport.upper()}\t{pick_date}\t{picks_total}\t"
                f"{hits}\t{misses}\t{pushes}\t{hit_rate:.2f}\tESPN\n")


def load_picks(sport: str, pick_date: date) -> List[dict]:
    """Load today's pick file (CSV or JSON) for a sport."""
    csv_path = PICKS_DIR / f"{sport.lower()}_{pick_date.isoformat()}.csv"
    json_path = PICKS_DIR / f"{sport.lower()}_{pick_date.isoformat()}.json"
    if csv_path.exists():
        with csv_path.open() as f:
            return list(csv.DictReader(f))
    if json_path.exists():
        data = json.loads(json_path.read_text())
        return data.get("picks", []) if isinstance(data, dict) else data
    return []


def load_boxscores(sport: str, pick_date: date) -> List[dict]:
    """Load final box scores saved by boxscore_saver for that date."""
    box_path = PROJECTS / "data" / "backtest" / sport.lower() / f"boxscore_{pick_date.isoformat()}.json"
    if not box_path.exists():
        return []
    data = json.loads(box_path.read_text())
    return data.get("games", []) if isinstance(data, dict) else data


def grade_pick(pick: dict, boxscores: List[dict]) -> str:
    """
    Return one of: 'hit', 'miss', 'push', 'no_data'.
    Looks up player stat vs line, then checks direction.
    """
    player = (pick.get("player") or pick.get("name") or "").strip().lower()
    stat   = (pick.get("stat") or "").strip().lower()
    line   = pick.get("line") or pick.get("market_line")
    direction = (pick.get("direction") or pick.get("pick") or "").strip().upper()
    if not (player and stat and line is not None and direction in ("OVER", "UNDER")):
        return "no_data"
    try:
        line = float(line)
    except (TypeError, ValueError):
        return "no_data"
    for game in boxscores:
        for p in game.get("player_stats", []):
            if player in (p.get("name", "")).lower():
                actual = p.get("stats", {}).get(stat)
                if actual is None:
                    continue
                try:
                    actual = float(actual)
                except (TypeError, ValueError):
                    continue
                if abs(actual - line) < 1e-9:
                    return "push"
                if direction == "OVER"  and actual >  line: return "hit"
                if direction == "UNDER" and actual <  line: return "hit"
                return "miss"
    return "no_data"


def settle_sport(sport: str, pick_date: Optional[date] = None) -> Dict[str, Any]:
    """Grade all picks for a sport on a date. Returns summary dict."""
    sport = sport.lower()
    pick_date = pick_date or date.today()
    picks     = load_picks(sport, pick_date)
    boxscores = load_boxscores(sport, pick_date)
    if not picks:
        return {"sport": sport, "date": pick_date.isoformat(),
                "picks": 0, "hits": 0, "misses": 0, "pushes": 0,
                "hit_rate": 0.0, "settled": []}
    settled = []
    hits = misses = pushes = 0
    for p in picks:
        result = grade_pick(p, boxscores)
        row = dict(p)
        row["result"] = result
        settled.append(row)
        if   result == "hit":  hits   += 1
        elif result == "miss": misses += 1
        elif result == "push": pushes += 1
    total = len(picks)
    hit_rate = (hits / total * 100.0) if total else 0.0
    out = {"sport": sport, "date": pick_date.isoformat(),
           "picks": total, "hits": hits, "misses": misses, "pushes": pushes,
           "hit_rate": hit_rate, "settled": settled}
    out_path = PICKS_DIR / f"settled_{sport}_{pick_date.isoformat()}.json"
    out_path.write_text(json.dumps(out, indent=2))
    _log_line(sport, pick_date.isoformat(), total, hits, misses, pushes)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", required=True,
                    choices=["wnba", "mlb", "nba", "nfl", "nhl", "soccer", "wc", "all"])
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)", default=None)
    args = ap.parse_args()
    target = date.fromisoformat(args.date) if args.date else None
    if args.sport == "all":
        for sp in ("wnba", "mlb", "wc"):
            result = settle_sport(sp, target)
            print(f"{sp.upper():<6} {result['date']}  "
                  f"{result['picks']} picks  {result['hits']} hits  "
                  f"hit_rate={result['hit_rate']:.1f}%")
    else:
        result = settle_sport(args.sport, target)
        print(json.dumps({k: v for k, v in result.items() if k != "settled"}, indent=2))


if __name__ == "__main__":
    main()
