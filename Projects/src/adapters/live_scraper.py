#!/usr/bin/env python3
"""Live ESPN play-by-play scraper for in-game stats."""
import requests
import json
from datetime import datetime
from pathlib import Path
from src.adapters.cache_adapter import CacheAdapter

cache = CacheAdapter(ttl_hours=0.0167)

LEAGUE_MAP = {
    "mlb": "baseball/mlb",
    "wnba": "basketball/wnba",
    "soccer": "soccer/usa.1",
}

def fetch_live_games(sport: str):
    """Fetch live games from ESPN scoreboard endpoint."""
    if sport not in LEAGUE_MAP:
        return []

    url = f"https://site.api.espn.com/apis/site/v2/sports/{LEAGUE_MAP[sport]}/scoreboard"
    cache_key = f"live_{sport}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    headers = {"User-Agent": "Mozilla/5.0 (compatible; TCSports/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        games = []
        for event in data.get("events", []):
            status = event.get("status", {}).get("type", {}).get("state", "")
            if status in ("in", "live"):
                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                games.append({
                    "id": event.get("id"),
                    "away": away.get("team", {}).get("displayName", "Away"),
                    "home": home.get("team", {}).get("displayName", "Home"),
                    "away_score": away.get("score", 0),
                    "home_score": home.get("score", 0),
                    "period": event.get("status", {}).get("period", 0),
                    "clock": event.get("status", {}).get("displayClock", ""),
                    "status": status,
                })
        cache.set(cache_key, games)
        return games
    except Exception as e:
        print(f"[live_scraper] {sport} scrape failed: {e}")
        return []


def fetch_game_boxscore(sport: str, game_id: str):
    """Fetch boxscore details for a specific live/ended game."""
    if sport not in LEAGUE_MAP:
        return {}

    url = f"https://site.api.espn.com/apis/site/v2/sports/{LEAGUE_MAP[sport]}/summary"
    params = {"event": game_id}
    cache_key = f"boxscore_{game_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    headers = {"User-Agent": "Mozilla/5.0 (compatible; TCSports/1.0)"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        cache.set(cache_key, data)
        return data
    except Exception as e:
        print(f"[live_scraper] boxscore {game_id} failed: {e}")
        return {}


def fetch_live_player_stats(sport: str, game_id: str):
    """Extract player stat lines from live boxscore."""
    box = fetch_game_boxscore(sport, game_id)
    if not box:
        return []

    players = []
    for team_box in box.get("boxscore", {}).get("teams", []):
        team_name = team_box.get("team", {}).get("displayName", "Unknown")
        for cat in team_box.get("statistics", []):
            cat_name = cat.get("name", "")
            for athlete in cat.get("athletes", []):
                player = {
                    "name": athlete.get("athlete", {}).get("displayName", ""),
                    "team": team_name,
                    "position": athlete.get("athlete", {}).get("position", {}).get("abbreviation", ""),
                    "stat_category": cat_name,
                    "stat_value": athlete.get("stats", [0])[0] if athlete.get("stats") else 0,
                }
                players.append(player)
    return players
