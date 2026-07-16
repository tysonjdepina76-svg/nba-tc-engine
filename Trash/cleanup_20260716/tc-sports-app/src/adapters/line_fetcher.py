"""line_fetcher.py — Fetch betting lines via TheOddsAPI.

Uses THEODDSAPI env var for the API key. Falls back gracefully
when quota is exhausted (Business tier maxed → returns empty players).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import requests

THEODDSAPI = os.getenv("THEODDSAPI", "")
BASE_URL = "https://api.the-odds-api.com/v4"
ET = timezone(timedelta(hours=-4))

log = logging.getLogger(__name__)

SPORT_KEY_MAP: Dict[str, str] = {
    "wnba": "basketball_wnba",
    "mlb": "baseball_mlb",
    "wc": "soccer_fifa_world_cup",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
}


def fetch_lines(sport: str, region: str = "us") -> Dict[str, Any]:
    """Fetch player props and game lines for a sport.

    Returns:
        {"players": [{"name": ..., "team": ..., "projection": ..., ...}],
         "games": [...],
         "source": "theoddsapi" | "fallback"}
    """
    api_key = THEODDSAPI or os.getenv("THE_ODDS_API_KEY", "")
    sport_key = SPORT_KEY_MAP.get(sport.lower(), sport)

    if not api_key:
        log.warning("No TheOddsAPI key set — returning empty lines")
        return {"players": [], "games": [], "source": "fallback"}

    try:
        resp = requests.get(
            f"{BASE_URL}/sports/{sport_key}/events",
            params={"apiKey": api_key},
            timeout=10,
        )
        if resp.status_code == 401:
            log.warning(
                "TheOddsAPI returned 401 — quota likely exhausted (Business tier)"
            )
            return {"players": [], "games": [], "source": "quota_exhausted"}
        if resp.status_code != 200:
            log.error(f"TheOddsAPI error {resp.status_code}: {resp.text[:200]}")
            return {"players": [], "games": [], "source": "error"}

        events = resp.json()
        players: List[Dict[str, Any]] = []
        games: List[Dict[str, Any]] = []

        for event in events:
            game = {
                "id": event.get("id", ""),
                "home": event.get("home_team", ""),
                "away": event.get("away_team", ""),
                "commence_time": event.get("commence_time", ""),
            }
            games.append(game)

            for bookmaker in event.get("bookmakers", []):
                if bookmaker.get("key") != "draftkings":
                    continue
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "player_points":
                        continue
                    for outcome in market.get("outcomes", []):
                        players.append({
                            "name": outcome.get("description", ""),
                            "team": outcome.get("name", ""),
                            "line": outcome.get("point", 0),
                            "projection": outcome.get("point", 0),
                            "over_under": "OVER",
                            "game_id": event.get("id", ""),
                        })

        log.info(f"Fetched {len(players)} player lines for {sport}")
        return {"players": players, "games": games, "source": "theoddsapi"}

    except requests.RequestException as e:
        log.error(f"TheOddsAPI request failed: {e}")
        return {"players": [], "games": [], "source": "network_error"}
