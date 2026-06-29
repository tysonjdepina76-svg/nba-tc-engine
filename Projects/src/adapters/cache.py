"""
Unified cache for all API responses.
TTL per endpoint, auto-expiry, size limit.

ADAPTER_TTL = {"espn_rosters": 3600, "espn_scores": 300, "sgo_lines": 300, "odds_lines": 300}

In each adapter:
    import os
    DAILY_LIMIT = int(os.getenv("API_DAILY_LIMIT", 500))
    calls_today = 0
    def _check_quota():
        global calls_today
        if calls_today >= DAILY_LIMIT:
            raise Exception("Daily API quota exceeded")
        calls_today += 1
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


ADAPTER_TTL = {
    "espn_rosters": 3600,
    "espn_scores": 300,
    "sgo_lines": 300,
    "odds_lines": 300,
}

DAILY_LIMIT = int(os.getenv("API_DAILY_LIMIT", 500))


class APICache:
    def __init__(self, cache_dir: str = "/tmp/tc_api_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, max_age: int = 300) -> Optional[Any]:
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text())
            cached_time = datetime.fromisoformat(data["timestamp"])
            if (datetime.now() - cached_time).seconds > max_age:
                return None
            return data["value"]
        except Exception:
            return None

    def set(self, key: str, value: Any):
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "value": value}))


# Daily-call ledger (persisted across runs)
_LEDGER_PATH = Path("/tmp/tc_api_call_ledger.json")


def _load_ledger() -> dict:
    if not _LEDGER_PATH.exists():
        return {"date": "", "counts": {"ESPN": 0, "SGO": 0, "OddsAPI": 0, "OTHER": 0}}
    try:
        return json.loads(_LEDGER_PATH.read_text())
    except Exception:
        return {"date": "", "counts": {"ESPN": 0, "SGO": 0, "OddsAPI": 0, "OTHER": 0}}


def _save_ledger(ledger: dict):
    _LEDGER_PATH.write_text(json.dumps(ledger))


def check_quota(adapter: str) -> None:
    """Raises if the adapter would exceed its daily quota. Increments counter."""
    from datetime import date
    today = date.today().isoformat()
    ledger = _load_ledger()
    if ledger.get("date") != today:
        ledger = {"date": today, "counts": {"ESPN": 0, "SGO": 0, "OddsAPI": 0, "OTHER": 0}}
    total = sum(ledger["counts"].values())
    if total >= DAILY_LIMIT:
        raise Exception(f"Daily API quota exceeded ({total}/{DAILY_LIMIT})")
    ledger["counts"][adapter] = ledger["counts"].get(adapter, 0) + 1
    _save_ledger(ledger)


def quota_state() -> dict:
    """Return current-day usage breakdown."""
    return _load_ledger()