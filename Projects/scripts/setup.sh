#!/bin/bash
# setup.sh — first-time setup for the TC pipeline
set -euo pipefail
PROJECT_ROOT="/home/workspace/Projects"
cd "$PROJECT_ROOT"

echo "🔧 TC pipeline setup"
mkdir -p logs data/picks data/odds
chmod +x scripts/*.sh 2>/dev/null || true

# Python deps (best-effort, never fatal)
pip install --quiet pandas numpy scipy streamlit requests 2>/dev/null || \
  echo "  (pip install skipped or partially failed — continuing)"

# Seed config + log files if missing
[ -f config/algorithm_weights.json ] || echo '{}' > config/algorithm_weights.json
[ -f logs/daily.log ] || : > logs/daily.log
[ -f logs/api.log ]  || : > logs/api.log
[ -f data/historical.csv ] || echo "date,league,matchup,team,player,role,status,stat,direction,market_line,tc_projection,tc_target,edge,threshold,raw_average,source,actual,result" > data/historical.csv

echo "✅ setup complete"
