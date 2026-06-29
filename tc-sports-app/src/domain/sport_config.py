# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""Per-sport TC tuning. Single source of truth for stat keys + thresholds."""

from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Stat keys (abbreviations used in projections)
# ─────────────────────────────────────────────────────────────────────────────

WNBA_STAT_KEYS = ["PTS", "REB", "AST", "3PM", "STL", "BLK"]
NBA_STAT_KEYS = ["PTS", "REB", "AST", "3PM", "STL", "BLK"]

MLB_STAT_KEYS = [
    "HITS", "RBI", "RUNS", "HR", "TB", "SB", "BB",
    "K", "K_ALLOWED", "ER",
]

SOCCER_STAT_KEYS = ["G", "A", "SOT", "S", "COR", "TKL", "FC", "CRD", "PAS"]

# NFL: passing, rushing, receiving, defense
NFL_STAT_KEYS = [
    # Passing
    "PASS_YDS",     # passing yards
    "PASS_TD",      # passing TDs
    "PASS_INT",     # interceptions (lower is better)
    "PASS_ATT",     # attempts (volume)
    "PASS_COMP",    # completions (volume)
    # Rushing
    "RUSH_YDS",     # rushing yards
    "RUSH_TD",      # rushing TDs
    "RUSH_ATT",     # carries
    # Receiving
    "REC",          # receptions
    "REC_YDS",      # receiving yards
    "REC_TD",       # receiving TDs
    "REC_TGT",      # targets
    # Misc
    "FUM",          # fumbles lost (lower is better)
]


# ─────────────────────────────────────────────────────────────────────────────
# NFL stat map (TC code -> ESPN / odds-API field name)
# ─────────────────────────────────────────────────────────────────────────────

NFL_STAT_MAP: Dict[str, str] = {
    "PASS_YDS":  "passingYards",
    "PASS_TD":   "passingTouchdowns",
    "PASS_INT":  "passingInterceptions",
    "PASS_ATT":  "passingAttempts",
    "PASS_COMP": "passingCompletions",
    "RUSH_YDS":  "rushingYards",
    "RUSH_TD":   "rushingTouchdowns",
    "RUSH_ATT":  "rushingAttempts",
    "REC":       "receptions",
    "REC_YDS":   "receivingYards",
    "REC_TD":    "receivingTouchdowns",
    "REC_TGT":   "receivingTargets",
    "FUM":       "fumblesLost",
}


# ─────────────────────────────────────────────────────────────────────────────
# NFL position groups + scoring weights (for fantasy-style or DK scoring)
# ─────────────────────────────────────────────────────────────────────────────

NFL_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]

# Position → list of stats relevant for that position
NFL_POSITION_STATS: Dict[str, List[str]] = {
    "QB":   ["PASS_YDS", "PASS_TD", "PASS_INT", "RUSH_YDS", "RUSH_TD"],
    "RB":   ["RUSH_YDS", "RUSH_TD", "REC", "REC_YDS", "REC_TD", "FUM"],
    "WR":   ["REC", "REC_YDS", "REC_TD", "REC_TGT", "RUSH_YDS"],
    "TE":   ["REC", "REC_YDS", "REC_TD", "REC_TGT"],
    "K":    ["FGM", "FGA", "XPM", "XPA"],  # placeholders, TC focuses on main positions
    "DEF":  ["SACK", "INT", "FR", "DEF_TD"],  # team-level, future expansion
}

# Position → stat weighting for fantasy/DFS scoring
# (only relevant if Fantasy scoring is ever wired in)
NFL_SCORING: Dict[str, float] = {
    "pass_yds_per_yard":   0.04,   # 1 pt per 25 yds
    "pass_td":             4.0,
    "pass_int":           -2.0,
    "rush_yds_per_yard":   0.1,    # 1 pt per 10 yds
    "rush_td":             6.0,
    "rec_yds_per_yard":    0.1,    # 1 pt per 10 yds
    "rec_td":              6.0,
    "reception":           1.0,    # PPR — set to 0 for standard, 0.5 for half-PPR
    "fumble_lost":        -2.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# NFL thresholds (TC defaults — may need seasonal calibration)
# ─────────────────────────────────────────────────────────────────────────────

NFL_THRESHOLDS = {
    "line_factor":       0.88,    # same TC line factor as other sports
    "edge_threshold":    3.0,     # NFL is lower-variance, raise edge floor
    "min_sample_games":  4,       # projections need at least 4 games of history
    "qb_min_minutes":    50.0,    # QBs play full games
    "skill_min_minutes": 15.0,    # WR/RB/TE need real snap count
    "out_factor":        0.0,
    "q_factor":          0.55,
}


# ─────────────────────────────────────────────────────────────────────────────


NHL_STAT_KEYS = [
    "GOALS",      # goals scored
    "ASSISTS",    # assists
    "POINTS",     # goals + assists
    "SHOTS",      # shots on goal (volume)
    "SOG",        # shots on goal alt
    "Saves",      # goalies only
    "GA",         # goals against (goalies, lower is better)
    "PPP",        # power play points
    "SHOTS_BLOCKED",
    "HITS",
    "PIM",        # penalty minutes (volume)
]

NHL_STAT_MAP = {
    "GOALS":         "goals",
    "ASSISTS":       "assists",
    "POINTS":        "points",
    "SHOTS":         "shots",
    "SOG":           "shotsOnGoal",
    "SAVES":         "saves",
    "GA":            "goalsAgainst",
    "PPP":           "powerPlayPoints",
    "SHOTS_BLOCKED": "blockedShots",
    "HITS":          "hits",
    "PIM":           "penaltyMinutes",
}

NHL_POSITIONS = ["C", "LW", "RW", "D", "G"]

NHL_THRESHOLDS = {
    "line_factor":      0.88,
    "edge_threshold":   2.5,
    "min_sample_games": 5,
    "out_factor":       0.0,
    "q_factor":         0.55,
}


# ─────────────────────────────────────────────────────────────────────────────
# Future sports — placeholders (no data source wired yet)
# ─────────────────────────────────────────────────────────────────────────────

TENNIS_STAT_KEYS = ["ACES", "WINNERS", "UNFORCED_ERRORS", "FIRST_SERVE_PCT", "BREAK_POINTS", "DOUBLE_FAULTS"]
TENNIS_STAT_MAP = {
    "ACES": "aces", "WINNERS": "winners",
    "UNFORCED_ERRORS": "unforcedErrors",
    "FIRST_SERVE_PCT": "firstServePct",
    "BREAK_POINTS": "breakPoints",
    "DOUBLE_FAULTS": "doubleFaults",
}
TENNIS_POSITIONS = ["Singles", "Doubles"]
TENNIS_THRESHOLDS = {"line_factor": 0.85, "edge_threshold": 2.0, "min_sample_games": 3}

GOLF_STAT_KEYS = ["SCORE", "BIRDIES", "EAGLES", "BOGEYS", "FAIRWAYS", "GREENS"]
GOLF_STAT_MAP = {
    "SCORE": "score", "BIRDIES": "birdies",
    "EAGLES": "eagles", "BOGEYS": "bogeys",
    "FAIRWAYS": "fairwaysHit", "GREENS": "greensInRegulation",
}
GOLF_POSITIONS = ["Individual"]
GOLF_THRESHOLDS = {"line_factor": 0.85, "edge_threshold": 2.0, "min_sample_games": 3}

CFB_STAT_KEYS = ["PASS_YDS", "RUSH_YDS", "REC_YDS", "TD", "INT", "REC", "RUSH_ATT"]
CFB_STAT_MAP = {
    "PASS_YDS": "passingYards", "RUSH_YDS": "rushingYards",
    "REC_YDS": "receivingYards", "TD": "touchdowns",
    "INT": "interceptions", "REC": "receptions",
    "RUSH_ATT": "rushingAttempts",
}
CFB_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]
CFB_THRESHOLDS = {"line_factor": 0.88, "edge_threshold": 3.0, "min_sample_games": 3}

CBB_STAT_KEYS = ["PTS", "REB", "AST", "STL", "BLK", "TOV", "3PM"]
CBB_STAT_MAP = {
    "PTS": "points", "REB": "rebounds", "AST": "assists",
    "STL": "steals", "BLK": "blocks", "TOV": "turnovers",
    "3PM": "threes",
}
CBB_POSITIONS = ["PG", "SG", "SF", "PF", "C"]
CBB_THRESHOLDS = {"line_factor": 0.85, "edge_threshold": 2.0, "min_sample_games": 3}



# Master sport config (consumed everywhere)
# ─────────────────────────────────────────────────────────────────────────────

SPORT_CONFIG: Dict[str, Dict] = {
    "WNBA": {
        "stat_keys": WNBA_STAT_KEYS,
        "line_factor": 0.88,
        "edge_threshold": 2.0,
    },
    "NBA": {
        "stat_keys": NBA_STAT_KEYS,
        "line_factor": 0.88,
        "edge_threshold": 2.0,
    },
    "MLB": {
        "stat_keys": MLB_STAT_KEYS,
        "line_factor": 0.88,
        "edge_threshold": 2.0,
    },
    "SOCCER": {
        "stat_keys": SOCCER_STAT_KEYS,
        "line_factor": 0.88,
        "edge_threshold": 1.5,
    },

    "NHL": {
        "stat_keys":       NHL_STAT_KEYS,
        "stat_map":        NHL_STAT_MAP,
        "positions":       NHL_POSITIONS,
        "thresholds":      NHL_THRESHOLDS,
        "line_factor":     NHL_THRESHOLDS["line_factor"],
        "edge_threshold":  NHL_THRESHOLDS["edge_threshold"],
    },
    "TENNIS": {
        "stat_keys":       TENNIS_STAT_KEYS,
        "stat_map":        TENNIS_STAT_MAP,
        "positions":       TENNIS_POSITIONS,
        "thresholds":      TENNIS_THRESHOLDS,
        "line_factor":     TENNIS_THRESHOLDS["line_factor"],
        "edge_threshold":  TENNIS_THRESHOLDS["edge_threshold"],
        "status":          "not_added",
    },
    "GOLF": {
        "stat_keys":       GOLF_STAT_KEYS,
        "stat_map":        GOLF_STAT_MAP,
        "positions":       GOLF_POSITIONS,
        "thresholds":      GOLF_THRESHOLDS,
        "line_factor":     GOLF_THRESHOLDS["line_factor"],
        "edge_threshold":  GOLF_THRESHOLDS["edge_threshold"],
        "status":          "not_added",
    },
    "CFB": {
        "stat_keys":       CFB_STAT_KEYS,
        "stat_map":        CFB_STAT_MAP,
        "positions":       CFB_POSITIONS,
        "thresholds":      CFB_THRESHOLDS,
        "line_factor":     CFB_THRESHOLDS["line_factor"],
        "edge_threshold":  CFB_THRESHOLDS["edge_threshold"],
        "status":          "not_added",
    },
    "CBB": {
        "stat_keys":       CBB_STAT_KEYS,
        "stat_map":        CBB_STAT_MAP,
        "positions":       CBB_POSITIONS,
        "thresholds":      CBB_THRESHOLDS,
        "line_factor":     CBB_THRESHOLDS["line_factor"],
        "edge_threshold":  CBB_THRESHOLDS["edge_threshold"],
        "status":          "not_added",
    },
    "NFL": {
        "stat_keys": NFL_STAT_KEYS,
        "stat_map": NFL_STAT_MAP,
        "positions": NFL_POSITIONS,
        "position_stats": NFL_POSITION_STATS,
        "scoring": NFL_SCORING,
        "thresholds": NFL_THRESHOLDS,
        # top-level convenience aliases
        "line_factor": NFL_THRESHOLDS["line_factor"],
        "edge_threshold": NFL_THRESHOLDS["edge_threshold"],
    },
}


def get_config(sport: str) -> Dict:
    """Return tuning for a sport. Defaults to WNBA if unknown."""
    s = sport.upper()
    if s in SPORT_CONFIG:
        return SPORT_CONFIG[s]
    return SPORT_CONFIG["WNBA"]


def stat_keys(sport: str) -> List[str]:
    return get_config(sport)["stat_keys"]

get_sport_config = get_config

def get_nfl_stat_map() -> Dict[str, str]:
    return dict(NFL_STAT_MAP)


def get_nfl_positions() -> List[str]:
    return list(NFL_POSITIONS)


def get_nfl_scoring() -> Dict[str, float]:
    return dict(NFL_SCORING)
