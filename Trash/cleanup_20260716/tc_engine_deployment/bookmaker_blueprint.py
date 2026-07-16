#!/usr/bin/env python3
"""
Bookmaker Blueprint Integration – Adds opening lines, risk, and live adjustment.
Run this inside your tc-sports-app directory.
"""
import os
from pathlib import Path

BASE = Path.cwd()

# ============================================================
# 1. OPENING LINE CREATION (Bayesian Poisson)
# ============================================================
os.makedirs(BASE / "src/bookmaker", exist_ok=True)
with open(BASE / "src/bookmaker/__init__.py", "w") as f:
    f.write("# Bookmaker simulation modules")

with open(BASE / "src/bookmaker/opening_line.py", "w") as f:
    f.write('''
import numpy as np
from scipy.stats import poisson

class OpeningLineGenerator:
    """
    Simulates a bookmaker's opening line using a Bayesian Poisson model.
    Input: team offensive/defensive ratings, player usage, etc.
    Output: fair probability for a prop (e.g., Player PTS > X).
    """
    def __init__(self):
        self.prior_league_avg = 0.5  # default prior

    def compute_fair_prob(self, sport, player_stat, opponent_def, usage, minutes=None):
        """
        Returns a fair probability for a player prop.
        For NBA PTS: use Poisson with expected points = usage * opponent_def adjustment.
        """
        if sport == 'NBA':
            # Expected points = (usage * 0.8 + (110 - opponent_def) * 0.2) * (minutes/36)
            if minutes is None:
                minutes = 34  # default star minutes
            expected = (usage * 0.8 + (110 - opponent_def) * 0.2) * (minutes / 36)
            # Poisson probability of scoring over a threshold (e.g., 20.5)
            # For simplicity, we return a sigmoid of expected - threshold
            threshold = 20.5  # example; in real usage, pass threshold from prop
            return 1 / (1 + np.exp(-(expected - threshold) * 0.3))
        # Add other sports...
        return 0.50
''')

# ============================================================
# 2. RISK MANAGEMENT & EXPOSURE
# ============================================================
with open(BASE / "src/bookmaker/risk_engine.py", "w") as f:
    f.write('''
class RiskEngine:
    """
    Simulates a bookmaker's liability and line adjustment.
    Tracks exposure on each side and suggests moving lines to balance.
    """
    def __init__(self):
        self.exposure = {}  # sport -> side -> total money

    def update_exposure(self, sport, side, amount):
        if sport not in self.exposure:
            self.exposure[sport] = {'OVER': 0, 'UNDER': 0}
        self.exposure[sport][side] += amount

    def suggested_line_adjustment(self, sport, current_line):
        """
        If one side has >60% of the money, suggest moving line by 0.5 points.
        Returns: (new_line, reason)
        """
        if sport not in self.exposure:
            return current_line, "No data"
        total = sum(self.exposure[sport].values())
        if total == 0:
            return current_line, "No exposure"
        over_pct = self.exposure[sport]['OVER'] / total
        under_pct = self.exposure[sport]['UNDER'] / total
        if over_pct > 0.60:
            return current_line + 0.5, f"Over money {over_pct:.0%}, moving line up"
        elif under_pct > 0.60:
            return current_line - 0.5, f"Under money {under_pct:.0%}, moving line down"
        return current_line, "Balanced"
''')

# ============================================================
# 3. LIVE LINE ADJUSTMENT (Velocity-based)
# ============================================================
with open(BASE / "src/bookmaker/live_adjuster.py", "w") as f:
    f.write('''
import time

class LiveLineAdjuster:
    """
    Simulates a bookmaker's real‑time adjustment based on sharp money velocity.
    """
    def __init__(self, threshold_velocity=2.0):
        self.threshold = threshold_velocity
        self.last_line = {}
        self.last_time = {}

    def adjust_line(self, sport, prop, current_line, velocity):
        """
        If velocity > threshold, predict that the book will move the line by 1 point.
        Returns: predicted_next_line, action (BUY/SELL)
        """
        key = (sport, prop)
        if velocity > self.threshold:
            # Bookmaker will likely move the line in the direction of the velocity
            predicted = current_line + (1 if velocity > 0 else -1)
            action = "FADE"  # Book overreacts, we fade
            return predicted, action
        return current_line, "HOLD"
''')
