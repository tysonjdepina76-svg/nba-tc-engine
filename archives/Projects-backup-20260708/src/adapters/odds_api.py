"""OddsAPI adapter — cached + quota-guarded."""
import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List
from .cache import APICache, ADAPTER_TTL, check_quota

_cache = APICache()
ODDS_BASE = "https://api.the-odds-api.com/v4"
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")


def _http_get_json(url: str, params: dict, headers: dict = None, timeout: int = 15) -> Optional[Any]:
    check_quota("OddsAPI")
    q = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
    full = f"{url}?{q}"
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(full, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def fetch_event_odds(sport_path: str, event_id: str, markets: str = "player_points_rebounds_assists,player_points_rebounds,player_points_assists", ttl: int = None) -> Optional[Dict[str, Any]]:
    key = f"odds_event_{sport_path.replace('/', '_')}_{event_id}"
    ttl = ttl or ADAPTER_TTL["odds_lines"]
    cached = _cache.get(key, max_age=ttl)
    if cached is not None:
        return cached
    data = _http_get_json(
        f"{ODDS_BASE}/sports/{sport_path}/events/{event_id}/odds",
        params={
            "regions": "us",
            "markets": markets,
            "oddsFormat": "american",
            "bookmakers": "draftkings",
            "apiKey": ODDS_API_KEY,
        },
    )
    if data is not None:
        _cache.set(key, data)
    return data


def fetch_events_list(sport_path: str, ttl: int = None) -> List[dict]:
    key = f"odds_list_{sport_path.replace('/', '_')}"
    ttl = ttl or ADAPTER_TTL["odds_lines"]
    cached = _cache.get(key, max_age=ttl)
    if cached is not None:
        return cached
    data = _http_get_json(
        f"{ODDS_BASE}/sports/{sport_path}/events",
        params={"apiKey": ODDS_API_KEY},
    )
    events = data or []
    _cache.set(key, events)
    return events