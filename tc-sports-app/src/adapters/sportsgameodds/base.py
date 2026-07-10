"""SportsGameOdds Base Adapter — Shared client for all sports."""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class SGOBase:
    """Base client for SportsGameOdds API v2. Provides shared HTTP, caching, and rate-limit handling for all sports."""

    BASE_URL = "https://api.sportsgameodds.com/v2"

    SPORT_KEYS = {
        "MLB": "baseball/mlb",
        "WNBA": "basketball/wnba",
        "NBA": "basketball/nba",
        "NHL": "hockey/nhl",
        "NFL": "football/nfl",
        "SOCCER": "soccer",
        "WORLD_CUP": "soccer",
    }

    def __init__(self, api_key: Optional[str] = None, sport: str = "MLB"):
        self.api_key = api_key or os.environ.get("SGO_API_KEY")
        if not self.api_key:
            raise ValueError("SGO_API_KEY secret not set")
        self.sport = sport.upper()
        self.sport_key = self.SPORT_KEYS.get(self.sport)
        if not self.sport_key:
            raise ValueError(f"Unknown sport: {sport}. Supported: {list(self.SPORT_KEYS)}")
        self.cache_dir = Path("/tmp/sgo_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = 300
        self.daily_count = 0
        self.last_429_at = None
        self.status = "unknown"

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        import hashlib
        key_str = f"{endpoint}_{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Any]:
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text())
            age = (datetime.now() - datetime.fromisoformat(data["timestamp"])).seconds
            if age > self.cache_ttl:
                return None
            return data["value"]
        except Exception:
            return None

    def _set_cached(self, key: str, value: Any):
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "value": value}))

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        cache_key = self._get_cache_key(endpoint, params)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        try:
            resp = requests.get(url, params={"apiKey": self.api_key, **params}, timeout=30)
            self.daily_count += 1
            if resp.status_code == 429:
                self.last_429_at = datetime.now().isoformat()
                self.status = "rate_limited"
            elif resp.status_code == 200:
                self.status = "healthy"
            resp.raise_for_status()
            data = resp.json()
            self._set_cached(cache_key, data)
            return data
        except Exception as e:
            self.status = "error"
            raise

    def get_sports(self) -> List[Dict]:
        return self._request("sports")

    def get_events(self, league: Optional[str] = None) -> List[Dict]:
        ep = f"events/{self.sport_key}" + (f"/{league}" if league else "")
        return self._request(ep)

    def get_event(self, event_id: str) -> Dict:
        return self._request(f"events/{self.sport_key}/{event_id}")

    def get_lines(self, event_id: str, market: Optional[str] = None) -> Dict:
        ep = f"events/{self.sport_key}/{event_id}/lines"
        if market:
            ep += f"?market={market}"
        return self._request(ep)

    def get_markets(self, event_id: str) -> List[Dict]:
        return self._request(f"events/{self.sport_key}/{event_id}/markets")

    def get_player_props(self, event_id: str) -> List[Dict]:
        return self._request(f"events/{self.sport_key}/{event_id}/player-props")

    def get_odds(self, event_id: str) -> Dict:
        return self._request(f"events/{self.sport_key}/{event_id}/odds")

    def get_consensus(self, event_id: str) -> Dict:
        return self._request(f"events/{self.sport_key}/{event_id}/consensus")

    def get_futures(self) -> List[Dict]:
        return self._request(f"futures/{self.sport_key}")

    def get_polls(self) -> List[Dict]:
        return self._request(f"polls/{self.sport_key}")

    def get_injuries(self) -> List[Dict]:
        return self._request(f"injuries/{self.sport_key}")

    def get_teams(self) -> List[Dict]:
        return self._request(f"teams/{self.sport_key}")

    def get_standings(self) -> List[Dict]:
        return self._request(f"standings/{self.sport_key}")

    def get_player_season_stats(self, player_id: str) -> Dict:
        return self._request(f"players/{self.sport_key}/{player_id}/stats")

    def get_player_game_log(self, player_id: str) -> List[Dict]:
        return self._request(f"players/{self.sport_key}/{player_id}/gamelog")

    def check_health(self) -> Dict:
        try:
            sports = self.get_sports()
            return {
                "status": self.status,
                "sports_count": len(sports) if isinstance(sports, list) else 0,
                "http_code": 200,
                "daily_count": self.daily_count,
                "last_429": self.last_429_at,
            }
        except Exception as e:
            return {
                "status": self.status,
                "error": str(e)[:200],
                "daily_count": self.daily_count,
                "last_429": self.last_429_at,
            }

    def get_status(self) -> Dict:
        return {"status": self.status, "daily_count": self.daily_count, "last_429": self.last_429_at}

    def __repr__(self):
        return f"<SGOBase sport={self.sport} key=...{self.api_key[-6:]}>"