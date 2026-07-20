#!/usr/bin/env python3
"""
Smart API Layer — unified cache, rate-limit, and call-tracker for all sports APIs.
Use this instead of raw requests for ANY external API call.

Sources tracked:
  DISCOVERY_LAB  — MLB odds/projections (100 or 1000 calls/day)
  SDIO            — WNBA/MLB odds (tier-dependent)
  SERPAPI         — scraped odds (250 calls/day)
  BALLDONTLIE     — WNBA/MLB/WC props (60/min free, 300/min paid)
  ESPN            — box scores, schedules (no hard cap)
  ODDS_API        — legacy, quota-maxed (disabled)
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, Tuple
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "api_cache"
TRACKER_PATH = DATA_DIR / "api_usage.json"

# ── Source Config ──────────────────────────────────────────────────
# daily_limit: max calls per calendar day (None = unlimited)
# cache_ttl_minutes: how long a cached result is valid
# current_key: env var holding the API key
SOURCES: Dict[str, dict] = {
    "DISCOVERY_LAB": {
        "daily_limit": 1000,
        "cache_ttl_minutes": 60,
        "current_key": "SPORTSDATAIO_DISCOVERY_KEY",
        "base_url": "https://api.sportsdata.io/v3/mlb",
        "headers_key": "Ocp-Apim-Subscription-Key",
    },
    "SDIO": {
        "daily_limit": None,
        "cache_ttl_minutes": 60,
        "current_key": "SPORTSDATAIO_API_KEY",
        "base_url": "https://api.sportsdata.io/v3",
        "headers_key": "Ocp-Apim-Subscription-Key",
    },
    "SERPAPI": {
        "daily_limit": 250,
        "cache_ttl_minutes": 20,
        "current_key": "SERPAPI_API_KEY",
        "base_url": "https://serpapi.com/search",
    },
    "BALLDONTLIE": {
        "daily_limit": None,
        "cache_ttl_minutes": 30,
        "current_key": "BALLDONTLIE_API_KEY",
        "base_url": "https://api.balldontlie.io/v1",
        "headers_key": "Authorization",
    },
    "ESPN": {
        "daily_limit": None,
        "cache_ttl_minutes": 10,
        "current_key": None,
        "base_url": "https://site.api.espn.com/apis/site/v2/sports",
    },
    "ODDS_API": {
        "daily_limit": 0,
        "cache_ttl_minutes": 1440,
        "current_key": None,
        "base_url": None,
    },
}

os.makedirs(CACHE_DIR, exist_ok=True)


class SmartAPIError(Exception):
    pass


class QuotaExceeded(SmartAPIError):
    pass


class InvalidKey(SmartAPIError):
    pass


def _load_tracker() -> dict:
    if TRACKER_PATH.exists():
        try:
            return json.loads(TRACKER_PATH.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def _save_tracker(data: dict):
    TRACKER_PATH.write_text(json.dumps(data, indent=2, default=str))


def _today_str() -> str:
    return date.today().isoformat()


def _cache_key(source: str, endpoint: str, params: Optional[dict] = None) -> str:
    raw = f"{source}:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


# ── Public API ─────────────────────────────────────────────────────


def check_quota(source: str) -> Tuple[bool, int, int]:
    """Return (allowed, used, limit) for the source today."""
    cfg = SOURCES.get(source)
    if not cfg:
        return True, 0, 0
    limit = cfg.get("daily_limit")
    if limit is None:
        return True, 0, 0
    tracker = _load_tracker()
    used = tracker.get(source, {}).get(_today_str(), 0)
    return used < limit, used, limit


def get(
    source: str,
    endpoint: str,
    params: Optional[dict] = None,
    force: bool = False,
    timeout: int = 30,
) -> Tuple[Optional[Any], bool]:
    """Fetch from API with cache + rate-limit enforcement.
    
    Returns (data, from_cache).
    Raises QuotaExceeded if daily limit hit.
    Raises InvalidKey if API key missing or 401.
    """
    params = params or {}
    cfg = SOURCES.get(source)
    if not cfg:
        raise SmartAPIError(f"Unknown source: {source}")

    cache_ttl = timedelta(minutes=cfg["cache_ttl_minutes"])

    # ── Check cache ──
    key_hash = _cache_key(source, endpoint, params)
    cpath = _cache_path(key_hash)
    if not force and cpath.exists():
        try:
            cached = json.loads(cpath.read_text())
            ts = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - ts < cache_ttl:
                return cached["data"], True
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # ── Check quota ──
    allowed, used, limit = check_quota(source)
    if not allowed:
        raise QuotaExceeded(
            f"{source}: daily limit {limit} reached ({used} calls used)"
        )

    # ── Build request ──
    base = cfg.get("base_url")
    if not base:
        raise SmartAPIError(f"{source}: no base_url configured (disabled)")

    url = f"{base}{endpoint}"
    headers = {}

    key_env = cfg.get("current_key")
    api_key = os.getenv(key_env) if key_env else None
    hdr_key = cfg.get("headers_key")

    if hdr_key:
        if hdr_key == "Authorization":
            headers["Authorization"] = api_key or ""
        else:
            headers[hdr_key] = api_key or "no-key"

    # ── Execute ──
    logger.info(f"[{source}] GET {endpoint} (call #{used+1}/{limit or '∞'})")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise SmartAPIError(f"{source}: request failed: {e}")

    if resp.status_code == 401:
        raise InvalidKey(f"{source}: 401 Unauthorized — API key invalid or expired")

    if resp.status_code == 429:
        raise QuotaExceeded(f"{source}: 429 rate-limited")

    if not resp.ok:
        raise SmartAPIError(f"{source}: HTTP {resp.status_code} from {url}")

    data = resp.json()

    # ── Save cache ──
    cpath.write_text(
        json.dumps({"timestamp": datetime.now().isoformat(), "data": data})
    )

    # ── Increment counter ──
    tracker = _load_tracker()
    tracker.setdefault(source, {})[_today_str()] = used + 1
    _save_tracker(tracker)

    return data, False


def get_cached(
    source: str,
    endpoint: str,
    params: Optional[dict] = None,
) -> Optional[Any]:
    """Cache-only read — no API call. Returns None if not cached."""
    key_hash = _cache_key(source, endpoint, params or {})
    cpath = _cache_path(key_hash)
    if not cpath.exists():
        return None
    try:
        cached = json.loads(cpath.read_text())
        cfg = SOURCES.get(source, {})
        ttl = timedelta(minutes=cfg.get("cache_ttl_minutes", 60))
        ts = datetime.fromisoformat(cached["timestamp"])
        if datetime.now() - ts < ttl:
            return cached["data"]
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    return None


def status() -> dict:
    """Return usage report for all sources."""
    tracker = _load_tracker()
    today = _today_str()
    report = {}
    for src, cfg in SOURCES.items():
        used = tracker.get(src, {}).get(today, 0)
        limit = cfg.get("daily_limit")
        report[src] = {
            "used_today": used,
            "limit": limit,
            "remaining": (limit - used) if limit is not None else None,
            "cache_ttl_min": cfg["cache_ttl_minutes"],
        }
    return report


def invalidate(source: str, endpoint: str, params: Optional[dict] = None):
    """Delete a specific cached entry."""
    key_hash = _cache_key(source, endpoint, params or {})
    cpath = _cache_path(key_hash)
    if cpath.exists():
        cpath.unlink()


def invalidate_source(source: str):
    """Delete ALL cached entries for a source."""
    prefix = hashlib.md5(source.encode()).hexdigest()[:6]
    for f in CACHE_DIR.glob("*.json"):
        try:
            cached = json.loads(f.read_text())
            if source in str(cached.get("url", "")):
                f.unlink()
        except (json.JSONDecodeError, KeyError):
            pass


def reset_daily(source: str):
    """Manually reset daily usage counter for a source."""
    tracker = _load_tracker()
    tracker.pop(source, None)
    _save_tracker(tracker)


# ── Quick CLI ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(json.dumps(status(), indent=2, default=str))
    elif sys.argv[1] == "reset" and len(sys.argv) > 2:
        reset_daily(sys.argv[2])
        print(f"Reset {sys.argv[2]}")
    elif sys.argv[1] == "clear-cache":
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()
        print("Cache cleared")
    else:
        print(json.dumps(status(), indent=2, default=str))
