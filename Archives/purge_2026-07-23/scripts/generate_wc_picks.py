import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

from sources.wc_tc_engine import generate_wc_picks

logger = logging.getLogger(__name__)


def main():
    p = argparse.ArgumentParser(description="WC daily picks generator")
    p.add_argument("--date", default=None, help="YYYYMMDD, default today")
    p.add_argument("--out", default=None, help="Output JSON path")
    p.add_argument("--csv", default=None, help="Output CSV path")
    args = p.parse_args()

    date = args.date or datetime.now().strftime("%Y%m%d")
    picks = generate_wc_picks(date=date)

    out_path = args.out or f"/home/workspace/Projects/data/proj_WC_{date}.json"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"date": date, "picks": picks}, f, indent=2)
    logger.info(f"Wrote {len(picks)} WC projections to {out_path}")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "team", "opponent", "stat", "mean", "over_line", "under_line"])
            for pick in picks:
                for stat, vals in pick.get("projections", {}).items():
                    w.writerow([pick["name"], pick.get("team", ""), pick["opponent"],
                                stat, vals["mean"], vals["over_line"], vals["under_line"]])

    print(f"WC picks: {len(picks)} | out={out_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
