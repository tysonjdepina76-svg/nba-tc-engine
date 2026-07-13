#!/usr/bin/env python3
"""Generate data/today.json from the latest Daily_Log picks.csv and last_run.json."""
import json
import os
import sys
from collections import Counter
from datetime import datetime

WORKSPACE = os.environ.get("WORKSPACE", "/home/workspace")
DASH_DIR = os.path.join(WORKSPACE, "sports_betting_dashboard")
TODAY = datetime.now().strftime("%Y-%m-%d")


def main():
    today_data = {
        "generated": datetime.now().isoformat(),
        "date": TODAY,
        "sports": {},
        "total_picks": 0,
        "status": "idle",
    }

    # Read last_run.json
    lr_path = os.path.join(WORKSPACE, "Daily_Log", "last_run.json")
    if os.path.exists(lr_path):
        try:
            with open(lr_path) as f:
                lr = json.load(f)
            today_data["last_run"] = lr.get("timestamp", "?")
            today_data["last_run_detail"] = {
                k: v for k, v in lr.items() if k != "timestamp"
            }
        except Exception as e:
            today_data["last_run"] = "error"
            today_data["last_run_error"] = str(e)
    else:
        today_data["last_run"] = "none"

    # Count picks from today's Daily_Log picks.csv
    picks_csv = os.path.join(WORKSPACE, "Daily_Log", TODAY, "picks.csv")
    if os.path.exists(picks_csv):
        with open(picks_csv) as f:
            lines = f.readlines()
        if len(lines) > 1:
            sports = Counter()
            for line in lines[1:]:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    league = parts[1].strip().lower()
                    sports[league] += 1
            today_data["sports"] = dict(sports)
            today_data["total_picks"] = sum(sports.values())
            today_data["status"] = "ready"
        else:
            today_data["status"] = "empty"
    else:
        today_data["status"] = "no_picks_yet"

    out_path = os.path.join(DASH_DIR, "data", "today.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(today_data, f, indent=2)
    print(f"✓ {out_path} ({os.path.getsize(out_path)} bytes)")
    print(f"  Status: {today_data['status']} | Picks: {today_data['total_picks']}")
    print(f"  Sports: {today_data['sports']}")


if __name__ == "__main__":
    main()
