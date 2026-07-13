"""Cache utility for scraper responses.

Stores JSON-serializable data in /tmp/tc_cache/ with TTL-based expiry.
Used to avoid hammering scrapers on every pipeline run.
"""
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

CACHE_DIR = "/tmp/tc_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(key: str) -> str:
    safe = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{safe}.json")


def cache_fetch(key: str, fetch_func: Callable, ttl_hours: int = 6) -> Any:
    """Return cached data if fresh, else call fetch_func and cache the result.

    Args:
        key:        Cache key (will be MD5-hashed for filename safety).
        fetch_func: Zero-arg callable that returns JSON-serializable data.
        ttl_hours:  Max age in hours before refetching.

    Returns:
        Whatever fetch_func returns (or cached equivalent).
    """
    cache_file = _cache_path(key)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            cached_time = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - cached_time < timedelta(hours=ttl_hours):
                return data["data"]
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            pass  # corrupted cache, ignore

    fresh_data = fetch_func()
    try:
        with open(cache_file, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "data": fresh_data}, f)
    except Exception as e:
        print(f"Cache write failed for {key}: {e}")
    return fresh_data


def clear_cache(key: Optional[str] = None) -> None:
    """Clear one key (str) or the entire cache (None)."""
    if key:
        path = _cache_path(key)
        if os.path.exists(path):
            os.remove(path)
    else:
        for f in os.listdir(CACHE_DIR):
            os.remove(os.path.join(CACHE_DIR, f))
