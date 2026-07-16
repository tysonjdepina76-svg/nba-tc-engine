#!/usr/bin/env python3
"""Generate projection JSON files for today's games from the TC API.
Saves proj_SPORT_MATCHUP.json into Daily_Log/<today>/
"""
import json, os, sys, subprocess
from datetime import datetime, timedelta
from pathlib import Path

ET = datetime.now().astimezone()
TODAY = ET.strftime("%Y-%m-%d")
LOG_DIR = Path("/home/workspace/Daily_Log") / TODAY
SPORTS = ["WNBA", "MLB"]
API_URL = "http://localhost:3099/api/tc"

def fetch_slate(sport):
    """Get today's games from the API."""
    result = subprocess.run(
        ["curl", "-s", f"{API_URL}?sport={sport}"],
        capture_output=True, text=True, timeout=15
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"games": []}

def fetch_projections(sport, away, home):
    """Fetch full projections for a game."""
    result = subprocess.run(
        ["curl", "-s", f"{API_URL}?sport={sport}&away={away}&home={home}"],
        capture_output=True, text=True, timeout=30
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    sports_generated = []
    
    for sport in SPORTS:
        slate = fetch_slate(sport)
        games = slate.get("games", [])
        if not games:
            print(f"  {sport}: no games today")
            continue
        
        game_count = 0
        for g in games:
            if g.get("status") == "Postponed":
                print(f"  {sport}: {g['away']}@{g['home']} SKIP (Postponed)")
                continue
            
            away = g["away"]
            home = g["home"]
            matchup = f"{away}_at_{home}"
            
            print(f"  {sport}: {matchup} ...", end=" ", flush=True)
            proj_data = fetch_projections(sport, away, home)
            
            if proj_data is None:
                print("FAILED")
                continue
            
            filename = LOG_DIR / f"proj_{sport}_{matchup}.json"
            with open(filename, "w") as f:
                json.dump(proj_data, f, indent=2, default=str)
            
            n_players = len(proj_data.get("away", {}).get("all", {}).get("players", [])) + \
                        len(proj_data.get("home", {}).get("all", {}).get("players", []))
            print(f"OK ({n_players} players)")
            game_count += 1
        
        if game_count > 0:
            sports_generated.append(sport)
    
    print(f"\nSaved projections to {LOG_DIR}/")
    return sports_generated

if __name__ == "__main__":
    main()
