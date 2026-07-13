"""
NCAA TC Engine - College basketball projections.
"""

import random
from datetime import datetime
from typing import Optional, Dict

NCAA_PLAYER_DATA = [
    {"name": "Cooper Flagg", "team": "DUKE", "pts": 22.5, "reb": 8.7, "ast": 4.2},
    {"name": "Zach Edey", "team": "PUR", "pts": 24.5, "reb": 12.2, "ast": 2.1},
]

def project_ncaa_game(matchup: Optional[str] = None) -> Dict:
    players = []
    for p in NCAA_PLAYER_DATA:
        player = p.copy()
        variance = 0.85 + random.random() * 0.3
        player["projection"] = round(player["pts"] * variance, 1)
        players.append(player)
    return {
        "source": "NCAA TC Engine",
        "timestamp": datetime.now().isoformat(),
        "players": players,
        "count": len(players)
    }
