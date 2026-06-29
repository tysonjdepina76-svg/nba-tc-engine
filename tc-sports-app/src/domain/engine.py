# TC — Triple Conservative — Trademark June 2026 — All rights reserved.

"""TC engine facade — sport-aware projection entrypoint."""

from typing import Dict, List, Optional

from src.domain.entities import Player, Projection, Sport
from src.domain.sport_config import get_config, get_sport_config


class TCEngine:
    """Lightweight facade: instantiates sport config and exposes stat_keys + line_factor."""

    SUPPORTED_SPORTS = {"NBA", "WNBA", "NFL", "MLB", "SOCCER", "NHL", "TENNIS", "GOLF", "CFB", "CBB"}

    def __init__(self, sport: str):
        if sport.upper() not in self.SUPPORTED_SPORTS:
            raise ValueError(f"Unsupported sport: {sport}")
        self.sport = sport.upper()
        self.config = get_config(self.sport)

    @property
    def stat_keys(self) -> List[str]:
        return self.config.get("stat_keys", [])

    @property
    def line_factor(self) -> float:
        return self.config.get("line_factor", 0.88)

    @property
    def edge_threshold(self) -> float:
        return self.config.get("edge_threshold", 2.0)

    def project(self, player: Player, stat: str, line: Optional[float] = None) -> Projection:
        raw_avg = (player.season_stats or {}).get(stat, 0.0) or 0.0
        base_line = line if line is not None else raw_avg * self.line_factor
        edge = raw_avg - base_line
        direction = "OVER" if edge > 0 else "UNDER"
        return Projection(
            player=player.name,
            team=player.team,
            role=player.role,
            status=player.status,
            stat=stat,
            tc_projection=round(raw_avg, 2),
            line=round(base_line, 2),
            edge=round(edge, 2),
            direction=direction,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Legacy function aliases — kept for backward compatibility with /api/tc
# ─────────────────────────────────────────────────────────────────────────────

def compute_line_and_edge(raw_avg: float, line_factor: float = 0.88, line: Optional[float] = None) -> Dict[str, float]:
    """Compute base line and edge from a raw average."""
    base_line = line if line is not None else raw_avg * line_factor
    edge = raw_avg - base_line
    return {"line": round(base_line, 2), "edge": round(edge, 2), "direction": "OVER" if edge > 0 else "UNDER"}


def compute_tc_projection(player: Player, stat: str, line: Optional[float] = None) -> Projection:
    """Compute a TC projection for a single player+stat."""
    engine = TCEngine(player.position if hasattr(player, "position") else "WNBA")
    return engine.project(player, stat, line)


def project_player(player: Player, stat: str, line: Optional[float] = None) -> Projection:
    return compute_tc_projection(player, stat, line)


def project_game(sport: str, players: List[Player]) -> List[Projection]:
    engine = TCEngine(sport)
    out: List[Projection] = []
    for p in players:
        for stat in engine.stat_keys:
            out.append(engine.project(p, stat))
    return out