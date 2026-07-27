#!/usr/bin/env python3
"""SharpAPI Adapter — Pro Tier. 300 RPM, 15-book max, player props + game lines."""

import os
import json
import time
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests
from api_cap_tracker import consume_budget, track_error

logger = logging.getLogger("sharp_api")

API_KEY = os.environ.get("SharpAPI_KEY", "")
BASE_URL = "https://api.sharpapi.io/api/v1"
DATA_DIR = Path("/home/workspace/data")
DATA_DIR.mkdir(exist_ok=True)

USAGE_FILE = DATA_DIR / "sharpapi_usage.json"
CACHE_DIR = DATA_DIR / "sharp_cache"
CACHE_DIR.mkdir(exist_ok=True)

REQUEST_TIMEOUT = 10
RATE_LIMIT_RPM = 300
_LAST_REQUEST_TS = 0
_MIN_INTERVAL = 60 / RATE_LIMIT_RPM
DAILY_MAX = 250

# Default books: 5 sharp anchors + 11 majors/regionals (max 15 per request per SharpAPI)
DEFAULT_BOOKS = [
    "pinnacle", "circa", "betcris", "bookmaker", "betonline",
    "draftkings", "fanduel", "betmgm", "caesars", "hardrock",
    "espnbet", "bet365", "ballybet", "pointsbet", "betrivers",
    "ladbrokes",
]


def _get_headers() -> Dict[str, str]:
    return {
        "Accept": "application/json",
    }


def _rate_limit():
    global _LAST_REQUEST_TS
    elapsed = time.monotonic() - _LAST_REQUEST_TS
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_REQUEST_TS = time.monotonic()


def _cache_key(*parts) -> str:
    return hashlib.md5(":".join(parts).encode()).hexdigest()[:12]


def _load_usage() -> Dict:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"total_calls": 0, "today_date": "", "today_calls": 0, "last_response_ms": 0, "errors": 0}


def _save_usage(usage: Dict):
    USAGE_FILE.write_text(json.dumps(usage))


def _track_call(success: bool, response_ms: int):
    today = datetime.now().strftime("%Y-%m-%d")
    usage = _load_usage()
    if usage.get("today_date") != today:
        usage = {"total_calls": usage.get("total_calls", 0), "today_date": today, "today_calls": 0, "last_response_ms": 0, "errors": 0}
    usage["total_calls"] = usage.get("total_calls", 0) + 1
    usage["today_calls"] = usage.get("today_calls", 0) + 1
    usage["last_response_ms"] = response_ms
    if not success:
        usage["errors"] = usage.get("errors", 0) + 1
    _save_usage(usage)
    if not success:
        from api_cap_tracker import track_error as cap_track_error
        cap_track_error("SharpAPI")


def get_usage() -> Dict:
    return _load_usage()


def get_account() -> Dict:
    _rate_limit()
    if not consume_budget("SharpAPI"):
        logger.warning("SharpAPI daily budget exceeded")
        return {"error": "budget_exceeded", "message": "Daily cap reached — try again tomorrow"}
    t0 = time.monotonic()
    try:
        resp = requests.get(f"{BASE_URL}/account", headers=_get_headers(), params={"api_key": API_KEY}, timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json() if resp.ok else {"error": resp.status_code, "detail": resp.text}
    except requests.RequestException as e:
        _track_call(False, 0)
        return {"error": "connection", "detail": str(e)}


def get_account_usage() -> Dict:
    _rate_limit()
    if not consume_budget("SharpAPI"):
        return {"error": "daily budget exceeded"}
    if not consume_budget("SharpAPI"):
        logger.warning("SharpAPI daily budget exceeded")
        return {"error": "budget_exceeded", "message": "Daily cap reached — try again tomorrow"}
    t0 = time.monotonic()
    try:
        resp = requests.get(f"{BASE_URL}/account/usage", headers=_get_headers(), params={"api_key": API_KEY}, timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json() if resp.ok else {"error": resp.status_code, "detail": resp.text}
    except requests.RequestException as e:
        _track_call(False, 0)
        return {"error": "connection", "detail": str(e)}


def get_sports() -> List[Dict]:
    _rate_limit()
    if not consume_budget("SharpAPI"):
        return {"error": "daily budget exceeded"}
    if not consume_budget("SharpAPI"):
        logger.warning("SharpAPI daily budget exceeded")
        return {"error": "budget_exceeded", "message": "Daily cap reached — try again tomorrow"}
    t0 = time.monotonic()
    try:
        resp = requests.get(f"{BASE_URL}/sports", headers=_get_headers(), params={"api_key": API_KEY}, timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json().get("data", []) if resp.ok else []
    except requests.RequestException as e:
        _track_call(False, 0)
        logger.error(f"get_sports failed: {e}")
        return []


def get_events(
    sport: str,
    league: Optional[str] = None,
    status: str = "upcoming",
    limit: int = 50,
    books: Optional[List[str]] = None,
) -> List[Dict]:
    params: Dict[str, Any] = {"sport": sport, "status": status, "limit": limit, "api_key": API_KEY}
    if league:
        params["league"] = league
    if books:
        params["books"] = ",".join(books[:15])

    _rate_limit()
    if not consume_budget("SharpAPI"):
        return {"error": "daily budget exceeded"}
    if not consume_budget("SharpAPI"):
        logger.warning("SharpAPI daily budget exceeded for %s", sport)
        return {"error": "budget_exceeded"}
    t0 = time.monotonic()
    try:
        params["api_key"] = API_KEY
        resp = requests.get(f"{BASE_URL}/events", headers=_get_headers(), params=params, timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json().get("data", []) if resp.ok else []
    except requests.RequestException as e:
        _track_call(False, 0)
        logger.error(f"get_events({sport}) failed: {e}")
        return []


def get_event_odds(
    event_id: str,
    books: Optional[List[str]] = None,
    markets: Optional[List[str]] = None,
) -> List[Dict]:
    params: Dict[str, Any] = {"api_key": API_KEY}
    if books:
        params["books"] = ",".join(books[:15])
    if markets:
        params["markets"] = ",".join(markets)

    _rate_limit()
    if not consume_budget("SharpAPI"):
        return {"error": "daily budget exceeded"}
    if not consume_budget("SharpAPI"):
        logger.warning("SharpAPI daily budget exceeded for %s", event_id)
        return {"error": "budget_exceeded"}
    t0 = time.monotonic()
    try:
        params["api_key"] = API_KEY
        resp = requests.get(
            f"{BASE_URL}/events/{event_id}/odds",
            headers=_get_headers(),
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        result = resp.json()
        if not resp.ok:
            fw = result.get("filter_warning", {})
            logger.warning(f"Event {event_id} odds warning: {fw.get('code')} — {fw.get('message')}")
            return []
        return result.get("data", [])
    except requests.RequestException as e:
        _track_call(False, 0)
        logger.error(f"get_event_odds({event_id}) failed: {e}")
        return []


def get_player_props(
    sport: str,
    league: str,
    books: Optional[List[str]] = None,
    market_types: Optional[List[str]] = None,
    limit: int = 100,
) -> List[Dict]:
    preferred_books = books or DEFAULT_BOOKS
    params: Dict[str, Any] = {
        "sport": sport,
        "league": league,
        "status": "upcoming",
        "limit": min(limit, 100),
        "books": ",".join(preferred_books[:15]),
        "api_key": API_KEY,
    }
    if market_types:
        params["markets"] = ",".join(market_types)

    _rate_limit()
    if not consume_budget("SharpAPI"):
        return []
    if not consume_budget("SharpAPI"):
        logger.warning("SharpAPI daily budget exceeded for player props")
        return []
    t0 = time.monotonic()
    try:
        params["api_key"] = API_KEY
        resp = requests.get(
            f"{BASE_URL}/events/{sport}_{league}_props".replace("__", "_"),
            headers=_get_headers(),
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 404:
            events = get_events(sport=sport, league=league, limit=limit, books=preferred_books)
            all_odds = []
            for event in events:
                odds = get_event_odds(event["id"], books=preferred_books)
                all_odds.extend(odds)
            _track_call(True, int((time.monotonic() - t0) * 1000))
            return all_odds

        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json().get("data", []) if resp.ok else []
    except requests.RequestException as e:
        _track_call(False, 0)
        logger.error(f"get_player_props({sport}/{league}) failed: {e}")
        return []


def extract_player_props(odds_data: List[Dict]) -> List[Dict]:
    props = []
    for entry in odds_data:
        if entry.get("market_type", "").startswith("player_"):
            props.append({
                "player_name": entry.get("player_name", entry.get("selection", "")),
                "market": entry.get("market_type", ""),
                "sportsbook": entry.get("book", entry.get("sportsbook", "")),
                "line": entry.get("line", entry.get("point", 0)),
                "over_odds": entry.get("over_odds", entry.get("over_price", 0)),
                "under_odds": entry.get("under_odds", entry.get("under_price", 0)),
                "event_id": entry.get("event_id", ""),
                "updated_at": entry.get("updated_at", ""),
            })
    return props


def search_odds(
    sport: str,
    league: str,
    market: Optional[str] = None,
    book: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    params: Dict[str, Any] = {"sport": sport, "league": league, "limit": limit, "api_key": API_KEY}
    if market:
        params["market"] = market
    if book:
        params["book"] = book

    _rate_limit()
    if not consume_budget("SharpAPI"):
        return {"error": "daily budget exceeded"}
    if not consume_budget("SharpAPI"):
        logger.warning("SharpAPI daily budget exceeded for %s/%s", sport, league)
        return {"error": "budget_exceeded"}
    t0 = time.monotonic()
    try:
        params["api_key"] = API_KEY
        resp = requests.get(f"{BASE_URL}/odds", headers=_get_headers(), params=params, timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json().get("data", []) if resp.ok else []
    except requests.RequestException as e:
        _track_call(False, 0)
        logger.error(f"search_odds({sport}/{league}) failed: {e}")
        return []


def health_check() -> Dict:
    try:
        account = get_account()
        usage = get_account_usage()
        local = _load_usage()
        return {
            "status": "ok" if "error" not in account else "degraded",
            "tier": account.get("data", {}).get("tier", "unknown"),
            "key_id": account.get("data", {}).get("key_id", "unknown"),
            "rpm_limit": account.get("data", {}).get("rate_limit", {}).get("requests_per_minute", 0),
            "remaining_rpm": usage.get("data", {}).get("rate_limit", {}).get("remaining", 0),
            "requests_today": usage.get("data", {}).get("requests_today", 0),
            "local_calls_today": local.get("today_calls", 0),
            "local_errors": local.get("errors", 0),
            "last_response_ms": local.get("last_response_ms", 0),
            "features": account.get("data", {}).get("features", []),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


SHARP_SPORT_MAP = {
    "MLB": ("baseball", "mlb"),
    "WNBA": ("basketball", "wnba"),
    "NBA": ("basketball", "nba"),
    "NFL": ("americanfootball", "nfl"),
    "NHL": ("icehockey", "nhl"),
}

SHARP_MARKET_MAP = {
    "MLB": {
        "Hits": "batter_hits",
        "Strikeouts": "pitcher_strikeouts",
        "RBI": "batter_rbis",
        "TotalBases": "batter_total_bases",
        "HR": "batter_home_runs",
        "Runs": "batter_runs_scored",
    },
    "WNBA": {
        "Points": "player_points",
        "Rebounds": "player_rebounds",
        "Assists": "player_assists",
        "3PM": "player_threes",
    },
    "NBA": {
        "Points": "player_points",
        "Rebounds": "player_rebounds",
        "Assists": "player_assists",
        "3PM": "player_threes",
    },
    "NFL": {
        "PassYards": "player_pass_yds",
        "RushYards": "player_rush_yds",
        "RecYards": "player_reception_yds",
        "PassTDs": "player_pass_tds",
        "RushTDs": "player_rush_tds",
        "RecTDs": "player_reception_tds",
    },
    "NHL": {
        "ShotsOnGoal": "player_shots_on_goal",
        "Points": "player_points",
        "Saves": "player_total_saves",
    },
}


def fetch_lines_for_sport(sport: str, books: Optional[List[str]] = None) -> Dict[str, Dict]:
    if sport not in SHARP_SPORT_MAP:
        logger.warning(f"Sport {sport} not in SHARP_SPORT_MAP")
        return {}

    api_sport, api_league = SHARP_SPORT_MAP[sport]
    market_map = SHARP_MARKET_MAP.get(sport, {})
    preferred_books = books or DEFAULT_BOOKS

    events = get_events(sport=api_sport, league=api_league, limit=20, books=preferred_books)
    logger.info(f"SharpAPI: {len(events)} {sport} events found")

    lines_by_player: Dict[str, Dict] = {}

    for event in events:
        event_id = event["id"]
        odds = get_event_odds(event_id, books=preferred_books)

        for odd in odds:
            player_name = odd.get("player_name", odd.get("selection", ""))
            if not player_name:
                continue

            market_type = odd.get("market_type", "")
            tc_stat = None
            for tc_key, sharp_key in market_map.items():
                if sharp_key in market_type:
                    tc_stat = tc_key
                    break

            if not tc_stat:
                continue

            line_val = odd.get("line", odd.get("point", 0))
            over_price = odd.get("over_price", odd.get("over_odds", 0))
            under_price = odd.get("under_price", odd.get("under_odds", 0))
            book_name = odd.get("book", odd.get("sportsbook", ""))

            if player_name not in lines_by_player:
                lines_by_player[player_name] = {}

            if tc_stat not in lines_by_player[player_name]:
                lines_by_player[player_name][tc_stat] = {}

            lines_by_player[player_name][tc_stat][book_name] = {
                "line": line_val,
                "over": over_price,
                "under": under_price,
                "updated": odd.get("updated_at", ""),
            }

    logger.info(f"SharpAPI: {len(lines_by_player)} players with lines for {sport}")
    return lines_by_player



def _auth_param():
    return {'api_key': API_KEY}


def get_best_odds(sport, league, market=None, limit=50):
    params = {'sport': sport, 'league': league, 'limit': limit}
    if market:
        params['market'] = market
    params.update(_auth_param())
    _rate_limit()
    if not consume_budget('SharpAPI'):
        return {'error': 'budget_exceeded'}
    t0 = time.monotonic()
    try:
        resp = requests.get(f'{BASE_URL}/odds/best', params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json() if resp.ok else {'error': resp.status_code}
    except requests.RequestException as e:
        _track_call(False, 0)
        return {'error': 'connection', 'detail': str(e)}


def get_ev_opportunities(sport=None, league=None, min_edge=0.03, limit=50):
    params = {'min_edge': min_edge, 'limit': limit}
    if sport:
        params['sport'] = sport
    if league:
        params['league'] = league
    params.update(_auth_param())
    _rate_limit()
    if not consume_budget('SharpAPI'):
        return {'error': 'budget_exceeded'}
    t0 = time.monotonic()
    try:
        resp = requests.get(f'{BASE_URL}/opportunities/ev', params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json() if resp.ok else {'error': resp.status_code}
    except requests.RequestException as e:
        _track_call(False, 0)
        return {'error': 'connection', 'detail': str(e)}


def get_arbitrage_opportunities(sport=None, league=None, min_roi=0.01, limit=50):
    params = {'min_roi': min_roi, 'limit': limit}
    if sport:
        params['sport'] = sport
    if league:
        params['league'] = league
    params.update(_auth_param())
    _rate_limit()
    if not consume_budget('SharpAPI'):
        return {'error': 'budget_exceeded'}
    t0 = time.monotonic()
    try:
        resp = requests.get(f'{BASE_URL}/opportunities/arbitrage', params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json() if resp.ok else {'error': resp.status_code}
    except requests.RequestException as e:
        _track_call(False, 0)
        return {'error': 'connection', 'detail': str(e)}


def get_low_hold_opportunities(sport=None, league=None, limit=50):
    params = {'limit': limit}
    if sport:
        params['sport'] = sport
    if league:
        params['league'] = league
    params.update(_auth_param())
    _rate_limit()
    if not consume_budget('SharpAPI'):
        return {'error': 'budget_exceeded'}
    t0 = time.monotonic()
    try:
        resp = requests.get(f'{BASE_URL}/opportunities/low_hold', params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        _track_call(resp.ok, int((time.monotonic() - t0) * 1000))
        return resp.json() if resp.ok else {'error': resp.status_code}
    except requests.RequestException as e:
        _track_call(False, 0)
        return {'error': 'connection', 'detail': str(e)}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if not API_KEY:
        print("ERROR: SharpAPI_KEY not set in environment")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "health"

    if cmd == "health":
        print(json.dumps(health_check(), indent=2))
    elif cmd == "usage":
        print(json.dumps(get_usage(), indent=2))
    elif cmd == "account":
        print(json.dumps(get_account(), indent=2))
    elif cmd == "sports":
        sports = get_sports()
        print(json.dumps([{"id": s["id"], "name": s["name"], "events": s.get("event_count", 0)} for s in sports], indent=2))
    elif cmd == "lines":
        sport = sys.argv[2] if len(sys.argv) > 2 else "MLB"
        lines = fetch_lines_for_sport(sport)
        print(json.dumps({p: list(s.keys()) for p, s in list(lines.items())[:10]}, indent=2))
        print(f"Total players: {len(lines)}")
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: health usage account sports lines")
