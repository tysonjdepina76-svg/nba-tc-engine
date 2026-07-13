#!/usr/bin/env bash
# Run backtest across all sports (offline — reads historical.csv)
set -euo pipefail
cd /home/workspace

echo "=== TC Backtest — $(date) ==="
python3 Projects/backtest_all_sports.py 2>&1 | tail -15
echo ""
echo "=== Grading current day's PENDING picks ==="
python3 Projects/grade_daily_picks.py 2>&1 | tail -5
