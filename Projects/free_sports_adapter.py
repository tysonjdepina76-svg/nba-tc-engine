#!/usr/bin/env python3
"""Free Sports Data Adapter — replaces dead Odds API (Business tier maxed).

Sources (all free, no API keys required):
- nba_api (swar/nba_api) — NBA & WNBA live stats, player data
- MLB-StatsAPI — MLB live game data, player stats  
- pybaseball — historical MLB, Statcast, player lookup
- ESPN API (v2 scoreboard) — box scores, rosters, schedule (already in use)
- SerpAPI — Google search for odds lines (fallback, key in env)

This module provides unified get_[sport]_data() functions and a CLI.
"""

import os, json, sys, time, hashlib
from datetime import datetime, timedelta
from pathlib import Path

CACHE_DIR = Path("/home/workspace/Projects/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cache_get(key: str, ttl: int = 300) -> dict | None:
    """Get cached data if fresh (within TTL seconds)."""
    f = CACHE_DIR / f"{key}.json"
    if not f.exists():
        return None
    age = time.time() - f.stat().st_mtime
    if age > ttl:
        return None
    return json.loads(f.read_text())

def _cache_set(key: str, data: dict):
    """Cache data to disk."""
    f = CACHE_DIR / f"{key}.json"
    f.write_text(json.dumps(data, default=str))

# ─── MLB (MLB-StatsAPI + pybaseball) ─────────────────────────────

def get_mlb_schedule(date_str: str = None) -> dict:
    """Get MLB schedule for a date using MLB-StatsAPI."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"mlb_schedule_{date_str}"
    cached = _cache_get(cache_key, ttl=3600)
    if cached:
        return cached
    try:
        import statsapi
        games = statsapi.schedule(date=date_str)
        result = {"date": date_str, "games": games, "count": len(games), "source": "MLB-StatsAPI"}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e), "source": "MLB-StatsAPI"}

def get_mlb_live_game(game_pk: int) -> dict:
    """Get live MLB game data using MLB-StatsAPI."""
    cache_key = f"mlb_live_{game_pk}"
    cached = _cache_get(cache_key, ttl=60)
    if cached:
        return cached
    try:
        import statsapi
        data = statsapi.get("game", {"gamePk": game_pk})
        result = {"game_pk": game_pk, "data": data, "source": "MLB-StatsAPI"}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e), "source": "MLB-StatsAPI"}

def get_mlb_player_stats(player_id: int, season: int = 2026) -> dict:
    """Get MLB player stats for a season using pybaseball."""
    cache_key = f"mlb_player_{player_id}_{season}"
    cached = _cache_get(cache_key, ttl=86400)
    if cached:
        return cached
    try:
        from pybaseball import statcast_batter, playerid_lookup
        data = statcast_batter(f"{season}-01-01", f"{season}-12-31", player_id=player_id)
        result = {"player_id": player_id, "season": season, "rows": len(data) if hasattr(data, '__len__') else 0, "source": "pybaseball"}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e), "source": "pybaseball"}

# ─── WNBA (nba_api) ──────────────────────────────────────────────

def get_wnba_scoreboard(date_str: str = None) -> dict:
    """Get WNBA scoreboard using nba_api."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"wnba_scoreboard_{date_str}"
    cached = _cache_get(cache_key, ttl=300)
    if cached:
        return cached
    try:
        from nba_api.live.nba.endpoints import scoreboard
        board = scoreboard.ScoreBoard()
        data = board.get_dict()
        result = {"date": date_str, "data": data, "source": "nba_api"}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e), "source": "nba_api"}

def get_wnba_player_stats(player_id: int) -> dict:
    """Get WNBA player career stats using nba_api."""
    cache_key = f"wnba_player_{player_id}"
    cached = _cache_get(cache_key, ttl=86400)
    if cached:
        return cached
    try:
        from nba_api.stats.endpoints import playercareerstats
        stats = playercareerstats.PlayerCareerStats(player_id=player_id, per_mode36="PerGame")
        data = stats.get_dict()
        result = {"player_id": player_id, "data": data, "source": "nba_api"}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e), "source": "nba_api"}

# ─── FREE ODDS SCRAPER (SerpAPI + web) ───────────────────────────

def get_odds_via_serpapi(sport: str, query: str = "") -> dict:
    """Search for odds lines via SerpAPI (Google). Returns structured results."""
    cache_key = f"serp_{sport}_{query}"[:64]
    cached = _cache_get(cache_key, ttl=600)
    if cached:
        return cached

    api_key = os.environ.get("Serp_Api_key", "")
    if not api_key:
        return {"error": "Serp_Api_key not set in environment", "source": "serpapi"}

    try:
        from serpapi import GoogleSearch
        params = {"q": f"{sport} player props odds today {query}", "api_key": api_key, "num": 10, "engine": "google"}
        search = GoogleSearch(params)
        results = search.get_dict()
        organic = results.get("organic_results", [])
        odds = []
        for r in organic:
            odds.append({"title": r.get("title", ""), "snippet": r.get("snippet", ""), "link": r.get("link", "")})
        result = {"sport": sport, "query": query, "results": odds, "count": len(odds), "source": "serpapi"}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e), "source": "serpapi"}

# ─── ESPN API (already working, cached) ──────────────────────────

def get_espn_scoreboard(sport: str, date_str: str = None) -> dict:
    """Get ESPN scoreboard for any sport. Uses existing ESPN v2 API."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    cache_key = f"espn_{sport}_{date_str}"
    cached = _cache_get(cache_key, ttl=120)
    if cached:
        return cached

    sport_map = {"mlb": "baseball", "wnba": "basketball", "nba": "basketball", "wc": "soccer", "nfl": "football"}
    espn_sport = sport_map.get(sport.lower(), sport.lower())

    try:
        import requests
        url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_sport}/{sport.lower()}/scoreboard"
        if date_str:
            url += f"?dates={date_str}"
        r = requests.get(url, timeout=10)
        data = r.json()
        result = {"sport": sport, "date": date_str, "events": data.get("events", []), "source": "espn_v2"}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e), "source": "espn_v2"}

# ─── UNIFIED INTERFACE ───────────────────────────────────────────

def get_live_data(sport: str, date_str: str = None) -> dict:
    """Get all available live data for a sport. Falls back across sources."""
    sport = sport.lower()

    if sport == "mlb":
        sched = get_mlb_schedule(date_str)
        if "error" not in sched and sched.get("games"):
            games = sched["games"]
            lives = []
            for g in games[:5]:
                gid = g.get("game_id")
                if gid:
                    lives.append(get_mlb_live_game(gid))
            return {"sport": "mlb", "schedule": sched, "live_games": lives, "source": "mlb_statsapi"}
        return get_espn_scoreboard("mlb", date_str.replace("-", "") if date_str else None)

    elif sport == "wnba":
        board = get_wnba_scoreboard(date_str)
        if "error" not in board:
            return {"sport": "wnba", "scoreboard": board, "source": "nba_api"}
        return get_espn_scoreboard("wnba", date_str.replace("-", "") if date_str else None)

    else:
        return get_espn_scoreboard(sport, date_str.replace("-", "") if date_str else None)

# ─── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Free Sports Data Adapter")
    p.add_argument("--sport", choices=["mlb", "wnba", "wc", "nba", "nfl"], default="mlb")
    p.add_argument("--date", default=None, help="YYYY-MM-DD or YYYYMMDD")
    p.add_argument("--live", action="store_true", help="Get live data")
    p.add_argument("--odds", action="store_true", help="Scrape odds via SerpAPI")
    args = p.parse_args()

    if args.live:
        print(json.dumps(get_live_data(args.sport, args.date), indent=2, default=str))
    elif args.odds:
        print(json.dumps(get_odds_via_serpapi(args.sport), indent=2, default=str))
    else:
        print(json.dumps(get_espn_scoreboard(args.sport, args.date), indent=2, default=str))
