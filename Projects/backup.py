#!/usr/bin/env python3
"""
Backup
"""

import shutil
from pathlib import Path
from datetime import datetime

def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"/home/workspace/backups/backup_{timestamp}")
    backup_path.mkdir(parents=True, exist_ok=True)

    log_dir = Path("/home/workspace/Daily_Log")
    if log_dir.exists():
        shutil.copytree(log_dir, backup_path / "Daily_Log")

    print(f"✅ Backup: {backup_path}")

if __name__ == "__main__":
    backup()
