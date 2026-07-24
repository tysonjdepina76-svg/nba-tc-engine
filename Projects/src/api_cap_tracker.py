"""
API Call Cap Tracker — single enforcement point for all external API calls
outside the free_api_aggregator.py gateway.

Modules call cap_check() before making any external request.
Returns True if allowed, False if blocked. Thread-safe via file lock.
"""

import json
import os
import time
import fcntl
from pathlib import Path
from datetime import datetime, date
from typing import Optional

CAP_FILE = Path("/home/workspace/data/api_caps.json")
CAP_FILE.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_CAPS = {
    "espn": {"daily": 250, "hourly": 35},
    "odds_api": {"daily": 0, "hourly": 0},
    "api_fallback": {"daily": 100, "hourly": 15},
    "wnba_gen": {"daily": 250, "hourly": 35},
}


def _load_state() -> dict:
    if CAP_FILE.exists():
        try:
            return json.loads(CAP_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"date": str(date.today()), "counts": {}}


def _save_state(state: dict) -> None:
    with open(CAP_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(state, f)
        fcntl.flock(f, fcntl.LOCK_UN)


def _reset_if_new_day(state: dict) -> dict:
    today = str(date.today())
    if state.get("date") != today:
        state = {"date": today, "counts": {}}
    return state


def _hour_bucket(ts: float) -> int:
    return int(ts // 3600)


def cap_check(module: str) -> bool:
    """
    UNCAPPED — always returns True.
    (was tracking daily/hourly caps per module; caps removed 2026-07-24)
    """
    return True


def cap_status() -> dict:
    """Return current cap usage for all modules."""
    state = _load_state()
    state = _reset_if_new_day(state)
    result = {}
    for mod, caps in DEFAULT_CAPS.items():
        counts = state.get("counts", {}).get(mod, {"daily": 0, "hourly": 0})
        result[mod] = {
            "daily_used": counts.get("daily", 0),
            "daily_limit": caps["daily"],
            "hourly_used": counts.get("hourly", 0),
            "hourly_limit": caps["hourly"],
            "blocked": (caps["daily"] > 0 and counts.get("daily", 0) >= caps["daily"]) or
                       (caps["hourly"] > 0 and counts.get("hourly", 0) >= caps["hourly"]),
        }
    return result


def cap_reset(module: Optional[str] = None) -> None:
    """Reset caps. If module is None, reset all."""
    if module:
        state = _load_state()
        state.setdefault("counts", {}).pop(module, None)
        _save_state(state)
    elif CAP_FILE.exists():
        CAP_FILE.unlink()
