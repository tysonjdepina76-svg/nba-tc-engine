"""Unified line fetcher: DraftKings public API -> Odds API -> empty."""
import os
import requests
import json
from datetime import datetime
DK_SPORTS = {"mlb": "MLB", "wnba": "WNBA", "wc": "WORLD_CUP"}
ODDS_API_SPORTS = {"mlb": "baseball_mlb", "wnba": "basketball_wnba", "wc": "soccer_fifa_world_cup"}

def fetch_dk(sport):
    code = DK_SPORTS.get(sport)
    if not code: raise ValueError("No DK code for " + sport)
    url = "https://api.draftkings.com/scores/json/" + code
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.draftkings.com/"}
    r = requests.get(url, headers=headers, timeout=10); r.raise_for_status()
    games = []
    for event in r.json().get("events", []):
        comps = event.get("competitors", [])
        away = next((c.get("name", "") for c in comps if str(c.get("homeTeam", "")).lower() == "false"), "")
        home = next((c.get("name", "") for c in comps if str(c.get("homeTeam", "")).lower() == "true"), "")
        spread = moneyline = total = None
        for offer in event.get("offers", []):
            market = str(offer.get("marketType", "")).lower()
            outs = offer.get("outcomes", [])
            if not outs: continue
            if "spread" in market: spread = outs[0].get("point")
            elif "moneyline" in market: moneyline = outs[0].get("price")
            elif "total" in market: total = outs[0].get("point")
        games.append({"away": away, "home": home, "spread": spread, "moneyline": moneyline, "total": total})
    return {"source": "DraftKings", "games": games}

def fetch_odds_api(sport):
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key: raise ValueError("No ODDS_API_KEY")
    sport_path = ODDS_API_SPORTS.get(sport)
    if not sport_path: raise ValueError("No Odds API sport path for " + sport)
    url = "https://api.the-odds-api.com/v4/sports/" + sport_path + "/odds"
    params = {"apiKey": api_key, "regions": "us", "markets": "spreads,totals,h2h"}
    r = requests.get(url, params=params, timeout=10); r.raise_for_status()
    games = []
    for g in r.json():
        sp = next((o.get("point") for m in g.get("markets", []) if m.get("key") == "spreads" for o in m.get("outcomes", [])), None)
        tot = next((o.get("point") for m in g.get("markets", []) if m.get("key") == "totals" for o in m.get("outcomes", [])), None)
        ml = next((o.get("price") for m in g.get("markets", []) if m.get("key") == "h2h" for o in m.get("outcomes", []) if o.get("name") == g.get("home_team")), None)
        games.append({"away": g.get("away_team"), "home": g.get("home_team"), "spread": sp, "moneyline": ml, "total": tot})
    return {"source": "Odds API", "games": games}

def fetch_lines(sport):
    for fn in (fetch_dk, fetch_odds_api):
        try:
            result = fn(sport)
            if result.get("games"): return result
        except Exception as e:
            print("[" + sport + "] " + fn.__name__ + " failed: " + str(e))
    return {"source": "none", "games": [], "error": "All sources failed"}
