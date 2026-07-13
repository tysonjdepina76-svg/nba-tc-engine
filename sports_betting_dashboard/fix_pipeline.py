#!/usr/bin/env python3
"""
TC Pipeline Auto-Repair — fix_pipeline.py
Mirrors scan.sh --fix logic in Python.
Usage: python3 fix_pipeline.py [--force]
"""
import subprocess
import sys
import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

ET = timezone(timedelta(hours=-4))
WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
DASH_DIR = WORKSPACE / "sports_betting_dashboard"
TODAY = datetime.now(ET).strftime("%Y-%m-%d")


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def fix_no_picks():
    picks_path = LOG_DIR / TODAY / "picks.json"
    if not picks_path.exists():
        print(f"  → No picks for {TODAY}, running pipeline...")
        code, out, err = run(
            f"cd {WORKSPACE} && python3 Projects/daily_picks.py --sport WNBA --date {TODAY} 2>&1",
            timeout=300,
        )
        if code == 0:
            print(f"  ✓ WNBA complete: {out.split(chr(10))[-3:]}")
        code2, out2, err2 = run(
            f"cd {WORKSPACE} && python3 Projects/daily_picks.py --sport MLB --date {TODAY} 2>&1",
            timeout=300,
        )
        if code2 == 0:
            print(f"  ✓ MLB complete: {out2.split(chr(10))[-3:]}")
        code3, out3, err3 = run(
            f"cd {WORKSPACE} && python3 Projects/daily_picks.py --sport WORLD_CUP --date {TODAY} 2>&1",
            timeout=300,
        )
        if code3 == 0:
            print(f"  ✓ World Cup complete: {out3.split(chr(10))[-3:]}")
        if code != 0 or code2 != 0 or code3 != 0:
            print(f"  ✗ Pipeline failed: {err[-200:]}")
        return True
    return False


def fix_streamlit():
    try:
        r = subprocess.run(
            "curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1",
            shell=True,
            capture_output=True,
            timeout=5,
        )
        if r.returncode != 0:
            print("  → Streamlit :8510 down, restarting...")
            run("pkill -f 'streamlit run.*dashboard' 2>/dev/null || true")
            time.sleep(1)
            code, out, err = run(
                f"cd {WORKSPACE} && nohup streamlit run {DASH_DIR}/dashboard.py "
                f"--server.port 8510 --server.headless true "
                f"> /dev/shm/streamlit_8510.log 2>&1 &",
                timeout=5,
            )
            time.sleep(3)
            r2 = subprocess.run(
                "curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1",
                shell=True,
                capture_output=True,
                timeout=5,
            )
            if r2.returncode == 0:
                print("  ✓ Streamlit :8510 restarted")
            else:
                print("  ✗ Streamlit restart failed — check /dev/shm/streamlit_8510.log")
                if os.path.exists("/dev/shm/streamlit_8510.log"):
                    with open("/dev/shm/streamlit_8510.log") as f:
                        print(f"    {f.read()[-300:]}")
            return True
    except Exception as e:
        print(f"  ✗ Streamlit check error: {e}")
    return False


def fix_symlinks():
    picks_link = DASH_DIR / "data" / "picks" / "today_picks.csv"
    target = LOG_DIR / TODAY / "picks.csv"
    if target.exists():
        if picks_link.is_symlink():
            current = os.readlink(str(picks_link))
            if str(target) not in current:
                print(f"  → Fixing stale symlink: {current} → {target}")
                picks_link.unlink()
                picks_link.symlink_to(target)
                print("  ✓ Symlink fixed")
        elif not picks_link.exists():
            print(f"  → Creating symlink: {picks_link} → {target}")
            picks_link.parent.mkdir(parents=True, exist_ok=True)
            picks_link.symlink_to(target)
            print("  ✓ Symlink created")


def fix_empty_dirs():
    cache_dir = LOG_DIR / "cache" / "odds"
    if cache_dir.exists():
        for d in sorted(cache_dir.iterdir()):
            if d.is_dir() and not any(d.iterdir()):
                print(f"  → Purging empty cache dir: {d}")
                d.rmdir()
    dupes = LOG_DIR / "_dupes"
    if dupes.exists() and not any(dupes.iterdir()):
        print(f"  → Purging empty dupes dir: {dupes}")
        dupes.rmdir()


def fix_missing_files():
    dashboard = DASH_DIR / "dashboard.py"
    if not dashboard.exists():
        print("  ⚠ dashboard.py missing — created by scaffold; restart Streamlit after fix")


def main():
    force = "--force" in sys.argv
    print("=" * 50)
    print("  TC Pipeline Auto-Repair")
    print(f"  {datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S ET')}")
    print("=" * 50)

    fixed_anything = False

    if fix_no_picks():
        fixed_anything = True
    if fix_streamlit():
        fixed_anything = True
    if force or fixed_anything:
        fix_symlinks()
        fix_empty_dirs()
    fix_missing_files()

    print("\n" + "=" * 50)
    if fixed_anything:
        print("  REPAIR COMPLETE — issues were fixed")
    else:
        print("  ALL CLEAR — nothing needed repair")
    print("=" * 50)


if __name__ == "__main__":
    main()
