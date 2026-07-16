"""Backup service — copy projections, combos, and picks to /archives.

Run nightly (or on demand) to keep a cold-storage copy of the daily outputs.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

WORKSPACE = Path("/home/workspace")
DAILY_LOG = WORKSPACE / "Daily_Log"
ARCHIVE = WORKSPACE / "archives" / "daily"

ET = timezone(timedelta(hours=-4))


def backup_daily_data(date: Optional[str] = None) -> dict:
    """Copy Daily_Log/{date}/ to /archives/daily/{date}/.

    Args:
        date: YYYY-MM-DD (defaults to today ET)

    Returns:
        {"date": str, "files_copied": int, "bytes": int, "dest": str}
    """
    date = date or datetime.now(ET).strftime("%Y-%m-%d")
    src = DAILY_LOG / date
    if not src.exists():
        return {"date": date, "files_copied": 0, "bytes": 0, "dest": "", "error": f"Source not found: {src}"}

    dest = ARCHIVE / date
    dest.mkdir(parents=True, exist_ok=True)

    files_copied = 0
    bytes_total = 0
    for f in src.rglob("*"):
        if f.is_file():
            target = dest / f.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            files_copied += 1
            bytes_total += f.stat().st_size

    return {
        "date": date,
        "files_copied": files_copied,
        "bytes": bytes_total,
        "dest": str(dest),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(backup_daily_data(), indent=2))
