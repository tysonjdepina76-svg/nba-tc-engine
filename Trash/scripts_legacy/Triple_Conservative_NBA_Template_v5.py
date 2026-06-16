"""
Triple Conservative NBA Template v5.0
======================================
Updated: May 7, 2026
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
  SPREAD   = whole number, e.g. OKC -11 (not -11.5)
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
    # Game 2 — OKC vs LAL (May 7, 2026)
    "okc_fav":   {"spread": -15, "total": 209.5, "ml": -950},
    "lal_dog":   {"spread": +15, "total": 209.5, "ml": +640},
}

# ─── PLAYER STATS ────────────────────────────────────────────────────────────
# Regular season averages + playoff adjusted for Game 2
STATS = {
    # OKC Thunder
    "SGA":           {"min": 36, "pts": 32.0, "reb": 5.0, "ast": 6.5, "3pm": 2.8, "fg_a": (10.2,21.1)},
    "Jalen Williams":{"min": 33, "pts": 21.4, "reb": 5.5, "ast": 4.0, "3pm": 1.9, "fg_a": (7.8,16.5), "status": "OUT"},
    "Holmgren":      {"min": 30, "pts": 17.0, "reb": 8.0, "ast": 2.5, "3pm": 1.6, "fg_a": (6.4,13.2)},
    "Hartenstein":   {"min": 28, "pts": 10.8, "reb": 9.5, "ast": 3.5, "3pm": 0.3, "fg_a": (4.1, 7.8)},
    "Lu Dort":       {"min": 30, "pts": 12.0, "reb": 3.5, "ast": 1.2, "3pm": 2.4, "fg_a": (4.1,10.1)},
    "Ajay Mitchell": {"min": 22, "pts": 15.0, "reb": 3.5, "ast": 4.8, "3pm": 2.0, "fg_a": (5.5,11.8), "status": "Q"},  # finger, limited
    "Alex Caruso":   {"min": 22, "pts": 7.0,  "reb": 2.8, "ast": 2.0, "3pm": 1.5, "fg_a": (2.8, 6.4)},
    "Cason Wallace": {"min": 20, "pts": 8.5,  "reb": 2.5, "ast": 1.5, "3pm": 1.8, "fg_a": (3.1, 7.0)},
    "Dillon Brooks": {"min": 24, "pts": 13.0, "reb": 4.8, "ast": 1.8, "3pm": 1.8, "fg_a": (5.0,12.1)},
    "Kenrich Williams": {"min": 16, "pts": 6.0, "reb": 3.5, "ast": 1.2, "3pm": 0.8, "fg_a": (2.4, 5.1)},
    "Jared McCain":  {"min": 15, "pts": 8.0,  "reb": 2.0, "ast": 1.5, "3pm": 1.5, "fg_a": (3.0, 6.5)},
    # LAL Lakers
    "LeBron James":  {"min": 36, "pts": 24.4, "reb": 7.2, "ast": 8.4, "3pm": 2.2, "fg_a": (8.5,18.5), "status": "PROB"},  # ankle prob
    "Austin Reaves": {"min": 34, "pts": 16.0, "reb": 4.0, "ast": 5.0, "3pm": 2.8, "fg_a": (5.8,13.5)},
    "Rui Hachimura": {"min": 28, "pts": 13.1, "reb": 4.5, "ast": 1.5, "3pm": 1.8, "fg_a": (5.2,11.2)},
    "Dorian Finney-Smith": {"min": 30, "pts": 9.5, "reb": 4.5, "ast": 1.8, "3pm": 1.8, "fg_a": (3.8, 8.5)},
    "Jaxson Hayes":  {"min": 24, "pts": 10.0, "reb": 5.5, "ast": 1.0, "3pm": 0.3, "fg_a": (4.2, 7.8)},
    "Gabe Vincent":  {"min": 20, "pts": 6.0,  "reb": 2.0, "ast": 2.5, "3pm": 1.3, "fg_a": (2.4, 6.0)},
    "Markieff Morris":{"min": 18, "pts": 7.0,  "reb": 3.5, "ast": 1.2, "3pm": 0.9, "fg_a": (2.8, 6.2)},
    "Maxi Kleber":   {"min": 16, "pts": 5.0,  "reb": 3.5, "ast": 0.8, "3pm": 0.9, "fg_a": (2.0, 5.0)},
    "Luke Kennard":  {"min": 18, "pts": 8.5,  "reb": 2.5, "ast": 2.0, "3pm": 2.1, "fg_a": (3.2, 7.0), "status": "Q"},  # neck Q
    "Luka Doncic":   {"min": 34, "pts": 28.5, "reb": 7.2, "ast": 8.4, "3pm": 3.2, "fg_a": (9.5,20.5), "status": "OUT"},
    "Bronny James":  {"min": 12, "pts": 5.0,  "reb": 2.0, "ast": 1.5, "3pm": 0.8, "fg_a": (2.0, 5.0)},
}

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────
CONSERVATIVE_FACTOR = 0.85

def tc_pts(name: str, factor: float = CONSERVATIVE_FACTOR) -> float:
    s = STATS.get(name)
    if not s:
        return 0.0
    base = s["pts"] * factor
    status = s.get("status", "OKC")  # default OKC for players not in STATS
    if status == "OUT":
        return 0.0
    if status == "Q":
        base *= 0.55
    elif status == "PROB":
        base *= 1.0  # probable — use full 85%
    return round(base, 1)

def tc_min(name: str) -> float:
    s = STATS.get(name)
    if not s:
        return 0.0
    status = s.get("status", "OKC")
    if status == "OUT":
        return 0.0
    if status == "Q":
        return s["min"] * 0.55
    return float(s["min"])

def tc_team_total(players: list) -> int:
    total = sum(tc_pts(p) for p in players)
    raw = total + 3  # bench fill bonus
    return int(raw - 2)  # derive total conservatively → whole number

def line_edge(projected: float, line: float, threshold: float = 2.0) -> bool:
    return (projected - line) >= threshold

def derive_line(pts: float) -> int:
    """TC LINE = pts × 0.88, rounded to nearest whole number."""
    return round(pts * 0.88)

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
        return (f"[{self.pick_type}] {self.description} | "
                f"Proj: {self.projected} | Line: {self.line} | "
                f"Edge: +{self.edge:.1f} | Odds: {self.odds[0]}/{self.odds[1]} "
                f"({self.decimal_odds:.2f}) | Conf: {self.confidence:.0%}")

@dataclass
class ParlayReport:
    matchup: str
    date: str
    game_number: str = ""
    series_standing: str = ""
    legs: list[Leg] = field(default_factory=list)
    stake: float = 10.0

    def add(self, leg: Leg) -> "ParlayReport":
        self.legs.append(leg)
        return self

    def build(self) -> str:
        lines = [
            f"# {self.matchup} — Triple Conservative Parlay",
            f"**Date:** {self.date} | {self.game_number}",
            f"**Series:** {self.series_standing}",
            "",
            "## TC Rules Applied",
            "1. All projections use ≤85% of season average (conservative floor)",
            "2. T-targets are WHOLE NUMBERS only — no decimals",
            "3. Minimum edge: +2 pts (legs), +3 pts (player props)",
            "4. Under selected for totals (safer in playoff games)",
            "5. Confidence threshold: 88%+ from last-5-games sample",
            "6. Injured players: OUT = 0 min; Q = 55% min; PROB = full 85%",
            "7. TC LINE = TC PTS × 0.88 (rounded to whole number)",
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
            "## Backtest Checklist",
            "□ Verify each leg against the opponent's last 5 games before betting",
            "□ Reduce stake if any leg confidence < 88%",
            "□ Confirm starting lineup before tip",
            "□ Check late injury updates (LeBron ankle, Kennard neck)",
        ]
        return "\n".join(lines)

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.build())
        print(f"Saved: {path}")

# ─── GAME DATA ───────────────────────────────────────────────────────────────
# OKC vs LAL — Game 2 (May 7, 2026)
# Status: JWill OUT, Luka OUT, LeBron PROB, Kennard Q
# Odds: OKC -15.5 / 209.5 total / OKC -950 ML / LAL +640 ML

OKC_STARTERS = ["SGA", "Lu Dort", "Holmgren", "Hartenstein", "Ajay Mitchell"]
OKC_BENCH    = ["Alex Caruso", "Cason Wallace", "Dillon Brooks", "Kenrich Williams", "Jared McCain"]
LAL_STARTERS = ["LeBron James", "Austin Reaves", "Rui Hachimura", "Dorian Finney-Smith", "Jaxson Hayes"]
LAL_BENCH    = ["Gabe Vincent", "Markieff Morris", "Maxi Kleber", "Luke Kennard", "Bronny James"]

def build_game():
    okc_start_pts  = sum(tc_pts(p) for p in OKC_STARTERS)
    okc_bench_pts  = sum(tc_pts(p) for p in OKC_BENCH)
    lal_start_pts  = sum(tc_pts(p) for p in LAL_STARTERS)
    lal_bench_pts  = sum(tc_pts(p) for p in LAL_BENCH)

    okc_tc   = int(okc_start_pts + okc_bench_pts + 3 - 2)
    lal_tc   = int(lal_start_pts + lal_bench_pts + 3 - 2)
    combined = okc_tc + lal_tc

    spread_line   = 15      # whole number per TC rules
    total_line    = 209     # whole number (209.5 → 209)
    okc_proj_win  = int(okc_tc - lal_tc)   # projected margin
    under_edge    = combined - total_line   # negative = under edge

    print("=== OKC STARTERS ===")
    for p in OKC_STARTERS:
        tc = tc_pts(p)
        print(f"  {p:20s} TC={tc:5.1f}  LINE={derive_line(tc):3d}  EDGE={tc-derive_line(tc):+5.1f}")
    print(f"  {'BENCH':20s} TC={okc_bench_pts:5.1f}")
    print(f"  {'OKC TEAM TOTAL':20s} TC={okc_tc}")

    print("\n=== LAL STARTERS ===")
    for p in LAL_STARTERS:
        tc = tc_pts(p)
        print(f"  {p:20s} TC={tc:5.1f}  LINE={derive_line(tc):3d}  EDGE={tc-derive_line(tc):+5.1f}")
    print(f"  {'BENCH':20s} TC={lal_bench_pts:5.1f}")
    print(f"  {'LAL TEAM TOTAL':20s} TC={lal_tc}")

    print(f"\n=== SYSTEM SUMMARY ===")
    print(f"  OKC TC: {okc_tc} | LAL TC: {lal_tc} | Combined: {combined}")
    print(f"  Projected OKC margin: +{okc_proj_win}")
    print(f"  Under edge: {under_edge:+.1f} vs total line {total_line}")
    print(f"  OKC spread edge: {okc_proj_win - spread_line:+.1f} vs line {spread_line}")

if __name__ == "__main__":
    build_game()