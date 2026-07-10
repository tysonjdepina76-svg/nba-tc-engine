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
    StatProfile("avg", "Batting Average", 1.0, 0.0, 1.0),
    StatProfile("hits", "Hits", 1.0, 0, 5),
    StatProfile("hr", "Home Runs", 1.2, 0, 3),
    StatProfile("rbi", "RBIs", 1.0, 0, 8),
    StatProfile("runs", "Runs", 0.9, 0, 5),
    StatProfile("sb", "Stolen Bases", 0.8, 0, 3),
    StatProfile("ops", "On-Base Plus Slugging", 1.0, 0.0, 1.5),
    StatProfile("era", "Earned Run Average (P)", 1.0, 0.0, 15.0),
    StatProfile("so", "Strikeouts (P)", 1.1, 0, 15),
]

_NHL_STATS = [
    StatProfile("goals", "Goals", 1.0, 0, 4),
    StatProfile("assists", "Assists", 0.9, 0, 5),
    StatProfile("points", "Points", 1.0, 0, 8),
    StatProfile("plus_minus", "Plus/Minus", 0.7, -5, 5),
    StatProfile("shots", "Shots on Goal", 0.85, 0, 12),
    StatProfile("hits", "Hits", 0.7, 0, 20),
    StatProfile("pim", "Penalty Minutes", 0.7, 0, 30),
    StatProfile("saves", "Saves (G)", 1.0, 0, 50),
]

_SOCCER_STATS = [
    StatProfile("goals", "Goals", 1.1, 0, 4),
    StatProfile("assists", "Assists", 0.85, 0, 4),
    StatProfile("shots", "Shots", 0.85, 0, 12),
    StatProfile("sot", "Shots on Target", 0.95, 0, 8),
    StatProfile("passes", "Passes", 0.6, 0, 120),
    StatProfile("tackles", "Tackles", 0.7, 0, 10),
    StatProfile("yellow_cards", "Yellow Cards", 0.7, 0, 2),
    StatProfile("red_cards", "Red Cards", 0.9, 0, 1),
]



# === NFL STATS (2026-06-30) ===
_NFL_STATS = [
    StatProfile("pass_yds", "Passing Yards", 1.0, 0, 500),
    StatProfile("pass_td", "Passing TDs", 1.2, 0, 6),
    StatProfile("pass_int", "Interceptions", 0.7, 0, 5),
    StatProfile("rush_yds", "Rushing Yards", 0.9, 0, 200),
    StatProfile("rush_td", "Rushing TDs", 1.1, 0, 4),
    StatProfile("rec_yds", "Receiving Yards", 0.85, 0, 250),
    StatProfile("rec_td", "Receiving TDs", 1.1, 0, 3),
    StatProfile("receptions", "Receptions", 0.8, 0, 15),
    StatProfile("targets", "Targets", 0.6, 0, 20),
    StatProfile("fantasy_pts", "Fantasy Points (PPR)", 1.0, 0, 50),
]


SPORTS = {
    "NBA": SportConfig("NBA", _NBA_STATS, primary_stat="pts", roster_size=13, primary_position_group="Wings", avg_minutes=36),
    "WNBA": SportConfig("WNBA", _WNBA_STATS, primary_stat="pts", roster_size=12, primary_position_group="Wings", avg_minutes=34),
    "MLB": SportConfig("MLB", _MLB_STATS, primary_stat="hits", roster_size=9, primary_position_group="hitters", mode="hitter", avg_minutes=None),
    "NHL": SportConfig("NHL", _NHL_STATS, primary_stat="points", roster_size=20, primary_position_group="Forwards", avg_minutes=20),
    "EPL": SportConfig("EPL", _SOCCER_STATS, primary_stat="goals", roster_size=11, primary_position_group="Forwards", match_minutes=90, avg_minutes=90),
    "SOCCER": SportConfig("SOCCER", _SOCCER_STATS, primary_stat="goals", roster_size=11, primary_position_group="Forwards", match_minutes=90, avg_minutes=90),
    "NFL": SportConfig("NFL", _NFL_STATS, primary_stat="pass_yds", roster_size=11, primary_position_group="QB/RB/WR", match_minutes=60, avg_minutes=60, mode="player"),
}


def get_config(sport):
    if sport not in SPORTS:
        raise KeyError(f"Sport '{sport}' not configured. Available: {list(SPORTS.keys())}")
    return SPORTS[sport]


def list_sports():
    return list(SPORTS.keys())


# === NFL PLAYER TIERS (2026-06-30) ===
# Elite/good/average/bad multipliers applied to player stat projections.
# Use to grade player quality before applying adjustments.
NFL_PLAYER_TIERS = {
    "elite":     1.20,
    "good":      1.05,
    "average":   1.00,
    "poor":      0.92,
    "bench":     0.80,
}

# === NFL PROP COMBOS (2026-06-30) ===
# Stat pair multipliers (both legs hit → bonus). Designed for parlay building.
# Each combo weights the legs and provides a synergy bonus when both hit.
NFL_PROP_COMBOS = {
    "pass_yds+rush_yds":  1.10,  # dual-threat QBs
    "rec_yds+receptions": 1.15,  # possession WRs
    "pass_td+pass_yds":   1.12,  # big-QB games
    "rush_td+rush_yds":   1.08,  # workhorse RBs
    "rec_td+rec_yds":     1.10,  # red-zone WRs
    "receptions+targets": 1.20,  # high-volume pass catchers
    "fantasy_pts+pass_yds": 1.18,  # strong QB correlation
    "fantasy_pts+rush_yds": 1.16,  # strong RB correlation
    "fantasy_pts+rec_yds":   1.14,  # strong WR correlation
    "pass_td+rush_td":       1.09,  # goal-line offense
}

# === NFL PROP COMBO BUILDER (2026-06-30) ===
def nfl_prop_combo_legs(stats_a: dict, stats_b: dict) -> list:
    """Build combo legs for two NFL players (Mahomes+Kelce, etc).
    Returns list of (stat, weight) tuples for parlay building.
    Uses NFL_PROP_COMBOS to apply synergy bonus between correlated stats.
    """
    legs = []
    for s, w in [("pass_yds", 1.0), ("pass_td", 1.2),
                  ("rush_yds", 0.9), ("rush_td", 1.1),
                  ("rec_yds", 0.85), ("rec_td", 1.1),
                  ("receptions", 0.8), ("targets", 0.6)]:
        legs.append((s, w))
    # Synergy boost when both players have stat in their profile
    a_keys = set(stats_a.get("keys", []))
    b_keys = set(stats_b.get("keys", []))
    shared = a_keys & b_keys
    for combo, mult in NFL_PROP_COMBOS.items():
        s1, s2 = combo.split("+")
        if s1 in shared and s2 in shared:
            legs.append((combo, mult))
    return legs

# === NFL POSITION CONSTANTS (2026-06-30) ===
# Used for snap share, target share, and red-zone touches.
NFL_POSITIONS = {
    "QB": {"max_snaps": 1.0, "primary_stats": ["pass_yds", "pass_td", "rush_yds"]},
    "RB": {"max_snaps": 0.70, "primary_stats": ["rush_yds", "rush_td", "rec_yds"]},
    "WR": {"max_snaps": 0.95, "primary_stats": ["rec_yds", "rec_td", "receptions"]},
    "TE": {"max_snaps": 0.85, "primary_stats": ["rec_yds", "rec_td", "receptions"]},
    "OL": {"max_snaps": 1.0, "primary_stats": []},  # no fantasy stats
    "DL": {"max_snaps": 0.85, "primary_stats": []},
    "LB": {"max_snaps": 0.95, "primary_stats": []},
    "DB": {"max_snaps": 0.95, "primary_stats": []},
}

# === NFL ADJUSTMENTS (re-added 2026-06-30) ===
