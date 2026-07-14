#!/bin/bash
# stop.sh — stop the Streamlit dashboard
set -euo pipefail
PORT="${TC_PORT:-8510}"
PID="$(lsof -ti:"$PORT" 2>/dev/null || true)"
if [ -z "$PID" ]; then
  echo "ℹ️  no process on port $PORT"
  exit 0
fi
echo "🛑 killing PID $PID on port $PORT"
kill "$PID" && echo "✅ stopped" || echo "❌ failed to kill $PID"
