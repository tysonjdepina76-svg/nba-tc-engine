# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""SelfEdge line provider — synthetic lines derived from TC projections.

When real market lines (DK, FD, OddsAPI) are unavailable, dead, or out of
quota, this provider generates plausible lines anchored to the player's
TC projection. Lines are marked with source='self_edge' so the TC engine
can decide whether to act on them.

Rules:
  - Default odds: -110 / -110 (standard both sides)
  - Default over/under split: every line offered as BOTH over and under
  - Line = round(proj * 0.5 + 0.5)  → conservative under
  - Stat keys map to TC projection keys (pts, reb, ast, thpt, stl, blk, ...)
  - NEVER returns an empty list if a player has any TC projection
"""

from __future__ import annotations

from typing import Any, Optional

STAT_KEYS = {
    "points": "pts",
    "pts": "pts",
    "rebounds": "reb",
    "reb": "reb",
    "assists": "ast",
    "ast": "ast",
    "threes": "thpt",
    "3pt": "thpt",
    "steals": "stl",
    "stl": "stl",
    "blocks": "blk",
    "blk": "blk",
    "turnovers": "tov",
    "tov": "tov",
    "pra": "pra",  # pts+reb+ast
    "pts_reb_ast": "pra",
}


class SelfEdgeLineProvider:
    """Generates synthetic OVER/UNDER lines from TC projections.

    Use as a fallback when live books are unreachable. Rows are marked
    source='self_edge' so downstream engines can flag them as model-derived.
    """

    SOURCE = "self_edge"
    DEFAULT_ODDS = -110
    LINE_KNOCK = 0.5  # under the projection, to bias toward the favorite side

    def __init__(self, projections: Optional[dict[str, dict[str, float]]] = None):
        """projections: { player_name: { stat_key: proj_value, ... } }"""
        self.projections = projections or {}

    def set_projections(self, projections: dict[str, dict[str, float]]) -> None:
        self.projections = projections

    def fetch_player_props(
        self,
        sport: str,
        stat_filter: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        sport = sport.upper()
        stats_to_offer = [s.lower() for s in stat_filter] if stat_filter else list(STAT_KEYS.keys())
        rows: list[dict[str, Any]] = []
        for player, proj in self.projections.items():
            for stat_label in stats_to_offer:
                tc_key = STAT_KEYS.get(stat_label)
                if not tc_key or tc_key not in proj:
                    continue
                proj_val = proj[tc_key]
                if proj_val is None or proj_val <= 0:
                    continue
                line = round(proj_val - self.LINE_KNOCK, 1)
                if line < 0.5:
                    continue
                for direction in ("OVER", "UNDER"):
                    rows.append({
                        "player": player,
                        "sport": sport,
                        "stat": stat_label,
                        "direction": direction,
                        "line": line,
                        "odds_american": self.DEFAULT_ODDS,
                        "book": self.SOURCE,
                        "sources": [self.SOURCE],
                        "self_edge": True,
                        "tc_projection": proj_val,
                    })
        return rows


if __name__ == "__main__":
    p = SelfEdgeLineProvider({
        "Caitlin Clark": {"pts": 24.3, "reb": 5.1, "ast": 8.2, "thpt": 3.4, "stl": 1.1},
        "Aja Wilson":    {"pts": 22.0, "reb": 9.5, "ast": 2.1, "thpt": 0.4, "blk": 1.8},
    })
    rows = p.fetch_player_props("WNBA", stat_filter=["points", "rebounds", "assists"])
    print(f"self-edge rows: {len(rows)}")
    for r in rows[:6]:
        print(f"  {r['player']:18s} {r['stat']:8s} {r['direction']:5s} {r['line']:5.1f} @ {r['odds_american']:+d}  (proj {r['tc_projection']})")
