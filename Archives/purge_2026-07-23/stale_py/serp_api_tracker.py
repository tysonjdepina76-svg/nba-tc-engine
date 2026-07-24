"""SerpAPI quota tracker — enforces 250 searches/day with per-run cap.
Ported from serp_odds_scraper.py into a hard file to survive restarts."""

import json
import os
from datetime import datetime, date
from pathlib import Path

TRACKER_PATH = Path("/home/workspace/Projects/data/serp_quota.json")
DAILY_LIMIT = 250
PER_RUN_CAP = 8

def _load():
    if not TRACKER_PATH.exists():
        return {"date": str(date.today()), "used": 0}
    try:
        return json.loads(TRACKER_PATH.read_text())
    except Exception:
        return {"date": str(date.today()), "used": 0}

def _save(data):
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_PATH.write_text(json.dumps(data))

def _today_str():
    return str(date.today())

def quota_left():
    """Return (remaining, daily_limit, used_today)."""
    d = _load()
    if d.get("date") != _today_str():
        return DAILY_LIMIT, DAILY_LIMIT, 0
    return max(0, DAILY_LIMIT - d["used"]), DAILY_LIMIT, d["used"]

def record_search(n=1):
    """Record n searches. Returns True if within quota, False if exceeded."""
    d = _load()
    today = _today_str()
    if d.get("date") != today:
        d = {"date": today, "used": 0}
    d["used"] += n
    _save(d)
    if d["used"] > DAILY_LIMIT:
        return False
    return True

def cap_this_run():
    """Return how many searches are allowed this run (min of remaining and per-run)."""
    remaining, _, _ = quota_left()
    return min(remaining, PER_RUN_CAP)

def is_exhausted():
    """True if daily quota fully used."""
    remaining, _, _ = quota_left()
    return remaining <= 0
