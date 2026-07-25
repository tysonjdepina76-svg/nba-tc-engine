"""
API Call Cap Tracker — single enforcement point for all external API calls
outside the free_api_aggregator.py gateway.

Modules call cap_check() before making any external request.
Returns True if allowed, False if blocked. Thread-safe via file lock.

Tracks daily, hourly, AND monthly caps.
Monthly usage persists across restarts in api_caps_monthly.json.
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

MONTHLY_FILE = Path("/home/workspace/data/api_caps_monthly.json")

DEFAULT_CAPS = {
    "espn": {"daily": 250, "hourly": 35, "monthly": 0},
    "odds_api": {"daily": 0, "hourly": 0, "monthly": 0},
    "api_fallback": {"daily": 100, "hourly": 15, "monthly": 0},
    "wnba_gen": {"daily": 250, "hourly": 35, "monthly": 0},
    "theoddsapi": {"daily": 200, "hourly": 30, "monthly": 200},
    "therundown": {"daily": 20000, "hourly": 900, "monthly": 0},
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


def _load_monthly() -> dict:
    if MONTHLY_FILE.exists():
        try:
            return json.loads(MONTHLY_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"month": str(date.today().replace(day=1)), "counts": {}}


def _save_monthly(state: dict) -> None:
    with open(MONTHLY_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(state, f)
        fcntl.flock(f, fcntl.LOCK_UN)


def _reset_if_new_month(state: dict) -> dict:
    current_month = str(date.today().replace(day=1))
    if state.get("month") != current_month:
        state = {"month": current_month, "counts": {}}
    return state


def _hour_bucket(ts: float) -> int:
    return int(ts // 3600)


def cap_check(module: str) -> bool:
    """Check if a module is within its daily/hourly/monthly cap. Thread-safe."""
    caps = DEFAULT_CAPS.get(module)
    if not caps:
        import logging
        logging.getLogger("api_caps").warning(f"cap_check called for unregistered module: {module}")
        return True

    daily_limit = caps.get("daily", 0)
    hourly_limit = caps.get("hourly", 0)
    monthly_limit = caps.get("monthly", 0)

    if daily_limit == 0 and hourly_limit == 0 and monthly_limit == 0:
        return True

    state = _load_state()
    state = _reset_if_new_day(state)
    state.setdefault("counts", {}).setdefault(module, {
        "daily": 0, "hourly": 0, "hour_bucket": _hour_bucket(time.time())
    })

    counts = state["counts"][module]
    now = time.time()
    current_hour = _hour_bucket(now)

    if counts.get("hour_bucket") != current_hour:
        counts["hourly"] = 0
        counts["hour_bucket"] = current_hour

    if monthly_limit > 0:
        mstate = _load_monthly()
        mstate = _reset_if_new_month(mstate)
        mstate.setdefault("counts", {}).setdefault(module, 0)
        if mstate["counts"][module] >= monthly_limit:
            _save_monthly(mstate)
            return False

    if daily_limit > 0 and counts["daily"] >= daily_limit:
        return False
    if hourly_limit > 0 and counts["hourly"] >= hourly_limit:
        return False

    counts["daily"] += 1
    counts["hourly"] += 1
    _save_state(state)

    if monthly_limit > 0:
        mstate["counts"][module] += 1
        _save_monthly(mstate)

    return True


def cap_status() -> dict:
    """Return current cap usage for all modules including monthly."""
    state = _load_state()
    state = _reset_if_new_day(state)
    mstate = _load_monthly()
    mstate = _reset_if_new_month(mstate)
    result = {}
    for mod, caps in DEFAULT_CAPS.items():
        counts = state.get("counts", {}).get(mod, {"daily": 0, "hourly": 0})
        monthly_used = mstate.get("counts", {}).get(mod, 0)
        monthly_limit = caps.get("monthly", 0)
        result[mod] = {
            "daily_used": counts.get("daily", 0),
            "daily_limit": caps.get("daily", 0),
            "hourly_used": counts.get("hourly", 0),
            "hourly_limit": caps.get("hourly", 0),
            "monthly_used": monthly_used,
            "monthly_limit": monthly_limit,
            "blocked": (
                (caps.get("daily", 0) > 0 and counts.get("daily", 0) >= caps["daily"]) or
                (caps.get("hourly", 0) > 0 and counts.get("hourly", 0) >= caps["hourly"]) or
                (monthly_limit > 0 and monthly_used >= monthly_limit)
            ),
        }
    return result


def cap_reset(module: Optional[str] = None) -> None:
    """Reset caps. If module is None, reset all (daily+monthly)."""
    if module:
        state = _load_state()
        state.setdefault("counts", {}).pop(module, None)
        _save_state(state)
        mstate = _load_monthly()
        mstate.setdefault("counts", {}).pop(module, None)
        _save_monthly(mstate)
    else:
        if CAP_FILE.exists():
            CAP_FILE.unlink()
        if MONTHLY_FILE.exists():
            MONTHLY_FILE.unlink()
