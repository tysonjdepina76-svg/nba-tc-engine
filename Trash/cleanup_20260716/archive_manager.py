#!/usr/bin/env python3
"""archive_manager.py - TC historical data archiving (safe mode)."""

import os, json, shutil, subprocess
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

BASE = Path("/home/workspace")
PROJECTS = BASE / "Projects"
DAILY = BASE / "Daily_Log"
ARCHIVE = BASE / "archives"
HISTORICAL = ARCHIVE / "historical_data"
OBSOLETE = ARCHIVE / "obsolete_code"

for d in [ARCHIVE, HISTORICAL, OBSOLETE]:
    d.mkdir(parents=True, exist_ok=True)


def archive_old_logs(days_keep: int = 30):
    cutoff = datetime.now() - timedelta(days=days_keep)
    archived = []
    for item in DAILY.iterdir():
        if not item.is_dir():
            continue
        try:
            d = datetime.strptime(item.name, "%Y-%m-%d")
        except ValueError:
            continue
        if d < cutoff:
            tar = HISTORICAL / f"{item.name}.tar.gz"
            if tar.exists():
                continue
            subprocess.run(
                ["tar", "-czf", str(tar), "-C", str(DAILY), item.name],
                check=True,
            )
            shutil.rmtree(item)
            archived.append(item.name)
            log.info(f"Archived: {item.name}")
    return archived


def archive_obsolete_files():
    patterns = ["*backup*.py", "test_*.py", "temp_*.py", "*deprecated*.py", "*mock*.py"]
    archived = []
    for pat in patterns:
        for f in PROJECTS.glob(pat):
            if f.is_file() and f.parent == PROJECTS:
                dest = OBSOLETE / f.name
                shutil.move(str(f), str(dest))
                archived.append(f.name)
                log.info(f"Archived: {f.name}")
    return archived


def create_metadata():
    meta = {
        "archived_at": datetime.now().isoformat(),
        "daily_log_archives": sorted([f.name for f in HISTORICAL.glob("*.tar.gz")]),
        "obsolete_files": sorted([f.name for f in OBSOLETE.glob("*.py")]),
    }
    (ARCHIVE / "metadata.json").write_text(json.dumps(meta, indent=2))
    return meta


def main():
    print("Starting archive process...")
    logs = archive_old_logs(30)
    print(f"Archived {len(logs)} daily logs")
    files = archive_obsolete_files()
    print(f"Archived {len(files)} obsolete files")
    create_metadata()
    print("Archive complete.")


if __name__ == "__main__":
    main()
