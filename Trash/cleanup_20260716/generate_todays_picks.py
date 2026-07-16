#!/usr/bin/env python3
"""
Generate Today's Picks
"""

import subprocess
from datetime import datetime

def generate():
    today = datetime.now().strftime("%Y-%m-%d")
    subprocess.run([
        "python3",
        "/home/workspace/Projects/daily_picks.py",
        "--date", today
    ])

if __name__ == "__main__":
    generate()
