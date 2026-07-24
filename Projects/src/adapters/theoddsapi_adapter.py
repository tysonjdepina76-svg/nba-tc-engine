"""theoddsapi.com adapter — Free tier: NBA + MLB moneylines/spreads/totals."""
from __future__ import annotations
import os, json, time, logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("theoddsapi")

BASE_URL = "https://api.theoddsapi.com"
CACHE_DIR = Path("/home/workspace/Daily_Log/cache/theoddsapi")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 120  # 2-minute cache for live odds


def _load_key() -> str:
    env_file = Path("/root/.zo/secrets.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("THEODDSAPI_KEY="):
                return line.split("=", 1)[1].strip()
    return os.getenv("THEODDSAPI_KEY", "")


def _cache_path(sport_key: str) -> Path:
    return CACHE_DIR / f"{sport_key}_odds.json"


def _read_cache(sport_key: str) -> Optional[Dict]:
    p = _cache_path(sport_key)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_cache(sport_key: str, data: Dict) -> None:
    _cache_path(sport_key).write_text(json.dumps(data))


SPORT_KEY_MAP = {
    "mlb": "baseball_mlb",
    "wnba": "basketball_wnba",
    "nba": "basketball_nba",
    "nfl": "americanfootball_nfl",
}


def fetch_live_odds(sport: str, bookmakers: str = "draftkings,fanduel") -> Dict[str, Any]:
    """Fetch live odds for a sport. Returns {games: [...], fetched_at: ISO, sport: str}."""
    api_key = _load_key()
    if not api_key:
        return {"error": "no_api_key", "games": []}

    sport_key = SPORT_KEY_MAP.get(sport.lower(), sport.lower())

    cached = _read_cache(sport_key)
    if cached:
        return cached

    import urllib.request
    url = f"{BASE_URL}/odds/?sport_key={sport_key}&bookmakers={bookmakers}&regions=us"
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"TheOddsAPI fetch error for {sport}: {e}")
        return {"error": str(e), "games": []}

    if not raw.get("success") or not raw.get("data"):
        return {"error": "empty_response", "games": []}

    games = []
    for event in raw["data"]:
        game = {
            "event_id": event.get("event_id"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "start_time": event.get("start_time"),
            "books": {},
        }
        for book_data in event.get("books", []):
            book_key = book_data.get("book", "unknown")
            if book_key not in game["books"]:
                game["books"][book_key] = {}
            market = book_data.get("market", "unknown")
            game["books"][book_key][market] = book_data.get("outcomes", [])
        games.append(game)

    result = {
        "sport": sport,
        "sport_key": sport_key,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "game_count": len(games),
        "games": games,
    }
    _write_cache(sport_key, result)
    return result


def get_best_lines(sport: str, stat: str = "spreads") -> List[Dict]:
    """Extract best lines (DK vs FD comparison) per game."""
    data = fetch_live_odds(sport)
    if data.get("error"):
        return []

    comparisons = []
    for game in data.get("games", []):
        entry = {
            "event_id": game["event_id"],
            "home": game["home_team"],
            "away": game["away_team"],
            "start": game["start_time"],
            "dk": None,
            "fd": None,
        }
        for book_name, markets in game.get("books", {}).items():
            if stat in markets:
                outcomes = markets[stat]
                line_info = {
                    "book": book_name,
                    "outcomes": outcomes,
                }
                if book_name == "draftkings":
                    entry["dk"] = line_info
                elif book_name == "fanduel":
                    entry["fd"] = line_info
        comparisons.append(entry)

    return comparisons


def fetch_events(sport: str) -> List[Dict]:
    """Fetch upcoming events for a sport (schedules, no odds needed)."""
    api_key = _load_key()
    if not api_key:
        return []
    sport_key = SPORT_KEY_MAP.get(sport.lower(), sport.lower())
    import urllib.request
    url = f"{BASE_URL}/events/?sport_key={sport_key}"
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"TheOddsAPI events fetch error for {sport}: {e}")
        return []
    return raw.get("data", []) if raw.get("success") else []


def get_odds_comparison(sport: str, bookmakers: str = "draftkings,fanduel") -> Dict[str, Any]:
    """Fetch player props for a sport and return comparisons between bookmakers.
    
    Returns {"comparisons": [...], "timestamp": "..."} where each comparison has:
    - player: str
    - stat: str
    - draftkings: {"line": float, "edge": float}
    - fanduel: {"line": float, "edge": float}
    """
    api_key = _load_key()
    if not api_key:
        return {"comparisons": [], "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    sport_key = SPORT_KEY_MAP.get(sport.lower(), sport.lower())
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    import urllib.request
    props_url = f"{BASE_URL}/props/?sport_key={sport_key}&bookmakers={bookmakers}&regions=us"
    req = urllib.request.Request(props_url, headers={"x-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
    except Exception as e:
        if isinstance(e, urllib.error.HTTPError):
            if e.code in (401, 402, 403):
                return {"comparisons": [], "timestamp": timestamp}
        logger.error(f"TheOddsAPI props fetch error for {sport}: {e}")
        return {"comparisons": [], "timestamp": timestamp}

    if not raw.get("success") or not raw.get("data"):
        return {"comparisons": [], "timestamp": timestamp}

    comparisons = []
    for prop in raw["data"]:
        player = prop.get("player")
        stat = prop.get("stat")
        if not player or not stat:
            continue

        dk = None
        fd = None
        for book in ["draftkings", "fanduel"]:
            if book in prop.get("books", {}):
                book_data = prop["books"][book]
                if book_data.get("line") is not None:
                    if book == "draftkings":
                        dk = {"line": book_data["line"], "edge": book_data.get("edge", 0)}
                    elif book == "fanduel":
                        fd = {"line": book_data["line"], "edge": book_data.get("edge", 0)}

        if dk and fd:
            comparisons.append({
                "player": player,
                "stat": stat,
                "draftkings": dk,
                "fanduel": fd,
            })

    return {"comparisons": comparisons, "timestamp": timestamp}
