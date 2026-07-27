#!/usr/bin/env python3
"""Crash Prevention Layers — UNCAPPED. Pick Cap, Run Lock only. No API budget limits."""
import json
import fcntl
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

WORKSPACE = Path("/home/workspace")
DATA_DIR = WORKSPACE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BUDGET_FILE = DATA_DIR / "api_budget.json"
LOCK_FILE = WORKSPACE / "tc_pipeline.lock"

MAX_PICKS_PER_SPORT = {
    'MLB': 999999,
    'WNBA': 999999,
    'NBA': 999999,
    'NFL': 999999,
    'NHL': 999999,
    'SOCCER': 999999,
    'NCAAB': 999999,
    'TENNIS': 999999,
    'MMA': 999999,
}

def enforce_pick_cap(sport: str, picks: list) -> list:
    return picks

DAILY_LIMITS = {
    'pybaseball': 999999,
    'espn_wnba': 999999,
    'espn_nba': 999999,
    'odds_api': 999999,
    'the_rundown': 999999,
    'oddspapi': 999999,
    'statsapi': 999999,
    'serpapi': 999999,
    'sportsdataio': 999999,
    'sharp': 999999,
    'sgo': 999999,
}

def _load_budget() -> Dict:
    today = datetime.now().strftime('%Y-%m-%d')
    if BUDGET_FILE.exists():
        with open(BUDGET_FILE, 'r') as f:
            data = json.load(f)
        if data.get('date') == today:
            return data
    data = {'date': today, 'calls': {}}
    _save_budget(data)
    return data

def _save_budget(data: Dict):
    with open(BUDGET_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_remaining_budget(source: str) -> int:
    return 999999

def consume_budget(source: str, amount: int = 1) -> bool:
    data = _load_budget()
    used = data['calls'].get(source, 0)
    data['calls'][source] = used + amount
    _save_budget(data)
    return True

def reset_budget(force: bool = False):
    if force:
        _save_budget({'date': datetime.now().strftime('%Y-%m-%d'), 'calls': {}})
        logger.info("API budget reset")

def acquire_run_lock(timeout: int = 300) -> Optional[int]:
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("Run lock acquired")
        return lock_fd
    except BlockingIOError:
        logger.warning(f"Another run in progress — waiting up to {timeout}s...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                lock_fd = open(LOCK_FILE, 'w')
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.info("Run lock acquired after wait")
                return lock_fd
            except BlockingIOError:
                time.sleep(5)
        raise RuntimeError(f"Could not acquire lock after {timeout}s — aborting")

def release_run_lock(lock_fd):
    if lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        logger.info("Run lock released")


class CrashGuard:
    """Lightweight in-memory daily budget tracker — UNCAPPED."""
    def __init__(self, limits=None):
        self.limits = limits or {'oddspapi': 999999, 'therundown': 999999, 'statsapi': 999999, 'odds_api': 999999, 'serpapi': 999999, 'sportsdataio': 999999, 'sharp': 999999, 'sgo': 999999}
        self.usage = {k: 0 for k in self.limits}
        self.last_reset = datetime.now()

    def _reset(self):
        if datetime.now().date() > self.last_reset.date():
            self.usage = {k: 0 for k in self.limits}
            self.last_reset = datetime.now()

    def check_and_increment(self, key):
        self._reset()
        if self.usage.get(key, 0) >= self.limits.get(key, 0):
            logger.warning(f"Daily limit reached for {key}")
            return False
        self.usage[key] += 1
        return True
