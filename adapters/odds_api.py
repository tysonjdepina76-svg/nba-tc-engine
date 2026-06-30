"""OddsAPI adapter — events + player props."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import urllib.request
import json
from dataclasses import dataclass, field
from typing import List


MARKET_TO_STAT = {
    "player_points": "pts",
    "player_rebounds": "reb",
    "player_assists": "ast",
    "player_threes": "3pm",
}


@dataclass
class OddsAPIEvent:
    id: str
    sport_key: str
    home_team: str
    away_team: str
    commence_time: str = ""


@dataclass
class OddsAPIProp:
    event_id: str
    market: str
    stat: str
    best_over_price: int = None
    best_under_price: int = None
    line: float = 0.0
    bookmakers: list = field(default_factory=list)


class OddsAPIClient:
    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key=None):
        if not api_key:
            raise ValueError("OddsAPI key is required")
        self.api_key = api_key

    def _get(self, url):
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}apiKey={self.api_key}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def fetch_events(self, sport: str) -> List[OddsAPIEvent]:
        url = f"{self.BASE_URL}/sports/{sport}/events"
        try:
            payload = self._get(url)
        except Exception:
            return []
        events = []
        for item in payload:
            events.append(OddsAPIEvent(
                id=item.get("id", ""),
                sport_key=item.get("sport_key", sport),
                home_team=item.get("home_team", ""),
                away_team=item.get("away_team", ""),
                commence_time=item.get("commence_time", ""),
            ))
        return events

    def fetch_player_props(self, sport: str, event_id: str) -> List[OddsAPIProp]:
        url = f"{self.BASE_URL}/sports/{sport}/events/{event_id}/odds?markets=player_points,player_rebounds,player_assists,player_threes"
        try:
            payload = self._get(url)
        except Exception:
            return []
        props = []
        for bm in payload.get("bookmakers", []):
            for market in bm.get("markets", []):
                market_key = market.get("key", "")
                stat = MARKET_TO_STAT.get(market_key)
                if not stat:
                    continue
                over_prices = [o["price"] for o in market.get("outcomes", []) if o.get("name") == "Over"]
                under_prices = [o["price"] for o in market.get("outcomes", []) if o.get("name") == "Under"]
                line = next((o.get("point", 0) for o in market.get("outcomes", []) if o.get("name") == "Over"), 0.0)
                props.append(OddsAPIProp(
                    event_id=event_id,
                    market=market_key,
                    stat=stat,
                    line=float(line),
                    best_over_price=max(over_prices) if over_prices else None,
                    best_under_price=max(under_prices) if under_prices else None,
                    bookmakers=[bm.get("key", "")],
                ))
        return props
