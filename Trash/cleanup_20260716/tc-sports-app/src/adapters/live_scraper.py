import requests
import json
import os
from datetime import datetime

CACHE_DIR = "data/cache/live"
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_live_games(sport):
    league_map = {
        "mlb": "baseball/mlb",
        "wnba": "basketball/wnba",
        "soccer": "soccer/usa.1"
    }
    if sport not in league_map:
        return []
    url = f"https://site.api.espn.com/apis/site/v2/sports/{league_map[sport]}/scoreboard"
    headers = {"User-Agent": "Mozilla/5.0"}
    cache_file = os.path.join(CACHE_DIR, f"{sport}_live.json")
    try:
        if os.path.exists(cache_file):
            age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if age < 60:
                with open(cache_file) as f:
                    cached = json.load(f)
                return cached.get("games", [])
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        games = []
        for event in data.get("events", []):
            status = event.get("status", {}).get("type", {}).get("state")
            if status in ["in", "live"]:
                comp = event["competitions"][0]
                competitors = comp["competitors"]
                away = next((c for c in competitors if c["homeAway"] == "away"), {})
                home = next((c for c in competitors if c["homeAway"] == "home"), {})
                games.append({
                    "id": event["id"],
                    "away": away.get("team", {}).get("displayName", "Away"),
                    "home": home.get("team", {}).get("displayName", "Home"),
                    "away_score": away.get("score", 0),
                    "home_score": home.get("score", 0),
                    "period": event.get("status", {}).get("period", 0),
                    "clock": event.get("status", {}).get("displayClock", ""),
                })
        with open(cache_file, "w") as f:
            json.dump({"games": games, "ts": datetime.now().isoformat()}, f)
        return games
    except Exception as e:
        print(f"Live scrape failed for {sport}: {e}")
        return []
