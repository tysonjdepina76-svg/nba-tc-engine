#!/usr/bin/env python3
"""Generate WNBA/MLB/WC projection JSON files from live /api/tc in the format daily_picks.py expects."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

API_BASE = "http://localhost:3099/api/tc"
LOG_DIR = Path("/home/workspace/Daily_Log")


def fetch_slate(sport: str, date_str: str | None = None):
    """Fetch all games for a sport on a given date."""
    params = {"sport": sport.upper()}
    if date_str:
        params["date"] = date_str
    try:
        resp = requests.get(API_BASE, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ERROR fetching {sport} slate: {e}")
        return None


def fetch_projections(sport, away, home):
    """Fetch per-game projections."""
    params = {"sport": sport.upper(), "away": away, "home": home}
    try:
        resp = requests.get(API_BASE, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"    ERROR fetching {sport} {away}@{home}: {e}")
        return None


def save_game_proj(sport, away, home, data, date_str):
    """Save a single game projection file."""
    out_dir = LOG_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"proj_{sport.upper()}_{away}_at_{home}.json"
    out_path = out_dir / fname
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate TC projection files")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--sport", default="all")
    args = parser.parse_args()

    sports = ["WNBA", "MLB"] if args.sport == "all" else [args.sport.upper()]

    total = 0
    for sport in sports:
        slate = fetch_slate(sport, args.date)
        if not slate or not slate.get("games"):
            print(f"  No {sport} games on {args.date}")
            continue

        games = slate["games"]
        print(f"  {sport}: {len(games)} game(s) on {args.date}")
        for g in games:
            away = g.get("away", "")
            home = g.get("home", "")
            if not away or not home:
                continue
            proj = fetch_projections(sport, away, home)
            if not proj:
                continue
            path = save_game_proj(sport, away, home, proj, args.date)
            players = (
                len(proj.get("away", {}).get("all", {}).get("players", []))
                + len(proj.get("home", {}).get("all", {}).get("players", []))
            )
            print(f"    {away}@{home}: {players} players → {path}")
            total += players

    print(f"\nTotal: {total} stat-lines across {len(sports)} sports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
