"""Sport configs: stats + thresholds per sport."""


class StatProfile:
    def __init__(self, key, label, weight=1.0, min_value=0.0, max_value=100.0):
        self.key = key
        self.label = label
        self.weight = weight
        self.min_value = min_value
        self.max_value = max_value

    def __contains__(self, item):
        return item == self.key

    def __eq__(self, other):
        return isinstance(other, StatProfile) and self.key == other.key


class SportConfig:
    def __init__(
        self,
        name,
        stats,
        primary_stat="pts",
        roster_size=13,
        primary_position_group="Wings",
        match_minutes=None,
        avg_minutes=None,
        mode="player",
    ):
        self.name = name
        self.stats = {s.key: s for s in stats}
        self.primary_stat = primary_stat
        self.roster_size = roster_size
        self.primary_position_group = primary_position_group
        self.match_minutes = match_minutes
        self.avg_minutes = avg_minutes if avg_minutes is not None else (match_minutes or 36)
        self.mode = mode

    def get_stat_keys(self):
        return list(self.stats.keys())

    def get_stat(self, key):
        return self.stats.get(key)


_NBA_STATS = [
    StatProfile("pts", "Points", 1.0, 0, 70),
    StatProfile("reb", "Rebounds", 0.9, 0, 30),
    StatProfile("ast", "Assists", 0.85, 0, 20),
    StatProfile("3pm", "3-Pointers Made", 0.9, 0, 10),
    StatProfile("stl", "Steals", 0.7, 0, 6),
    StatProfile("blk", "Blocks", 0.7, 0, 6),
    StatProfile("tov", "Turnovers", 0.6, 0, 10),
]

_WNBA_STATS = [
    StatProfile("pts", "Points", 1.0, 0, 50),
    StatProfile("reb", "Rebounds", 0.9, 0, 25),
    StatProfile("ast", "Assists", 0.85, 0, 15),
    StatProfile("3pm", "3-Pointers Made", 0.85, 0, 8),
    StatProfile("stl", "Steals", 0.7, 0, 5),
    StatProfile("blk", "Blocks", 0.6, 0, 5),
]

_MLB_STATS = [
    StatProfile("hits", "Hits", 1.0, 0, 5),
    StatProfile("hr", "Home Runs", 1.2, 0, 3),
    StatProfile("rbi", "RBIs", 1.0, 0, 8),
    StatProfile("runs", "Runs", 0.9, 0, 5),
    StatProfile("sb", "Stolen Bases", 0.8, 0, 3),
    StatProfile("so", "Strikeouts (P)", 1.1, 0, 15),
]

_NHL_STATS = [
    StatProfile("goals", "Goals", 1.0, 0, 4),
    StatProfile("assists", "Assists", 0.9, 0, 5),
    StatProfile("points", "Points", 1.0, 0, 8),
    StatProfile("shots", "Shots on Goal", 0.85, 0, 12),
    StatProfile("saves", "Saves (G)", 1.0, 0, 50),
]

_SOCCER_STATS = [
    StatProfile("goals", "Goals", 1.1, 0, 4),
    StatProfile("shots", "Shots", 0.85, 0, 12),
    StatProfile("sot", "Shots on Target", 0.95, 0, 8),
    StatProfile("assists", "Assists", 0.85, 0, 4),
    StatProfile("passes", "Passes", 0.6, 0, 120),
    StatProfile("tackles", "Tackles", 0.7, 0, 10),
]


SPORTS = {
    "NBA": SportConfig("NBA", _NBA_STATS, primary_stat="pts", roster_size=13, primary_position_group="Wings", avg_minutes=36),
    "WNBA": SportConfig("WNBA", _WNBA_STATS, primary_stat="pts", roster_size=12, primary_position_group="Wings", avg_minutes=34),
    "MLB": SportConfig("MLB", _MLB_STATS, primary_stat="hits", roster_size=9, primary_position_group="hitters", mode="hitter", avg_minutes=None),
    "NHL": SportConfig("NHL", _NHL_STATS, primary_stat="points", roster_size=20, primary_position_group="Forwards", avg_minutes=20),
    "EPL": SportConfig("EPL", _SOCCER_STATS, primary_stat="goals", roster_size=11, primary_position_group="Forwards", match_minutes=90, avg_minutes=90),
    "SOCCER": SportConfig("SOCCER", _SOCCER_STATS, primary_stat="goals", roster_size=11, primary_position_group="Forwards", match_minutes=90, avg_minutes=90),
}


def get_config(sport):
    if sport not in SPORTS:
        raise KeyError(f"Sport '{sport}' not configured. Available: {list(SPORTS.keys())}")
    return SPORTS[sport]


def list_sports():
    return list(SPORTS.keys())
