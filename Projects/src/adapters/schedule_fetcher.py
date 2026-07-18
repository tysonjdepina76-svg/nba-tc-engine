import requests
from datetime import datetime

LEAGUE_MAP = {
    "mlb": "baseball/mlb",
    "wnba": "basketball/wnba",
    "wc": "soccer/usa.1",
}

def has_games_today(sport):
    league = LEAGUE_MAP.get(sport)
    if not league:
        return False
    url = f"https://site.api.espn.com/apis/site/v2/sports/{league}/scoreboard"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("events", [])
            return len(events) > 0
    except Exception:
        pass
    return False
