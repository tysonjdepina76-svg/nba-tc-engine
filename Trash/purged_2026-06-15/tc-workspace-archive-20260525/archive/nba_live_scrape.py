#!/usr/bin/env python3
"""NBA Live Scrape — Update all active series with fresh lines and rosters"""
import json, urllib.request, datetime, warnings
warnings.filterwarnings("ignore")

ESPN_SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠️  Fetch error: {e}")
        return {}

def get_games(date):
    url = f"{ESPN_SB}?dates={date}"
    return fetch_json(url)

# Try a range of dates
dates = ["20250505", "20250506", "20250504", "20250503"]
all_games = {}

for d in dates:
    data = get_games(d)
    for event in data.get("events", []):
        eid = event["id"]
        comp = event.get("competitions", [{}])[0]
        home = comp.get("home", {})
        away = comp.get("away", {})
        
        hteam = home.get("team", {})
        ateam = away.get("team", {})
        
        hname = hteam.get("shortDisplayName", "?")
        aname = ateam.get("shortDisplayName", "?")
        
        status = event.get("status", {}).get("type", {}).get("description", "?)
        period = event.get("status", {}).get("period", 0)
        
        venue = event.get("venue", {}).get("fullName", "")
        
        # Odds
        odds_arr = comp.get("odds", [])
        total = None
        spread = None
        if odds_arr:
            total = odds_arr[0].get("overUnder")
            spread = odds_arr[0].get("spread")
        
        # Leaders / box if final
        leaders = comp.get("leaders", [])
        
        print(f"\n{'='*60}")
        print(f"  {aname} @ {hname}")
        print(f"  Status: {status} | Period: {period} | Venue: {venue}")
        if total: print(f"  Total: {total} | Spread: {spread}")
        if leaders:
            print(f"  Leaders:")
            for L in leaders:
                print(f"    - {L.get('athlete',{}).get('shortName','?')}: {L.get('value','?')} {L.get('statistics',['?'])[0] if L.get('statistics') else ''}")

        all_games[eid] = {
            "away": aname, "home": hname, "status": status,
            "period": period, "total": total, "spread": spread,
            "venue": venue, "date": d
        }

print(f"\n\nTotal games scraped: {len(all_games)}")

# Save raw
with open("/home/workspace/NBA_LIVE_SCRAPE.json", "w") as f:
    json.dump(all_games, f, indent=2)
print("Saved: NBA_LIVE_SCRAPE.json")

