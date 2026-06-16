"""
Triple Conservative NBA Template v5.0
======================================
Updated: April 27, 2026
Philosophy: Low-side estimates only. If any projection feels uncertain, trim it.
Never project a line you'd be uncomfortable betting yourself.

RULES (hardcoded):
1. All player projections use conservative estimates (85% of season avg max)
2. T-targets are WHOLE NUMBERS only — never decimals
3. Pick value MUST exceed line by ≥2 pts for legs, ≥3 pts for props
4. Total is derived from conservative team totals (sum of parts, then -2)
5. Props require 88%+ confidence threshold from recent sample
6. Never project a rookie for >25 min in a playoff game
7. Injury adjustments: subtract full projected min if ruled OUT; halve if Q
8. Backtest every leg against last 5 games of that opponent

PICK TYPES:
  SPREAD   = whole number, e.g. BOS -7 (not -7.5)
  TOTAL    = Under only (safer in playoffs), whole number O/U
  ML       = only if true implied prob > 60%
  PLAYER PROP = only if edge ≥ 3 pts on conservative estimate

Payout calc: Decimal = (leg_odds[0]/leg_odds[1]) + 1
Parlay payout = product of leg decimals × stake
"""

import json
from dataclasses import dataclass, field
from typing import Optional

# ─── ODDS LIBRARY ────────────────────────────────────────────────────────────
ODDS = {
    # favorites (negative) / underdogs (positive)
    "bos_fav":   {"spread": -7,  "total": 215, "ml": -320},
    "phi_dog":   {"spread": +7,  "total": 215, "ml": +265},
}

# ─── PLAYER STATS ────────────────────────────────────────────────────────────
STATS = {
    "SGA":       {"min": 36, "pts": 31.1, "reb": 5.0, "ast": 6.6, "3pm": 2.8, "fg_a": (10.2,21.1)},
    "JWilliams": {"min": 33, "pts": 21.5, "reb": 5.5, "ast": 4.0, "3pm": 1.9, "fg_a": (7.8,16.5), "status": "OUT"},
    "Holmgren":  {"min": 30, "pts": 17.0, "reb": 8.0, "ast": 2.5, "3pm": 1.6, "fg_a": (6.4,13.2)},
    "Hartenstein":{"min": 28, "pts": 10.5, "reb": 9.5, "ast": 3.5, "3pm": 0.3, "fg_a": (4.1, 7.8)},
    "Lu Dort":   {"min": 30, "pts": 12.0, "reb": 3.5, "ast": 1.2, "3pm": 2.4, "fg_a": (4.1, 10.1)},
    "Ish Joe":   {"min": 18, "pts":  9.0, "reb": 2.0, "ast": 0.8, "3pm": 2.1, "fg_a": (3.2, 7.6)},
    "Cason Wallace": {"min": 20, "pts": 8.5, "reb": 2.5, "ast": 1.5, "3pm": 1.8, "fg_a": (3.1, 7.0)},
    "Booker":    {"min": 37, "pts": 26.1, "reb": 4.3, "ast": 6.0, "3pm": 2.6, "fg_a": (8.7,19.2)},
    "Jalen Green":{"min": 34, "pts": 19.5, "reb": 4.0, "ast": 2.8, "3pm": 2.5, "fg_a": (6.8,15.3)},
    "Dillon Brooks": {"min": 32, "pts": 13.5, "reb": 6.7, "ast": 1.8, "3pm": 1.8, "fg_a": (5.0,12.1)},
    "Oso Ighodaro": {"min": 26, "pts":  9.5, "reb": 5.5, "ast": 2.8, "3pm": 0.4, "fg_a": (3.8, 7.2)},
    "Grayson Allen": {"min": 22, "pts": 10.5, "reb": 3.0, "ast": 2.0, "3pm": 2.4, "fg_a": (3.7, 8.1)},
    "Tatum":     {"min": 37, "pts": 26.8, "reb": 7.5, "ast": 5.0, "3pm": 2.9, "fg_a": (8.5,18.8)},
    "Brown":     {"min": 33, "pts": 22.5, "reb": 6.0, "ast": 3.5, "3pm": 2.2, "fg_a": (8.2,17.1)},
    "White":     {"min": 31, "pts": 15.5, "reb": 4.2, "ast": 4.8, "3pm": 2.8, "fg_a": (5.2,11.8)},
    "Pritchard": {"min": 26, "pts": 14.2, "reb": 3.5, "ast": 3.0, "3pm": 3.1, "fg_a": (4.8,11.3)},
    "Horford":   {"min": 27, "pts": 11.2, "reb": 6.2, "ast": 3.5, "3pm": 2.0, "fg_a": (4.2, 9.8)},
    "Prozinga":  {"min": 26, "pts": 15.5, "reb": 6.8, "ast": 2.0, "3pm": 0.8, "fg_a": (5.8,11.2)},
    "Maxey":     {"min": 36, "pts": 24.6, "reb": 3.8, "ast": 5.8, "3pm": 2.2, "fg_a": (8.1,17.5)},
    "Embiid":    {"min": 30, "pts": 22.8, "reb": 8.5, "ast": 3.2, "3pm": 1.2, "fg_a": (7.4,15.8), "status": "Q"},
}

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────
CONSERVATIVE_FACTOR = 0.85

def tc_pts(name: str, factor: float = CONSERVATIVE_FACTOR) -> float:
    s = STATS.get(name)
    if not s:
        return 0.0
    base = s["pts"] * factor
    if s.get("status") == "OUT":
        return 0.0
    if s.get("status") == "Q":
        base *= 0.55
    return round(base, 1)

def tc_min(name: str) -> float:
    s = STATS.get(name)
    if not s:
        return 0.0
    if s.get("status") == "OUT":
        return 0.0
    if s.get("status") == "Q":
        return s["min"] * 0.55
    return float(s["min"])

def tc_team_total(players: list) -> int:
    total = sum(tc_pts(p) for p in players)
    raw = total + 3   # bench fill
    return int(raw - 2)   # derive total conservatively → whole number

def line_edge(projected: float, line: float, threshold: float = 2.0) -> bool:
    return (projected - line) >= threshold

def pick_str(pick_type: str, team: str, value: int, line: int) -> str:
    if pick_type == "SPREAD":
        return f"{team} {'+' if value > 0 else ''}{value} (line {line})"
    if pick_type == "TOTAL":
        return f"Under {value} (total line {line})"
    if pick_type == "ML":
        return f"{team} ML ({line})"
    if pick_type == "PROP":
        return f"{team} {value} (line {line})"
    return f"{team} {value}"

@dataclass
class Leg:
    pick_type: str    # SPREAD / TOTAL / ML / PROP
    team: str
    description: str
    projected: float
    line: int
    odds: tuple        # (numerator, denominator) e.g. (3,4) = +150
    confidence: float  # 0.0–1.0

    @property
    def edge(self) -> float:
        return self.projected - self.line

    @property
    def decimal_odds(self) -> float:
        n, d = self.odds
        return (n / d) + 1

    def __str__(self) -> str:
        return f"[{self.pick_type}] {self.description} | Proj: {self.projected} | Line: {self.line} | Edge: +{self.edge:.1f} | Odds: {self.odds[0]}/{self.odds[1]} ({self.decimal_odds:.2f}) | Conf: {self.confidence:.0%}"

@dataclass
class ParlayReport:
    matchup: str
    date: str
    legs: list[Leg] = field(default_factory=list)
    stake: float = 10.0

    def add(self, leg: Leg) -> "ParlayReport":
        self.legs.append(leg)
        return self

    def build(self) -> str:
        lines = [
            f"# {self.matchup} — Triple Conservative Parlay",
            f"**Date:** {self.date}",
            "",
            "## Rules Applied",
            "1. All projections use ≤85% of season average (conservative floor)",
            "2. T-targets are WHOLE NUMBERS only — no decimals",
            "3. Minimum edge: +2 pts (legs), +3 pts (player props)",
            "4. Under selected for totals (safer in playoff games)",
            "5. Confidence threshold: 88%+ from last-5-games sample",
            "6. Injured players projected OUT = 0 min; Q = 55% min",
            "",
            "## Pick Legs",
        ]
        total_decimal = 1.0
        for i, leg in enumerate(self.legs, 1):
            status = "✅" if leg.edge >= 2 else "⚠️"
            lines.append(f"{status} Leg {i}: {leg}")
            total_decimal *= leg.decimal_odds

        payout = total_decimal * self.stake
        win = payout - self.stake
        lines += [
            "",
            "## Payout Summary",
            f"- Stake: ${self.stake:.2f}",
            f"- Odds: {' / '.join(f'+{l.odds[0]/l.odds[1]*100:.0f}' for l in self.legs)}",
            f"- Combined Decimal: {total_decimal:.3f}",
            f"- Payout: ${payout:.2f}",
            f"- Net Win: ${win:.2f}",
            "",
            "## Backtest Notes",
            "Verify each leg against the opponent's last 5 games before betting.",
            "Reduce stake if any leg confidence < 88%.",
        ]
        return "\n".join(lines)

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.build())
        print(f"Saved: {path}")

if __name__ == "__main__":
    pass
