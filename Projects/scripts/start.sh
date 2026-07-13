#!/usr/bin/env bash
# Start TC dashboard on port 8510
set -euo pipefail
DASH="/home/workspace/sports_betting_dashboard/dashboard.py"
PORT=8510

if pgrep -f "streamlit run $DASH" >/dev/null; then
    echo "TC dashboard already running on :$PORT"
    exit 0
fi

nohup python3 -m streamlit run "$DASH" \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false \
    >/dev/shm/tc_dashboard.log 2>&1 &

sleep 3
if curl -sf --max-time 3 "http://localhost:$PORT" >/dev/null; then
    echo "TC dashboard started on :$PORT (PID $!)"
else
    echo "ERROR: dashboard did not start. Check /dev/shm/tc_dashboard.log"
    exit 1
fi
