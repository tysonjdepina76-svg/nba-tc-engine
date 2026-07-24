"""Minimal ESPN adapter — delegates to actual implementations.
Restored after cleanup removed the original file.
"""
import json
from datetime import date
from typing import Dict, List, Optional

from .espn_odds_fetcher import fetch_scoreboard as _fetch_scoreboard
from .wnba_data_fetcher import fetch_roster as _fetch_roster_wnba

TODAY = date.today().isoformat()


def fetch_scoreboard(sport_path: str) -> Dict:
    """Old-style: 'baseball/mlb', 'basketball/wnba', 'soccer/fifa.world'."""
    parts = sport_path.split("/")
    if len(parts) == 2:
        sport, league = parts
        return _fetch_scoreboard(sport, league, TODAY)
    return {"events": []}


def fetch_roster(team_id: int) -> Dict:
    """Fetch roster for a team. Falls back to WNBA fetcher."""
    return _fetch_roster_wnba(team_id)


def fetch_summary(game_id: str, sport_path: str = "") -> Dict:
    """Fetch game summary from ESPN."""
    import urllib.request
    try:
        url = f"https://sports.core.api.espn.com/v2/sports/basketball/wnba/summaries?event={game_id}"
        with urllib.request.urlopen(url, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return {}
