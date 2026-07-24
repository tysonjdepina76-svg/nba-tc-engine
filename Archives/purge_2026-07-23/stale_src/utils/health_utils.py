import datetime


def is_off_season(sport: str) -> bool:
    """Return True if sport is currently in off-season."""
    now = datetime.datetime.now()
    month = now.month

    off_season_map = {
        "nba": [6, 7, 8, 9],
        "nfl": [2, 3, 4, 5, 6, 7],
        "nhl": [7, 8, 9],
        "mlb": [11, 12, 1, 2],
        "wnba": [10, 11, 12, 1, 2],
    }
    return month in off_season_map.get(sport.lower(), [])


def get_sport_status(sport: str) -> dict:
    if is_off_season(sport):
        return {
            "status": "OK",
            "message": f"⏸️ OFF-SEASON (projection-only mode)",
            "enabled": False,
            "reason": "Seasonal",
        }
    return {"status": "OK", "message": "Active", "enabled": True}
