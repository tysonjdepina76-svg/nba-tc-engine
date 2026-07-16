"""OptimizedCache — LRU + TTL cache targeting ≥60% hit rate.

Replaces raw dict caches across the pipeline. Each entry has a TTL
(sport-dependent) and is evicted on LRU when the size cap is hit.

Usage:
    cache = OptimizedCache(max_entries=512, default_ttl=900)
    cache.set("wnba:slate:2026-07-09", payload, ttl=1800)
    hit = cache.get("wnba:slate:2026-07-09")
"""
from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Default TTLs (seconds) per sport — tuned to slate refresh cadence
SPORT_TTL = {
    "WNBA": 1800,    # 30 min — DK posts props 30-60 min before tip
    "MLB": 2700,     # 45 min — pitcher lines settle close to first pitch
    "NFL": 3600,     # 60 min
    "SOCCER": 7200,  # 2 hr
    "NBA": 1800,
    "NHL": 1800,
}

DEFAULT_TTL = 1800
HIT_RATE_TARGET = 0.60


@dataclass
class _Entry:
    value: Any
    expires_at: float
    hits: int = 0
    misses: int = 0


class OptimizedCache:
    """LRU + TTL cache with hit-rate tracking."""

    hit_rate_target: float = HIT_RATE_TARGET

    def __init__(self, max_entries: int = 1024, default_ttl: int = DEFAULT_TTL, persist_path: Optional[str] = None):
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self._data: "OrderedDict[str, _Entry]" = OrderedDict()
        self.persist_path = Path(persist_path) if persist_path else None
        if self.persist_path and self.persist_path.exists():
            self._load()

    def _now(self) -> float:
        return time.time()

    def _ttl_for(self, key: str, ttl: Optional[int]) -> int:
        if ttl is not None:
            return ttl
        for sport, t in SPORT_TTL.items():
            if key.upper().startswith(sport):
                return t
        return self.default_ttl

    def get(self, key: str) -> Optional[Any]:
        e = self._data.get(key)
        if e is None:
            return None
        if e.expires_at < self._now():
            del self._data[key]
            return None
        # LRU bump
        self._data.move_to_end(key)
        e.hits += 1
        return e.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires = self._now() + self._ttl_for(key, ttl)
        self._data[key] = _Entry(value=value, expires_at=expires)
        self._data.move_to_end(key)
        if len(self._data) > self.max_entries:
            self._data.popitem(last=False)
        if self.persist_path:
            self._save()

    def miss(self, key: str) -> None:
        e = self._data.get(key)
        if e:
            e.misses += 1

    def stats(self) -> dict:
        total_hits = sum(e.hits for e in self._data.values())
        total_misses = sum(e.misses for e in self._data.values())
        total = total_hits + total_misses
        hit_rate = total_hits / total if total else 0.0
        return {
            "entries": len(self._data),
            "max": self.max_entries,
            "hits": total_hits,
            "misses": total_misses,
            "hit_rate": round(hit_rate, 3),
            "target": self.hit_rate_target,
            "meets_target": hit_rate >= self.hit_rate_target,
        }

    def clear(self) -> None:
        self._data.clear()
        if self.persist_path:
            self._save()

    def _save(self) -> None:
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            k: {"v": e.value, "exp": e.expires_at, "h": e.hits, "m": e.misses}
            for k, e in self._data.items()
        }
        self.persist_path.write_text(json.dumps(payload, default=str))

    def _load(self) -> None:
        try:
            data = json.loads(self.persist_path.read_text())
        except Exception:
            return
        now = self._now()
        for k, v in data.items():
            if v.get("exp", 0) > now:
                self._data[k] = _Entry(value=v.get("v"), expires_at=v["exp"], hits=v.get("h", 0), misses=v.get("m", 0))
