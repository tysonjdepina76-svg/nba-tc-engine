"""Enterprise OddsAPIAdapter with caching, retries, and quota-safe fallback.

Wraps the existing src.adapters.odds_api module so we can keep quota guards
and the on-disk APICache, while adding the SimpleCacheAdapter layer and a
clean class interface for the Streamlit dashboard.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, List, Dict, Any

from .cache_adapter import SimpleCacheAdapter
from . import odds_api as _internal_odds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ODDS_BASE = "https://api.the-odds-api.com/v4"

SPORT_KEY_MAP = {
    "basketball_nba": "basketball",
    "basketball_euroleague": "euroleague",
    "baseball_mlb": "baseball",
    "icehockey_nhl": "hockey",
    "americanfootball_nfl": "football",
    "soccer_uefa_champs_league": "soccer",
}

LEAGUE_PATH_MAP = {
    "basketball": "basketball_nba",
    "euroleague": "basketball_euroleague",
    "baseball": "baseball_mlb",
    "hockey": "icehockey_nhl",
    "football": "americanfootball_nfl",
    "soccer": "soccer_uefa_champs_league",
}


class OddsAPIAdapter:
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 300):
        self.api_key = (
            api_key
            or os.environ.get("ODDS_API_KEY")
            or os.environ.get("TOA_API_KEY")
            or _internal_odds.ODDS_API_KEY
        )
        if not self.api_key:
            raise ValueError("ODDS_API_KEY environment variable not set")

        self.cache = SimpleCacheAdapter(default_ttl=cache_ttl)
        self._bookmaker_cache: Dict[str, List[str]] = {}
        self.quota_exhausted = False
        logger.info("OddsAPIAdapter initialized successfully")

    # ---------- HTTP helper with quota-safe fallback ----------
    def _http_get_json(self, url: str, params: dict, timeout: int = 15) -> Optional[Any]:
        if self.quota_exhausted:
            return None
        q = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        full = f"{url}?{q}"
        req = urllib.request.Request(full, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.warning(
                    "OddsAPI returned 401 — Business tier quota maxed. "
                    "Falling back to cached/self-edge projections."
                )
                self.quota_exhausted = True
            else:
                logger.error(f"HTTP error: {e.code}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    # ---------- Public API ----------
    def get_sports(self, use_cache: bool = True) -> List[Dict]:
        cache_key = "sports_list"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        try:
            data = self._http_get_json(
                f"{ODDS_BASE}/sports",
                params={"apiKey": self.api_key, "all": "false"},
            )
            sports = data or []
            if not sports:
                sports = [
                    {"id": k, "name": k.replace("_", " ").title(), "key": k}
                    for k in SPORT_KEY_MAP.keys()
                ]
            self.cache.set(cache_key, sports, ttl=86400)
            logger.info(f"Retrieved {len(sports)} sports")
            return sports
        except Exception as e:
            logger.error(f"Failed to get sports: {e}")
            return []

    def get_events(
        self,
        sport: str = "basketball",
        league: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> List[Dict]:
        cache_key = f"events_{sport}_{league or 'all'}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        try:
            sport_path = LEAGUE_PATH_MAP.get(sport, league or sport)
            data = _internal_odds.fetch_events_list(sport_path)
            events = data or []
            self.cache.set(cache_key, events, ttl=120)
            logger.info(f"Retrieved {len(events)} events for {sport}/{league or 'all'}")
            return events
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

    def get_event_odds(
        self,
        event_id: str,
        bookmakers: str = "fanduel,draftkings",
        use_cache: bool = True,
        **kwargs,
    ) -> Dict:
        cache_key = f"odds_{event_id}_{bookmakers}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        try:
            data = self._http_get_json(
                f"{ODDS_BASE}/sports/{event_id}/odds",
                params={
                    "regions": "us",
                    "markets": kwargs.get("markets", "h2h,spreads,totals"),
                    "oddsFormat": "american",
                    "bookmakers": bookmakers,
                    "apiKey": self.api_key,
                },
            )
            odds = data or {}
            self.cache.set(cache_key, odds, ttl=30)
            return odds
        except Exception as e:
            logger.error(f"Failed to get odds for event {event_id}: {e}")
            return {}

    def get_bookmakers_for_sport(self, sport: str) -> List[str]:
        if sport in self._bookmaker_cache:
            return self._bookmaker_cache[sport]
        events = self.get_events(sport=sport, use_cache=True)
        if events:
            sample_event = events[0]
            odds = self.get_event_odds(sample_event.get("id"), use_cache=True)
            bookmakers = list(odds.get("bookmakers", {}).keys())
            if not bookmakers:
                bookmakers = ["fanduel", "draftkings", "betmgm", "caesars"]
            self._bookmaker_cache[sport] = bookmakers
            return bookmakers
        return ["fanduel", "draftkings", "betmgm", "caesars"]

    def get_market_summary(
        self, sport: str = "basketball", league: str = "usa-nba"
    ) -> Dict:
        events = self.get_events(sport=sport, league=league)
        summary = {
            "total_events": len(events),
            "bookmakers_available": self.get_bookmakers_for_sport(sport),
            "latest_odds": [],
            "timestamp": datetime.now().isoformat(),
            "quota_exhausted": self.quota_exhausted,
        }
        for event in events[:10]:
            odds = self.get_event_odds(event.get("id"))
            if odds:
                summary["latest_odds"].append(
                    {
                        "event": f"{event.get('home_team')} vs {event.get('away_team')}",
                        "commence_time": event.get("commence_time"),
                        "odds": odds,
                    }
                )
        return summary

    def close(self):
        self.cache.clear()
        logger.info("OddsAPIAdapter closed")
