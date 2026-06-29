"""SGO adapter — cached + quota-guarded."""
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Dict, Any, List
from .cache import APICache, ADAPTER_TTL, check_quota

_cache = APICache()
SGO_BASE = "https://api.sportsgameodds.com/v2"
SGO_API_KEY = os.environ.get("SGO_API_KEY", "")


def _http_get_json(url: str, params: dict, headers: dict = None, timeout: int = 15) -> Optional[Dict[str, Any]]:
    check_quota("SGO")
    q = urllib.parse.urlencode(params)
    full = f"{url}?{q}"
    req = urllib.request.Request(full, headers=headers or {"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def fetch_events(sport_key: str, ttl: int = None) -> List[dict]:
    key = f"sgo_events_{sport_key}"
    ttl = ttl or ADAPTER_TTL["sgo_lines"]
    cached = _cache.get(key, max_age=ttl)
    if cached is not None:
        return cached
    headers = {"X-Api-Key": SGO_API_KEY, "Accept": "application/json"}
    data = _http_get_json(
        f"{SGO_BASE}/events",
        params={"leagueID": sport_key, "oddsAvailable": "true", "limit": 100},
        headers=headers,
    )
    events = (data or {}).get("data", [])
    _cache.set(key, events)
    return events