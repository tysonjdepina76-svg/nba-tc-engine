#!/usr/bin/env python3
"""TC Sports run shim — forwards to daily_picks.py so run.py references work."""
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ALL_SPORTS = ["WNBA", "MLB", "WORLD_CUP"]  # off-season: NBA/NFL/NHL skipped

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sport", choices=ALL_SPORTS + ["all"], default="all")
    p.add_argument("--show-positions", action="store_true")
    p.add_argument("--settle", action="store_true", help="Settle yesterday's picks via report.py")
    p.add_argument("--sample", action="store_true", help="Generate sample picks_mlb.csv")
    p.add_argument("--test-espn", action="store_true", help="Test ESPN scraper")
    p.add_argument("--all-sports", action="store_true")
    args = p.parse_args()

    date = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    sports = ALL_SPORTS if args.all_sports or args.sport == "all" else [args.sport]

    for s in sports:
        print(f"\n{'='*60}\nRUNNING {s}\n{'='*60}")
        cmd = ["python3", "daily_picks.py", "--sport", s, "--date", date]
        subprocess.run(cmd, cwd=Path(__file__).parent)

    if args.settle:
        from datetime import timedelta
        yest = (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"\n{'='*60}\nSETTLEMENT {yest}\n{'='*60}")
        subprocess.run(["python3", "settle_positions.py", "--date", yest], cwd=Path(__file__).parent)

    return 0


if __name__ == "__main__":
    sys.exit(main())
