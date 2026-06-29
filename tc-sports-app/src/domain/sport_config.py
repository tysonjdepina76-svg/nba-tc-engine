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

# NFL_PRESEASON — same stat universe as regular NFL but with stricter thresholds.
# Preseason games: starters play 1-2 series, backups dominate snaps,
# many position battles → high variance. Stat keys identical for parity,
# but thresholds raise line_factor floor and edge_threshold.
NFL_PRESEASON_STAT_KEYS = [
    "PASS_YDS", "PASS_TD", "PASS_INT",
    "RUSH_YDS", "RUSH_TD", "RUSH_ATT",
    "REC", "REC_YDS", "REC_TD", "REC_TGT",
    "FUM",
]
NFL_PRESEASON_STAT_MAP = {
    "PASS_YDS":  "passingYards",
    "PASS_TD":   "passingTouchdowns",
    "PASS_INT":  "passingInterceptions",
    "RUSH_YDS":  "rushingYards",
    "RUSH_TD":   "rushingTouchdowns",
    "RUSH_ATT":  "rushingAttempts",
    "REC":       "receptions",
    "REC_YDS":   "receivingYards",
    "REC_TD":    "receivingTouchdowns",
    "REC_TGT":   "receivingTargets",
    "FUM":       "fumblesLost",
}
NFL_PRESEASON_POSITIONS = ["QB", "RB", "WR", "TE"]
NFL_PRESEASON_THRESHOLDS = {
    "line_factor":       0.85,    # lower confidence in snap projections
    "edge_threshold":    4.5,     # higher floor — variance is huge
    "min_sample_games":  1,       # preseason is short, accept tiny samples
    "qb_min_minutes":    12.0,    # starters play 1-2 drives only
    "skill_min_minutes": 8.0,     # backup WRs/TE need fewer snaps to qualify
    "out_factor":        0.0,
    "q_factor":          0.45,    # lower quality factor for preseason reps
    "max_snaps":         35,      # projection cap — preseason doesn't drive real lines
}


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




# NFL — full expansion (catches, combined yards, defense, special teams)
NFL_STAT_KEYS = ['PASS_YDS', 'PASS_TD', 'INT', 'PASS_RATING', 'COMP', 'ATT', 'COMP_PCT', 'RUSH_YDS', 'RUSH_TD', 'RUSH_ATT', 'YPC', 'REC', 'REC_YDS', 'REC_TD', 'TARGETS', 'YPR', 'COMBO_PASS_RUSH', 'COMBO_RUSH_REC', 'COMBO_REC_RUSH', 'TKL', 'AST_TKL', 'SACK', 'INT_DEF', 'FF', 'FR', 'PD', 'DEF_TD', 'QB_HIT', 'TFL', 'FG', 'FGA', 'XP', 'PUNT', 'PUNT_YDS', 'KR', 'KR_YDS', 'PR', 'PR_YDS']
NFL_STAT_MAP = {'PASS_YDS': 'passYds', 'PASS_TD': 'passTD', 'INT': 'int', 'PASS_RATING': 'passRating', 'COMP': 'comp', 'ATT': 'att', 'COMP_PCT': 'compPct', 'RUSH_YDS': 'rushYds', 'RUSH_TD': 'rushTD', 'RUSH_ATT': 'rushAtt', 'YPC': 'ypc', 'REC': 'rec', 'REC_YDS': 'recYds', 'REC_TD': 'recTD', 'TARGETS': 'targets', 'YPR': 'ypr', 'COMBO_PASS_RUSH': 'passRushYds', 'COMBO_RUSH_REC': 'rushRecYds', 'COMBO_REC_RUSH': 'recRushYds', 'TKL': 'tkl', 'AST_TKL': 'astTkl', 'SACK': 'sack', 'INT_DEF': 'intDef', 'FF': 'ff', 'FR': 'fr', 'PD': 'pd', 'DEF_TD': 'defTD', 'QB_HIT': 'qbHit', 'TFL': 'tfl', 'FG': 'fg', 'FGA': 'fga', 'XP': 'xp', 'PUNT': 'punt', 'PUNT_YDS': 'puntYds', 'KR': 'kr', 'KR_YDS': 'krYds', 'PR': 'pr', 'PR_YDS': 'prYds'}
NFL_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF', 'LB', 'DL', 'DB']
NFL_SCORING = {'pass_yds': 0.04, 'pass_td': 4, 'pass_int': -2, 'comp': 0.1, 'pass_rating': 0.1, 'rush_yds': 0.1, 'rush_td': 6, 'rush_att': 0.05, 'ypc': 0.2, 'rec': 0.5, 'rec_yds': 0.1, 'rec_td': 6, 'targets': 0.05, 'ypr': 0.2, 'combo_pass_rush': 0.06, 'combo_rush_rec': 0.1, 'combo_rec_rush': 0.1, 'tkl': 1, 'ast_tkl': 0.5, 'sack': 2, 'int_def': 2, 'ff': 2, 'fr': 2, 'fumble_lost': -2, 'pd': 1, 'def_td': 6, 'qb_hit': 1, 'tfl': 1.5, 'fg': 3, 'fga': -0.5, 'xp': 1, 'punt': 0.1, 'punt_yds': 0.01, 'kr': 0.5, 'kr_yds': 0.02, 'pr': 0.5, 'pr_yds': 0.02}
NFL_THRESHOLDS = {'line_factor': 0.88, 'edge_threshold': 3.0, 'min_sample_games': 4, 'qb_min_minutes': 50.0, 'skill_min_minutes': 15.0, 'out_factor': 0.0, 'q_factor': 0.55, 'min_attempts': 3, 'edge_min': 3.0}

# MLB — full expansion (batting, pitching, fielding, combo stats)
MLB_STAT_KEYS = ['AVG', 'HR', 'RBI', 'R', 'H', '2B', '3B', 'SB', 'CS', 'BB', 'K_BAT', 'OBP', 'SLG', 'OPS', 'HBP', 'SF', 'SH', '111', 'K_COMB', 'ERA', 'W', 'L', 'SV', 'HD', 'IP', 'K9', 'BB9', 'HA', 'ER', 'HRA', 'WHIP', 'K_BB', 'QS', 'CG', 'SHO', 'PO', 'A', 'E', 'FPCT', 'DP', 'PB', 'SBA', 'CSPCT']
MLB_STAT_MAP = {'AVG': 'avg', 'HR': 'hr', 'RBI': 'rbi', 'R': 'r', 'H': 'h', '2B': '2b', '3B': '3b', 'SB': 'sb', 'CS': 'cs', 'BB': 'bb', 'K_BAT': 'k', 'OBP': 'obp', 'SLG': 'slg', 'OPS': 'ops', 'HBP': 'hbp', 'SF': 'sf', 'SH': 'sh', '111': '111', 'K_COMB': 'kComb', 'ERA': 'era', 'W': 'w', 'L': 'l', 'SV': 'sv', 'HD': 'hd', 'IP': 'ip', 'K9': 'k9', 'BB9': 'bb9', 'HA': 'ha', 'ER': 'er', 'HRA': 'hra', 'WHIP': 'whip', 'K_BB': 'kbb', 'QS': 'qs', 'CG': 'cg', 'SHO': 'sho', 'PO': 'po', 'A': 'a', 'E': 'e', 'FPCT': 'fpct', 'DP': 'dp', 'PB': 'pb', 'SBA': 'sba', 'CSPCT': 'cspct'}
MLB_POSITIONS = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'OF', 'DH']
MLB_SCORING = {'batting_avg': 5, 'home_runs': 10, 'runs_batted_in': 5, 'runs': 3, 'hits': 3, 'doubles': 4, 'triples': 6, 'stolen_bases': 4, 'caught_stealing': -2, 'walks': 2, 'strikeouts_batting': -1, 'on_base_pct': 3, 'slugging_pct': 4, 'on_base_plus_slugging': 5, 'hit_by_pitch': 2, 'sacrifice_flies': 1, 'sacrifice_hits': 1, '1_plus_1_plus_1': 5, 'strikeouts_combined': 2, 'earned_run_average': -2, 'wins': 5, 'losses': -3, 'saves': 7, 'holds': 4, 'innings_pitched': 1, 'strikeouts_pitching': 2, 'walks_pitching': -1, 'hits_allowed': -1, 'earned_runs': -2, 'home_runs_allowed': -3, 'walks_plus_hits_per_inning': -3, 'strikeout_to_walk_ratio': 2, 'quality_starts': 3, 'complete_games': 5, 'shutouts': 10, 'putouts': 0.5, 'assists': 1, 'errors': -2, 'fielding_pct': 2, 'double_plays': 2, 'passed_balls': -1, 'stolen_bases_allowed': -1, 'caught_stealing_pct': 2}
MLB_THRESHOLDS = {'min_attempts': 3, 'edge_min': 2.0, 'line_factor': 0.85, 'edge_threshold': 2.0}

# Boxing — punches landed, accuracy, knockdowns, rounds, decision type
BOXING_STAT_KEYS = ['LANDED', 'THROWN', 'ACC_PCT', 'POWER_LANDED', 'POWER_THROWN', 'JABS_LANDED', 'JABS_THROWN', 'KD', 'KO', 'ROUNDS', 'ROUNDS_WON', 'ROUNDS_LOST', 'DECISION_TYPE', 'WEIGHT_CLASS']
BOXING_STAT_MAP = {'LANDED': 'landed', 'THROWN': 'thrown', 'ACC_PCT': 'accPct', 'POWER_LANDED': 'powerLanded', 'POWER_THROWN': 'powerThrown', 'JABS_LANDED': 'jabsLanded', 'JABS_THROWN': 'jabsThrown', 'KD': 'kd', 'KO': 'ko', 'ROUNDS': 'rounds', 'ROUNDS_WON': 'roundsWon', 'ROUNDS_LOST': 'roundsLost', 'DECISION_TYPE': 'decisionType', 'WEIGHT_CLASS': 'weightClass'}
BOXING_POSITIONS = ['Fighter']
BOXING_SCORING = {'punches_landed': 0.5, 'punches_thrown': 0.1, 'accuracy_pct': 2, 'power_punches_landed': 1, 'jabs_landed': 0.3, 'knockdowns': 10, 'knockouts': 20, 'rounds_won': 3, 'rounds': 1}
BOXING_THRESHOLDS = {'min_attempts': 2, 'edge_min': 2.0, 'line_factor': 0.85, 'edge_threshold': 2.0}

# MMA — strikes, takedowns, submissions, control time
MMA_STAT_KEYS = ['SIG_LANDED', 'SIG_THROWN', 'STRIKE_ACC', 'TD_LANDED', 'TD_ATTEMPTED', 'TD_ACC', 'SUB_ATTEMPTS', 'CONTROL_TIME', 'CONTROL_PCT', 'KD_MMA', 'KO_MMA', 'SUB', 'DEC', 'ROUNDS_MMA', 'ROUNDS_WON_MMA', 'WEIGHT_CLASS_MMA']
MMA_STAT_MAP = {'SIG_LANDED': 'sigStrikesLanded', 'SIG_THROWN': 'sigStrikesThrown', 'STRIKE_ACC': 'strikeAcc', 'TD_LANDED': 'tdLanded', 'TD_ATTEMPTED': 'tdAttempted', 'TD_ACC': 'tdAcc', 'SUB_ATTEMPTS': 'subAttempts', 'CONTROL_TIME': 'controlTime', 'CONTROL_PCT': 'controlPct', 'KD_MMA': 'kdMma', 'KO_MMA': 'koMma', 'SUB': 'sub', 'DEC': 'dec', 'ROUNDS_MMA': 'roundsMma', 'ROUNDS_WON_MMA': 'roundsWonMma', 'WEIGHT_CLASS_MMA': 'weightClassMma'}
MMA_POSITIONS = ['Fighter']
MMA_SCORING = {'significant_strikes_landed': 0.5, 'strikes_accuracy': 2, 'takedowns_landed': 3, 'takedown_accuracy': 2, 'submission_attempts': 3, 'control_time': 0.1, 'control_time_pct': 2, 'knockdowns_mma': 10, 'knockouts_mma': 20, 'submissions': 15, 'rounds_won_mma': 3, 'decisions': 5}
MMA_THRESHOLDS = {'min_attempts': 2, 'edge_min': 2.0, 'line_factor': 0.85, 'edge_threshold': 2.0}
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
        "stat_map": MLB_STAT_MAP,
        "positions": MLB_POSITIONS,
        "scoring": MLB_SCORING,
        "thresholds": MLB_THRESHOLDS,
        "line_factor": MLB_THRESHOLDS["line_factor"],
        "edge_threshold": MLB_THRESHOLDS["edge_threshold"],
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
        "scoring": NFL_SCORING,
        "thresholds": NFL_THRESHOLDS,
        "line_factor": NFL_THRESHOLDS["line_factor"],
        "edge_threshold": NFL_THRESHOLDS["edge_threshold"],
    },

    "BOXING": {
        "stat_keys": BOXING_STAT_KEYS,
        "stat_map": BOXING_STAT_MAP,
        "positions": BOXING_POSITIONS,
        "scoring": BOXING_SCORING,
        "thresholds": BOXING_THRESHOLDS,
        "line_factor": BOXING_THRESHOLDS["line_factor"],
        "edge_threshold": BOXING_THRESHOLDS["edge_threshold"],
    },

    "MMA": {
        "stat_keys": MMA_STAT_KEYS,
        "stat_map": MMA_STAT_MAP,
        "positions": MMA_POSITIONS,
        "scoring": MMA_SCORING,
        "thresholds": MMA_THRESHOLDS,
        "line_factor": MMA_THRESHOLDS["line_factor"],
        "edge_threshold": MMA_THRESHOLDS["edge_threshold"],
    },
}


def get_config(sport: str, phase: str = "REGULAR") -> Dict:
    """Return tuning for a sport. Defaults to WNBA if unknown.

    phase: "REGULAR" (default) or "PRESEASON" — used by NFL to pick between
    NFL_THRESHOLDS (full season) and NFL_PRESEASON_THRESHOLDS (preseason).
    Other sports ignore phase.
    """
    s = sport.upper()
    if s == "NFL" and phase.upper() == "PRESEASON":
        return {
            "stat_keys":      NFL_PRESEASON_STAT_KEYS,
            "stat_map":       NFL_PRESEASON_STAT_MAP,
            "positions":      NFL_PRESEASON_POSITIONS,
            "thresholds":     NFL_PRESEASON_THRESHOLDS,
            "line_factor":    NFL_PRESEASON_THRESHOLDS["line_factor"],
            "edge_threshold": NFL_PRESEASON_THRESHOLDS["edge_threshold"],
            "phase":          "PRESEASON",
        }
    if s in SPORT_CONFIG:
        cfg = dict(SPORT_CONFIG[s])
        cfg["phase"] = phase.upper()
        return cfg
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
