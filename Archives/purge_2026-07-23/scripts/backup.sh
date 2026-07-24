#!/usr/bin/env bash
# Backup Daily_Log and Projects to /home/workspace/Archives
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP="/home/workspace/Archives/backup_${STAMP}.tar.gz"

echo "=== TC Backup — $STAMP ==="
tar -czf "$BACKUP" \
    -C /home/workspace \
    Daily_Log \
    Projects/daily_picks.py \
    Projects/sports_registry.py \
    Projects/config \
    Projects/scripts \
    sports_betting_dashboard/dashboard.py 2>/dev/null

ls -lh "$BACKUP"
echo "Backup complete."
