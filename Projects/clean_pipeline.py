#!/usr/bin/env python3
"""Clean pipeline: dedupe logs, remove zero-byte files, vacuum old pick CSVs."""

import os
import glob
from pathlib import Path
from datetime import datetime, timedelta

DAILY = Path("/home/workspace/Daily_Log")
PROJECTS = Path("/home/workspace/Projects")
RETENTION_DAYS = 14


def clean_daily_log():
    removed = 0
    freed = 0
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for d in DAILY.iterdir():
        if not d.is_dir() or d.name == "backtests":
            continue
        try:
            dtime = datetime.strptime(d.name, "%Y-%m-%d")
        except ValueError:
            continue
        if dtime >= cutoff:
            continue
        for f in d.glob("*.json"):
            if f.stat().st_size == 0:
                freed += f.stat().st_size
                f.unlink()
                removed += 1
    print(f"  daily_log: {removed} empty files removed ({freed/1024:.1f} KB)")


def clean_empty_jsons():
    removed = 0
    for f in DAILY.rglob("*.json"):
        if f.stat().st_size == 0:
            f.unlink()
            removed += 1
    print(f"  empty JSONs: {removed}")


def dedupe_picks_csv():
    seen = 0
    dupes = 0
    for csv in DAILY.glob("*/picks.csv"):
        try:
            lines = csv.read_text().splitlines()
        except Exception:
            continue
        header = lines[0] if lines else ""
        unique = [header]
        keys = set()
        for line in lines[1:]:
            key = line[:80]
            if key in keys:
                dupes += 1
                continue
            keys.add(key)
            unique.append(line)
        if dupes:
            csv.write_text("\n".join(unique) + "\n")
            seen += 1
    print(f"  picks.csv deduped: {seen} files, {dupes} duplicate rows removed")


def main():
    print("=" * 60)
    print("CLEAN PIPELINE")
    print(f"  {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 60)
    clean_daily_log()
    clean_empty_jsons()
    dedupe_picks_csv()
    print("=" * 60)
    print("CLEAN COMPLETE")


if __name__ == "__main__":
    main()
