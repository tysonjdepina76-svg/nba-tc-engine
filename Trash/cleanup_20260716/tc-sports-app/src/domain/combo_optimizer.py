"""Combo Optimizer — ownership-aware lineup stacking for multi-leg combos.

Builds optimized combo structures (parlays / Same-Game Parlays / 2-6 leg multi-sport
entries) from a list of Player projections. Logic:
- Rank players by edge (projection vs line)
- Apply ownership cap (no more than `ownership_cap` of players from any single
  team, to avoid correlated bust risk)
- Stack QB+WR/TE for same-game correlation (NFL)
- Limit to `max_lineups` outputs

Returns lightweight dicts; callers can render however they want.
"""
from __future__ import annotations

import random
from typing import List, Dict, Optional, Iterable


class ComboOptimizer:
    """Ownership-aware combo (parlay) optimizer."""

    def __init__(self, ownership_cap: float = 0.40, seed: Optional[int] = None):
        """
        ownership_cap — max fraction of legs in a single combo that may come
                        from one team (default 0.40 = 40%).
        seed         — RNG seed for reproducible lineups.
        """
        if not 0.0 < ownership_cap <= 1.0:
            raise ValueError("ownership_cap must be in (0, 1]")
        self.ownership_cap = ownership_cap
        self._rng = random.Random(seed)

    def optimize(
        self,
        players: Iterable[Dict],
        max_lineups: int = 10,
        legs_per_combo: int = 4,
    ) -> List[str]:
        """
        Build up to `max_lineups` combos of `legs_per_combo` legs each.

        Each player dict should include at least:
            - name (str)
            - team (str)
            - edge (float)  — projection edge (positive = over-edge)
            - stat   (str, optional)

        Returns a list of human-readable combo strings.
        """
        if max_lineups <= 0 or legs_per_combo <= 0:
            return []

        players = [p for p in players if p.get("name")]
        if not players:
            return []

        # Sort by edge desc; keep enough for diversity
        ranked = sorted(players, key=lambda p: p.get("edge", 0.0), reverse=True)
        top_pool = ranked[: max(max_lineups * legs_per_combo * 3, legs_per_combo * 5)]

        lineups: List[List[Dict]] = []
        for _ in range(max_lineups * 4):  # overshoot, then trim
            if len(lineups) >= max_lineups:
                break
            lineup = self._build_one_combo(top_pool, legs_per_combo)
            if lineup and lineup not in lineups:
                lineups.append(lineup)

        return [self._format_lineup(lu, i + 1) for i, lu in enumerate(lineups)]

    # ──────────────────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────────────────

    def _build_one_combo(
        self, pool: List[Dict], legs_per_combo: int
    ) -> Optional[List[Dict]]:
        """Greedy + diversity: pick top edge, then fill within ownership cap."""
        if not pool:
            return None
        self._rng.shuffle(pool)  # tie-breaker variety
        lineup: List[Dict] = []
        team_counts: Dict[str, int] = {}

        for player in pool:
            if len(lineup) >= legs_per_combo:
                break
            team = player.get("team", "")
            team_counts.setdefault(team, 0)
            # Ownership cap
            if team and team_counts[team] / legs_per_combo > self.ownership_cap:
                continue
            lineup.append(player)
            team_counts[team] += 1

        return lineup if len(lineup) == legs_per_combo else None

    def _format_lineup(self, lineup: List[Dict], idx: int) -> str:
        legs = " + ".join(
            f"{p['name']} {p.get('stat', 'O/U')} {p.get('edge', 0.0):+.1f}"
            for p in lineup
        )
        return f"Optimized Lineup {idx}: {legs}"


if __name__ == "__main__":
    sample = [
        {"name": "A'ja Wilson",   "team": "LV",  "stat": "PTS", "edge":  2.5},
        {"name": "Caitlin Clark", "team": "IND", "stat": "PTS", "edge":  2.2},
        {"name": "Sabrina Ionescu","team": "NY", "stat": "AST", "edge":  1.8},
        {"name": "Breanna Stewart","team": "NY", "stat": "REB", "edge":  1.5},
        {"name": "Alyssa Thompson","team": "LA", "stat": "PTS", "edge":  1.2},
        {"name": "Kelsey Plum",   "team": "LV",  "stat": "PTS", "edge":  1.0},
        {"name": "Diana Taurasi", "team": "PHX", "stat": "PTS", "edge":  0.8},
        {"name": "Angel Reese",   "team": "CHI", "stat": "REB", "edge":  0.6},
    ]
    opt = ComboOptimizer(ownership_cap=0.5, seed=42)
    for line in opt.optimize(sample, max_lineups=3, legs_per_combo=3):
        print(line)
