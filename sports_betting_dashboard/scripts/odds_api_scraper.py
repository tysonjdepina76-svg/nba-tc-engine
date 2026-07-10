#!/usr/bin/env python3
"""
Odds API Scraper — fetches live odds for all active sports.
NBA/NHL are off-season aware and skipped.
Writes to sports_betting_dashboard/data/odds/.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

ET = timezone(timedelta(hours=-4))
WORKSPACE = Path("/home/workspace")
ODDS_DIR = WORKSPACE / "sports_betting_dashboard" / "data" / "odds"
ODDS_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ.get("ODDS_API_KEY") or os.environ.get("THEODDSAPI", "")
BASE = "https://api.the-odds-api.com/v4"
SPORTS_ENDPOINT = f"{BASE}/sports"
ACTIVE_SPORTS = ["basketball_wnba", "baseball_mlb", "soccer_fifa_world_cup"]
OFF_SEASON = ["basketball_nba", "icehockey_nhl"]


def fetch_odds(sport_key, regions="us", markets="h2h,spreads,totals"):
    url = f"{BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "american",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 401:
            print(f"  {sport_key}: 401 — quota exhausted")
        elif r.status_code == 422:
            print(f"  {sport_key}: 422 — no events available")
        else:
            print(f"  {sport_key}: HTTP {r.status_code} — {r.text[:120]}")
    except Exception as e:
        print(f"  {sport_key}: fetch error — {e}")
    return None


def main():
    print(f"Odds API Scraper — {datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S ET')}")
    print(f"API Key: {'present' if API_KEY else 'MISSING'}")
    print()

    if not API_KEY:
        print("No ODDS_API_KEY set — cannot scrape.")
        sys.exit(1)

    for sport_key in ACTIVE_SPORTS:
        short = sport_key.split("_", 1)[1].upper()
        print(f"Fetching {sport_key} ({short})...")
        data = fetch_odds(sport_key)
        if data:
            out_path = ODDS_DIR / f"{sport_key}_live.json"
            out_path.write_text(json.dumps(data, indent=2, default=str))
            game_count = len(data) if isinstance(data, list) else 0
            print(f"  ✓ Saved {game_count} games → {out_path.name}")
        else:
            print(f"  ✗ No data for {sport_key}")

    print(f"\nDone. Files in {ODDS_DIR}")

    total_size = sum(f.stat().st_size for f in ODDS_DIR.glob("*.json") if f.is_file())
    print(f"Total: {total_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
