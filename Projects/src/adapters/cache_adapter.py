"""In-memory cache with TTL for reducing API calls."""
import time
from typing import Any, Dict, Optional


class SimpleCacheAdapter:
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry['expires_at']:
                return entry['value']
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
        }

    def clear(self):
        self._cache.clear()

    def stats(self) -> Dict[str, int]:
        return {
            'total_entries': len(self._cache),
            'active_entries': sum(
                1 for v in self._cache.values() if time.time() < v['expires_at']
            ),
        }
