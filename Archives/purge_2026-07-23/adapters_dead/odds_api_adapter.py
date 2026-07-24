"""Odds API adapter with caching and fallback."""

import os
import requests
from typing import Dict, List, Optional, Any

from src.adapters.cache_adapter import CacheAdapter


class OddsAPIAdapter:
    """Adapter for The Odds API with cache and fallback."""

    BASE_URL = "https://api.the-odds-api.com/v4"

    SPORT_KEYS = {
        "mlb": "baseball_mlb",
        "wnba": "basketball_wnba",
        "wc": "soccer_fifa_world_cup",
        "nfl": "americanfootball_nfl",
        "nba": "basketball_nba",
        "nhl": "icehockey_nhl",
    }

    def __init__(self, api_key: Optional[str] = None, cache: Optional[CacheAdapter] = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        self.cache = cache or CacheAdapter()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TC-Sports-App/1.0"})

    def get_odds(self, sport: str, regions: str = "us", markets: str = "h2h,spreads,totals",
                 bookmakers: str = "draftkings,fanduel", odds_format: str = "american",
                 use_cache: bool = True) -> List[Dict[str, Any]]:
        sport_key = self.SPORT_KEYS.get(sport)
        if not sport_key:
            raise ValueError(f"Unsupported sport: {sport}")
        cache_key = f"odds_{sport}_{regions}_{markets}_{bookmakers}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        url = f"{self.BASE_URL}/sports/{sport_key}/odds"
        params = {"apiKey": self.api_key, "regions": regions, "markets": markets,
                  "oddsFormat": odds_format, "bookmakers": bookmakers}
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.cache.set(cache_key, data, ttl_seconds=300)
            return data
        except requests.exceptions.RequestException as e:
            print(f"Odds API error: {e}")
            return []

    def get_player_props(self, sport: str, player: Optional[str] = None,
                          use_cache: bool = True) -> List[Dict[str, Any]]:
        sport_key = self.SPORT_KEYS.get(sport)
        if not sport_key:
            return []
        cache_key = f"props_{sport}_{player or 'all'}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        url = f"{self.BASE_URL}/sports/{sport_key}/player-props"
        params = {"apiKey": self.api_key}
        if player:
            params["player"] = player
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.cache.set(cache_key, data, ttl_seconds=300)
            return data
        except requests.exceptions.RequestException as e:
            print(f"Player props error: {e}")
            return []

    def check_quota(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/usage"
        params = {"apiKey": self.api_key}
        try:
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
