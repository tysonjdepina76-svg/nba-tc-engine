#!/bin/bash
# TC System Cleanup — runs nightly at 4 AM ET
# Dedup boxscores, purge stale files, rotate logs, health check, push to Drive
set -euo pipefail
WORKSPACE=/home/workspace
DT=$(date +%Y-%m-%d_%H%M)
LOG=/dev/shm/system_cleanup_$DT.log
exec > >(tee -a "$LOG") 2>&1

echo "=== System Cleanup $DT ==="

# 1. Dedup boxscores (move older duplicates to _dupes/)
echo "[1/8] Dedup boxscores..."
python3 "$WORKSPACE/Projects/boxscore_saver.py" --purge-dupes 2>&1 | tail -3

# 1a. Purge old _dupes (>7 days)
echo "[2/8] Purging old _dupes..."
find "$WORKSPACE/Daily_Log/_dupes" -type f -mtime +7 -delete 2>/dev/null && echo "  old dupes purged" || echo "  no old dupes"

# 2. Purge stale caches (>48h consensus, >3d gamelogs)
echo "[3/8] Purging stale caches..."
find "$WORKSPACE/Daily_Log" -name "consensus_*.json" -mtime +2 -delete 2>/dev/null && echo "  consensus caches purged" || echo "  no old consensus"
find "$WORKSPACE/Daily_Log" -name "gamelogs_cache_*.json" -mtime +3 -delete 2>/dev/null && echo "  gamelogs caches purged" || echo "  no old gamelogs"

# 3. Purge __pycache__ (not in Trash or Archives)
echo "[4/8] Purging __pycache__..."
find "$WORKSPACE" -type d -name __pycache__ \
  -not -path "*/Trash/*" \
  -not -path "*/Archives/*" \
  -exec rm -rf {} + 2>/dev/null
echo "  pycache clean"

# 4. Clean empty files (log files, temp artifacts)
echo "[5/8] Cleaning empty files..."
find "$WORKSPACE" -type f -empty \
  -not -path "*/Trash/*" \
  -not -path "*/Archives/*" \
  -not -name ".gitkeep" \
  -delete 2>/dev/null
echo "  empty files removed"

# 5. Rotate old daily logs (>30 days to _archive)
echo "[6/8] Rotating old daily logs..."
THIRTY_DAYS=$(date -d '30 days ago' +%Y-%m-%d)
for d in "$WORKSPACE"/Daily_Log/20*/; do
  dirname=$(basename "$d")
  if [[ "$dirname" < "$THIRTY_DAYS" ]] && [[ "$dirname" != "_archive" ]] && [[ "$dirname" != "halftime" ]] && [[ "$dirname" != "final" ]]; then
    mkdir -p "$WORKSPACE/Daily_Log/_archive/$dirname"
    mv "$d"* "$WORKSPACE/Daily_Log/_archive/$dirname/" 2>/dev/null || true
    rmdir "$d" 2>/dev/null || true
    echo "  archived $dirname"
  fi
done
echo "  log rotation complete"

# 6. Pipeline health snapshot
echo "[7/8] Pipeline health..."
cd "$WORKSPACE"
python3 Projects/pipeline_master.py --quick --dry-run 2>&1 | tail -10

# 7. Google Drive sync (core pipeline files)
echo "[8/8] Google Drive sync..."
python3 "$WORKSPACE/Scripts/gdrive_sync.py" 2>&1 | tail -3 || echo "  Drive sync skipped (script not found or no connection)"

echo ""
echo "=== Cleanup complete $DT ==="
