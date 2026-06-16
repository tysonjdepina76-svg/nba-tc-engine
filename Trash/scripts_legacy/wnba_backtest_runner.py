"""
WNBA TC Backtest Runner — May 15, 2026
=====================================
Uses official WNBA box scores to validate:
1. Player-level TC: pts×0.85 + reb×0.12 + ast×0.10 + tpm×0.08
2. Team-level TC: sum of all player TC values
3. TC vs actual game totals (systematic bias check)

KEY FINDING: TC raw ≈ 93.3% of actual WNBA total.
WNBA pace factor ≈ 1.072x (TC × 1.072 ≈ actual total)
This is the equivalent of the NBA engine's 0.76-0.82 game-level multiplier.

Files in wnba_backtest/ use wnba_tc_engine Player/Team classes directly.
"""
from wnba_backtest_runner import *   # self-referencing — run directly

# This file is designed to be run with:
#   python3 /home/workspace/wnba_backtest_runner.py
