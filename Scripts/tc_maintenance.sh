#!/bin/bash
# TC Pipeline Maintenance Script — tysonjdepina76@gmail.com
# Schedule: daily at 3 AM ET
set -euo pipefail
WORKSPACE=/home/workspace
DT=$(date +%Y-%m-%d_%H%M)
echo "=== TC Maintenance $DT ==="

# 0. Dedup boxscores (harmless idempotent call)
echo "[0/6] Dedup boxscores..."
python3 "$WORKSPACE/Projects/boxscore_saver.py" --purge-dupes 2>&1 | grep -oP '\d+ files' || echo "  no dupes found"

# 1. Purge stale caches (>48h)
echo "[1/6] Purging stale caches..."
find /home/workspace/Daily_Log -name "consensus_*.json" -mtime +2 -delete 2>/dev/null && echo "  consensus caches purged" || echo "  no old caches"
find /home/workspace/Daily_Log -name "gamelogs_cache_*.json" -mtime +3 -delete 2>/dev/null && echo "  gamelogs caches purged" || echo "  no old gamelogs"

# 2. Purge __pycache__
echo "[2/6] Purging __pycache__..."
find "$WORKSPACE" -type d -name __pycache__ -not -path "*/Trash/*" -exec rm -rf {} + 2>/dev/null
echo "  pycache clean"

# 3. Clean empty files
echo "[3/6] Cleaning empty files..."
find "$WORKSPACE" -type f -empty -not -path "*/Trash/*" -not -path "*/Archives/*" -delete 2>/dev/null
echo "  empty files removed"

# 4. Rotate old Daily_Log dirs (>30 days) to archive
echo "[4/6] Rotating old daily logs..."
THIRTY_DAYS=$(date -d '30 days ago' +%Y-%m-%d)
for d in "$WORKSPACE"/Daily_Log/20*/; do
  dirname=$(basename "$d")
  if [[ "$dirname" < "$THIRTY_DAYS" ]] && [[ "$dirname" != "_archive" ]]; then
    mkdir -p "$WORKSPACE/Daily_Log/_archive/$dirname"
    mv "$d"* "$WORKSPACE/Daily_Log/_archive/$dirname/" 2>/dev/null || true
    rmdir "$d" 2>/dev/null || true
    echo "  archived $dirname"
  fi
done

# 5. Assess pipeline health
echo "[5/6] Pipeline health..."
cd "$WORKSPACE"
python3 Projects/pipeline_master.py --quick --dry-run 2>&1 | tail -10

# 6. Push to Drive
echo "[6/6] Push to Drive..."
python3 -c "
import os, json
files = ['Projects/consensus_engine.py','Projects/daily_picks.py','Projects/build_pregame_combos.py','Projects/dk_combos_engine.py','AGENTS.md','SYSTEM_MAP.md','TC_TRADEMARK.txt']
print(f'  {len([f for f in files if os.path.exists(os.path.join('/home/workspace',f))])}/{len(files)} core files ready for Drive push')
"

echo ""
echo "=== Maintenance complete $DT ==="
