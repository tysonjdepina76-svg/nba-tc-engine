"""
Priority-based sports scheduler — ensures quota is used wisely.
"""

from datetime import datetime
from typing import List

SPORT_PRIORITY = {
    "WNBA": 1,
    "MLB": 2,
    "WC": 3,
    "NFL": 4,
    "NBA": 5,
    "NHL": 6,
}

ACTIVE_SPORTS = ["WNBA", "MLB", "WC"]
OFF_SEASON_SPORTS = ["NBA", "NHL", "NFL"]


def get_sports_to_fetch() -> List[str]:
    """Return sports to fetch based on priority and time of day."""
    now = datetime.now()
    hour = now.hour

    if 6 <= hour < 9:
        return ["WNBA", "MLB"]
    elif 9 <= hour < 12:
        return ["WC"]
    elif 12 <= hour < 15:
        return ["NFL"]
    else:
        return []


def get_all_active_sports() -> List[str]:
    """Return all active (in-season) sports — bypasses hour logic. For tests/backfills."""
    return list(ACTIVE_SPORTS)
