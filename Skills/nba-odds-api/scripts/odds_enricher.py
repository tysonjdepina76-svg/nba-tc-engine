#!/usr/bin/env python3
"""
Odds Enricher — Injects live player prop lines from The Odds API into the TC pipeline.

Two-step fetch (required by free tier):
  1. /sports/{sport}/odds?markets=h2h,spreads,totals  → get game IDs
  2. /sports/{sport}/events/{id}/odds?markets=player_points,player_rebounds,player_assists → get props

Usage:
  Import: from odds_enricher import enrich_player_lines
  CLI:    python odds_enricher.py --sport NBA --matchup "NYK@CLE"
"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime, timezone

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4"

SPORT_MAP = {
    "NBA": "basketball_nba",
    "WNBA": "basketball_wnba",
}

BOOK_PRIORITY = ["draftkings", "fanduel", "betmgm", "fanatics", "bovada"]

CACHE_DIR = Path.home() / ".zo" / "odds"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _find_game(sport_key, away_team, home_team):
    url = f"{BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    for g in r.json():
        if g.get("home_team") == home_team and g.get("away_team") == away_team:
            return g
    return None


def _fetch_player_props(sport_key, game_id):
    url = f"{BASE_URL}/sports/{sport_key}/events/{game_id}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "player_points,player_rebounds,player_assists",
        "oddsFormat": "decimal",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _extract_game_odds(game_data, preferred_book):
    h2h, spreads, totals = {}, {}, {}
    for bk in game_data.get("bookmakers", []):
        if bk.get("key") != preferred_book:
            continue
        for m in bk.get("markets", []):
            mk = m.get("key", "")
            if mk == "h2h":
                h2h = {o["name"]: o["price"] for o in m.get("outcomes", [])}
            elif mk == "spreads":
                spreads = {o["name"]: {"point": o["point"], "price": o["price"]}
                          for o in m.get("outcomes", [])}
            elif mk == "totals":
                totals = {o["name"]: {"point": o["point"], "price": o["price"]}
                         for o in m.get("outcomes", [])}
    return {"h2h": h2h, "spreads": spreads, "totals": totals}


def _extract_props(prop_data, preferred_book):
    """Return { player_name: { points: line, rebounds: line, assists: line } }"""
    props = {}
    stat_map = {
        "player_points": "points",
        "player_rebounds": "rebounds",
        "player_assists": "assists",
    }
    for bk in prop_data.get("bookmakers", []):
        if bk.get("key") != preferred_book:
            continue
        for m in bk.get("markets", []):
            stat = stat_map.get(m.get("key", ""))
            if not stat:
                continue
            for o in m.get("outcomes", []):
                name = o.get("description", o.get("name", ""))
                if o.get("name") == "Over":
                    props.setdefault(name, {})[stat] = o.get("point")
    return props


def enrich_player_lines(sport, away, home, preferred_book="draftkings"):
    """
    Main entry point for the TC pipeline.

    Returns:
      { game_odds, player_lines, source, book, fetched_at } or { error, player_lines: {}, source: "none" }
    """
    if not ODDS_API_KEY:
        return {"error": "ODDS_API_KEY not set", "player_lines": {}, "source": "none"}

    sport_key = SPORT_MAP.get(sport.upper())
    if not sport_key:
        return {"error": f"No sport key for {sport}", "player_lines": {}, "source": "none"}

    try:
        game = _find_game(sport_key, away, home)
        if not game:
            return {"error": f"Game {away}@{home} not found", "player_lines": {}, "source": "none"}

        game_id = game["id"]
        game_odds = _extract_game_odds(game, preferred_book)

        prop_data = _fetch_player_props(sport_key, game_id)
        player_lines = _extract_props(prop_data, preferred_book)

        return {
            "game_odds": game_odds,
            "player_lines": player_lines,
            "player_count": len(player_lines),
            "source": "odds_api",
            "book": preferred_book,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return {"error": str(e), "player_lines": {}, "source": "error"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Odds Enricher for TC Pipeline")
    parser.add_argument("--sport", required=True, help="NBA or WNBA")
    parser.add_argument("--matchup", required=True, help="Away@Home format")
    parser.add_argument("--book", default="draftkings", help="Preferred bookmaker slug")
    args = parser.parse_args()

    parts = args.matchup.split("@")
    if len(parts) != 2:
        print("❌ Matchup must be in Away@Home format")
        sys.exit(1)

    result = enrich_player_lines(args.sport, parts[0], parts[1], args.book)
    print(json.dumps(result, indent=2))
