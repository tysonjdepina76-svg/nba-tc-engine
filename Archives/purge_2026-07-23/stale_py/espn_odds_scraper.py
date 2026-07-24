#!/usr/bin/env python3
"""ESPN v2 API Odds Scraper — free, no key, DraftKings game odds.
Provides: spread, over/under, moneyline per game for WNBA, MLB.
Also scrapes ESPN hidden API for richer data via espn_scraper lib.
"""
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger("espn_odds")

# ESPN v2 endpoints (public, no auth)
ESPN_V2_BASE = "https://site.api.espn.com/apis/site/v2/sports"
SPORT_PATHS = {
    "wnba": "/basketball/wnba/scoreboard",
    "mlb": "/baseball/mlb/scoreboard",
}

# ESPN hidden API (no auth, richer data — boxscores, play-by-play)
ESPN_HIDDEN = "https://site.web.api.espn.com/apis/site/v2/sports"
ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"


def fetch_espn_v2_odds(sport: str, date_str: Optional[str] = None) -> dict:
    """Fetch game-level DraftKings odds from ESPN v2 public API.
    
    Args:
        sport: 'wnba' or 'mlb'
        date_str: YYYYMMDD format, defaults to today
    
    Returns:
        {event_id: {spread, overUnder, moneyline_home, moneyline_away, ...}}
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    path = SPORT_PATHS.get(sport.lower())
    if not path:
        logger.error(f"Unknown sport: {sport}")
        return {}
    
    url = f"{ESPN_V2_BASE}{path}?dates={date_str}"
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"ESPN v2 fetch failed for {sport}: {e}")
        return {}
    
    odds_map = {}
    for event in data.get("events", []):
        eid = event.get("id")
        for comp in event.get("competitions", []):
            odds_list = comp.get("odds", [])
            if not odds_list:
                continue
            
            # Take first odds provider (usually DraftKings)
            odds = odds_list[0]
            provider = odds.get("provider", {}).get("name", "unknown")
            details = odds.get("details", "")
            spread = odds.get("spread")
            over_under = odds.get("overUnder")
            
            # Moneyline
            ml = odds.get("moneyline", {})
            ml_home = ml.get("home", {}).get("close", {}).get("odds")
            ml_away = ml.get("away", {}).get("close", {}).get("odds")
            
            # Team abbreviations
            competitors = comp.get("competitors", [])
            home_team = away_team = None
            for team in competitors:
                abbrev = team.get("team", {}).get("abbreviation", "")
                if team.get("homeAway") == "home":
                    home_team = abbrev
                else:
                    away_team = abbrev
            
            odds_map[str(eid)] = {
                "provider": provider,
                "details": details,
                "spread": spread,
                "overUnder": over_under,
                "moneyline_home": ml_home,
                "moneyline_away": ml_away,
                "home_team": home_team,
                "away_team": away_team,
                "sport": sport,
                "fetched_at": datetime.now().isoformat(),
            }
    
    logger.info(f"ESPN v2: fetched {len(odds_map)} game odds for {sport}")
    return odds_map


def fetch_espn_boxscore(event_id: str, sport: str = "wnba") -> dict:
    """Fetch boxscore from ESPN hidden API (no auth).
    Uses the espn_scraper-compatible endpoints.
    """
    sport_map = {"wnba": "basketball/wnba", "mlb": "baseball/mlb"}
    sport_path = sport_map.get(sport, sport)
    
    url = f"{ESPN_HIDDEN}/{sport_path}/summary?event={event_id}"
    
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Boxscore fetch failed for {event_id}: {e}")
        return {}


def fetch_espn_roster(team_id: str, sport: str = "wnba") -> dict:
    """Fetch team roster from ESPN core API."""
    sport_map = {"wnba": "basketball/wnba", "mlb": "baseball/mlb"}
    sport_path = sport_map.get(sport, sport)
    
    url = f"{ESPN_CORE}/{sport_path}/teams/{team_id}/athletes?limit=50"
    
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Roster fetch failed for {team_id}: {e}")
        return {}


def fetch_all_game_odds(date_str: Optional[str] = None) -> dict:
    """Fetch odds for all supported sports on a given date."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    all_odds = {}
    for sport in ["wnba", "mlb"]:
        odds = fetch_espn_v2_odds(sport, date_str)
        all_odds[sport] = odds
    
    total = sum(len(o) for o in all_odds.values())
    logger.info(f"ESPN total odds: {total} games across {list(all_odds.keys())}")
    return all_odds


# Cache singleton
_ODDS_CACHE: dict = {}
_CACHE_TIME: float = 0
_CACHE_TTL = 300  # 5 minutes


def get_game_odds(sport: str, event_id: str, force_refresh: bool = False) -> dict:
    """Get cached game odds, refreshing if needed."""
    global _ODDS_CACHE, _CACHE_TIME
    
    now = time.time()
    if force_refresh or not _ODDS_CACHE or (now - _CACHE_TIME) > _CACHE_TTL:
        _ODDS_CACHE = fetch_all_game_odds()
        _CACHE_TIME = now
    
    for sport_odds in _ODDS_CACHE.values():
        if event_id in sport_odds:
            return sport_odds[event_id]
    return {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    for sport in ["wnba", "mlb"]:
        print(f"\n=== {sport.upper()} ===")
        odds = fetch_espn_v2_odds(sport)
        for eid, o in list(odds.items())[:3]:
            print(f"  {o['away_team']} @ {o['home_team']}: spread={o['spread']}, OU={o['overUnder']}, ML={o['moneyline_away']}/{o['moneyline_home']}")
