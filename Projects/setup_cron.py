#!/usr/bin/env python3
"""
Setup Cron
"""

import subprocess

def setup_cron():
    lines = [
        "# TC System",
        "0 4 * * * cd /home/workspace/Projects && python3 daily_picks.py --sport all > /home/workspace/logs/daily.log 2>&1",
        "30 4 * * * cd /home/workspace/Projects && python3 backup.py > /home/workspace/logs/backup.log 2>&1"
    ]
    subprocess.run(["crontab"], input="\n".join(lines), text=True)
    print("✅ Cron installed")

if __name__ == "__main__":
    setup_cron()
