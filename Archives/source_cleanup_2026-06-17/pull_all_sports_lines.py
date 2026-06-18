#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""Pull live lines for all supported sports via SGO + Odds API and save as backtest-ready files."""
import json, os, re, requests, sys
from datetime import datetime
from pathlib import Path

secrets = Path("/root/.zo/secrets.env").read_text()
SGO_KEY = re.search(r'^SPORTSGAMEODDS_API_KEY=(\S+)', secrets, re.MULTILINE).group(1)
ODDS_KEY = re.search(r'^ODDS_API_KEY=(\S+)', secrets, re.MULTILINE).group(1)

OUT = Path("/home/workspace/Daily_Log/2026-06-13")
OUT.mkdir(parents=True, exist_ok=True)

# SGO leagues that work
SGO_LEAGUES = {"NBA": "NBA", "MLB": "MLB", "NHL": "NHL", "MLS": "MLS"}
# Odds API sport keys
ODDS_SPORTS = {
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "worldcup": "soccer_fifa_world_cup",
    "mls": "soccer_usa_mls",
    "wnba": "basketball_wnba",
    "nba": "basketball_nba",
}

all_data = {}

# --- SGO pull ---
for league_id, name in SGO_LEAGUES.items():
    try:
        r = requests.get(
            "https://api.sportsgameodds.com/v2/events",
            params={"leagueID": league_id, "oddsAvailable": "true", "apikey": SGO_KEY},
            headers={"x-api-key": SGO_KEY},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            all_data[f"sgo_{name.lower()}"] = data
            print(f"SGO {name}: {len(data)} events")
        else:
            print(f"SGO {name}: {r.status_code} ({r.text[:100]})")
            all_data[f"sgo_{name.lower()}"] = []
    except Exception as e:
        print(f"SGO {name}: ERROR {e}")

# --- Odds API pull ---
for name, sport_key in ODDS_SPORTS.items():
    try:
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
            params={
                "apiKey": ODDS_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
                "bookmakers": "draftkings",
            },
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            all_data[f"oddsapi_{name}"] = data
            print(f"OddsAPI {name}: {len(data)} events")
        else:
            print(f"OddsAPI {name}: {r.status_code} ({r.text[:100]})")
            all_data[f"oddsapi_{name}"] = []
    except Exception as e:
        print(f"OddsAPI {name}: ERROR {e}")

# Save combined
out_file = OUT / "all_sports_lines.json"
out_file.write_text(json.dumps(all_data, indent=2, default=str))
print(f"\nSaved {sum(len(v) for v in all_data.values())} total entries → {out_file}")

# Also save per-sport summary
summary = {}
for k, v in all_data.items():
    summary[k] = len(v)
    sport_out = OUT / f"lines_{k}.json"
    Path(sport_out).write_text(json.dumps(v, indent=2, default=str))

(OUT / "lines_summary.json").write_text(json.dumps(summary, indent=2))
print(f"Per-sport files saved, summary: {json.dumps(summary)}")
