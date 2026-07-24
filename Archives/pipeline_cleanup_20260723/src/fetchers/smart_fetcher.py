"""Smart fetcher — decides when and what to fetch based on priority, injuries, quota."""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

from src.scheduler.priority_scheduler import (
    get_sports_to_fetch,
    ACTIVE_SPORTS,
)
from src.scrapers.injury_scraper import InjuryScraper
from src.fetchers.early_lines import EarlyLinesFetcher
from src.utils.quota_monitor import QuotaMonitor


_SPORT_KEY_MAP = {
    "MLB": "baseball_mlb",
    "WNBA": "basketball_wnba",
    "NBA": "basketball_nba",
    "NFL": "americanfootball_nfl",
    "NHL": "icehockey_nhl",
    "WC": "soccer_world_cup",
}


class SmartFetcher:
    """Fetch decisions = priority + injury trigger + early-line cache + quota gate."""

    def __init__(self):
        self.quota = QuotaMonitor()
        self.injury_scraper = InjuryScraper()
        self.early_lines = EarlyLinesFetcher()
        self.api_key = os.environ.get('ODDS_API_KEY')
        self.base_url = "https://api.the-odds-api.com/v4"
        self.cache_dir = Path("/home/workspace/Projects/cache/api")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_all_sports(self) -> Dict[str, List]:
        results: Dict[str, List] = {}

        if not self.quota.can_call():
            print("⚠️ Quota exhausted — using cached data")
            return self._get_cached_odds()

        sports_to_fetch = get_sports_to_fetch()
        print(f"📋 Priority sports: {sports_to_fetch}")

        for sport in sports_to_fetch:
            results[sport] = self._fetch_sport(sport)

        # Injury-driven fetches for active sports not already pulled
        for sport in ACTIVE_SPORTS:
            if sport not in sports_to_fetch:
                if self.injury_scraper.should_fetch_odds(sport):
                    print(f"🚨 Injury trigger: fetching {sport}")
                    results[sport] = self._fetch_sport(sport)

        return results

    def _fetch_sport(self, sport: str) -> List:
        # Early-lines cache (0 API calls)
        early = self.early_lines.get_early_lines(sport)
        if early:
            print(f"✅ {sport}: early lines used (0 calls)")
            return early if isinstance(early, list) else [early]

        if not self.quota.can_call():
            print(f"⚠️ Quota exhausted — skipping {sport}")
            return []

        if not self.api_key or not _REQUESTS_OK:
            print(f"⚠️ {sport}: no API key or requests — skipping live fetch")
            return []

        sport_key = _SPORT_KEY_MAP.get(sport)
        if not sport_key:
            return []

        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
        }
        url = f"{self.base_url}/sports/{sport_key}/odds"

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self.quota.increment()
                usage = self.quota.get_usage()
                print(f"🔄 {sport}: fetched ({usage['remaining']} remaining)")
                return data
            print(f"⚠️ {sport}: API error {resp.status_code}")
            return []
        except Exception as e:
            print(f"❌ {sport}: fetch error — {e}")
            return []

    def fetch_sport_odds(self, sport: str) -> Optional[List]:
        return self._fetch_sport(sport)

    def _get_cached_odds(self) -> Dict[str, List]:
        results: Dict[str, List] = {}
        for f in self.cache_dir.glob("*.json"):
            sport = f.stem.split('_')[0]
            try:
                with open(f) as fp:
                    results[sport] = json.load(fp)
                    print(f"✅ {sport}: from cache (quota exhausted)")
            except (json.JSONDecodeError, OSError):
                continue
        return results
