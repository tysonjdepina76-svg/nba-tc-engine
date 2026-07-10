"""TheOddsAPI Base Adapter — Shared client for all sports."""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class OddsAPIBase:
    """Base client for TheOddsAPI. Uses root paths + sport_key query param (v4 deprecated)."""

    BASE_URL = "https://api.theoddsapi.com"

    SPORT_KEYS = {
        "wnba": "basketball_wnba",
        "nfl": "americanfootball_nfl",
        "mlb": "baseball_mlb",
        "nba": "basketball_nba",
        "nhl": "icehockey_nhl",
    }

    def __init__(self, sport: str, api_key: Optional[str] = None):
        self.sport = sport
        self.sport_key = self.SPORT_KEYS.get(sport, sport)
        self.api_key = api_key or os.environ.get("THEODDSAPI") or os.environ.get("THE_ODDS_API_KEY")
        if not self.api_key:
            raise ValueError("THEODDSAPI (or THE_ODDS_API_KEY) not set")

        self.cache_dir = Path("/tmp/oddsapi_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = 300

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
            cached_time = datetime.fromisoformat(data["timestamp"])
            if (datetime.now() - cached_time).seconds > self.cache_ttl:
                return None
            return data["value"]
        except Exception:
            return None

    def _set_cached(self, key: str, value: Any):
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "value": value
        }))

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}
        params["apiKey"] = self.api_key

        cache_key = self._get_cache_key(endpoint, params)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        response = requests.get(url, params=params, timeout=30, allow_redirects=True)
        response.raise_for_status()
        data = response.json()
        self._set_cached(cache_key, data)
        return data

    def fetch_odds(self, markets: str = "h2h,spreads,totals", regions: str = "us") -> List[Dict]:
        return self._request("/odds/", {
            "sport_key": self.sport_key,
            "markets": markets,
            "regions": regions,
        })

    def fetch_events(self) -> List[Dict]:
        return self._request("/events/", {"sport_key": self.sport_key})

    def fetch_event_odds(self, event_id: str, markets: str = "player_points,player_rebounds,player_assists,player_threes") -> List[Dict]:
        return self._request(f"/events/{event_id}/odds", {
            "sport_key": self.sport_key,
            "markets": markets,
            "regions": "us",
        })

    def fetch_player_props(self, event_id: str = None) -> List[Dict]:
        markets = "player_points,player_rebounds,player_assists,player_threes"
        if not event_id:
            raise ValueError("fetch_player_props requires event_id (per-event player props only)")
        return self.fetch_event_odds(event_id, markets)

    def fetch_event_props(self, event_id: str) -> List[Dict]:
        return self._request(f"/events/{event_id}/props", {"sport_key": self.sport_key})

    def fetch_period_markets(self, event_id: str) -> List[Dict]:
        return self._request(f"/events/{event_id}/period-markets", {"sport_key": self.sport_key})

    def fetch_futures(self) -> List[Dict]:
        return self._request("/futures/", {"sport_key": self.sport_key})

    def fetch_historical_odds(self, date: str) -> List[Dict]:
        return self._request("/historical/odds/", {"sport_key": self.sport_key, "date": date})

    def get_remaining_credits(self) -> Dict:
        url = f"{self.BASE_URL}/odds/?sport_key={self.sport_key}&apiKey={self.api_key}"
        resp = requests.get(url, timeout=15)
        return {
            "remaining": resp.headers.get("x-requests-remaining"),
            "used": resp.headers.get("x-requests-used"),
        }


class OddsAPIMonitor:
    """Monitor OddsAPI key health, quota, and 401/410 events."""

    ALERT_THRESHOLD = 100

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("THEODDSAPI") or os.environ.get("THE_ODDS_API_KEY")
        self.daily_count = 0
        self.last_remaining = None
        self.last_used = None
        self.last_401_at = None
        self.last_410_at = None
        self.status = "unknown"

    def check_health(self) -> Dict:
        """Ping /sports/ endpoint and return quota + health status."""
        url = f"{OddsAPIBase.BASE_URL}/sports/?apiKey={self.api_key}"
        try:
            resp = requests.get(url, timeout=15)
            self.record_response(resp.headers, resp.status_code)
            return {
                "status": self.status,
                "remaining": self.last_remaining,
                "used": self.last_used,
                "daily_count": self.daily_count,
                "last_401": self.last_401_at,
                "last_410": self.last_410_at,
                "http_code": resp.status_code,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def record_response(self, headers: Dict, status_code: int):
        self.daily_count += 1
        if "x-requests-remaining" in headers:
            self.last_remaining = headers["x-requests-remaining"]
        if "x-requests-used" in headers:
            self.last_used = headers["x-requests-used"]
        if status_code == 401:
            self.last_401_at = datetime.now().isoformat()
            self.status = "auth_failed"
        elif status_code == 410:
            self.last_410_at = datetime.now().isoformat()
            self.status = "gone"
        elif status_code == 429:
            self.status = "rate_limited"
        else:
            self.status = "healthy"

    def get_status(self) -> Dict:
        alert = False
        try:
            if self.last_remaining is not None and int(self.last_remaining) < self.ALERT_THRESHOLD:
                alert = True
        except (ValueError, TypeError):
            pass
        return {
            "status": self.status,
            "remaining": self.last_remaining,
            "used": self.last_used,
            "daily_count": self.daily_count,
            "alert_low_quota": alert,
        }


class SGOMonitor:
    """Monitor SportsGameOdds (SGO) v2 key health, quota, and 401/429 events.

    SGO uses sport-specific endpoints under /v2/sports/{sport}/events.
    Sport IDs: BASKETBALL_NBA=4, BASKETBALL_NCAAB=3, BASKETBALL_WNBA=10,
                BASEBALL_MLB=1, ICE_HOCKEY_NHL=6, AMERICANFOOTBALL_NFL=2,
                SOCCER_EPL=19, SOCCER_WORLD_CUP=NULL (varies).
    """

    BASE_URL = "https://api.sportsgameodds.com/v2"
    SPORT_PATHS = {
        "NBA": "basketball_nba",
        "WNBA": "basketball_wnba",
        "MLB": "baseball_mlb",
        "NHL": "icehockey_nhl",
        "NFL": "americanfootball_nfl",
        "WORLD_CUP": "soccer_fifa_world_cup",
    }
    ALERT_THRESHOLD = 50

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SGO_API_KEY")
        self.daily_count = 0
        self.last_remaining = None
        self.last_used = None
        self.last_401_at = None
        self.last_429_at = None
        self.status = "unknown"
        self.last_error = None

    def check_health(self, sport: str = "MLB") -> Dict:
        """Ping /v2/sports/{sport}/events and return quota + health status."""
        sport_path = self.SPORT_PATHS.get(sport.upper(), sport.lower())
        url = f"{self.BASE_URL}/sports/{sport_path}/events"
        headers = {"X-Api-Key": self.api_key} if self.api_key else {}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            self.record_response(resp.headers, resp.status_code)
            return {
                "status": self.status,
                "sport_tested": sport,
                "remaining": self.last_remaining,
                "used": self.last_used,
                "daily_count": self.daily_count,
                "last_401": self.last_401_at,
                "last_429": self.last_429_at,
                "http_code": resp.status_code,
            }
        except Exception as e:
            self.last_error = str(e)
            return {"status": "error", "error": str(e), "sport_tested": sport}

    def record_response(self, headers: Dict, status_code: int):
        self.daily_count += 1
        if "x-ratelimit-remaining" in headers:
            self.last_remaining = headers["x-ratelimit-remaining"]
        if "x-ratelimit-used" in headers:
            self.last_used = headers["x-ratelimit-used"]
        if status_code == 401:
            self.last_401_at = datetime.now().isoformat()
            self.status = "auth_failed"
        elif status_code == 429:
            self.last_429_at = datetime.now().isoformat()
            self.status = "rate_limited"
        elif status_code == 200:
            self.status = "healthy"
        else:
            self.status = f"http_{status_code}"

    def get_status(self) -> Dict:
        alert = False
        try:
            if self.last_remaining is not None and int(self.last_remaining) < self.ALERT_THRESHOLD:
                alert = True
        except (ValueError, TypeError):
            pass
        return {
            "status": self.status,
            "remaining": self.last_remaining,
            "used": self.last_used,
            "daily_count": self.daily_count,
            "last_401": self.last_401_at,
            "last_429": self.last_429_at,
            "alert_low_quota": alert,
        }
