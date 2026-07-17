"""Unified line/odds fetcher for all sports. Delegates to sport-specific adapters."""
from __future__ import annotations
import os
import time
from typing import Dict, Any, Optional

from src.adapters.mlb_book_fetcher import fetch_mlb_moneyline, fetch_mlb_totals
from src.adapters.odds_api import fetch_event_odds, fetch_events_list
from src.adapters.sgo import fetch_events as sgo_fetch_events


def fetch_lines(sport: str, date_str: Optional[str] = None) -> Dict[str, Any]:
    """Fetch available lines for a sport. Returns a dict with source + data."""
    sport = sport.lower().strip()

    if sport == "mlb":
        d = date_str or time.strftime("%Y-%m-%d")
        ml = fetch_mlb_moneyline(d)
        totals = fetch_mlb_totals(d)
        return {
            "source": ml.get("source", "unknown"),
            "moneyline": ml.get("games", []),
            "totals": totals.get("games", []),
            "fetched_at": time.time(),
        }

    if sport == "wnba":
        events = sgo_fetch_events("wnba")
        return {
            "source": "sgo",
            "events": events or [],
            "fetched_at": time.time(),
        }

    if sport == "wc":
        events = fetch_events_list("soccer_world_cup")
        return {
            "source": "odds_api",
            "events": events or [],
            "fetched_at": time.time(),
        }

    return {"source": "unknown", "error": f"No adapter for sport '{sport}'"}
