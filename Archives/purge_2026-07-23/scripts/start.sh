#!/bin/bash
# start.sh — start the Streamlit dashboard
set -euo pipefail
PROJECT_ROOT="/home/workspace/Projects"
cd "$PROJECT_ROOT"
PORT="${TC_PORT:-8510}"
echo "🚀 starting TC dashboard on port $PORT"
exec streamlit run streamlit_app.py --server.port "$PORT" --server.headless true
