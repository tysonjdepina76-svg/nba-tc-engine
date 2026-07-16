# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""API Call Budget Tracker — enforces daily limits and prevents overages.

Provides a shared budget tracker that all adapters can check before making
external API calls. Prevents wasted calls when quota is exhausted and gives
observability into live vs cache vs off-season call distribution.

Usage:
    from src.monitoring.api_call_budget import get_budget, BudgetTracker

    budget = get_budget("oddsapi", daily_limit=6667)
    if budget.can_call():
        budget.record()
        # ... make the call
    else:
        # fall back to cache or self-edge
        ...
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BUDGET_DIR = Path("/home/workspace/Daily_Log/budget")
BUDGET_DIR.mkdir(parents=True, exist_ok=True)

# Known tier limits for each service
DEFAULT_LIMITS = {
    "oddsapi": 6667,       # Business tier
    "oddsapi_free": 500,   # Free keys
    "sportsdataio": 1000,  # Conservative
    "espn": 100000,        # Effectively unlimited
    "sgo": 1000,           # SportsGameOdds estimate
}


class BudgetTracker:
    """Thread-safe daily API call budget tracker."""

    def __init__(self, service: str, daily_limit: int = 1000):
        self.service = service
        self.daily_limit = daily_limit
        self._lock = threading.Lock()
        self._path = BUDGET_DIR / f"{service}_budget.json"
        self._today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._state = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                if data.get("date") == self._today:
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "date": self._today,
            "service": self.service,
            "daily_limit": self.daily_limit,
            "calls_made": 0,
            "cache_hits": 0,
            "self_edge": 0,
            "off_season": 0,
            "errors": 0,
        }

    def _save(self):
        try:
            self._path.write_text(json.dumps(self._state, indent=2))
        except OSError:
            pass

    def can_call(self) -> bool:
        """Check if we have budget remaining."""
        with self._lock:
            return self._state["calls_made"] < self.daily_limit

    def record(self, category: str = "live"):
        """Record a call. category: live | cache | self_edge | off_season | error."""
        with self._lock:
            # New day rollover
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if today != self._state["date"]:
                self._state = {
                    "date": today,
                    "service": self.service,
                    "daily_limit": self.daily_limit,
                    "calls_made": 0,
                    "cache_hits": 0,
                    "self_edge": 0,
                    "off_season": 0,
                    "errors": 0,
                }
            key_map = {
                "live": "calls_made",
                "cache": "cache_hits",
                "self_edge": "self_edge",
                "off_season": "off_season",
                "error": "errors",
            }
            key = key_map.get(category, "calls_made")
            self._state[key] = self._state.get(key, 0) + 1
            self._save()

    def status(self) -> dict:
        with self._lock:
            used = self._state["calls_made"]
            return {
                "service": self.service,
                "date": self._state["date"],
                "used": used,
                "limit": self.daily_limit,
                "remaining": max(0, self.daily_limit - used),
                "pct_used": round(100 * used / self.daily_limit, 1) if self.daily_limit else 0,
                "cache_hits": self._state.get("cache_hits", 0),
                "self_edge": self._state.get("self_edge", 0),
                "off_season": self._state.get("off_season", 0),
                "errors": self._state.get("errors", 0),
            }

    def reset(self):
        """Force reset (admin only)."""
        with self._lock:
            self._state = {
                "date": self._today,
                "service": self.service,
                "daily_limit": self.daily_limit,
                "calls_made": 0,
                "cache_hits": 0,
                "self_edge": 0,
                "off_season": 0,
                "errors": 0,
            }
            self._save()


_trackers: dict[str, BudgetTracker] = {}
_tracker_lock = threading.Lock()


def get_budget(service: str, daily_limit: Optional[int] = None) -> BudgetTracker:
    """Get or create a budget tracker for a service."""
    with _tracker_lock:
        if service not in _trackers:
            limit = daily_limit or DEFAULT_LIMITS.get(service, 1000)
            _trackers[service] = BudgetTracker(service, limit)
        return _trackers[service]


def report_all() -> dict:
    """Get status report for all tracked services."""
    with _tracker_lock:
        return {svc: tracker.status() for svc, tracker in _trackers.items()}


if __name__ == "__main__":
    import sys
    service = sys.argv[1] if len(sys.argv) > 1 else "oddsapi"
    budget = get_budget(service)
    print(json.dumps(budget.status(), indent=2))


# ── Legacy aliases (Projects/daily_picks.py compat) ──
BUDGET_FILE = "/home/workspace/Reports/api_call_budget.json"


def budget_status(service: str = "oddsapi") -> dict:
    """Flat dict status for legacy Projects/daily_picks.py callers."""
    b = get_budget(service)
    s = b.status()
    return {
        "service": s["service"],
        "calls_today": s["used"],
        "daily_limit": s["limit"],
        "calls_month": s["used"],  # proxy until monthly counter is added
        "monthly_limit": s["limit"] * 30,
    }


def budget_ok(service: str = "oddsapi") -> bool:
    """True if under daily limit."""
    return get_budget(service).can_call()


def track_api_call(service: str = "oddsapi") -> dict:
    """Record a call and return updated status."""
    return get_budget(service).record_call()