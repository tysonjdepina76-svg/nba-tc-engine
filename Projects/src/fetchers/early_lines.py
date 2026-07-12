"""Fetch early lines once per day — cache for 24 hours."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class EarlyLinesFetcher:
    """Fetch early lines once per day; cache as JSON."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("/home/workspace/Projects/cache/early_lines")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_early_lines(self, sport: str) -> Optional[Dict]:
        today = datetime.now().strftime('%Y-%m-%d')
        cache_file = self.cache_dir / f"{sport}_{today}.json"

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                print(f"✅ {sport}: early lines from cache")
                return data
            except (json.JSONDecodeError, OSError):
                pass  # fall through to fetch

        odds = self._fetch_from_api(sport)
        if odds:
            with open(cache_file, 'w') as f:
                json.dump(odds, f, indent=2)
            print(f"🔄 {sport}: early lines fetched")
        return odds

    def _fetch_from_api(self, sport: str) -> Optional[Dict]:
        try:
            from src.fetchers.smart_fetcher import SmartFetcher
            fetcher = SmartFetcher()
            return fetcher.fetch_sport_odds(sport)
        except Exception as e:
            print(f"⚠️ Early lines fetch failed for {sport}: {e}")
            return None
