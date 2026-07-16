"""core_math_engine.py — Triple Conservative edge calculator.

Computes a TC projection for a single player-stat-market combination,
then measures edge vs the bookmaker line.  All numbers are normalized
so that edge ∈ [0.0, 1.0] represents the fraction of the TC projection
that exceeds the line in the direction that matters.

Used by daily_picks.py, the API projection endpoints, and backtests.
"""
from __future__ import annotations

from typing import Any, Dict, List


# Per-stat correction factors (sport-specific scaling)
CORRECTION: Dict[str, Dict[str, float]] = {
    "WNBA": {
        "PTS": 1.05, "REB": 1.03, "AST": 1.03,
        "3PM": 1.02, "STL": 1.02, "BLK": 1.02,
    },
    "MLB": {
        "H": 0.98, "HR": 0.95, "RBI": 0.98, "R": 0.98,
        "SB": 0.92, "AVG": 0.97, "K": 1.02, "ER": 1.01,
        "HA": 0.99, "TB": 0.97,
    },
    "WC": {
        "G": 1.00, "A": 0.98, "SOT": 1.01, "SHOTS": 1.00,
        "TCK": 0.97, "PAS": 0.99, "YC": 1.02,
    },
}


def run_full_scan(
    sport: str,
    game_id: str,
    player_name: str,
    stat: str,
    player_data: Dict[str, Any],
    opponents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run a full TC projection scan for a player-stat combo.

    Returns a dict with keys:
        projection  — TC projected value (float)
        line        — bookmaker line (float)
        over_under  — "OVER" or "UNDER" (the side TC recommends)
        edge        — normalized edge fraction (0.0 = no edge, >0.0 = TC projects toward that side)
        reason      — plain-English explanation
    """
    proj = float(player_data.get("projection", player_data.get("tc_projection", 0)))
    line = float(player_data.get("line", player_data.get("dk_line", 0)))
    over_under = player_data.get("over_under", "OVER")

    if proj <= 0 or line <= 0:
        return {
            "projection": proj,
            "line": line,
            "over_under": over_under,
            "edge": 0.0,
            "reason": "No projection or line available",
        }

    factor = CORRECTION.get(sport, {}).get(stat, 1.0)
    tc_proj = proj * factor

    if over_under == "OVER":
        edge = max(0.0, (tc_proj - line) / line)
        side = "OVER"
    else:
        edge = max(0.0, (line - tc_proj) / line)
        side = "UNDER"

    reason = (
        f"TC projects {tc_proj:.1f} {stat} "
        f"vs book line {line:.1f} "
        f"(correction ×{factor:.2f})"
    )

    return {
        "projection": round(tc_proj, 2),
        "line": line,
        "over_under": side,
        "edge": round(edge, 4),
        "reason": reason,
    }
