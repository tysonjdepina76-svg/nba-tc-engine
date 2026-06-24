#!/usr/bin/env bash
# Start TC services
set -euo pipefail
echo "→ Starting Streamlit dashboard on :8510..."
pkill -f "streamlit run.*dashboard" 2>/dev/null || true
sleep 1
nohup streamlit run /home/workspace/Projects/dashboard.py --server.port 8510 --server.headless true > /dev/shm/streamlit_8510.log 2>&1 &
sleep 2
curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1 && echo "✓ Dashboard: http://localhost:8510" || echo "✗ Start failed — check /dev/shm/streamlit_8510.log"
