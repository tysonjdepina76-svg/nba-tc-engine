"""LivePoller — periodic live-stats puller.

Polls every 10 minutes during active slates, plus a 1:00 AM ET fallback
to catch late-night line moves and overnight roster swaps.

Usage:
    poller = LivePoller(interval_sec=600, fallback_hour=1)
    poller.start()         # blocking
    poller.start_once()    # one-shot (used by 1:00 AM fallback)
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("live_poller")

ET = timezone(timedelta(hours=-4))
DEFAULT_INTERVAL = 600  # 10 min
FALLBACK_HOUR_ET = 1    # 1:00 AM ET
LOG_PATH = Path("/home/workspace/Daily_Log/live_polls.log")


class LivePoller:
    """Polls live stats on an interval + a once-daily 1:00 AM ET fallback."""

    def __init__(
        self,
        interval_sec: int = DEFAULT_INTERVAL,
        fallback_hour_et: int = FALLBACK_HOUR_ET,
        fetcher: Optional[Callable[[], Dict[str, Any]]] = None,
        log_path: Path = LOG_PATH,
    ):
        self.interval_sec = interval_sec
        self.fallback_hour_et = fallback_hour_et
        self.fetcher = fetcher or self._default_fetch
        self.log_path = log_path
        self.last_poll_et: Optional[str] = None
        self.last_fallback_et: Optional[str] = None
        self.poll_count = 0
        self.fallback_count = 0

    def _default_fetch(self) -> Dict[str, Any]:
        """Default: try SGO live → ESPN boxscore → no-op."""
        try:
            from src.adapters.sportsgameodds.base import SGOBase  # type: ignore
            sgo = SGOBase()
            return sgo.fetch_live(limit=10)
        except Exception as e:
            log.debug(f"sgo live failed: {e}")
            return {}

    def _log(self, msg: str) -> None:
        ts = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as f:
            f.write(f"[{ts}] {msg}\n")

    def _now_et(self) -> datetime:
        return datetime.now(ET)

    def _is_fallback_window(self) -> bool:
        n = self._now_et()
        return n.hour == self.fallback_hour_et and n.minute < 5

    def tick(self) -> Dict[str, Any]:
        """One poll iteration. Returns fetch result + metadata."""
        now = self._now_et()
        is_fallback = self._is_fallback_window()
        try:
            data = self.fetcher()
        except Exception as e:
            self._log(f"poll error: {e}")
            return {"ok": False, "error": str(e)}
        self.last_poll_et = now.isoformat()
        if is_fallback:
            self.last_fallback_et = now.isoformat()
            self.fallback_count += 1
            self._log(f"FALLBACK poll #{self.fallback_count} → {len(data) if isinstance(data, (list, dict)) else 'n/a'}")
        else:
            self.poll_count += 1
        return {"ok": True, "data": data, "fallback": is_fallback, "ts": self.last_poll_et}

    def start_once(self) -> Dict[str, Any]:
        """Single-tick entry (used by 1:00 AM fallback)."""
        return self.tick()

    def start(self, max_ticks: Optional[int] = None) -> None:
        """Blocking poll loop. Use max_ticks for tests."""
        ticks = 0
        while True:
            self.tick()
            ticks += 1
            if max_ticks and ticks >= max_ticks:
                return
            time.sleep(self.interval_sec)

    def status(self) -> Dict[str, Any]:
        return {
            "interval_sec": self.interval_sec,
            "fallback_hour_et": self.fallback_hour_et,
            "last_poll_et": self.last_poll_et,
            "last_fallback_et": self.last_fallback_et,
            "poll_count": self.poll_count,
            "fallback_count": self.fallback_count,
        }
