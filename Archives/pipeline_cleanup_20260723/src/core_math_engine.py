#!/usr/bin/env python3
"""Core Math Engine — wrapper that calls hybrid predictors for edge computation.

Dispatches to sport-specific hybrid predictors and returns:
  - true_probability
  - edge (true_prob - book_implied)
  - action (HIGH_EV / MEDIUM_EV / NO_EDGE / FADE)
  - velocity signal

All projection inputs come from the projection engine; this module
is a math-only router — no scraping, no API calls, no DB writes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
_PROJ = _HERE.parent
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

from tc_math import implied_prob_from_odds, remove_vig


def _sport_algorithms(sport: str, player: str, prop: str, raw_data: Dict) -> float:
    """Heuristic true probability per sport."""
    base = 0.50
    sport_lower = sport.lower()

    if sport_lower == "mlb":
        if "TOTAL" in prop:
            wrc = raw_data.get("team_wrc", 100)
            fip = raw_data.get("opp_fip", 4.0)
            pf = raw_data.get("park_factor", 1.0)
            base = ((wrc / 100) * (fip / 4.0)) * pf
            return max(0.30, min(0.70, base))
        if "SPREAD" in prop:
            ts = raw_data.get("team_strength", 50)
            os_ = raw_data.get("opp_strength", 50)
            base = 0.50 + (ts - os_) / 100
            return max(0.10, min(0.90, base))
        if "H" in prop or prop == "Hits":
            xba = raw_data.get("batter_xba", 0.250)
            fb = raw_data.get("pitcher_fastball_pct", 50)
            base = xba * 2
            if fb > 50:
                base += 0.10
        return max(0.10, min(0.90, base))

    if sport_lower in ("wnba", "nba"):
        if raw_data.get("back_to_back"):
            base -= 0.15

    if sport_lower in ("wc", "world_cup", "soccer"):
        xg = raw_data.get("xg", 1.0)
        base = (xg / 3.5) + 0.35
        return max(0.10, min(0.90, base))

    return max(0.10, min(0.90, base))


def _opening_line_fallback(sport: str, prop: str, opponent_def: float, usage: float) -> float:
    """Simple sigmoid fair-probability when opening-line generator isn't available."""
    try:
        import numpy as np
    except ImportError:
        return 0.50
    if sport.lower() == "wnba":
        expected = (usage * 0.8 + (110 - opponent_def) * 0.2) * (34 / 36)
        return 1 / (1 + np.exp(-(expected - 20.5) * 0.3))
    return 0.50


def run_full_scan(
    sport: str,
    game_id: str,
    player: str,
    prop: str,
    raw_data: Dict,
    historical_odds: Optional[List[Tuple[Any, float]]] = None,
) -> Dict[str, Any]:
    """Primary entry point — called by daily_picks.py for every pick."""

    heuristic_prob = _sport_algorithms(sport, player, prop, raw_data)

    opp_def = raw_data.get("opponent_defensive_rating", 110)
    usage = raw_data.get("player_usage", 0.20)
    opening_prob = _opening_line_fallback(sport, prop, opp_def, usage)

    true_prob = 0.6 * heuristic_prob + 0.4 * opening_prob

    velocity_signal = "BET_NOW"
    velocity_val = 0.0
    if historical_odds and len(historical_odds) >= 2:
        try:
            from datetime import datetime
            first = historical_odds[0]
            last = historical_odds[-1]
            elapsed = (last[0] - first[0]).total_seconds() / 60.0 if isinstance(first[0], datetime) else 5.0
            vel = abs(last[1] - first[1]) / max(elapsed, 0.1)
            velocity_val = vel
            if vel > 5.0:
                velocity_signal = "FADE_MARKET"
            elif vel > 2.0:
                velocity_signal = "CAUTION"
            else:
                velocity_signal = "BET_NOW"
        except Exception:
            pass

    book_odds = raw_data.get("book_odds", -110)
    book_implied = implied_prob_from_odds(book_odds)
    fair_line = remove_vig(book_implied)
    edge = true_prob - fair_line

    if velocity_signal == "FADE_MARKET":
        action = "FADE"
    elif velocity_signal == "BET_NOW" and edge > 0.05:
        action = "HIGH_EV"
    elif velocity_signal == "BET_NOW" and edge > 0.02:
        action = "MEDIUM_EV"
    else:
        action = "NO_EDGE"

    return {
        "true_prob": round(true_prob, 4),
        "edge": round(edge, 4),
        "action": action,
        "velocity": round(velocity_val, 4),
        "velocity_signal": velocity_signal,
    }
