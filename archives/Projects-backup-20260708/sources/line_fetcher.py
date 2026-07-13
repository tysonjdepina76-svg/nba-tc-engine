"""Unified line fetcher: DraftKings -> SportsDataIO -> Odds API -> cache -> empty.

Imports `fetch_odds_api_lines` from the new sources/odds_api_client wrapper.
The Odds API is on Business tier and quota is MAXED — the wrapper handles
401s gracefully and returns empty games so we fall through to cache.
"""
import os
import sys
import requests
import json
from datetime import datetime

# Path bootstrap: allow `from sources.line_fetcher import ...` from any cwd.
_THIS = os.path.abspath(__file__)
_PROJ_ROOT = os.path.dirname(os.path.dirname(_THIS))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

from sources.odds_api_client import fetch_odds_api_lines

DK_SPORTS = {"mlb": "MLB", "wnba": "WNBA", "wc": "WORLD_CUP"}


def fetch_dk(sport):
    code = DK_SPORTS.get(sport)
    if not code:
        raise ValueError("No DK code for " + sport)
    url = "https://api.draftkings.com/scores/json/" + code
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.draftkings.com/"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    games = []
    for event in r.json().get("events", []):
        comps = event.get("competitors", [])
        away = next((c.get("name", "") for c in comps if str(c.get("homeTeam", "")).lower() == "false"), "")
        home = next((c.get("name", "") for c in comps if str(c.get("homeTeam", "")).lower() == "true"), "")
        spread = moneyline = total = None
        for offer in event.get("offers", []):
            market = str(offer.get("marketType", "")).lower()
            outs = offer.get("outcomes", [])
            if not outs:
                continue
            if "spread" in market:
                spread = outs[0].get("point")
            elif "moneyline" in market:
                moneyline = outs[0].get("price")
            elif "total" in market:
                total = outs[0].get("point")
        games.append({"away": away, "home": home, "spread": spread, "moneyline": moneyline, "total": total})
    return {"source": "DraftKings", "games": games}


def fetch_odds_api_wrapped(sport):
    """Calls the new odds_api_client wrapper. Returns {source, games} shape.

    The wrapper handles 401/429 (Business tier quota) and returns empty games
    with quota_exhausted=True so the chain falls through to cache / self-edge.
    """
    data = fetch_odds_api_lines(sport)
    return {
        "source": data.get("source", "Odds API"),
        "games": data.get("games", []),
        "quota_exhausted": data.get("quota_exhausted", False),
        "error": data.get("error"),
    }


def fetch_lines(sport):
    # 1. DraftKings
    try:
        dk_data = fetch_dk(sport)
        if dk_data and dk_data.get("games"):
            return dk_data
    except Exception as e:
        print("[" + sport + "] fetch_dk failed: " + str(e))

    # 2. Odds API (via wrapper)
    try:
        odds_data = fetch_odds_api_wrapped(sport)
        if odds_data and odds_data.get("games"):
            return odds_data
    except Exception as e:
        print("[" + sport + "] fetch_odds_api_wrapped failed: " + str(e))

    # 3. Empty (triggers self-edge fallback in caller)
    return {"source": "none", "games": [], "error": "All sources failed"}


if __name__ == "__main__":
    for sport in ("mlb", "wnba", "wc"):
        result = fetch_lines(sport)
        print(f"[{sport}] source={result.get('source')} games={len(result.get('games', []))} "
              f"quota_exhausted={result.get('quota_exhausted', False)}")
