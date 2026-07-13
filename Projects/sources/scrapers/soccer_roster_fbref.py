"""
FBref scraper for World Cup rosters.
"""

import requests
import pandas as pd
from sources.utils.cache import cache_fetch
from sources.utils.logging import get_logger

logger = get_logger(__name__)

def fetch_wc_rosters():
    """Fetch World Cup rosters from FBref."""
    url = "https://fbref.com/en/comps/1/2026/2026-World-Cup-Squads"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        tables = pd.read_html(resp.text)
    except Exception as e:
        logger.error(f"FBref fetch failed: {e}")
        return {"error": str(e)}
    rosters = {}
    for table in tables:
        if "Player" in table.columns and "Squad" in table.columns:
            team = table["Squad"].iloc[0]
            players = []
            for _, row in table.iterrows():
                players.append({
                    "name": row.get("Player", "").strip(),
                    "position": row.get("Pos", ""),
                    "number": str(row.get("No.", "")) if row.get("No.") else "",
                    "age": row.get("Age", "")
                })
            rosters[team] = players
    return rosters

def fetch_team_roster(team_name):
    """Fetch roster for a specific team."""
    all_rosters = cache_fetch("wc_rosters_fbref", fetch_wc_rosters, ttl_hours=24)
    if "error" in all_rosters:
        return []
    if team_name in all_rosters:
        return all_rosters[team_name]
    for key in all_rosters:
        if key.lower() == team_name.lower():
            return all_rosters[key]
    return []
