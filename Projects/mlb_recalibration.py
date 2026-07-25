#!/usr/bin/env python3
"""
MLB Recalibration Module — Triple Conservative Pipeline
========================================================
Mirrors wnba_recalibration.py for MLB self-edge picks.

Purpose:
  1. Filter unreliable stats for self-edge (rate stats don't work)
  2. Drop players with zero backtest hits (blacklist)
  3. Weight picks by stat reliability
  4. Enforce direction diversity (target 50/50 OVER/UNDER split)

MLB stat reliability (self-edge context):
  - H, R: moderate — season average somewhat predictive
  - RBI, HR: low — highly volatile, matchup-dependent
  - BB: moderate — plate discipline is stable-ish
  - 2B, 3B, SB: low — rare events, high variance
  - AVG, OBP, SLG, OPS: DROP — rate stats make no sense as over/under with self-edge lines
"""

import logging

logger = logging.getLogger("mlb_recalibration")

# Stat reliability weights for self-edge MLB
MLB_STAT_RELIABILITY = {
    "H": 1.0,
    "R": 1.0,
    "RBI": 0.7,
    "HR": 0.6,
    "BB": 0.8,
    "SB": 0.5,
    "2B": 0.5,
    "3B": 0.5,
    "AVG": 0.0,   # drop — rate stat, meaningless for self-edge O/U
    "OBP": 0.0,
    "SLG": 0.0,
    "OPS": 0.0,
}

# Stats to drop entirely from self-edge picks
MLB_DROP_STATS = {"AVG", "OBP", "SLG", "OPS"}

# Zero-hit players (to be populated from backtest data)
MLB_BLACKLIST = set()

# High-hit players (to boost)
MLB_BOOST = {}


def calibrate_mlb_picks(picks: list) -> list:
    """
    Apply MLB-specific calibration:
      1. Drop rate-stat picks (AVG, OBP, SLG, OPS)
      2. Drop blacklisted players
      3. Weight by stat reliability
      4. Enforce direction diversity
    """
    if not picks:
        return picks

    before = len(picks)

    # 1. Drop rate-stat picks
    picks = [p for p in picks if str(p.get("stat", "")).upper() not in MLB_DROP_STATS]

    # 2. Drop blacklisted players
    picks = [p for p in picks if p.get("name", "") not in MLB_BLACKLIST]

    # 3. Weight by stat reliability — keep picks where stat weight > 0
    picks = [p for p in picks if MLB_STAT_RELIABILITY.get(str(p.get("stat", "")).upper(), 1.0) > 0]

    # 4. Direction diversity — enforce ~50/50 OVER/UNDER split
    over_picks = [p for p in picks if p.get("direction", "").upper() == "OVER"]
    under_picks = [p for p in picks if p.get("direction", "").upper() == "UNDER"]

    total = len(over_picks) + len(under_picks)
    if total == 0:
        return picks

    # Target: no more than 60% in either direction
    over_pct = len(over_picks) / total if total > 0 else 0
    target = total // 2

    if over_pct > 0.60:
        # Too many OVER — trim lowest-edge OVER picks
        over_picks.sort(key=lambda p: abs(float(p.get("edge", 0))))
        keep_over = target
        over_picks = over_picks[-keep_over:] if keep_over > 0 else []
    elif over_pct < 0.40:
        # Too many UNDER — trim lowest-edge UNDER picks
        under_picks.sort(key=lambda p: abs(float(p.get("edge", 0))))
        keep_under = target
        under_picks = under_picks[-keep_under:] if keep_under > 0 else []

    calibrated = over_picks + under_picks
    calibrated.sort(key=lambda p: -abs(float(p.get("edge", 0))))

    after = len(calibrated)
    logger.info(f"[MLB_RECAL] {before} -> {after} picks ({after - before} removed)")
    logger.info(f"[MLB_RECAL] Direction split: {len(over_picks)} OVER / {len(under_picks)} UNDER")
    logger.info(f"[MLB_RECAL] Dropped stats: {MLB_DROP_STATS}")
    logger.info(f"[MLB_RECAL] Blacklisted: {len(MLB_BLACKLIST)} players, Boosted: {len(MLB_BOOST)} players")

    return calibrated
