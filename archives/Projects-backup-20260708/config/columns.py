"""Sport-specific stat column configuration.

Single source of truth for which columns the dashboard renders per sport.
get_stat_columns() returns:
  {
    'stats':   ['pts', 'reb', 'ast', ...],   # canonical snake_case keys
    'labels':  ['PTS', 'REB', 'AST', ...],   # display labels (same order)
    'aliases': {'pts': ['Pts', 'Points', ...], ...},  # field name aliases
  }
"""
from typing import Dict, List

SPORT_CONFIG: Dict[str, Dict[str, List]] = {
    "wnba": {
        "stats":  ["pts", "reb", "ast", "stl", "blk", "3pm", "fg_pct", "3p_pct", "ft_pct", "minutes"],
        "labels": ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "3P%", "FT%", "Minutes"],
    },
    "nba": {
        "stats":  ["pts", "reb", "ast", "stl", "blk", "3pm", "fg_pct", "3p_pct", "ft_pct", "minutes"],
        "labels": ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "3P%", "FT%", "Minutes"],
    },
    "mlb": {
        "stats":  ["hits", "hr", "rbi", "runs", "sb", "avg", "obp", "slg", "ops", "ip", "era", "whip", "strikeouts"],
        "labels": ["Hits", "HR", "RBI", "Runs", "SB", "Avg", "OBP", "SLG", "OPS", "IP", "ERA", "WHIP", "K"],
    },
    "nhl": {
        "stats":  ["goals", "assists", "points", "plus_minus", "sog", "hits", "blocks", "pim", "toi"],
        "labels": ["Goals", "Assists", "Points", "+/-", "SOG", "Hits", "Blocks", "PIM", "TOI"],
    },
    "nfl": {
        "stats":  ["pass_yds", "rush_yds", "rec_yds", "pass_td", "rush_td", "rec_td", "receptions", "ints", "cmp", "att"],
        "labels": ["Pass Yds", "Rush Yds", "Rec Yds", "Pass TD", "Rush TD", "Rec TD", "Receptions", "INT", "CMP", "ATT"],
    },
    "wc": {
        "stats":  ["goals", "assists", "shots", "sot", "passes", "tackles", "minutes", "yellow_cards", "red_cards"],
        "labels": ["Goals", "Assists", "Shots", "SOT", "Passes", "Tackles", "Minutes", "Yellow", "Red"],
    },
    "soccer": {
        "stats":  ["goals", "assists", "shots", "sot", "passes", "tackles", "minutes", "yellow_cards", "red_cards"],
        "labels": ["Goals", "Assists", "Shots", "SOT", "Passes", "Tackles", "Minutes", "Yellow", "Red"],
    },
}

DEFAULT_CONFIG = {
    "stats":  ["stat", "value"],
    "labels": ["Stat", "Value"],
}

FIELD_ALIASES: Dict[str, Dict[str, List[str]]] = {
    "wnba": {"pts": ["Pts", "Points", "PTS"], "reb": ["Reb", "Rebounds", "REB"],
             "ast": ["Ast", "Assists", "AST"], "3pm": ["3PM", "3pm", "3P Made"]},
    "mlb":  {"hits": ["Hits", "H"], "hr": ["HR", "Home Runs", "HomeRuns"],
             "rbi": ["RBI", "Runs Batted In"], "avg": ["Avg", "Batting Average", "BA"]},
    "nhl":  {"goals": ["Goals", "G"], "assists": ["Assists", "A"], "points": ["Points", "Pts", "PTS"]},
    "nfl":  {"pass_yds": ["Pass Yds", "PassYds", "Passing Yards"],
             "rush_yds": ["Rush Yds", "RushYds", "Rushing Yards"]},
    "wc":   {"goals": ["Goals", "G"], "assists": ["Assists", "A"], "shots": ["Shots", "SH"]},
}


def get_stat_columns(sport: str) -> Dict[str, object]:
    """Return {'stats': [...], 'labels': [...], 'aliases': {stat: [alias,...]}}."""
    key = (sport or "").lower()
    cfg = SPORT_CONFIG.get(key, DEFAULT_CONFIG)
    aliases = FIELD_ALIASES.get(key, {})
    return {"stats": cfg["stats"], "labels": cfg["labels"], "aliases": aliases}


# Backward compat: list-returning helper for callers that want just stats
def get_stat_list(sport: str) -> List[str]:
    return get_stat_columns(sport)["stats"]
