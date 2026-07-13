"""
MLB book lines and player stats with fallbacks.
"""

import json
import os
from datetime import datetime
from sources.scrapers.baseball_reference import BaseballReferenceScraper
from sources.utils.cache import cache_fetch
from sources.utils.logging import get_logger

logger = get_logger(__name__)

def fetch_mlb_book_lines(matchup: str = None, dry_run: bool = False) -> dict:
    """Fetch MLB player stats and game lines."""
    if dry_run:
        return {"source": "dry_run", "players": []}
    try:
        logger.info("Fetching MLB stats from Baseball-Reference...")
        scraper = BaseballReferenceScraper(season=2026)
        batting = cache_fetch("mlb_batting_br", lambda: scraper.fetch_batting(), ttl_hours=6)
        pitching = cache_fetch("mlb_pitching_br", lambda: scraper.fetch_pitching(), ttl_hours=6)
        if batting or pitching:
            players = merge_batting_pitching(batting, pitching)
            if players:
                logger.info(f"Found {len(players)} MLB players")
                return {"source": "BaseballReference", "players": players}
    except Exception as e:
        logger.warning(f"Baseball-Reference failed: {e}")
    cached = load_cached_mlb()
    if cached:
        return cached
    return {"source": "none", "players": [], "error": "No MLB data available"}

def merge_batting_pitching(batting: list, pitching: list) -> list:
    """Merge batting and pitching stats into a single player list."""
    players = {p["name"]: p for p in batting}
    for pitcher in pitching:
        name = pitcher["name"]
        if name in players:
            players[name].update(pitcher)
        else:
            players[name] = pitcher
    return list(players.values())

def load_cached_mlb() -> dict:
    """Load cached MLB data."""
    cache_file = "/tmp/mlb_players_cache.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"source": "none", "players": []}
