# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""RosterManager — track team rosters with player roles.

Usage:
    from src.domain.roster_manager import RosterManager
    rm = RosterManager("Boston Celtics")
    rm.add_player("Jayson Tatum", "SF", "STARTER")
    rm.add_player("Bench Guy", "SG")
    print(rm.to_dict())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.domain.entities import Player


@dataclass
class RosterManager:
    """Manage a team's roster with role tracking."""

    team_name: str
    players: List[Player] = field(default_factory=list)
    sport: str = "NBA"

    def add_player(self, name: str, position: str, role: str = "BENCH", player_id: str = "") -> Player:
        """Add a player to the roster."""
        p = Player(
            name=name,
            team=self.team_name,
            position=position,
            role=role,
            id=player_id or f"{self.team_name}_{name}".replace(" ", "_"),
        )
        self.players.append(p)
        return p

    def remove_player(self, name: str) -> bool:
        """Remove a player by name. Returns True if removed."""
        before = len(self.players)
        self.players = [p for p in self.players if p.name != name]
        return len(self.players) < before

    def starters(self) -> List[Player]:
        """Return only STARTER-role players."""
        return [p for p in self.players if p.role == "STARTER"]

    def bench(self) -> List[Player]:
        """Return BENCH-role players."""
        return [p for p in self.players if p.role == "BENCH"]

    def by_position(self, position: str) -> List[Player]:
        """Filter players by position."""
        return [p for p in self.players if p.position == position]

    def to_dict(self) -> dict:
        """Serialize roster to dict for JSON output."""
        return {
            "team": self.team_name,
            "sport": self.sport,
            "total": len(self.players),
            "starters": [
                {"name": p.name, "position": p.position, "role": p.role, "id": p.id}
                for p in self.starters()
            ],
            "bench": [
                {"name": p.name, "position": p.position, "role": p.role, "id": p.id}
                for p in self.bench()
            ],
        }


if __name__ == "__main__":
    import json
    rm = RosterManager("Boston Celtics")
    rm.add_player("Jayson Tatum", "SF", "STARTER")
    rm.add_player("Jrue Holiday", "PG", "STARTER")
    rm.add_player("Bench Guy", "SG")
    print(json.dumps(rm.to_dict(), indent=2))
