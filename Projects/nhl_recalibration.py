#!/usr/bin/env python3
"""
NHL Recalibration Module — Triple Conservative Pipeline
Mirrors wnba_recalibration.py for NHL self-edge picks.
Active during NHL season (October–June). Off-season now.
"""

import logging

logger = logging.getLogger("nhl_recalibration")

NHL_STAT_RELIABILITY = {
    "G": 0.5,
    "A": 0.55,
    "SOG": 0.75,
    "HITS": 0.6,
    "BLK": 0.55,
    "PIM": 0.4,
    "TOI": 0.7,
}

NHL_DROP_STATS = {"PIM"}

NHL_BLACKLIST = set()

NHL_BOOST = {}

NHL_CONVICTION_THRESHOLD = 0.35

DIRECTION_DIVERSITY_ENABLED = True


def calibrate_nhl_picks(picks: list) -> list:
    if not picks:
        return picks

    before = len(picks)

    picks = [p for p in picks if str(p.get("stat", "")).upper() not in NHL_DROP_STATS]
    picks = [p for p in picks if p.get("name", "") not in NHL_BLACKLIST]
    picks = [p for p in picks if NHL_STAT_RELIABILITY.get(str(p.get("stat", "")).upper(), 1.0) > 0]

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
    logger.info(f"[NHL_RECAL] {before} -> {after} picks ({after - before} removed)")
    logger.info(f"[NHL_RECAL] Direction split: {len(over_picks)} OVER / {len(under_picks)} UNDER")

    return calibrated
