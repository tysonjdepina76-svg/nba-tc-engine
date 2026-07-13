"""
Unified caching utility.
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Dict
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = "/tmp/tc_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

_MEMORY_CACHE: Dict[str, tuple] = {}

def cache_fetch(key: str, fetch_func: Callable, ttl_hours: float = 6, use_memory: bool = True) -> Any:
    if use_memory and key in _MEMORY_CACHE:
        data, timestamp = _MEMORY_CACHE[key]
        if datetime.now() - timestamp < timedelta(hours=ttl_hours):
            return data

    cache_file = os.path.join(CACHE_DIR, f"{hashlib.md5(key.encode()).hexdigest()}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            if datetime.now() - datetime.fromisoformat(cached["timestamp"]) < timedelta(hours=ttl_hours):
                data = cached["data"]
                if use_memory:
                    _MEMORY_CACHE[key] = (data, datetime.now())
                return data
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")

    fresh_data = fetch_func()
    try:
        with open(cache_file, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "data": fresh_data}, f)
        if use_memory:
            _MEMORY_CACHE[key] = (fresh_data, datetime.now())
    except Exception as e:
        logger.warning(f"Cache write failed for {key}: {e}")

    return fresh_data

def clear_cache(key: Optional[str] = None) -> None:
    if key:
        cache_file = os.path.join(CACHE_DIR, f"{hashlib.md5(key.encode()).hexdigest()}.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
        _MEMORY_CACHE.pop(key, None)
    else:
        for f in os.listdir(CACHE_DIR):
            os.remove(os.path.join(CACHE_DIR, f))
        _MEMORY_CACHE.clear()
