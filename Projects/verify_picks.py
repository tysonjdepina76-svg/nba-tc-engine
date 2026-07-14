#!/usr/bin/env python3
"""
Verify Picks
"""

from pathlib import Path
from datetime import datetime

def verify():
    today = datetime.now().strftime("%Y-%m-%d")
    picks_file = Path(f"/home/workspace/Daily_Log/{today}/picks.json")

    if picks_file.exists():
        print(f"✅ Picks exist for {today}")
    else:
        print(f"❌ No picks for {today}")

if __name__ == "__main__":
    verify()
