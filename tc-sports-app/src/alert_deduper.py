"""Alert deduplication - prevents alert fatigue.

Tracks alerts by (source, key) and suppresses duplicates within a time window.
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class AlertDeduper:
    def __init__(self, default_window_sec: int = 3600, max_history: int = 1000):
        self.default_window_sec = default_window_sec
        self.max_history = max_history
        self._alerts: Dict[str, datetime] = {}
        self._counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def should_send(self, source: str, key: str, window_sec: Optional[int] = None) -> bool:
        """Returns True if alert should be sent (not a duplicate in window)."""
        full_key = f"{source}:{key}"
        window = window_sec or self.default_window_sec
        now = datetime.now()
        with self._lock:
            self._cleanup_old_alerts(now)
            if full_key in self._alerts:
                age = (now - self._alerts[full_key]).total_seconds()
                if age < window:
                    self._counts[full_key] = self._counts.get(full_key, 0) + 1
                    return False
            self._alerts[full_key] = now
            self._counts[full_key] = 1
            return True

    def get_suppressed_count(self, source: str, key: str) -> int:
        full_key = f"{source}:{key}"
        with self._lock:
            return self._counts.get(full_key, 0) - 1

    def _cleanup_old_alerts(self, now: datetime):
        if len(self._alerts) <= self.max_history:
            return
        cutoff = now - timedelta(seconds=self.default_window_sec)
        old_keys = [k for k, t in self._alerts.items() if t < cutoff]
        for k in old_keys:
            del self._alerts[k]
            if k in self._counts:
                del self._counts[k]

    def force_send(self, source: str, key: str):
        """Mark alert as sent, bypassing dedup window."""
        full_key = f"{source}:{key}"
        with self._lock:
            self._alerts[full_key] = datetime.now()
            self._counts[full_key] = 1

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "active_alerts": len(self._alerts),
                "total_suppressed": sum(c - 1 for c in self._counts.values() if c > 1),
                "alert_keys": list(self._alerts.keys()),
            }


_deduper_instance: Optional[AlertDeduper] = None
_deduper_lock = threading.Lock()


def get_deduper() -> AlertDeduper:
    global _deduper_instance
    with _deduper_lock:
        if _deduper_instance is None:
            _deduper_instance = AlertDeduper()
        return _deduper_instance
