import random
from datetime import datetime
from typing import Dict, List, Optional

NHL_PLAYER_DATA = [
    {"name": "Connor McDavid", "team": "EDM", "goals": 1.2, "assists": 1.8, "points": 3.0},
    {"name": "Nathan MacKinnon", "team": "COL", "goals": 1.0, "assists": 1.5, "points": 2.5},
]

def project_nhl_game(matchup: Optional[str] = None) -> Dict:
    players = []
    for p in NHL_PLAYER_DATA:
        player = p.copy()
        variance = 0.85 + random.random() * 0.3
        player["projection"] = round(player["points"] * variance, 1)
        players.append(player)
    return {"source": "NHL TC Engine", "players": players, "count": len(players)}
