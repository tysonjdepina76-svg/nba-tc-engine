#!/usr/bin/env python3
"""TheOddsAPI Adapter — Player Props + Game Lines for TC Pipeline"""
import os, time, json, logging
from typing import Optional, Dict, List, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError

logger = logging.getLogger(__name__)

TOA_KEY = os.environ.get("TOA_API_KEY", "toa_live_t5d8p3n1")
TOA_BASE = "https://api.theoddsapi.com"

STAT_TO_MARKET = {
    "H": "batter_hits",
    "HR": "batter_home_runs", 
    "RBI": "batter_rbis",
    "R": "batter_runs_scored",
    "2B": "batter_total_bases",
    "3B": "batter_total_bases",
    "SB": "batter_total_bases",
    "BB": None,
    "PTS": "player_points",
    "REB": "player_rebounds",
    "AST": "player_assists",
}

class TOAAdapter:
    def __init__(self, sport="baseball_mlb"):
        self.sport = sport
        self.cache = {}
        self.calls = 0
    
    def _fetch(self, path, params=None):
        url = f"{TOA_BASE}{path}"
        if '?' not in path:
            url += '?'
        else:
            url += '&'
        url += f"apikey={TOA_KEY}"
        if params:
            for k,v in params.items():
                if v:
                    url += f"&{k}={v}"
        
        req = Request(url)
        req.add_header("x-api-key", TOA_KEY)
        self.calls += 1
        
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            logger.warning(f"TOA {e.code}: {url[:80]}")
            return None
    
    def get_props(self, markets=None):
        if not markets:
            markets = "batter_hits,batter_home_runs,batter_rbis,batter_runs_scored"
        
        path = f"/props/?sport_key={self.sport}&regions=us&markets={markets}"
        return self._fetch(path)
    
    def get_odds(self, markets="h2h,totals,spreads"):
        path = f"/odds/?sport_key={self.sport}&regions=us&markets={markets}"
        return self._fetch(path)
    
    def build_line_lookup(self) -> Dict[str, Dict[str, float]]:
        raw = self.get_props()
        if not raw or not raw.get("data"):
            return {}
        
        lookup = {}
        for event in raw["data"]:
            matchup = f"{event['away_team']} @ {event['home_team']}"
            for prop in event.get("props", []):
                market = prop["market"]
                for book in prop.get("books", []):
                    for outcome in book.get("outcomes", []):
                        player = outcome["description"]
                        point = outcome.get("point")
                        name = outcome.get("name")
                        if player and point is not None and name:
                            key = f"{matchup}|{player}|{market}|{name}"
                            if key not in lookup:
                                lookup[key] = []
                            lookup[key].append({
                                "book": book["book"],
                                "line": point,
                                "price": outcome.get("price"),
                                "updated": book.get("updated_at", "")
                            })
        
        return lookup
    
    def get_player_line(self, player, stat, matchup, direction="OVER", books=None):
        """Get consensus line for a player/stat/direction combo"""
        market = STAT_TO_MARKET.get(stat)
        if not market:
            return None
        
        lookup = self.build_line_lookup()
        key_prefix = f"{matchup}|{player}|{market}|"
        
        matches = {}
        for key, outcomes in lookup.items():
            if key.startswith(key_prefix):
                for o in outcomes:
                    if books and o["book"] not in books:
                        continue
                    b = o["book"]
                    if b not in matches:
                        matches[b] = o
        
        if not matches:
            return None
        
        lines = [m["line"] for m in matches.values()]
        from statistics import median
        return median(lines)


_SINGLETON = None
def get_toa() -> TOAAdapter:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = TOAAdapter()
    return _SINGLETON
