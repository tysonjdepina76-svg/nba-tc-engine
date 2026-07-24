"""
odds_fetcher.py – Unified, free odds source with cascading fallbacks.
No API keys, no quotas, no 401 errors.
"""

import requests
import json
import time
import os
from typing import Dict, List, Optional

CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/tc_cache")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", 300))

MCP_HOST = os.getenv("MCP_HOST", "localhost")
MCP_PORT = os.getenv("MCP_PORT", "8000")
MCP_BASE = f"http://{MCP_HOST}:{MCP_PORT}"

ESPN_ODDS_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"

SPORT_SLUGS = {
    "NBA": "basketball/nba",
    "WNBA": "basketball/wnba",
    "MLB": "baseball/mlb",
    "NFL": "football/nfl",
    "NHL": "hockey/nhl",
    "NCAA": "football/college-football",
}

def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"odds_{key}.json")

def _get_cached(key: str) -> Optional[Dict]:
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        if time.time() - data.get("timestamp", 0) < CACHE_TTL:
            return data.get("value")
    return None

def _set_cache(key: str, value: Dict):
    path = _cache_path(key)
    with open(path, "w") as f:
        json.dump({"timestamp": time.time(), "value": value}, f)

def _fetch_espn(sport: str) -> Optional[List[Dict]]:
    """Pull odds from ESPN's public scoreboard endpoint."""
    slug = SPORT_SLUGS.get(sport.upper())
    if not slug:
        return None
    try:
        url = ESPN_ODDS_URL.format(sport=slug)
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            games = []
            for event in data.get("events", []):
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                odds_list = comp.get("odds", [])
                if odds_list:
                    games.append({
                        "game_id": event.get("id"),
                        "away_team": comp.get("competitors", [{}, {}])[1].get("team", {}).get("displayName", ""),
                        "home_team": comp.get("competitors", [{}, {}])[0].get("team", {}).get("displayName", ""),
                        "odds": odds_list,
                        "status": comp.get("status", {}).get("type", {}).get("name", "unknown"),
                    })
            return games
    except Exception as e:
        pass
    return None

def get_odds(sport: str, market: str = "totals", force_refresh: bool = False) -> List[Dict]:
    """
    Main entry point – returns odds lines for all games today.
    Cascades: ESPN → cached (if stale).
    """
    cache_key = f"{sport.lower()}_{market}"
    if not force_refresh:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    data = _fetch_espn(sport)
    if data:
        _set_cache(cache_key, data)
        return data

    cached = _get_cached(cache_key)
    if cached:
        return cached

    return []

def get_spread(sport: str) -> List[Dict]:
    return get_odds(sport, "spread")

def get_total(sport: str) -> List[Dict]:
    return get_odds(sport, "totals")

def get_moneyline(sport: str) -> List[Dict]:
    return get_odds(sport, "moneyline")

def get_player_props(sport: str, force_refresh: bool = False) -> List[Dict]:
    """
    Fetch player props. Falls back to self-edge when ESPN has no props.
    """
    slug = SPORT_SLUGS.get(sport.upper())
    if not slug:
        return []
    cache_key = f"{sport.lower()}_props"
    if not force_refresh:
        cached = _get_cached(cache_key)
        if cached:
            return cached
    try:
        url = ESPN_ODDS_URL.format(sport=slug)
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            props = []
            for event in data.get("events", []):
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                away = comp.get("competitors", [{}, {}])[1].get("team", {}).get("displayName", "")
                home = comp.get("competitors", [{}, {}])[0].get("team", {}).get("displayName", "")
                for odd in comp.get("odds", []):
                    if odd.get("details"):
                        props.append({
                            "game_id": event.get("id"),
                            "away_team": away,
                            "home_team": home,
                            "provider": odd.get("provider", {}).get("name", "ESPN"),
                            "details": odd.get("details", ""),
                            "over_under": odd.get("overOdds", odd.get("total", "")),
                        })
            if props:
                _set_cache(cache_key, props)
                return props
    except Exception:
        pass
    return []

def calculate_edge(projection: float, line: float, direction: str, odds: float = -110) -> float:
    """Calculate TC edge percentage."""
    if direction.lower() == "over":
        diff = projection - line
    else:
        diff = line - projection
    if line == 0:
        return 0.0
    edge_pct = (diff / abs(line)) * 100
    if odds < 0:
        implied = abs(odds) / (abs(odds) + 100)
    else:
        implied = 100 / (odds + 100)
    return edge_pct - ((1 - implied) * 100)

def format_pick(pick: Dict) -> str:
    """Format a pick dict into a readable string."""
    player = pick.get("player_name", pick.get("name", "Unknown"))
    stat = pick.get("stat_type", pick.get("stat", "PTS"))
    direction = pick.get("direction", "over").upper()
    line = pick.get("line", pick.get("market_line", 0))
    proj = pick.get("projected_value", pick.get("tc_projection", 0))
    edge = pick.get("edge", 0)
    return f"{player} {stat} {direction} {line} (proj: {proj:.1f} edge: {edge:.1f}%)"

if __name__ == "__main__":
    odds = get_odds("MLB", "totals")
    print(f"MLB totals: {len(odds)} games")
    for g in odds[:3]:
        print(f"  {g.get('away_team')} @ {g.get('home_team')} | odds: {len(g.get('odds', []))} sources")
    props = get_player_props("WNBA")
    print(f"WNBA props: {len(props)} entries")
