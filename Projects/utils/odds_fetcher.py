import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("odds_fetcher")

CACHE_DIR = Path("/home/workspace/.cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_DEAD = os.getenv("ODDS_API_QUOTA_DEADLINE", "") != ""

def fetch_bookmaker_odds(sport, market="h2h", regions="us", bookmakers="draftkings"):
    cache_file = CACHE_DIR / f"odds_{sport}_{market}_{datetime.now().strftime('%Y%m%d')}.json"
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                return json.load(f)
        except:
            pass
    if not ODDS_API_KEY or ODDS_API_DEAD:
        logger.info(f"[OddsFetcher] Odds API dead — returning empty for {sport}")
        return []
    import requests
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        resp = requests.get(url, params={
            "apiKey": ODDS_API_KEY, "regions": regions,
            "markets": market, "bookmakers": bookmakers
        }, timeout=15)
        if resp.status_code == 401:
            logger.warning("[OddsFetcher] 401 — Odds API quota maxed")
            return []
        if resp.status_code != 200:
            logger.warning(f"[OddsFetcher] {resp.status_code}")
            return []
        data = resp.json()
        with open(cache_file, "w") as f:
            json.dump(data, f)
        return data
    except Exception as e:
        logger.error(f"[OddsFetcher] Error: {e}")
        return []

def estimate_edge(projection, current_line):
    if not current_line or current_line == 0:
        return 0, 0
    diff = projection - current_line
    edge_pct = round((diff / abs(current_line)) * 100, 1)
    return diff, edge_pct

def get_odds(sport="basketball_wnba", market="h2h", region="us"):
    return fetch_bookmaker_odds(sport, market=market, regions=region)

def get_player_props(sport="basketball_wnba", player_name=""):
    return []

def format_pick(player, stat, direction, line, projection, edge, book="DK"):
    return {
        "player": player, "stat": stat, "direction": direction,
        "line": line, "projection": projection, "edge": edge,
        "bookmaker": book,
        "display": f"{player} {direction} {line} {stat} (Edge: {edge}%)"
    }

def calculate_edge(projection, market_line):
    diff, pct = estimate_edge(projection, market_line)
    return {"diff": diff, "edge_pct": pct}
