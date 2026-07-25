#!/usr/bin/env python3
"""
NBA Recalibration Module — Triple Conservative Pipeline
Mirrors wnba_recalibration.py for NBA self-edge picks.
Active during NBA season (October–June). Off-season now but hooks wired.
"""

import logging

logger = logging.getLogger("nba_recalibration")

NBA_STAT_RELIABILITY = {
    "PTS": 1.0,
    "REB": 0.9,
    "AST": 0.85,
    "STL": 0.6,
    "BLK": 0.6,
    "3PM": 0.75,
    "FG%": 0.4,
    "FT%": 0.3,
    "TO": 0.7,
    "DREB": 0.6,
    "OREB": 0.5,
    "PRA": 0.8,
    "P+R": 0.8,
    "P+A": 0.8,
}

NBA_DROP_STATS = {"FG%", "FT%"}

NBA_BLACKLIST = set()

NBA_BOOST = {}

NBA_CONVICTION_THRESHOLD = 0.35

DIRECTION_DIVERSITY_ENABLED = True


def calibrate_nba_picks(picks: list) -> list:
    if not picks:
        return picks

    before = len(picks)

    picks = [p for p in picks if str(p.get("stat", "")).upper() not in NBA_DROP_STATS]
    picks = [p for p in picks if p.get("name", "") not in NBA_BLACKLIST]
    picks = [p for p in picks if NBA_STAT_RELIABILITY.get(str(p.get("stat", "")).upper(), 1.0) > 0]

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
    logger.info(f"[NBA_RECAL] {before} -> {after} picks ({after - before} removed)")
    logger.info(f"[NBA_RECAL] Direction split: {len(over_picks)} OVER / {len(under_picks)} UNDER")

    return calibrated
