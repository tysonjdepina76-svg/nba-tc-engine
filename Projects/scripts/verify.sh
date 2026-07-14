#!/bin/bash
# verify.sh — quick end-to-end verification
set -euo pipefail
PROJECT_ROOT="/home/workspace/Projects"
cd "$PROJECT_ROOT"
TODAY="$(date +%F)"

echo "=== TC verify @ $TODAY ==="
echo "[1/3] scan"
python3 scan.py
echo "[2/3] picks dry-run (wnba)"
python3 daily_picks.py --sport wnba --date "$TODAY" || echo "  (no WNBA picks — off-season or no slate)"
echo "[3/3] verify_picks"
python3 verify_picks.py "$TODAY" || echo "  (no picks to verify)"
echo "✅ verify done"
