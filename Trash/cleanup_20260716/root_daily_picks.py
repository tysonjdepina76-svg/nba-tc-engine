#!/usr/bin/env python3
"""root_daily_picks.py — Convenience wrapper to run daily_picks from /.
Usage: python3 root_daily_picks.py [sport]
"""
import os
import sys
import subprocess

os.chdir("/home/workspace/Projects")
sport = sys.argv[1] if len(sys.argv) > 1 else "all"
cmd = ["python3", "daily_picks.py", "--sport", sport]
print(f"$ {' '.join(cmd)}")
sys.exit(subprocess.call(cmd))
