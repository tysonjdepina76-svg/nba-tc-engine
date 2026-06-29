# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""The Odds API adapter — multi-book odds + h2h + totals.

Pattern mirrors ESPN adapter: fetch + parse, NO math.
Returns domain entities.

Notes from your existing pipeline:
  - Business trial tier (toa_live_t5d8p3n1), reverts to Pro 2026-07-26
  - Multiple books available in one call (dk, fd, betmgm, caesars, pointsbet, bovada)
  - Cost: ~1 credit per market per sport
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlencode

from src.circuit_breaker import CircuitBreakerRegistry, CircuitOpenError
from src.auto_retry import retry_with_backoff

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_API_KEY_ENV = "ODDS_API_KEY"
SECRETS_FILE = Path("/root/.zo/secrets.env")

# Sport key mapping (the-odds-api uses its own keys)
SPORT_KEYS = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "WNBA": "basketball_wnba",
    "MLB": "baseball_mlb",
    "SOCCER": "soccer_fifa_world_cup",
}

SUPPORTED_BOOKS = [
    "draftkings",
    "fanduel",
    "betmgm",
    "caesars",
    "pointsbet",
    "bovada",
    "williamhill_us",
]


def _load_api_key() -> Optional[str]:
    k = os.environ.get(ODDS_API_KEY_ENV)
    if k:
        return k
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith(ODDS_API_KEY_ENV + "="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


def _fetch(url: str, timeout: int = 10) -> dict:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}


class OddsAPIAdapter:
    """The Odds API — multi-book odds."""

    _breakers = CircuitBreakerRegistry()

    def __init__(self, sport: str, regions: str = "us", markets: str = "h2h,spreads,totals"):
        sport = sport.upper()
        if sport not in SPORT_KEYS:
            raise ValueError(f"Unsupported sport: {sport}")
        self.sport = sport
        self.sport_key = SPORT_KEYS[sport]
        self.regions = regions
        self.markets = markets
        self.api_key = _load_api_key()
        if not self.api_key:
            raise RuntimeError(f"Missing {ODDS_API_KEY_ENV}")
        self._breaker = self._breakers.get(
            f"oddsapi_{sport}", failure_threshold=3, recovery_timeout_sec=60
        )

    def fetch_events(self) -> List[dict]:
        """List upcoming events for the sport."""
        params = {"apiKey": self.api_key}
        url = f"{ODDS_API_BASE}/sports/{self.sport_key}/events?{urlencode(params)}"
        return self._safe_get(url)

    def fetch_odds(self, event_id: Optional[str] = None, books: Optional[List[str]] = None) -> List[dict]:
        """Fetch odds across multiple books. ~1 credit per market.

        If event_id omitted, returns all events for sport.
        """
        books = books or SUPPORTED_BOOKS
        params = {
            "apiKey": self.api_key,
            "regions": self.regions,
            "markets": self.markets,
            "oddsFormat": "american",
            "bookmakers": ",".join(books),
        }
        if event_id:
            url = f"{ODDS_API_BASE}/sports/{self.sport_key}/events/{event_id}/odds?{urlencode(params)}"
        else:
            url = f"{ODDS_API_BASE}/sports/{self.sport_key}/odds?{urlencode(params)}"
        return self._safe_get(url)

    def fetch_player_props(self, event_id: str, markets: str = "player_points,player_rebounds,player_assists") -> List[dict]:
        """Fetch player props (player_points, player_rebounds, player_assists, etc)."""
        params = {
            "apiKey": self.api_key,
            "regions": self.regions,
            "markets": markets,
            "oddsFormat": "american",
        }
        url = f"{ODDS_API_BASE}/sports/{self.sport_key}/events/{event_id}/odds?{urlencode(params)}"
        return self._safe_get(url)

    def _safe_get(self, url: str) -> List[dict]:
        try:
            data = self._breaker.call(retry_with_backoff, _fetch, url, 10)
        except CircuitOpenError as e:
            print(f"[OddsAPI] blocked: {e}")
            return []
        except Exception as e:
            print(f"[OddsAPI] failed: {e}")
            return []
        if data.get("_error"):
            return []
        return data if isinstance(data, list) else [data]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="WNBA")
    args = ap.parse_args()
    a = OddsAPIAdapter(sport=args.sport)
    events = a.fetch_events()
    print(f"OddsAPI {args.sport}: {len(events)} events")