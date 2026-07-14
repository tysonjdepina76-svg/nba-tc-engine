"""
ESPN Odds Fetcher — pulls odds from ESPN's core API.
Falls back to empty games list if API is unreachable or rate-limited.
"""

import requests
from typing import Dict, List
from sources.utils.cache import cache_fetch
from sources.utils.logging import get_logger

logger = get_logger(__name__)

SPORT_PATHS = {
    "wnba": "basketball/wnba",
    "nba": "basketball/nba",
    "mlb": "baseball/mlb",
    "nfl": "football/nfl",
    "nhl": "hockey/nhl",
    "soccer": "soccer/usa.1",
    "wc": "soccer/usa.1",
}


def _fetch_espn_odds(sport: str) -> Dict:
    path = SPORT_PATHS.get(sport)
    if not path:
        return {"source": f"espn_odds_{sport}", "games": [], "error": "unknown sport"}
    url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/odds"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"ESPN odds fetch failed for {sport}: {e}")
        return {"source": f"espn_odds_{sport}", "games": [], "error": str(e)}

    games = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        odds_list = comp.get("odds", [])
        game = {
            "id": event.get("id"),
            "home": comp.get("competitors", [{}, {}])[1].get("team", {}).get("displayName"),
            "away": comp.get("competitors", [{}, {}])[0].get("team", {}).get("displayName"),
            "start_time": event.get("date"),
            "status": event.get("status", {}).get("type", {}).get("description"),
            "odds": [
                {
                    "provider": o.get("provider", {}).get("name"),
                    "spread": o.get("details"),
                    "over_under": o.get("overUnder"),
                    "home_ml": o.get("homeTeamOdds", {}).get("moneyLine"),
                    "away_ml": o.get("awayTeamOdds", {}).get("moneyLine"),
                }
                for o in odds_list
            ],
        }
        games.append(game)
    return {"source": f"espn_odds_{sport}", "games": games}


def fetch_espn_odds(sport: str) -> Dict:
    return cache_fetch(f"espn_odds_{sport}", lambda: _fetch_espn_odds(sport), ttl_hours=0.5)
