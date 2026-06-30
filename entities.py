"""Domain entities: Player, Game, Projection, Team, Boxscore, PlayerStats."""

from enum import Enum
from dataclasses import dataclass, field


class GameStatus(Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINAL = "final"
    POSTPONED = "postponed"


@dataclass
class Team:
    abbr: str
    name: str = ""
    score: int = 0

    @classmethod
    def from_str(cls, abbr):
        if isinstance(abbr, str) and len(abbr) <= 4 and abbr.isupper():
            return cls(abbr=abbr, name=abbr)
        return cls(abbr=str(abbr), name=str(abbr))


@dataclass
class Player:
    id: str
    name: str
    team: str
    position: str
    stats: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d["id"],
            name=d["name"],
            team=d["team"],
            position=d["position"],
            stats=dict(d.get("stats", {})),
        )

    def get_stat(self, key):
        if key not in self.stats:
            raise KeyError(f"Stat '{key}' not found on {self.name}")
        return self.stats[key]

    @property
    def minutes_avg(self):
        return self.stats.get("min", 0.0)

    def __repr__(self):
        return f"<Player {self.name} ({self.team})>"


@dataclass
class Game:
    id: str
    sport: str
    home: str
    away: str
    start_time: str = ""
    home_team: Team = None
    away_team: Team = None
    status: GameStatus = GameStatus.SCHEDULED

    @classmethod
    def from_dict(cls, d):
        status = d.get("status", "scheduled")
        if isinstance(status, str):
            try:
                status = GameStatus(status)
            except ValueError:
                status = GameStatus.SCHEDULED
        return cls(
            id=d["id"],
            sport=d["sport"],
            home=d["home"],
            away=d["away"],
            start_time=d.get("start_time"),
            status=status,
            home_team=Team.from_str(d["home"]),
            away_team=Team.from_str(d["away"]),
        )

    @property
    def matchup(self):
        return f"{self.away} @ {self.home}"

    @property
    def is_scheduled(self):
        return self.status == GameStatus.SCHEDULED

    @property
    def is_final(self):
        return self.status == GameStatus.FINAL


@dataclass
class PlayerStats:
    player_id: str
    player_name: str
    team: str
    minutes: float
    stats: dict = field(default_factory=dict)


@dataclass
class Boxscore:
    game_id: str
    sport: str
    player_stats: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d, sport="NBA"):
        ps = []
        for entry in d.get("boxscore", {}).get("players", []):
            player = entry.get("player", {})
            stats_dict = entry.get("stats", {})
            mins_raw = stats_dict.get("minutes", "0")
            try:
                minutes = float(str(mins_raw).replace(":", "."))
            except (ValueError, TypeError):
                minutes = 0.0
            ps.append(PlayerStats(
                player_id=str(player.get("id", "")),
                player_name=player.get("displayName", ""),
                team=entry.get("team", ""),
                minutes=minutes,
                stats=dict(stats_dict),
            ))
        return cls(game_id=str(d.get("gameId", "")), sport=sport, player_stats=ps)


@dataclass
class Projection:
    player_id: str
    player_name: str
    team: str
    stat: str
    line: float
    projection: float
    std_dev: float
    direction: str

    @classmethod
    def from_dict(cls, d):
        direction = d["direction"]
        if direction not in ("OVER", "UNDER"):
            raise ValueError(f"direction must be OVER or UNDER, got {direction!r}")
        return cls(
            player_id=d["player_id"],
            player_name=d["player_name"],
            team=d["team"],
            stat=d["stat"],
            line=float(d["line"]),
            projection=float(d["projection"]),
            std_dev=float(d["std_dev"]),
            direction=direction,
        )

    @property
    def edge_pct(self):
        if self.line == 0:
            return 0.0
        if self.direction == "OVER":
            return round(((self.projection - self.line) / self.line) * 100, 2)
        return round(((self.line - self.projection) / self.line) * 100, 2)

    @property
    def confidence(self):
        sd = max(self.std_dev, 0.1)
        raw = 0.5 + (self.projection - self.line) / (2 * sd)
        if self.direction == "UNDER":
            raw = 0.5 + (self.line - self.projection) / (2 * sd)
        return round(min(1.0, max(0.0, raw)), 4)

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team": self.team,
            "stat": self.stat,
            "line": self.line,
            "projection": self.projection,
            "std_dev": self.std_dev,
            "direction": self.direction,
        }
