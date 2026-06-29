# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""Player + Game dataclasses — pure data, no behavior, no I/O."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Sport(Enum):
    NBA = "NBA"
    WNBA = "WNBA"
    NFL = "NFL"
    MLB = "MLB"
    SOCCER = "SOCCER"
    NHL = "NHL"
    TENNIS = "TENNIS"
    GOLF = "GOLF"
    CFB = "CFB"
    CBB = "CBB"


BADGE_COLORS = {
    "SOCCER": "#2e7d32",
    "NFL":    "#1a237e",
    "NBA":    "#e65100",
    "WNBA":   "#4a148c",
    "MLB":    "#0d47a1",
    "NHL":    "#c62828",
    "TENNIS": "#2e7d32",
    "GOLF":   "#00695c",
    "CFB":    "#1a237e",
    "CBB":    "#e65100",
}


@dataclass
class Player:
    name: str
    team: str
    role: str = "BENCH"
    status: str = "ACTIVE"
    position: str = ""

    # Minutes expected to play
    minutes: float = 0.0

    # Season averages (per game) — keys are stat codes ("PTS", "REB", "AST", etc.)
    season_stats: Dict[str, float] = field(default_factory=dict)

    # Sport-specific role
    is_batter: bool = True

    def is_active(self) -> bool:
        return self.status.upper() == "ACTIVE"

    def is_questionable(self) -> bool:
        return self.status.upper() in ("QUESTIONABLE", "Q", "DOUBTFUL")

    def is_out(self) -> bool:
        return self.status.upper() in ("OUT", "INJURED", "DNP")


@dataclass
class Game:
    away_team: str
    home_team: str
    sport: str
    source: str = ""
    dk_total: Optional[float] = None
    odds: Dict[str, Optional[str]] = field(default_factory=dict)

    def matchup(self) -> str:
        return f"{self.away_team}@{self.home_team}"


@dataclass
class Projection:
    """One player + one stat. Pure output, no I/O."""
    player: str
    team: str
    role: str
    status: str
    stat: str
    tc_projection: float
    line: float
    edge: float
    direction: str
    valid: bool

    def to_dict(self) -> Dict:
        return {
            "player": self.player,
            "team": self.team,
            "role": self.role,
            "status": self.status,
            "stat": self.stat,
            "tc_projection": self.tc_projection,
            "line": self.line,
            "edge": self.edge,
            "direction": self.direction,
            "valid": self.valid,
        }
