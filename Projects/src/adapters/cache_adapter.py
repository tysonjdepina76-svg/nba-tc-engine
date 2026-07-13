"""Cache adapter with disk + memory caching."""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class CacheAdapter:
    """Disk + memory cache adapter."""

    def __init__(self, cache_dir: str = "data/cache", ttl_hours: float = 6):
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self._memory_cache: Dict[str, tuple] = {}
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed}.json")

    def get(self, key: str) -> Optional[Any]:
        if key in self._memory_cache:
            data, timestamp = self._memory_cache[key]
            if datetime.now() - timestamp < timedelta(hours=self.ttl_hours):
                return data
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    cached = json.load(f)
                cached_time = datetime.fromisoformat(cached["timestamp"])
                if datetime.now() - cached_time < timedelta(hours=self.ttl_hours):
                    data = cached["data"]
                    self._memory_cache[key] = (data, datetime.now())
                    return data
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        try:
            cache_path = self._get_cache_path(key)
            with open(cache_path, "w") as f:
                json.dump({"timestamp": datetime.now().isoformat(), "data": value}, f)
            self._memory_cache[key] = (value, datetime.now())
            return True
        except Exception as e:
            logger.error(f"Cache write failed: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
            self._memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False

    def clear(self) -> bool:
        try:
            for f in os.listdir(self.cache_dir):
                os.remove(os.path.join(self.cache_dir, f))
            self._memory_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
