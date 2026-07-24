"""
Sport stat configurations.
"""

SPORT_COLUMNS = {
    "mlb": {
        "stats": ["avg", "hr", "rbi", "r", "sb", "ops", "era", "whip", "so"],
        "labels": ["AVG", "HR", "RBI", "R", "SB", "OPS", "ERA", "WHIP", "SO"],
        "aliases": {"avg": "AVG", "hr": "HR", "rbi": "RBI", "r": "R", "sb": "SB", "ops": "OPS", "era": "ERA", "whip": "WHIP", "so": "SO"}
    },
    "wnba": {
        "stats": ["pts", "reb", "ast", "fg_pct", "fg3", "stl", "blk"],
        "labels": ["PTS", "REB", "AST", "FG%", "3PM", "STL", "BLK"],
        "aliases": {"pts": "PTS", "reb": "REB", "ast": "AST", "fg_pct": "FG%", "fg3": "3PM", "stl": "STL", "blk": "BLK"}
    },
    "nba": {
        "stats": ["pts", "reb", "ast", "fg_pct", "fg3", "stl", "blk"],
        "labels": ["PTS", "REB", "AST", "FG%", "3PM", "STL", "BLK"],
        "aliases": {"pts": "PTS", "reb": "REB", "ast": "AST", "fg_pct": "FG%", "fg3": "3PM", "stl": "STL", "blk": "BLK"}
    },
    "nfl": {
        "stats": ["pass_yds", "rush_yds", "rec_yds", "td", "int", "sacks"],
        "labels": ["PASS YDS", "RUSH YDS", "REC YDS", "TD", "INT", "SACKS"],
        "aliases": {"pass_yds": "PASS YDS", "rush_yds": "RUSH YDS", "rec_yds": "REC YDS", "td": "TD", "int": "INT", "sacks": "SACKS"}
    },
    "nhl": {
        "stats": ["goals", "assists", "points", "sog", "pim"],
        "labels": ["Goals", "Assists", "Points", "SOG", "PIM"],
        "aliases": {"goals": "Goals", "assists": "Assists", "points": "Points", "sog": "SOG", "pim": "PIM"}
    },
    "wc": {
        "stats": ["goals", "assists", "shots", "shots_on_target", "pass_pct", "tackles", "fouls"],
        "labels": ["Goals", "Assists", "Shots", "SOT", "Pass%", "Tackles", "Fouls"],
        "aliases": {"goals": "Goals", "assists": "Assists", "shots": "Shots", "shots_on_target": "SOT", "pass_pct": "Pass%", "tackles": "Tackles", "fouls": "Fouls"}
    }
}

def get_stat_columns(sport):
    return SPORT_COLUMNS.get(sport, SPORT_COLUMNS.get("mlb"))

def get_stat_aliases(sport):
    return get_stat_columns(sport).get("aliases", {})
