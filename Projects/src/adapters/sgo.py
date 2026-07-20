"""SGO (SportsGameOdds) adapter — MLB + World Cup lines.
WNBA is NOT supported by SGO (NBA-only tier). Use Odds API for WNBA.
"""

from __future__ import annotations
import os
import time
import json
from pathlib import Path
from typing import Any

import requests

SGO_BASE = "https://api.sportsgameodds.com/v2"

class SGOAdapter:
    def __init__(self) -> None:
        self.key = os.environ.get("SGO_API_KEY", "")
        self.cache_dir = Path("/home/workspace/.cache/sgo")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get(self, path: str, params: dict | None = None) -> dict:
        if not self.key:
            return {}
        params = params or {}
        params["key"] = self.key
        url = f"{SGO_BASE}{path}"
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  [SGO] {path} err: {e}")
            return {}

    def fetch_events(self, sport: str = "mlb") -> list[dict]:
        sport_map = {
            "mlb": "/baseball/mlb/events",
            "wc": "/soccer/world-cup/events",
        }
        path = sport_map.get(sport.lower(), "")
        if not path:
            return []
        data = self._get(path)
        return data.get("events", data.get("data", []))

    def fetch_odds(self, event_id: str, sport: str = "mlb") -> dict:
        path = f"/events/{event_id}/odds"
        return self._get(path)

    def fetch_player_props(self, event_id: str, sport: str = "mlb") -> list[dict]:
        path = f"/events/{event_id}/player-props"
        data = self._get(path)
        return data.get("props", data.get("data", []))

    def get_lines_for_matchup(self, sport: str, away: str, home: str) -> dict[str, Any]:
        if sport.lower() == "wnba":
            return {"players": {}, "available_books": [], "source": "sgo", "error": "SGO does not support WNBA (NBA-only tier)"}

        events = self.fetch_events(sport)
        for ev in events:
            teams = ev.get("teams", [])
            if len(teams) >= 2:
                a = teams[0].get("name", {}).get("short", "")
                h = teams[1].get("name", {}).get("short", "")
                if a and h and (away in a or a in away) and (home in h or h in home):
                    event_id = ev.get("id", "")
                    odds = self.fetch_odds(event_id, sport)
                    return self._parse_odds_to_players(odds, sport)
        return {"players": {}, "available_books": [], "source": "sgo", "error": f"No matching event for {away}@{home}"}

    def _parse_odds_to_players(self, odds_data: dict, sport: str) -> dict[str, Any]:
        players: dict[str, Any] = {}
        books = odds_data.get("bookmakers", [])
        available_books: list[str] = []

        for book in books:
            if book.get("key") != "draftkings":
                continue
            available_books.append("draftkings")
            for market in book.get("markets", []):
                for outcome in market.get("outcomes", []):
                    name = outcome.get("description", outcome.get("name", ""))
                    if not name:
                        continue
                    players[name] = players.get(name, {})
                    stat_key = outcome.get("name", "").lower()
                    players[name][stat_key] = {
                        "line": outcome.get("point", 0),
                        "over_price": outcome.get("price", 0),
                        "under_price": 0,
                        "book": "draftkings",
                    }

        return {"players": players, "available_books": available_books, "source": "sgo"}

_sgo_instance = SGOAdapter()

def fetch_events(sport: str = "mlb") -> list[dict]:
    return _sgo_instance.fetch_events(sport)

def fetch_player_props(event_id: str, sport: str = "mlb") -> list[dict]:
    return _sgo_instance.fetch_player_props(event_id, sport)
