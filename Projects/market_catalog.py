"""Truthful cross-sport market catalog and projection-period normalization."""

from typing import Any, Dict, Iterable, List


BASKETBALL_STATS = ["PTS", "REB", "AST", "3PM", "STL", "BLK", "PRA", "PR", "RA"]
MLB_BATTER_STATS = ["H", "TB", "RBI", "R", "HR", "SB", "BB", "K"]
MLB_PITCHER_STATS = ["K", "OUTS", "H", "BB", "ER", "PITCHES"]
NFL_STATS = ["PASS_YDS", "PASS_ATT", "CMP", "PASS_TD", "INT", "RUSH_YDS", "RUSH_ATT", "REC", "REC_YDS", "REC_TD", "TARGETS", "TD"]
NHL_STATS = ["G", "A", "PTS", "SOG", "SAVES", "HITS", "BLOCKS"]
SOCCER_STATS = ["GOALS", "SHOTS", "SHOTS_ON_TARGET", "ASSISTS", "CORNERS", "CARDS", "FOULS"]

REAL_BOOK_SOURCES = {
    "DK", "DRAFTKINGS", "FANDUEL", "FD", "BETMGM", "CAESARS",
    "POINTSBET", "ESPN_ODDS", "ODDS_API", "BOOK", "BOOK_LINE",
}


def _source_token(source: Any) -> str:
    return str(source or "").strip().upper().replace("-", "_").replace(" ", "_")


def is_real_book_source(source: Any) -> bool:
    token = _source_token(source)
    return token in REAL_BOOK_SOURCES or any(
        token.startswith(prefix + "_") for prefix in REAL_BOOK_SOURCES
    )

PERIOD_PLAYER_STATS: Dict[str, Dict[str, List[str]]] = {
    "NBA": {"GAME": BASKETBALL_STATS, "Q1": BASKETBALL_STATS, "Q2": BASKETBALL_STATS, "Q3": BASKETBALL_STATS, "Q4": BASKETBALL_STATS, "1H": BASKETBALL_STATS, "2H": BASKETBALL_STATS},
    "WNBA": {"GAME": BASKETBALL_STATS, "Q1": BASKETBALL_STATS, "Q2": BASKETBALL_STATS, "Q3": BASKETBALL_STATS, "Q4": BASKETBALL_STATS, "1H": BASKETBALL_STATS, "2H": BASKETBALL_STATS},
    "MLB": {"GAME": MLB_BATTER_STATS + MLB_PITCHER_STATS, "1ST_INNING": MLB_BATTER_STATS + MLB_PITCHER_STATS, "2ND_INNING": MLB_BATTER_STATS + MLB_PITCHER_STATS, "3RD_INNING": MLB_BATTER_STATS + MLB_PITCHER_STATS, "F5": MLB_BATTER_STATS + MLB_PITCHER_STATS, "F9": MLB_BATTER_STATS + MLB_PITCHER_STATS},
    "NFL": {"GAME": NFL_STATS, "Q1": NFL_STATS, "Q2": NFL_STATS, "Q3": NFL_STATS, "Q4": NFL_STATS, "1H": NFL_STATS, "2H": NFL_STATS},
    "NHL": {"GAME": NHL_STATS, "P1": NHL_STATS, "P2": NHL_STATS, "P3": NHL_STATS},
    "SOCCER": {"GAME": SOCCER_STATS, "1H": SOCCER_STATS, "2H": SOCCER_STATS},
    "WC": {"GAME": SOCCER_STATS, "1H": SOCCER_STATS, "2H": SOCCER_STATS},
}

TEAM_MARKET_DEFINITIONS: Dict[str, Dict[str, List[str]]] = {
    "NBA": {"GAME": ["TEAM_TOTAL", "SPREAD", "TOTAL"], "Q1": ["TEAM_TOTAL", "TOTAL"], "1H": ["TEAM_TOTAL", "TOTAL"], "2H": ["TEAM_TOTAL", "TOTAL"]},
    "WNBA": {"GAME": ["TEAM_TOTAL", "SPREAD", "TOTAL"], "Q1": ["TEAM_TOTAL", "TOTAL"], "1H": ["TEAM_TOTAL", "TOTAL"], "2H": ["TEAM_TOTAL", "TOTAL"]},
    "MLB": {"GAME": ["TEAM_TOTAL", "TOTAL"], "1ST_INNING": ["INNING_RUNS", "NRFI", "YRFI"], "2ND_INNING": ["INNING_RUNS"], "3RD_INNING": ["INNING_RUNS"], "F5": ["F5_TOTAL", "TEAM_TOTAL"], "F9": ["TOTAL", "TEAM_TOTAL"]},
    "NFL": {"GAME": ["TEAM_TOTAL", "SPREAD", "TOTAL"], "Q1": ["TEAM_TOTAL", "TOTAL"], "1H": ["TEAM_TOTAL", "TOTAL"], "2H": ["TEAM_TOTAL", "TOTAL"]},
    "NHL": {"GAME": ["TEAM_TOTAL", "TOTAL"], "P1": ["PERIOD_GOALS", "TOTAL"], "P2": ["PERIOD_GOALS", "TOTAL"], "P3": ["PERIOD_GOALS", "TOTAL"]},
    "SOCCER": {"GAME": ["TEAM_TOTAL", "TOTAL", "BTTS"], "1H": ["TEAM_TOTAL", "TOTAL"], "2H": ["TEAM_TOTAL", "TOTAL"]},
    "WC": {"GAME": ["TEAM_TOTAL", "TOTAL", "BTTS"], "1H": ["TEAM_TOTAL", "TOTAL"], "2H": ["TEAM_TOTAL", "TOTAL"]},
}



MARKET_CATALOG: Dict[str, Dict[str, Any]] = {
    "NBA": {
        "periods": ["GAME", "Q1", "Q2", "Q3", "Q4", "1H", "2H"],
        "stats": BASKETBALL_STATS,
        "team_markets": ["TEAM_TOTAL", "SPREAD", "TOTAL", "FIRST_BASKET", "FIRST_3", "FIRST_5_MIN", "FIRST_10_MIN"],
    },
    "WNBA": {
        "periods": ["GAME", "Q1", "Q2", "Q3", "Q4", "1H", "2H"],
        "stats": BASKETBALL_STATS,
        "team_markets": ["TEAM_TOTAL", "SPREAD", "TOTAL", "FIRST_BASKET", "FIRST_3", "FIRST_5_MIN", "FIRST_10_MIN"],
    },
    "MLB": {
        "periods": ["GAME", "1ST_INNING", "2ND_INNING", "3RD_INNING", "F5", "F9"],
        "stats": MLB_BATTER_STATS + MLB_PITCHER_STATS,
        "team_markets": ["INNING_RUNS", "NRFI", "YRFI", "TEAM_TOTAL", "F5_TOTAL"],
    },
    "NFL": {
        "periods": ["GAME", "Q1", "Q2", "Q3", "Q4", "1H", "2H"],
        "stats": NFL_STATS,
        "team_markets": ["TEAM_TOTAL", "SPREAD", "TOTAL", "FIRST_SCORE", "FIRST_TD"],
    },
    "NHL": {
        "periods": ["GAME", "P1", "P2", "P3"],
        "stats": NHL_STATS,
        "team_markets": ["PERIOD_GOALS", "TEAM_TOTAL", "TOTAL", "FIRST_GOAL"],
    },
    "SOCCER": {
        "periods": ["GAME", "1H", "2H", "0_15", "16_30", "31_45", "46_60", "61_75", "76_90"],
        "stats": SOCCER_STATS,
        "team_markets": ["TEAM_TOTAL", "TOTAL", "BTTS", "FIRST_GOAL", "CORNERS", "CARDS"],
    },
    "WC": {
        "periods": ["GAME", "1H", "2H", "0_15", "16_30", "31_45", "46_60", "61_75", "76_90"],
        "stats": SOCCER_STATS,
        "team_markets": ["TEAM_TOTAL", "TOTAL", "BTTS", "FIRST_GOAL", "CORNERS", "CARDS"],
    },
}


_PERIOD_ALIASES = {
    "game": "GAME", "full_game": "GAME", "full": "GAME",
    "q1": "Q1", "1q": "Q1", "first_quarter": "Q1",
    "q2": "Q2", "2q": "Q2", "second_quarter": "Q2",
    "q3": "Q3", "3q": "Q3", "third_quarter": "Q3",
    "q4": "Q4", "4q": "Q4", "fourth_quarter": "Q4",
    "1h": "1H", "first_half": "1H", "half1": "1H",
    "2h": "2H", "second_half": "2H", "half2": "2H",
    "1st_inning": "1ST_INNING", "first_inning": "1ST_INNING", "inning_1": "1ST_INNING", "i1": "1ST_INNING",
    "2nd_inning": "2ND_INNING", "second_inning": "2ND_INNING", "inning_2": "2ND_INNING", "i2": "2ND_INNING",
    "3rd_inning": "3RD_INNING", "third_inning": "3RD_INNING", "inning_3": "3RD_INNING", "i3": "3RD_INNING",
    "f5": "F5", "first_five": "F5", "first_5": "F5",
    "f9": "F9", "first_nine": "F9",
    "p1": "P1", "period_1": "P1", "first_period": "P1",
    "p2": "P2", "period_2": "P2", "second_period": "P2",
    "p3": "P3", "period_3": "P3", "third_period": "P3",
}


def normalize_period(value: Any) -> str:
    raw = str(value or "GAME").strip().lower().replace("-", "_").replace(" ", "_")
    return _PERIOD_ALIASES.get(raw, str(value or "GAME").upper())


def _is_stat_value(value: Any) -> bool:
    return isinstance(value, (int, float)) or (isinstance(value, dict) and any(k in value for k in ("tc_projection", "projection", "mean", "line", "over_line", "dk_line")))


def iter_projection_stats(projections: Dict[str, Any]) -> Iterable[tuple[str, str, Any]]:
    """Yield (period, stat, value) from flat or period-nested projection data."""
    for key, value in (projections or {}).items():
        period = normalize_period(key)
        if isinstance(value, dict) and not _is_stat_value(value):
            for stat, stat_value in value.items():
                if _is_stat_value(stat_value):
                    yield period, str(stat).upper(), stat_value
        elif _is_stat_value(value):
            yield "GAME", str(key).upper(), value


def catalog_for(sport: str) -> Dict[str, Any]:
    return MARKET_CATALOG.get(str(sport or "").upper(), {"periods": ["GAME"], "stats": [], "team_markets": []})


def truth_metadata(*, market_line: Any, source: str, period: str) -> Dict[str, Any]:
    has_value = market_line is not None and str(market_line) not in ("", "0", "0.0", "None")
    has_real_line = bool(has_value and is_real_book_source(source))
    return {
        "period": normalize_period(period),
        "line_status": "REAL_LINE" if has_real_line else "NO_REAL_LINE",
        "alert_eligible": bool(has_real_line),
        "truth_note": "Sportsbook line present" if has_real_line else "Projection/reference line only; not a sportsbook +EV alert",
    }
