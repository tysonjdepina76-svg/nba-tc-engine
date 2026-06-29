# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""SGO (SportsGameOdds) adapter — DK player props + lines.

Pattern mirrors ESPN adapter: fetch + parse, NO math.
Returns domain entities (Game, OddsLine).

SGO V2 API notes (from existing daily_picks.py):
  - Default page size is 10 — all calls MUST include limit=100
  - Rate-limited
  - Returns DK lines (spreads, totals, moneyline, player props)
"""

import json
import os
import socket
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlencode

from src.circuit_breaker import CircuitBreakerRegistry, CircuitOpenError
from src.auto_retry import retry_with_backoff
from src.domain.entities import Game

socket.setdefaulttimeout(8)

WORKSPACE = Path("/home/workspace")
SECRETS_FILE = Path("/root/.zo/secrets.env")

SGO_BASE = "https://api.sportsgameodds.com/v2"
SGO_API_KEY_ENV = "SPORTSGAMEODDS_API_KEY"

# Default page size per your AGENTS.md — never call without it
DEFAULT_LIMIT = 100


def _load_api_key() -> Optional[str]:
    """Read SPORTSGAMEODDS_API_KEY from env or secrets file."""
    k = os.environ.get(SGO_API_KEY_ENV)
    if k:
        return k
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith(SGO_API_KEY_ENV + "="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


def _fetch(url: str, headers: dict, timeout: int = 10) -> dict:
    """Raw fetch."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}


class SGOAdapter:
    """SportsGameOdds data adapter."""

    _breakers = CircuitBreakerRegistry()

    def __init__(self, sport: str, league: Optional[str] = None):
        sport = sport.upper()
        if sport not in {"NFL", "NBA", "WNBA", "MLB", "SOCCER"}:
            raise ValueError(f"Unsupported sport: {sport}")
        self.sport = sport
        self.league = league or self._default_league(sport)
        self.api_key = _load_api_key()
        if not self.api_key:
            raise RuntimeError(f"Missing {SGO_API_KEY_ENV} in env or secrets file")
        self._breaker = self._breakers.get(
            f"sgo_{sport}", failure_threshold=3, recovery_timeout_sec=60
        )

    @staticmethod
    def _default_league(sport: str) -> str:
        return {
            "NFL": "nfl",
            "NBA": "nba",
            "WNBA": "wnba",
            "MLB": "mlb",
            "SOCCER": "fifa_world_cup",
        }[sport]

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key, "Accept": "application/json"}

    def fetch_live_odds(self, market: str = "all") -> List[dict]:
        """Fetch live odds. market ∈ {'all', 'spreads', 'totals', 'h2h', 'player_props'}.

        Lifted pattern from your existing /api/dk-lines pipeline.
        """
        params = {"league": self.league, "limit": DEFAULT_LIMIT}
        if market != "all":
            params["market"] = market
        url = f"{SGO_BASE}/odds?{urlencode(params)}"
        try:
            data = self._breaker.call(retry_with_backoff, _fetch, url, self._headers(), 10)
        except CircuitOpenError as e:
            print(f"[SGO] blocked: {e}")
            return []
        except Exception as e:
            print(f"[SGO] failed: {e}")
            return []
        if data.get("_error"):
            return []
        return data.get("data", data.get("events", []))

    def fetch_player_props(self, stat_key: Optional[str] = None) -> List[dict]:
        """Fetch DK-style player props for the current league.

        Returns list of dicts with at least:
        {player, team, stat, line, direction, odds, event_id}
        """
        rows = self.fetch_live_odds(market="player_props")
        props: List[dict] = []
        for row in rows:
            if stat_key and row.get("stat", "").upper() != stat_key.upper():
                continue
            for outcome in row.get("outcomes", []):
                props.append({
                    "player": row.get("player"),
                    "team": row.get("team"),
                    "stat": row.get("stat"),
                    "line": outcome.get("point") or row.get("line"),
                    "direction": outcome.get("name", "").lower(),
                    "odds": outcome.get("odds"),
                    "event_id": row.get("eventId") or row.get("event_id"),
                    "sport": self.sport,
                    "source": "SGO",
                })
        return props


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="WNBA")
    ap.add_argument("--market", default="player_props")
    args = ap.parse_args()
    a = SGOAdapter(sport=args.sport)
    data = a.fetch_live_odds(market=args.market)
    print(f"SGO {args.sport}/{args.market}: {len(data)} rows")