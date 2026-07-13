"""
NHL TC Engine - Hockey projections (off-season placeholder).
"""

import random
from datetime import datetime
from typing import Dict, Optional

NHL_PLAYER_DATA = [
    {"name": "Connor McDavid", "team": "EDM", "goals": 1.2, "assists": 1.8, "points": 3.0, "sog": 4.5, "pim": 0.5},
    {"name": "Nathan MacKinnon", "team": "COL", "goals": 1.0, "assists": 1.5, "points": 2.5, "sog": 4.2, "pim": 0.4},
    {"name": "Auston Matthews", "team": "TOR", "goals": 1.3, "assists": 0.9, "points": 2.2, "sog": 4.8, "pim": 0.3},
]

def project_nhl_game(matchup: Optional[str] = None) -> Dict:
    players = []
    for p in NHL_PLAYER_DATA:
        player = p.copy()
        variance = 0.85 + random.random() * 0.3
        player["projection"] = round(player["points"] * variance, 1)
        players.append(player)
    return {
        "source": "NHL TC Engine",
        "timestamp": datetime.now().isoformat(),
        "players": players,
        "count": len(players)
    }
