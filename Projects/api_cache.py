#!/usr/bin/env python3
"""Smart API Cache + Rate-Limit Governor
Unified caching layer for all external API sources.
Prevents quota burns by caching responses and tracking daily call counts.
"""

import json
import os
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, Callable
from functools import wraps

from src.adapters.cache_adapter import CacheAdapter

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "api_cache"
USAGE_FILE = DATA_DIR / "api_usage.json"

SOURCE_CONFIGS = {
    "discovery_lab": {
        "daily_limit": 1000,
        "reset_at": "00:00",
        "cache_ttl_hours": {"game_odds": 1, "player_props": 2, "schedule": 6, "default": 4},
    },
    "serpapi": {
        "daily_limit": 250,
        "reset_at": "00:00",
        "cache_ttl_hours": {"odds_search": 2, "default": 6},
    },
    "balldontlie": {
        "daily_limit": 300,  # per minute
        "rate_limit_seconds": 1.0,
        "cache_ttl_hours": {"stats": 2, "odds": 1, "default": 4},
    },
    "odds_api": {
        "daily_limit": 1000,
        "reset_at": "00:00",
        "cache_ttl_hours": {"odds": 2, "props": 2, "default": 4},
    },
    "espn": {
        "daily_limit": float("inf"),
        "cache_ttl_hours": {"roster": 4, "boxscore": 0.25, "schedule": 6, "default": 2},
    },
}

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


class APIGovernor:
    """Rate-limits + caches all external API calls."""

    def __init__(self):
        self._cache = CacheAdapter(str(CACHE_DIR), ttl_hours=4)
        self._usage = self._load_usage()
        self._last_call = {}  # source → timestamp

    def _load_usage(self) -> Dict:
        if USAGE_FILE.exists():
            try:
                with open(USAGE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                pass
        return {}

    def _save_usage(self):
        with open(USAGE_FILE, "w") as f:
            json.dump(self._usage, f, indent=2)

    def _daily_key(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _reset_daily_if_stale(self, source: str):
        today = self._daily_key()
        if source not in self._usage or self._usage[source].get("date") != today:
            self._usage[source] = {"date": today, "calls": 0}

    def _cache_key(self, source: str, endpoint: str, params: Dict = None) -> str:
        raw = f"{source}|{endpoint}|{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _ttl_for(self, source: str, endpoint: str) -> float:
        config = SOURCE_CONFIGS.get(source, {})
        ttls = config.get("cache_ttl_hours", {"default": 4})
        for pattern, hours in ttls.items():
            if pattern in endpoint:
                return hours
        return ttls.get("default", 4)

    def remaining_calls(self, source: str) -> int:
        config = SOURCE_CONFIGS.get(source, {})
        limit = config.get("daily_limit", float("inf"))
        self._reset_daily_if_stale(source)
        used = self._usage.get(source, {}).get("calls", 0)
        return max(0, int(limit) - used)

    def get(self, source: str, endpoint: str, params: Dict = None) -> Optional[Any]:
        """Check cache. Returns cached data or None."""
        key = self._cache_key(source, endpoint, params)
        return self._cache.get(key)

    def set(self, source: str, endpoint: str, params: Dict, data: Any):
        """Cache an API response."""
        key = self._cache_key(source, endpoint, params)
        ttl = self._ttl_for(source, endpoint)
        self._cache.set(key, data, ttl_seconds=int(ttl * 3600))

    def can_call(self, source: str) -> bool:
        """Check if we have budget for another call."""
        config = SOURCE_CONFIGS.get(source, {})
        limit = config.get("daily_limit", float("inf"))
        if limit == float("inf"):
            return True
        self._reset_daily_if_stale(source)
        return self._usage[source]["calls"] < limit

    def record_call(self, source: str):
        """Mark one call against daily budget."""
        self._reset_daily_if_stale(source)
        self._usage[source]["calls"] += 1
        self._save_usage()

    def fetch(self, source: str, endpoint: str, params: Dict = None,
              fetcher: Callable = None, force: bool = False) -> Optional[Any]:
        """Main entry: fetch from cache if fresh, else call API with rate-limit check.

        Returns (data, source_str) where source_str is 'cache' or 'api'.
        """
        key = self._cache_key(source, endpoint, params)

        if not force:
            cached = self._cache.get(key)
            if cached is not None:
                logger.debug(f"[CACHE HIT] {source}/{endpoint}")
                return cached, "cache"

        if not self.can_call(source):
            logger.warning(f"[QUOTA EXHAUSTED] {source} — {self.remaining_calls(source)} remaining")
            stale = self._cache.get(key)
            if stale is not None:
                logger.warning(f"[FALLBACK] Returning stale cache for {source}/{endpoint}")
                return stale, "stale_cache"
            return None, "quota_exhausted"

        if fetcher is None:
            logger.error(f"No fetcher provided for {source}/{endpoint}")
            return None, "no_fetcher"

        logger.info(f"[API CALL] {source}/{endpoint} ({self.remaining_calls(source)} remaining)")
        self.record_call(source)
        try:
            data = fetcher(params or {})
        except Exception as e:
            logger.error(f"[FETCH ERROR] {source}/{endpoint}: {e}")
            stale = self._cache.get(key)
            if stale is not None:
                return stale, "stale_cache_error"
            return None, "fetch_error"

        self._cache.set(key, data)
        return data, "api"

    def status(self) -> Dict:
        """Return usage report for all sources."""
        status = {}
        for source in SOURCE_CONFIGS:
            self._reset_daily_if_stale(source)
            used = self._usage.get(source, {}).get("calls", 0)
            limit = SOURCE_CONFIGS[source]["daily_limit"]
            status[source] = {
                "used": used,
                "limit": "unlimited" if limit == float("inf") else int(limit),
                "remaining": "unlimited" if limit == float("inf") else max(0, int(limit) - used),
            }
        return status


_governor = None


def get_governor() -> APIGovernor:
    global _governor
    if _governor is None:
        _governor = APIGovernor()
    return _governor


def cached_api(source: str, endpoint: str, cache_ttl_hours: float = None):
    """Decorator for API functions — auto-cache + rate-limit."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            gov = get_governor()
            params = kwargs.get("params", {})
            if args:
                params["_args"] = str(args)

            key = gov._cache_key(source, endpoint, params)
            cached = gov._cache.get(key)
            if cached is not None:
                return cached

            if not gov.can_call(source):
                logger.warning(f"[BLOCKED] {source}: daily quota exhausted")
                return gov._cache.get(key)

            gov.record_call(source)
            result = func(*args, **kwargs)

            ttl = cache_ttl_hours or gov._ttl_for(source, endpoint)
            gov._cache.set(key, result, ttl_seconds=int(ttl * 3600))
            return result
        return wrapper
    return decorator


if __name__ == "__main__":
    gov = get_governor()
    print("=== API Cache Governor ===")
    print(json.dumps(gov.status(), indent=2))
