#!/usr/bin/env python3
"""
API Call Manager — Smart caching + rate limiting for all external APIs.

Supports: SportsDataIO (Discovery Lab), SerpAPI, balldontlie, Odds API, ESPN.
Strategy: cache-first → check quota → call → cache result → log usage.

Usage:
    from api_call_manager import APICallManager
    mgr = APICallManager()
    data = mgr.smart_call("discovery_mlb", "https://api.sportsdata.io/v3/mlb/odds/json/GameOddsByDate/2026-07-19")
    # data is dict if cached/fresh, None if quota exhausted or error
"""

import json
import os
import hashlib
import time
import sqlite3
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Optional, Callable
from urllib.request import Request, urlopen, HTTPError
from urllib.parse import urlparse
import gzip
from io import BytesIO

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "cache"
TRACKER_FILE = DATA_DIR / "api_usage.json"

# ── Rate limits per source ──────────────────────────────────────────
RATE_LIMITS = {
    "discovery_mlb":   {"daily": 100,  "ttl_minutes": 30},   # Discovery Lab Odds tier
    "discovery_nfl":   {"daily": 100,  "ttl_minutes": 60},   # Off-season, longer TTL
    "discovery_nba":   {"daily": 100,  "ttl_minutes": 60},   # Off-season
    "serpapi":         {"daily": 250,  "ttl_minutes": 60},   # SerpAPI
    "balldontlie_wnba":{"daily": 300,  "ttl_minutes": 15},   # balldontlie (live odds)
    "balldontlie_mlb": {"daily": 300,  "ttl_minutes": 15},
    "balldontlie_wc":  {"daily": 300,  "ttl_minutes": 15},
    "odds_api_v3":     {"daily": 500,  "ttl_minutes": 3},    # Odds API (quota-dependent)
    "odds_api_v4":     {"daily": 500,  "ttl_minutes": 3},
    "espn_api":        {"daily": 2000, "ttl_minutes": 10},   # ESPN free
    "sgo_api":         {"daily": 100,  "ttl_minutes": 30},
}

# Minimum interval between calls per source (seconds)
CALL_SPACING = {
    "discovery_mlb": 2.0,
    "serpapi": 3.0,
    "balldontlie_wnba": 0.5,
    "balldontlie_mlb": 0.5,
    "odds_api_v3": 1.0,
    "espn_api": 0.1,
}

DEFAULT_MINUTE_RATE = 10   # per-minute cap fallback
DEFAULT_TTL_MINUTES = 30   # default cache TTL


class APICallManager:
    """Smart API call manager with caching, rate limiting, and quota tracking."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.cache_dir = self.data_dir / "cache"
        self.tracker_file = self.data_dir / "api_usage.json"
        self._mem_cache: dict = {}
        self._last_call_time: dict = {}
        self._daily_counts: dict = {}

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._load_tracker()

    # ── Tracker persistence ──────────────────────────────────────────

    def _load_tracker(self):
        """Load daily usage from disk."""
        today = date.today().isoformat()
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file) as f:
                    data = json.load(f)
                if data.get("date") == today:
                    self._daily_counts = data.get("counts", {})
                else:
                    self._daily_counts = {}
            except (json.JSONDecodeError, KeyError):
                self._daily_counts = {}
        else:
            self._daily_counts = {}

    def _save_tracker(self):
        """Persist daily usage to disk."""
        with open(self.tracker_file, "w") as f:
            json.dump({
                "date": date.today().isoformat(),
                "counts": self._daily_counts,
                "updated": datetime.now().isoformat(),
            }, f, indent=2)

    # ── Rate limit checks ────────────────────────────────────────────

    def _get_limits(self, source: str) -> dict:
        return RATE_LIMITS.get(source, {"daily": 100, "ttl_minutes": DEFAULT_TTL_MINUTES})

    def _get_spacing(self, source: str) -> float:
        return CALL_SPACING.get(source, 1.0)

    def quota_remaining(self, source: str) -> int:
        """How many calls remain today for this source."""
        daily_max = self._get_limits(source)["daily"]
        used = self._daily_counts.get(source, 0)
        return max(0, daily_max - used)

    def quota_exhausted(self, source: str) -> bool:
        return self.quota_remaining(source) <= 0

    def usage_report(self) -> dict:
        """Full usage report for all sources."""
        report = {}
        for source, limits in RATE_LIMITS.items():
            used = self._daily_counts.get(source, 0)
            report[source] = {
                "used": used,
                "limit": limits["daily"],
                "remaining": max(0, limits["daily"] - used),
                "exhausted": used >= limits["daily"],
            }
        return report

    # ── Cache layer ──────────────────────────────────────────────────

    def _cache_key(self, url: str, params: Optional[dict] = None) -> str:
        raw = url
        if params:
            raw += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hashlib.md5(raw.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _cache_get(self, key: str, ttl_minutes: int) -> Optional[Any]:
        if key in self._mem_cache:
            data, ts = self._mem_cache[key]
            if (datetime.now() - ts).total_seconds() < ttl_minutes * 60:
                return data
        path = self._cache_path(key)
        if path.exists():
            try:
                with open(path) as f:
                    cached = json.load(f)
                cached_ts = datetime.fromisoformat(cached["timestamp"])
                if (datetime.now() - cached_ts).total_seconds() < ttl_minutes * 60:
                    data = cached["data"]
                    self._mem_cache[key] = (data, datetime.now())
                    return data
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        return None

    def _cache_set(self, key: str, data: Any):
        path = self._cache_path(key)
        with open(path, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "data": data}, f)
        self._mem_cache[key] = (data, datetime.now())

    # ── HTTP call ────────────────────────────────────────────────────

    def _http_call(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: int = 15,
    ) -> Optional[Any]:
        """Make an HTTP GET with automatic gzip decompression and JSON parsing."""
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"

        req_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "TC-Pipeline/1.0",
        }
        if headers:
            req_headers.update(headers)

        req = Request(url, headers=req_headers)
        try:
            resp = urlopen(req, timeout=timeout)
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            text = raw.decode("utf-8")
            return json.loads(text) if text else {}
        except HTTPError as e:
            status = e.code
            body = e.read().decode("utf-8", errors="replace")[:200]
            print(f"[API] HTTP {status} from {urlparse(url).netloc}: {body}")
            return None
        except Exception as e:
            print(f"[API] Error calling {urlparse(url).netloc}: {e}")
            return None

    # ── Smart call (main entry point) ────────────────────────────────

    def smart_call(
        self,
        source: str,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        force: bool = False,
        cache_ttl_minutes: Optional[int] = None,
    ) -> Optional[Any]:
        """
        Unified smart API call.

        - source: key in RATE_LIMITS (e.g. 'discovery_mlb', 'serpapi')
        - url: full API endpoint URL
        - headers: extra HTTP headers
        - params: query parameters dict
        - force: bypass cache (still subject to rate limit)
        - cache_ttl_minutes: override default TTL for this call

        Returns parsed JSON data, or None if cached/blocked/error.
        """
        limits = self._get_limits(source)
        ttl = cache_ttl_minutes if cache_ttl_minutes is not None else limits["ttl_minutes"]
        key = self._cache_key(url, params)

        # 1. Check cache
        if not force:
            cached = self._cache_get(key, ttl)
            if cached is not None:
                return cached

        # 2. Check quota
        if self.quota_exhausted(source):
            print(f"[API] Quota exhausted for {source} ({self._daily_counts.get(source, 0)}/{limits['daily']})")
            return None

        # 3. Respect call spacing
        now = time.time()
        last = self._last_call_time.get(source, 0)
        spacing = self._get_spacing(source)
        if now - last < spacing:
            time.sleep(spacing - (now - last))

        # 4. Make the call
        data = self._http_call(url, headers=headers, params=params)
        self._last_call_time[source] = time.time()

        # 5. Track usage
        self._daily_counts[source] = self._daily_counts.get(source, 0) + 1
        self._save_tracker()

        # 6. Cache result
        if data is not None:
            self._cache_set(key, data)

        return data

    def make_discovery_call(
        self,
        league: str,
        endpoint: str,
        api_key: str,
        force: bool = False,
    ) -> Optional[Any]:
        """Convenience wrapper for SportsDataIO Discovery Lab calls.

        league: 'mlb', 'nfl', 'nba'
        endpoint: e.g. '/v3/mlb/odds/json/GameOddsByDate/2026-07-19'
        """
        source = f"discovery_{league}"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        base = f"https://api.sportsdata.io/v3/{league}"
        url = f"{base}/{endpoint.lstrip('/')}" if not endpoint.startswith("http") else endpoint
        return self.smart_call(source, url, headers=headers, force=force)

    def make_serpapi_call(self, query: str, api_key: str, force: bool = False) -> Optional[Any]:
        """Convenience wrapper for SerpAPI search calls."""
        return self.smart_call(
            "serpapi",
            "https://serpapi.com/search",
            params={"q": query, "api_key": api_key, "engine": "google"},
            force=force,
            cache_ttl_minutes=60,
        )

    def make_balldontlie_call(
        self,
        league: str,
        endpoint: str,
        api_key: str,
        force: bool = False,
    ) -> Optional[Any]:
        """Convenience wrapper for balldontlie API calls.

        league: 'wnba', 'mlb', 'wc'
        endpoint: e.g. '/v1/odds?date=2026-07-19'
        """
        source = f"balldontlie_{league}"
        headers = {"Authorization": api_key}
        base = "https://api.balldontlie.io"
        url = f"{base}{endpoint}" if not endpoint.startswith("http") else endpoint
        return self.smart_call(source, url, headers=headers, force=force)

    def make_espn_call(self, url: str, force: bool = False) -> Optional[Any]:
        """Convenience wrapper for ESPN API calls."""
        return self.smart_call("espn_api", url, force=force)

    # ── Utility ──────────────────────────────────────────────────────

    def cache_stats(self) -> dict:
        """Return cache directory stats."""
        files = list(self.cache_dir.glob("*.json"))
        return {
            "cached_entries": len(files),
            "cache_dir": str(self.cache_dir),
            "usage_tracker": str(self.tracker_file),
        }

    def warm_cache(self, calls: list[dict]):
        """Pre-warm cache with a list of calls. Each dict has: source, url, headers?, params?."""
        for call in calls:
            self.smart_call(
                call["source"],
                call["url"],
                headers=call.get("headers"),
                params=call.get("params"),
            )

    def reset_daily(self):
        """Reset daily counters (for testing)."""
        self._daily_counts = {}
        self._save_tracker()


# ── Singleton ────────────────────────────────────────────────────────
_manager: Optional[APICallManager] = None


def get_manager() -> APICallManager:
    global _manager
    if _manager is None:
        _manager = APICallManager()
    return _manager
