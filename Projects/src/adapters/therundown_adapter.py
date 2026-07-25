"""
TheRundown API v2 adapter — Free tier: 20k data points/day, 1 req/sec.
Sports: WNBA(8), MLB(3), NBA(4), NFL(2), NCAAF(1), NCAAB(5), NHL(6).
Markets: moneyline(1), handicap(2), totals(3).
Player props require Starter tier ($49/mo) — NOT available on free.

API key: get at https://therundown.io/api → store as THERUNDOWN_API_KEY env var.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api_cap_tracker import cap_check as _cap_check

logger = logging.getLogger("therundown")

BASE_URL = "https://therundown.io/api/v2"
API_KEY = os.environ.get("THERUNDOWN_API_KEY", "")
DEFAULT_MARKETS = "1,2,3"
DEFAULT_AFFILIATES = "19,23,22"  # DraftKings, FanDuel, BetMGM
SPORT_IDS = {"mlb": 3, "wnba": 8, "nba": 4, "nfl": 2, "ncaaf": 1, "ncaab": 5, "nhl": 6}
SPORT_NAMES = {v: k.upper() for k, v in SPORT_IDS.items()}
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "therundown"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _api_key_warning() -> bool:
    if not API_KEY:
        logger.warning("THERUNDOWN_API_KEY not set — get free key at https://therundown.io/api")
        return False
    return True


def _get(url: str, params: Dict = None, cache_ttl: int = 0, cache_key: str = "") -> Optional[Dict]:
    if not API_KEY:
        return None
    if not _api_key_warning():
        return None
    if not _cap_check("therundown"):
        return {}

    if cache_ttl > 0 and cache_key:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < cache_ttl:
                with open(cache_file) as f:
                    return json.load(f)

    full_url = f"{BASE_URL}{url}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        full_url += f"?{qs}"

    try:
        req = urllib.request.Request(full_url)
        req.add_header("X-TheRundown-Key", API_KEY)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "TC-Pipeline/1.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        if cache_ttl > 0 and cache_key:
            cache_file = CACHE_DIR / f"{cache_key}.json"
            with open(cache_file, "w") as f:
                json.dump(data, f)
        return data

    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300] if e.fp else ""
        logger.error(f"HTTP {e.code} from {full_url}: {body}")
        if e.code == 429 and "Daily data point limit reached" in body:
            logger.critical("DAILY DATA POINT CAP REACHED — waiting for reset")
        return None
    except Exception as e:
        logger.error(f"Request failed for {full_url}: {e}")
        return None


def get_sports() -> List[Dict]:
    """List all available sports (no auth required)."""
    return _get("/sports", cache_ttl=86400, cache_key="sports")


def get_today_events(sport: str, market_ids: str = DEFAULT_MARKETS,
                     affiliate_ids: str = DEFAULT_AFFILIATES,
                     date_str: str = None) -> Optional[Dict]:
    """Get today's events with markets for a sport."""
    sport_id = SPORT_IDS.get(sport.lower())
    if not sport_id:
        logger.error(f"Unknown sport: {sport}. Valid: {list(SPORT_IDS.keys())}")
        return None

    if date_str is None:
        date_str = date.today().isoformat()

    params = {
        "market_ids": market_ids,
        "affiliate_ids": affiliate_ids,
        "main_line": "true",
        "offset": "300",  # Eastern Time
    }

    cache_key = f"events_{sport}_{date_str}"
    return _get(f"/sports/{sport_id}/events/{date_str}", params,
                cache_ttl=120, cache_key=cache_key)


def get_event_details(event_id: str) -> Optional[Dict]:
    """Get a single event with all markets."""
    cache_key = f"event_{event_id}"
    return _get(f"/events/{event_id}", cache_ttl=60, cache_key=cache_key)


def get_markets_delta(sport: str, last_id: int = 0) -> Optional[Dict]:
    """Efficient delta polling — only changed markets since last_id."""
    sport_id = SPORT_IDS.get(sport.lower())
    if not sport_id:
        return None

    params = {
        "sport_id": sport_id,
        "market_ids": DEFAULT_MARKETS,
        "last_id": last_id,
    }
    return _get("/markets/delta", params)


def parse_event_odds(event: Dict) -> Dict:
    """Extract clean odds from a TheRundown event into our standard format."""
    teams = event.get("teams", [])
    away_team = next((t for t in teams if t.get("is_away")), {})
    home_team = next((t for t in teams if t.get("is_home")), {})

    result = {
        "event_id": event.get("event_id"),
        "event_date": event.get("event_date"),
        "away": away_team.get("abbreviation", away_team.get("name", "")),
        "home": home_team.get("abbreviation", home_team.get("name", "")),
        "away_full": f"{away_team.get('name', '')} {away_team.get('mascot', '')}".strip(),
        "home_full": f"{home_team.get('name', '')} {home_team.get('mascot', '')}".strip(),
        "sport_id": event.get("sport_id"),
        "score": event.get("score", {}),
        "moneyline": {},
        "spread": {},
        "totals": {},
    }

    for market in event.get("markets", []):
        name = market.get("name", "")
        for participant in market.get("participants", []):
            pname = participant.get("name", "")
            ptype = participant.get("type", "")

            for line_data in participant.get("lines", []):
                value = line_data.get("value", "")
                prices = line_data.get("prices", {})

                for aff_id, price_data in prices.items():
                    book_name = _affiliate_name(aff_id)
                    price = price_data.get("price", None)
                    if price is None:
                        continue

                    if name == "moneyline":
                        result["moneyline"].setdefault(pname, {})[book_name] = price
                    elif name == "handicap" and ptype == "TYPE_TEAM":
                        result["spread"].setdefault(pname, {})[book_name] = {
                            "line": float(value), "price": price
                        }
                    elif name == "totals":
                        key = "over" if "over" in pname.lower() else "under"
                        result["totals"].setdefault(key, {})[book_name] = {
                            "line": float(value), "price": price
                        }

    return result


def parse_all_events(events: List[Dict]) -> List[Dict]:
    """Parse a list of events into clean odds format."""
    return [parse_event_odds(e) for e in events]


def _affiliate_name(aff_id: str | int) -> str:
    """Map known affiliate IDs to short names."""
    names = {
        "19": "DK", "23": "FD", "22": "MGM", "1": "Pinnacle",
        "2": "5Dimes", "3": "Bookmaker", "6": "BetOnline",
        "24": "ESPNBet", "25": "Kalshi", "26": "BetRivers",
    }
    return names.get(str(aff_id), f"BOOK_{aff_id}")


def get_formatted_odds(sport: str, date_str: str = None) -> Dict:
    """Main entry point — get formatted odds for a sport."""
    data = get_today_events(sport, date_str=date_str)
    if not data:
        return {"error": "No data", "sport": sport, "events": []}

    parsed = parse_all_events(data.get("events", []))
    return {
        "sport": sport,
        "sport_id": SPORT_IDS.get(sport.lower()),
        "date": date_str or date.today().isoformat(),
        "event_count": len(parsed),
        "events": parsed,
        "timestamp": datetime.now().isoformat(),
        "source": "therundown.io",
    }


if __name__ == "__main__":
    if not API_KEY:
        print("Set THERUNDOWN_API_KEY env var for live data")
        print("Adapter ready — call get_formatted_odds('mlb') or get_formatted_odds('wnba')")
        sys.exit(0)
    print(json.dumps(get_formatted_odds("mlb"), indent=2, default=str))
