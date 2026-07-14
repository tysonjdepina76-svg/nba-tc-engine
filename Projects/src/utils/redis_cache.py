"""redis_cache.py — Cache layer for projections and odds.

Falls back to JSON file cache if Redis isn't available.
"""
import json
import time
import os
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path("/home/workspace/Daily_Log/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

try:
    import redis
    REDIS_AVAILABLE = bool(os.environ.get("REDIS_URL"))
except ImportError:
    REDIS_AVAILABLE = False


class Cache:
    """File-backed cache with optional Redis layer."""

    def __init__(self, ttl_seconds: int = 3600, namespace: str = "tc"):
        self.ttl = ttl_seconds
        self.ns = namespace
        self._r = None
        if REDIS_AVAILABLE:
            try:
                self._r = redis.from_url(os.environ["REDIS_URL"])
            except Exception:
                self._r = None

    def _key(self, k: str) -> str:
        return f"{self.ns}:{k}"

    def get(self, key: str) -> Optional[Any]:
        k = self._key(key)
        if self._r:
            try:
                v = self._r.get(k)
                if v:
                    return json.loads(v)
            except Exception:
                pass
        f = CACHE_DIR / f"{k}.json"
        if not f.exists():
            return None
        try:
            data = json.loads(f.read_text())
            if time.time() - data.get("ts", 0) > self.ttl:
                return None
            return data.get("value")
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        k = self._key(key)
        ttl = ttl or self.ttl
        payload = {"ts": time.time(), "value": value, "ttl": ttl}
        if self._r:
            try:
                self._r.setex(k, ttl, json.dumps(value, default=str))
            except Exception:
                pass
        try:
            (CACHE_DIR / f"{k}.json").write_text(json.dumps(payload, default=str))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        k = self._key(key)
        if self._r:
            try:
                self._r.delete(k)
            except Exception:
                pass
        f = CACHE_DIR / f"{k}.json"
        if f.exists():
            f.unlink()


if __name__ == "__main__":
    c = Cache()
    c.set("test", {"hello": "world"})
    print(c.get("test"))
