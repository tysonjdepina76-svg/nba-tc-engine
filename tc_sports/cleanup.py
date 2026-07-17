#!/usr/bin/env python3
"""Remove all obsolete files and empty directories. Only whitelisted files/folders are kept."""

import os
import shutil
from pathlib import Path

BASE = Path("/home/workspace")
WHITELIST = {
    BASE / "tc_sports",
    BASE / "Daily_Log",
    BASE / "data",
    BASE / "tc_sports/pipeline/ev_pipeline.py",
    BASE / "tc_sports/dashboard/dashboard.py",
    BASE / "tc_sports/cleanup.py",
    BASE / "tc_sports/config.env",
    BASE / "tc_sports/run_pipeline.sh",
    BASE / "data/historical.csv",
    BASE / "data/processed/alerts.json",
    BASE / "data/processed/alerts.csv",
    BASE / ".git",
    BASE / ".gitignore",
    BASE / ".z",
    BASE / "AGENTS.md",
    BASE / "SOUL.md",
    BASE / "Projects",
    BASE / "Skills",
    BASE / "Images",
    BASE / "Backtest_Reports",
    BASE / "Reports",
    BASE / "Articles",
    BASE / "Cache",
}


def is_protected(path: Path) -> bool:
    for p in WHITELIST:
        if path == p or p in path.parents:
            return True
    return False


def clean_directory(root: Path):
    for item in root.iterdir():
        if is_protected(item):
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
            print(f"Removed directory: {item}")
        else:
            item.unlink()
            print(f"Removed file: {item}")


def remove_empty_dirs(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for d in dirnames:
            full = Path(dirpath) / d
            if not is_protected(full) and not any(full.iterdir()):
                full.rmdir()
                print(f"Removed empty dir: {full}")


if __name__ == "__main__":
    for item in BASE.iterdir():
        if item.name in ["tc_sports", "Daily_Log", "data", "Projects", "Skills", ".git", ".z"]:
            continue
        if is_protected(item):
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
            print(f"Removed top-level dir: {item}")
        else:
            item.unlink()
            print(f"Removed top-level file: {item}")

    for d in [BASE / "tc_sports", BASE / "Daily_Log", BASE / "data"]:
        if d.exists():
            clean_directory(d)

    remove_empty_dirs(BASE)

    print("Cleanup complete.")
