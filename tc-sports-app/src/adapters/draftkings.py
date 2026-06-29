"""DraftKings public adapter — no auth required.

Fetches player props and odds from DK's public sportsbook API.
Endpoint is unofficial but stable: https://sportsbook.draftkings.com/sites/US-NJ-SB/api/v5/eventgroups
"""
from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class DraftKingsAdapter:
    """Public DraftKings adapter for player props and game lines."""

    DK_BASE = "https://sportsbook.draftkings.com"
    API_BASE = "https://sportsbook.draftkings.com/sites/US-NJ-SB/api/v5"

    # Sport → DK league id mapping
    SPORT_LEAGUE_IDS: dict[str, int] = {
        "NBA": 42648,
        "WNBA": 42910,
        "MLB": 84240,
        "NFL": 88808,
        "NHL": 42133,
        "EPL": 40253,
        "WC": 42648,  # generic fallback
    }

    def __init__(self, timeout: float = 15.0, user_agent: str | None = None):
        self.timeout = timeout
        self.ua = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )

    def _fetch(self, url: str) -> dict[str, Any] | list[Any]:
        req = Request(url, headers={"User-Agent": self.ua, "Accept": "application/json"})
        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_event_groups(self, sport: str) -> list[dict[str, Any]]:
        """Return list of event groups for a sport."""
        league_id = self.SPORT_LEAGUE_IDS.get(sport.upper(), 42648)
        url = f"{self.API_BASE}/eventgroups/{league_id}/categories"
        try:
            data = self._fetch(url)
            return data.get("eventGroup", {}).get("events", []) or []
        except Exception as e:
            print(f"[draftkings] eventgroups error for {sport}: {e}")
            return []

    def get_event_markets(self, event_id: str | int) -> list[dict[str, Any]]:
        """Return list of markets (player props, lines) for an event."""
        url = f"{self.API_BASE}/events/{event_id}/markets"
        try:
            data = self._fetch(url)
            markets = data.get("markets", []) or []
            return markets
        except Exception as e:
            print(f"[draftkings] event markets error for {event_id}: {e}")
            return []

    def parse_prop_outcomes(self, market: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert a DK market dict into normalized prop rows."""
        rows: list[dict[str, Any]] = []
        market_type = market.get("marketType", {}).get("name", "")
        for sel in market.get("selections", []) or []:
            label = sel.get("label", "")
            if "Over" not in label and "Under" not in label:
                continue
            direction = "OVER" if "Over" in label else "UNDER"
            participant = sel.get("participant", label.replace("Over", "").replace("Under", "").strip())
            point = sel.get("points", 0.0)
            odds_decimal = sel.get("displayDecimalOdds", 1.91)
            try:
                odds_american = sel.get("displayAmericanOdds") or self._dec_to_american(odds_decimal)
            except Exception:
                odds_american = -110
            rows.append({
                "player": participant,
                "stat": market_type,
                "direction": direction,
                "line": float(point or 0.0),
                "odds_american": int(odds_american),
                "odds_decimal": float(odds_decimal),
                "book": "draftkings",
            })
        return rows

    @staticmethod
    def _dec_to_american(decimal_odds: float) -> int:
        try:
            d = float(decimal_odds)
        except Exception:
            return -110
        if d >= 2.0:
            return int(round((d - 1.0) * 100))
        return int(round(-100 / (d - 1.0)))

    def fetch_player_props(
        self,
        sport: str,
        stat_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """High-level: fetch normalized player prop rows for a sport."""
        if stat_filter is None:
            stat_filter = ["Points", "Rebounds", "Assists", "3-Pointers Made", "Steals", "Blocks"]

        out: list[dict[str, Any]] = []
        events = self.get_event_groups(sport)
        for ev in events:
            event_id = ev.get("eventId")
            if not event_id:
                continue
            for market in self.get_event_markets(event_id):
                market_name = market.get("marketType", {}).get("name", "")
                if market_name not in stat_filter:
                    continue
                out.extend(self.parse_prop_outcomes(market))
        return out


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "NBA"
    a = DraftKingsAdapter()
    rows = a.fetch_player_props(sport)
    print(f"draftkings {sport}: {len(rows)} rows")
    for r in rows[:5]:
        print(r)