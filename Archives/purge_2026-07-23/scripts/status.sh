#!/bin/bash
# status.sh — pipeline + dashboard status
set -euo pipefail
PORT="${TC_PORT:-8510}"
PROJECT_ROOT="/home/workspace/Projects"
TODAY="$(date +%F)"

echo "=== TC status @ $TODAY ==="
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "✅ dashboard  : running on port $PORT"
else
  echo "❌ dashboard  : not running on port $PORT"
fi

if [ -d "/home/workspace/Daily_Log/$TODAY" ]; then
  PROJ="$(ls /home/workspace/Daily_Log/$TODAY/proj_*.json 2>/dev/null | wc -l)"
  PICK="$( [ -f /home/workspace/Daily_Log/$TODAY/picks.csv ] && echo 1 || echo 0 )"
  echo "📂 daily log  : $PROJ projection file(s), picks.csv=$PICK"
else
  echo "⚠️  daily log  : no directory for $TODAY"
fi

python3 "$PROJECT_ROOT/scan.py" --report 2>&1 | tail -3
