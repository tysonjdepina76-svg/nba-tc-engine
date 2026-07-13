"""
WNBA data fetcher with TC engine and fallbacks.
"""

import json
import os
from datetime import datetime
from sources.scrapers.basketball_reference import BasketballReferenceScraper
from sources.utils.cache import cache_fetch
from sources.utils.logging import get_logger

logger = get_logger(__name__)

def fetch_wnba_lines(matchup: str = None, dry_run: bool = False) -> dict:
    """Fetch WNBA player stats and lines."""
    if dry_run:
        return {"source": "dry_run", "players": []}
    try:
        from sources.wnba_tc_engine import project_game
        logger.info("Fetching WNBA stats from TC engine...")
        data = project_game(matchup)
        if data and data.get("players"):
            logger.info(f"Found {len(data['players'])} players from TC engine")
            return data
    except Exception as e:
        logger.warning(f"TC engine failed: {e}")
    try:
        logger.info("Fetching WNBA stats from Basketball-Reference...")
        scraper = BasketballReferenceScraper(season=2026)
        players = cache_fetch("wnba_stats_br", lambda: scraper.fetch_player_stats(), ttl_hours=6)
        if players:
            logger.info(f"Found {len(players)} players from BR")
            return {"source": "BasketballReference", "timestamp": datetime.now().isoformat(), "players": players}
    except Exception as e:
        logger.warning(f"Basketball-Reference failed: {e}")
    cached = load_cached_wnba()
    if cached:
        cached["source"] = "cache"
        return cached
    return {"source": "none", "players": [], "error": "No WNBA data available"}

def load_cached_wnba() -> dict:
    """Load cached WNBA data."""
    cache_file = "/tmp/wnba_players_cache.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"source": "none", "players": []}
