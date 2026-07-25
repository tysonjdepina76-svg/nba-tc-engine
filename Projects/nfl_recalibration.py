#!/usr/bin/env python3
"""
NFL Recalibration Module — Triple Conservative Pipeline
Mirrors wnba_recalibration.py for NFL self-edge picks.
Active during NFL season (September–February). Pre-season now.
"""

import logging

logger = logging.getLogger("nfl_recalibration")

NFL_STAT_RELIABILITY = {
    "PASS_YDS": 0.85,
    "RUSH_YDS": 0.75,
    "REC_YDS": 0.7,
    "REC": 0.65,
    "TD": 0.5,
    "INT": 0.4,
    "FG": 0.6,
    "TACKLES": 0.55,
    "SACKS": 0.45,
}

NFL_DROP_STATS = set()

NFL_BLACKLIST = set()

NFL_BOOST = {}

NFL_CONVICTION_THRESHOLD = 0.35

DIRECTION_DIVERSITY_ENABLED = True


def calibrate_nfl_picks(picks: list) -> list:
    if not picks:
        return picks

    before = len(picks)

    picks = [p for p in picks if str(p.get("stat", "")).upper() not in NFL_DROP_STATS]
    picks = [p for p in picks if p.get("name", "") not in NFL_BLACKLIST]
    picks = [p for p in picks if NFL_STAT_RELIABILITY.get(str(p.get("stat", "")).upper(), 1.0) > 0]

    over_picks = [p for p in picks if p.get("direction", "").upper() == "OVER"]
    under_picks = [p for p in picks if p.get("direction", "").upper() == "UNDER"]

    total = len(over_picks) + len(under_picks)
    if total == 0:
        return picks

    over_pct = len(over_picks) / total if total > 0 else 0
    target = total // 2

    if over_pct > 0.60:
        over_picks.sort(key=lambda p: abs(float(p.get("edge", 0))))
        over_picks = over_picks[-target:] if target > 0 else []
    elif over_pct < 0.40:
        under_picks.sort(key=lambda p: abs(float(p.get("edge", 0))))
        under_picks = under_picks[-target:] if target > 0 else []

    calibrated = over_picks + under_picks
    calibrated.sort(key=lambda p: -abs(float(p.get("edge", 0))))

    after = len(calibrated)
    logger.info(f"[NFL_RECAL] {before} -> {after} picks ({after - before} removed)")
    logger.info(f"[NFL_RECAL] Direction split: {len(over_picks)} OVER / {len(under_picks)} UNDER")

    return calibrated
