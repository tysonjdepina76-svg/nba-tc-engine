"""ESPN adapter — cached + quota-guarded."""
import json
import urllib.request
from typing import Optional, Dict, Any
from .cache import APICache, ADAPTER_TTL, check_quota

_cache = APICache()
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"


def _http_get_json(url: str, timeout: int = 8) -> Optional[Dict[str, Any]]:
    check_quota("ESPN")
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def fetch_scoreboard(sport: str, ttl: int = None) -> Optional[Dict[str, Any]]:
    key = f"espn_scoreboard_{sport.replace('/', '_')}"
    ttl = ttl or ADAPTER_TTL["espn_scores"]
    cached = _cache.get(key, max_age=ttl)
    if cached is not None:
        return cached
    data = _http_get_json(f"{ESPN_BASE}/{sport}/scoreboard")
    if data is not None:
        _cache.set(key, data)
    return data


def fetch_summary(sport: str, event_id: str, ttl: int = None) -> Optional[Dict[str, Any]]:
    key = f"espn_summary_{sport.replace('/', '_')}_{event_id}"
    ttl = ttl or ADAPTER_TTL["espn_scores"]
    cached = _cache.get(key, max_age=ttl)
    if cached is not None:
        return cached
    data = _http_get_json(f"{ESPN_BASE}/{sport}/summary?event={event_id}")
    if data is not None:
        _cache.set(key, data)
    return data


def fetch_boxscore(sport: str, event_id: str, ttl: int = None) -> Optional[Dict[str, Any]]:
    """Alias for fetch_summary — many legacy callers use this name."""
    return fetch_summary(sport, event_id, ttl=ttl)


def fetch_roster(team_id: str, sport: str = "basketball/nba", ttl: int = None) -> Optional[Dict[str, Any]]:
    key = f"espn_roster_{sport.replace('/', '_')}_{team_id}"
    ttl = ttl or ADAPTER_TTL["espn_rosters"]
    cached = _cache.get(key, max_age=ttl)
    if cached is not None:
        return cached
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/teams/{team_id}/roster"
    data = _http_get_json(url)
    if data is not None:
        _cache.set(key, data)
    return data