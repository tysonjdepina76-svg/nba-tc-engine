"""
Soccer TC Engine - Generates World Cup player projections.
"""

import random
from datetime import datetime
from typing import Dict, List, Optional, Any

from sources.scrapers.soccer_roster_fbref import fetch_team_roster
from sources.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_PROJECTIONS = {
    "goals": 0.5,
    "assists": 0.3,
    "shots": 2.0,
    "shots_on_target": 1.0,
    "pass_pct": 75.0,
    "tackles": 1.5,
    "fouls": 1.0
}

def generate_player_projections(team: str, matchup: Optional[str] = None) -> List[Dict]:
    players = fetch_team_roster(team)
    if not players:
        logger.warning(f"No roster found for {team}")
        return []
    projected = []
    for p in players:
        player = p.copy()
        variance = 0.7 + random.random() * 0.6
        for stat, default_val in DEFAULT_PROJECTIONS.items():
            player[stat] = round(default_val * variance, 1)
        player["edge"] = round(random.uniform(-1.0, 1.0), 1)
        if player["edge"] > 0.3:
            player["signal"] = "OVER"
        elif player["edge"] < -0.3:
            player["signal"] = "UNDER"
        else:
            player["signal"] = "PUSH"
        projected.append(player)
    return projected

def project_matchup(home_team: str, away_team: str) -> Dict[str, Any]:
    home_players = generate_player_projections(home_team)
    away_players = generate_player_projections(away_team)
    return {
        "source": "TC Engine",
        "timestamp": datetime.now().isoformat(),
        "home": home_team,
        "away": away_team,
        "home_players": home_players,
        "away_players": away_players,
        "total_players": len(home_players) + len(away_players)
    }
