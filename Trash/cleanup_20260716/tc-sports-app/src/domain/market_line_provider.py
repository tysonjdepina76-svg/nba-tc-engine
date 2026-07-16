"""MarketLineProvider — unified market lines across Odds API, SGO, SportsDataIO, self-edge.

Per sport, returns:
- lines: list of {event_id, sport, market, side, line, price, book, source, fetched_at}
- status: dict describing which sources were tried and their results
- source: the winning source ('oddsapi', 'sgo', 'sportsdataio', 'selfedge', 'off_season', 'none')
- props: bool — whether player props are available
- message: human-readable status

Off-season: NBA and NHL return source='off_season' until Oct.
Quota-exhausted: falls back to self-edge.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Off-season windows (sport -> month of return; 0=Jan, 9=Oct)
_OFF_SEASON_MONTHS = {
    "NBA": 9,   # returns Oct
    "NHL": 9,   # returns Oct
}


def _is_off_season(sport: str, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    if sport not in _OFF_SEASON_MONTHS:
        return False
    return now.month < _OFF_SEASON_MONTHS[sport]


class SelfEdgeAdapter:
    """Fallback when no market lines are available — uses TC projections only."""

    sport: str = ""

    def get_status(self) -> dict:
        return {
            "sport": self.sport,
            "status": "self_edge",
            "message": "Using TC projections (no market lines available)",
            "source": "selfedge",
            "props": True,
            "events": 0,
        }


class OffSeasonAdapter:
    sport: str = ""

    def get_status(self) -> dict:
        return {
            "sport": self.sport,
            "status": "off_season",
            "message": f"{self.sport} is off-season — projections resume in October",
            "source": "off_season",
            "props": False,
            "events": 0,
        }


class MarketLineProvider:
    """Unified market line provider with graceful degradation."""

    def __init__(self, sport: str):
        self.sport = sport.upper()
        self._events: list[dict] = []
        self._source: str = "none"
        self._message: str = "No data yet — call get_lines() first"

    def _try_oddsapi(self) -> Optional[list[dict]]:
        key = os.environ.get("ODDS_API_KEY", "")
        if not key:
            return None
        try:
            import requests
            sport_key = {"WNBA": "basketball_wnba", "MLB": "baseball_mlb",
                         "NFL": "americanfootball_nfl", "NBA": "basketball_nba",
                         "NHL": "icehockey_nhl", "SOCCER": "soccer"}.get(self.sport, "")
            if not sport_key:
                return None
            r = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={"apiKey": key, "regions": "us", "markets": "h2h,spreads,totals"},
                timeout=5,
            )
            if r.status_code == 200:
                self._source = "oddsapi"
                return r.json()
            if r.status_code == 401:
                self._message = "Odds API quota exhausted (401)"
                return None
        except Exception as e:
            logger.debug("Odds API failed: %s", e)
        return None

    def _try_sgo(self) -> Optional[list[dict]]:
        key = os.environ.get("SPORTSGAMEODDS_API_KEY", "")
        if not key:
            return None
        try:
            from src.adapters.sportsgameodds.base import SGOClient
            client = SGOClient(api_key=key)
            data = client.fetch_events(self.sport)
            if data:
                self._source = "sgo"
                return data
        except Exception as e:
            logger.debug("SGO failed: %s", e)
        return None

    def _try_sportsdataio(self) -> Optional[list[dict]]:
        key = os.environ.get("SPORTSDATAIO_KEY", "")
        if not key:
            return None
        try:
            adapter_map = {
                "WNBA": "src.adapters.sportsdataio.wnba.WNBAAdapter",
                "NFL": "src.adapters.sportsdataio.nfl.NFLAdapter",
                "MLB": "src.adapters.sportsdataio.mlb.MLBAdapter",
            }
            mod_path = adapter_map.get(self.sport)
            if not mod_path:
                return None
            mod_name, cls_name = mod_path.rsplit(".", 1)
            import importlib
            mod = importlib.import_module(mod_name)
            adapter = getattr(mod, cls_name)(api_key=key)
            data = adapter.fetch_events()
            if data:
                self._source = "sportsdataio"
                return data
        except Exception as e:
            logger.debug("SportsDataIO failed: %s", e)
        return None

    def _self_edge(self) -> list[dict]:
        self._source = "selfedge"
        self._message = "Using TC projections (no market lines available)"
        return []

    def get_lines(self) -> dict:
        if _is_off_season(self.sport):
            adapter = OffSeasonAdapter()
            adapter.sport = self.sport
            return adapter.get_status()

        for fetcher in (self._try_oddsapi, self._try_sgo, self._try_sportsdataio):
            try:
                data = fetcher()
                if data is not None:
                    self._events = data
                    return {
                        "sport": self.sport,
                        "status": "ok",
                        "source": self._source,
                        "events": len(self._events),
                        "props": True,
                        "message": f"Lines from {self._source}",
                        "data": self._events,
                    }
            except Exception as e:
                logger.debug("Fetcher %s failed: %s", fetcher.__name__, e)

        # All failed — self-edge
        self._self_edge()
        adapter = SelfEdgeAdapter()
        adapter.sport = self.sport
        return adapter.get_status()
