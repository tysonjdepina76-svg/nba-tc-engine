"""EventTrigger — fire callbacks when market lines or rosters change.

Replaces ad-hoc polling. Subscribers register handlers for sport+event;
trigger fires when line value or roster membership changes beyond a
threshold.

Usage:
    et = EventTrigger()
    et.subscribe("WNBA", on_line_change)
    et.notify("WNBA", {"event_id": "...", "new_line": 18.5, "old_line": 17.5})
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("event_trigger")

LINE_DELTA = 0.5  # fire on ≥0.5 point swing
ROSTER_DELTA = 1  # fire on any roster membership change


@dataclass
class TriggerRecord:
    sport: str
    payload: Dict[str, Any]
    fired_at: float = 0.0


class EventTrigger:
    """Pub/sub for sport + line / roster changes."""

    def __init__(self, line_delta: float = LINE_DELTA, roster_delta: int = ROSTER_DELTA):
        self.line_delta = line_delta
        self.roster_delta = roster_delta
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._last_state: Dict[str, Dict[str, Any]] = {}
        self._history: List[TriggerRecord] = []

    def subscribe(self, sport: str, handler: Callable) -> None:
        self._handlers[sport.upper()].append(handler)

    def on_line_change(self, sport: str, data: Dict[str, Any]) -> List[TriggerRecord]:
        """Check if a line moved enough to fire; if so, run handlers.

        `data` keys: event_id, player, stat, new_line, old_line (optional).
        """
        sport = sport.upper()
        key = f"{sport}:{data.get('event_id', '')}:{data.get('player', '')}:{data.get('stat', '')}"
        prev = self._last_state.get(key, {})
        new_val = data.get("new_line")
        old_val = data.get("old_line", prev.get("new_line"))
        fired: List[TriggerRecord] = []
        if old_val is not None and new_val is not None:
            if abs(float(new_val) - float(old_val)) >= self.line_delta:
                rec = TriggerRecord(sport=sport, payload=data)
                self._history.append(rec)
                fired.append(rec)
                for h in self._handlers.get(sport, []):
                    try:
                        h(data)
                    except Exception as e:
                        log.warning(f"handler error: {e}")
        self._last_state[key] = {"new_line": new_val}
        return fired

    def on_roster_change(self, sport: str, data: Dict[str, Any]) -> List[TriggerRecord]:
        """Fire if a player joined/left the active roster."""
        sport = sport.upper()
        key = f"{sport}:roster:{data.get('team', '')}"
        prev = set(self._last_state.get(key, {}).get("players", []))
        new = set(data.get("players", []))
        if prev and (new - prev or prev - new):
            rec = TriggerRecord(sport=sport, payload=data)
            self._history.append(rec)
            for h in self._handlers.get(sport, []):
                try:
                    h({"type": "roster", **data})
                except Exception as e:
                    log.warning(f"handler error: {e}")
            self._last_state[key] = {"players": list(new)}
            return [rec]
        self._last_state[key] = {"players": list(new)}
        return []

    def history(self, sport: Optional[str] = None) -> List[TriggerRecord]:
        if sport:
            return [r for r in self._history if r.sport == sport.upper()]
        return list(self._history)

    def reset(self) -> None:
        self._last_state.clear()
        self._history.clear()
