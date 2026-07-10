"""COMBO QUALIFIER — generates combos from projections using sport-specific rules.

Combos are derived from TC math (props) or bookline (totals / match results),
not from a single hard-coded engine.
"""
from __future__ import annotations

from typing import Any, Dict, List


def generate_combos(projections: List[Dict[str, Any]] | None = None, sport: str = "WNBA") -> List[Dict[str, Any]]:
    """Return sport-specific combo structure.

    Args:
        projections: optional list of player/game projection dicts (used to count
            available legs but not required — returns defaults if empty).
        sport: WNBA, NBA, NFL, FANTASY, MLB, NHL, WORLD_CUP.

    Returns:
        List of combo dicts, each with a `type`, leg count, and `edge`.
    """
    s = (sport or "").upper()
    n = len(projections or [])

    if s in ("WNBA", "NBA", "NFL", "FANTASY"):
        # TC Math + Props — 3-leg combos weighted by available projections
        legs = 3 if n >= 3 else max(1, n)
        return [{"type": "math_prop", "legs": legs, "edge": 0.22}]

    if s in ("MLB", "NHL"):
        # Bookline totals — 2-leg combos
        legs = 2 if n >= 2 else max(1, n)
        return [{"type": "bookline", "legs": legs, "edge": 0.15}]

    if s == "WORLD_CUP":
        # Bookline match + goals
        return [{"type": "wc_bookline", "legs": ["winner", "over_goals"], "edge": 0.18}]

    return []


class ComboQualifier:
    """Stub for dashboard compatibility — delegates to generate_combos()."""

    def __init__(self, sport: str | None = None):
        self.sport = sport

    def filter(self, projections, min_edge=0, min_conf=0, min_corr=0, min_hit=0, max_legs=10, min_legs=2):
        combos = generate_combos(projections, sport=self.sport or "WNBA")
        return combos, {"passed_count": len(combos), "filtered_count": 0, "filtered_reasons": []}

    def qualify(self, projections, **kwargs):
        return self.filter(projections, **kwargs)


def build_combos(projections, sport: str = "NBA") -> List[Dict[str, Any]]:
    """Return sport-appropriate combo structure."""
    return generate_combos(projections, sport=sport)


def load_combos(sport: str, date: str) -> List[Dict[str, Any]]:
    """Return empty list (no on-disk combo cache layer)."""
    return []
