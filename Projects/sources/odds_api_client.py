"""The Odds API client — wrapped fetch_odds_api_lines(sport) for the line_fetcher.

Quota note: ODDS_API_KEY is on Business tier and quota is MAXED.
The /events/ endpoint still works, but /odds/ and /props/ return 401.
This wrapper handles the 401 gracefully and returns empty games so the
line_fetcher chain falls through to cache → self-edge.
"""
import os
import sys
import requests
from typing import Optional, Dict, List

# Path bootstrap: allow `from sources.odds_api_client import ...` from any cwd.
_THIS = os.path.abspath(__file__)
_PROJ_ROOT = os.path.dirname(os.path.dirname(_THIS))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Sport key mapping for The Odds API
SPORT_KEYS = {
    "mlb": "baseball_mlb",
    "wnba": "basketball_wnba",
    "wc": "soccer_fifa_world_cup",
    "soccer": "soccer_fifa_world_cup",
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
}

# Markets we care about
DEFAULT_MARKETS = "h2h,spreads,totals"


def _get_api_key() -> Optional[str]:
    """Read ODDS_API_KEY from env. Returns None if not set."""
    return os.getenv("ODDS_API_KEY")


def _normalize_game(game: Dict, sport: str) -> Dict:
    """Convert an Odds API game object to the line_fetcher standard shape."""
    bookmakers = game.get("bookmakers", [])
    spread = None
    moneyline = None
    total = None

    # Prefer DraftKings, fall back to first available bookmaker
    dk = next((b for b in bookmakers if b.get("key") == "draftkings"), None)
    primary = dk or (bookmakers[0] if bookmakers else None)

    if primary:
        for market in primary.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])
            if key == "spreads":
                # outcomes: [away, home] with point
                if len(outcomes) >= 2:
                    spread = {
                        "away": outcomes[0].get("point"),
                        "home": outcomes[1].get("point"),
                    }
            elif key == "h2h":
                if len(outcomes) >= 2:
                    moneyline = {
                        "away": outcomes[0].get("price"),
                        "home": outcomes[1].get("price"),
                    }
            elif key == "totals":
                if len(outcomes) >= 2:
                    over = next((o for o in outcomes if o.get("name") == "Over"), None)
                    under = next((o for o in outcomes if o.get("name") == "Under"), None)
                    total = {
                        "point": over.get("point") if over else (under.get("point") if under else None),
                        "over": over.get("price") if over else None,
                        "under": under.get("price") if under else None,
                    }

    return {
        "id": game.get("id"),
        "sport": sport,
        "commence_time": game.get("commence_time"),
        "away": game.get("away_team"),
        "home": game.get("home_team"),
        "spread": spread,
        "moneyline": moneyline,
        "total": total,
        "book": primary.get("title") if primary else None,
    }


def fetch_odds_api_lines(
    sport: str,
    markets: str = DEFAULT_MARKETS,
    bookmakers: str = "draftkings",
    regions: str = "us",
) -> Dict:
    """Fetch odds lines from The Odds API for the given sport.

    Returns:
        dict with shape {"source": "Odds API", "games": [...], "quota_exhausted": bool}

    On 401 (quota exhausted) or any error, returns:
        {"source": "Odds API", "games": [], "quota_exhausted": True, "error": str}
    """
    sport_key = SPORT_KEYS.get(sport.lower() if sport else "")
    if not sport_key:
        return {
            "source": "Odds API",
            "games": [],
            "quota_exhausted": False,
            "error": f"Unknown sport: {sport}",
        }

    api_key = _get_api_key()
    if not api_key:
        return {
            "source": "Odds API",
            "games": [],
            "quota_exhausted": False,
            "error": "ODDS_API_KEY not set",
        }

    url = (
        f"{ODDS_API_BASE}/sports/{sport_key}/odds/"
        f"?apiKey={api_key}&regions={regions}&markets={markets}"
        f"&bookmakers={bookmakers}&oddsFormat=american&dateFormat=iso"
    )

    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException as e:
        return {
            "source": "Odds API",
            "games": [],
            "quota_exhausted": False,
            "error": f"Network error: {e}",
        }

    # 401 = Business tier quota exhausted. Expected behavior — not a bug.
    if resp.status_code == 401:
        return {
            "source": "Odds API",
            "games": [],
            "quota_exhausted": True,
            "error": "401 Unauthorized — quota exhausted (Business tier)",
        }

    if resp.status_code == 429:
        return {
            "source": "Odds API",
            "games": [],
            "quota_exhausted": True,
            "error": "429 Rate limited",
        }

    if resp.status_code != 200:
        return {
            "source": "Odds API",
            "games": [],
            "quota_exhausted": False,
            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
        }

    try:
        raw_games = resp.json()
    except ValueError as e:
        return {
            "source": "Odds API",
            "games": [],
            "quota_exhausted": False,
            "error": f"Invalid JSON: {e}",
        }

    games: List[Dict] = []
    for g in raw_games:
        games.append(_normalize_game(g, sport))

    return {
        "source": "Odds API",
        "games": games,
        "quota_exhausted": False,
        "error": None,
    }


def fetch_events(sport: str) -> Dict:
    """Fetch just the events list (lighter call, doesn't burn odds quota)."""
    sport_key = SPORT_KEYS.get(sport.lower() if sport else "")
    if not sport_key:
        return {"source": "Odds API", "events": [], "error": f"Unknown sport: {sport}"}

    api_key = _get_api_key()
    if not api_key:
        return {"source": "Odds API", "events": [], "error": "ODDS_API_KEY not set"}

    url = f"{ODDS_API_BASE}/sports/{sport_key}/events/?apiKey={api_key}&dateFormat=iso"
    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException as e:
        return {"source": "Odds API", "events": [], "error": f"Network error: {e}"}

    if resp.status_code != 200:
        return {
            "source": "Odds API",
            "events": [],
            "error": f"HTTP {resp.status_code}",
        }

    try:
        events = resp.json()
    except ValueError as e:
        return {"source": "Odds API", "events": [], "error": f"Invalid JSON: {e}"}

    return {
        "source": "Odds API",
        "events": [
            {
                "id": e.get("id"),
                "sport": sport,
                "commence_time": e.get("commence_time"),
                "away": e.get("away_team"),
                "home": e.get("home_team"),
            }
            for e in events
        ],
        "error": None,
    }


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "mlb"
    data = fetch_odds_api_lines(sport)
    print(f"Source: {data.get('source')}")
    print(f"Games: {len(data.get('games', []))}")
    print(f"Quota exhausted: {data.get('quota_exhausted')}")
    if data.get("error"):
        print(f"Error: {data['error']}")
    if data.get("games"):
        print(f"First game: {data['games'][0]}")
