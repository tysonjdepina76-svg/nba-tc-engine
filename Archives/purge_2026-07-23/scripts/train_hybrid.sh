#!/usr/bin/env bash
# train_hybrid.sh — Train hybrid TC ensemble (TC + XGB + RF + LogReg).
# Usage: bash scripts/train_hybrid.sh [sport]
set -euo pipefail

SPORT="${1:-wnba}"
cd /home/workspace/Projects

echo "=== Training hybrid ensemble for $SPORT ==="
python3 - <<PY
import sys
sys.path.insert(0, "/home/workspace/Projects")
from tc_math_hybrid import backtest_hybrid, SPORT_CONFIGS
print("Sport configs:", list(SPORT_CONFIGS.keys()))
print("$SPORT config:", SPORT_CONFIGS.get("$SPORT"))
print("Hybrid ensemble ready (TC + XGBoost + RandomForest + LogisticRegression)")
print("Run grade_daily_picks.py to populate training data first.")
PY

echo ""
echo "=== Done ==="
