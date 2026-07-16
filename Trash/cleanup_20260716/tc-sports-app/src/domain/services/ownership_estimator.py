"""Ownership estimator — simple model based on TC projections.

Real DFS ownership comes from DK/Pinnacle data, but a usable approximation
uses:
- edge magnitude (higher edge = higher public ownership)
- star factor (All-Star tier = +15%)
- recent form (3-game hot streak = +10%)

This feeds combo_optimizer for lineups that are diverse vs the field.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional


def estimate_ownership(
    players: Iterable[Dict],
    all_star_boost: float = 0.15,
    hot_streak_boost: float = 0.10,
    base: float = 0.10,
) -> Dict[str, float]:
    """Return {player_name: ownership_pct} in 0.0-1.0 range.

    Each player dict should have:
        - name (str)
        - edge (float)
        - tier (str, optional: "STAR" | "STARTER" | "BENCH")
        - recent_games (list of dicts with 'points', optional)
    """
    out: Dict[str, float] = {}
    for p in players:
        name = p.get("name") or p.get("player")
        if not name:
            continue
        own = base
        edge = abs(float(p.get("edge", 0) or 0))
        # Edge boost: +0.05 per +1 edge, capped at +0.30
        own += min(0.30, edge * 0.05)
        # Star tier boost
        if (p.get("tier") or "").upper() in ("STAR", "ALL-STAR", "ALLSTAR"):
            own += all_star_boost
        # Hot streak
        recent = p.get("recent_games") or []
        if len(recent) >= 3:
            try:
                pts = [g.get("points", 0) for g in recent[-3:]]
                if all(pts[i] >= pts[i - 1] for i in range(1, 3)) and sum(pts) > 60:
                    own += hot_streak_boost
            except Exception:
                pass
        # Clamp
        own = max(0.01, min(0.95, own))
        out[name] = round(own, 3)
    return out


if __name__ == "__main__":
    sample = [
        {"name": "A'ja Wilson", "team": "LV", "edge": 2.5, "tier": "STAR", "recent_games": [{"points": 25}, {"points": 28}, {"points": 30}]},
        {"name": "Bench Player", "team": "NY", "edge": 0.3, "tier": "BENCH"},
        {"name": "Caitlin Clark", "team": "IND", "edge": 1.8, "tier": "STAR"},
    ]
    for name, own in estimate_ownership(sample).items():
        print(f"{name}: {own:.1%}")
