"""
Redis caching for faster data access.
"""

import json
import os
from typing import Any, Optional
from sources.utils.logging import get_logger

logger = get_logger(__name__)

try:
    import redis
except ImportError:
    redis = None
    logger.warning("redis package not installed; redis_cache will be a no-op")

class RedisCache:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = None
        self._connect()

    def _connect(self) -> None:
        if not redis:
            return
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.debug(f"Redis get failed: {e}")
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        if not self.client:
            return False
        try:
            self.client.setex(key, ttl_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.debug(f"Redis set failed: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self.client:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.debug(f"Redis delete failed: {e}")
        return False

    def clear(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            logger.debug(f"Redis clear failed: {e}")
        return False

redis_cache = RedisCache()
