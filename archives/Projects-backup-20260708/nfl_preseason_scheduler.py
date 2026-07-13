#!/usr/bin/env python3
"""NFL Preseason auto-enable for August 6."""
import datetime, json, os, sys
from pathlib import Path

SCHEDULE_FILE = Path("/home/workspace/Daily_Log/cache/nfl_preseason_schedule.json")
NFL_TIP_DATE = datetime.date(2026, 8, 6)
THREE_WEEKS_OUT = NFL_TIP_DATE - datetime.timedelta(weeks=3)

def check():
    today = datetime.date.today()
    payload = {
        "nfl_tip_date": str(NFL_TIP_DATE),
        "three_weeks_out": str(THREE_WEEKS_OUT),
        "today": str(today),
        "days_until_tip": (NFL_TIP_DATE - today).days,
        "warn_window": today >= THREE_WEEKS_OUT,
        "live": today >= NFL_TIP_DATE,
        "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(payload, indent=2))
    print(f"NFL Preseason check: {today} → {NFL_TIP_DATE}")
    print(f"  days_until_tip: {payload['days_until_tip']}")
    print(f"  warn_window:   {payload['warn_window']}")
    print(f"  live:          {payload['live']}")
    return payload

if __name__ == "__main__":
    check()
