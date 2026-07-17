from datetime import datetime
from typing import Dict, List

class NFLRaptorEngine:
    def __init__(self):
        self.player_stats = {
            "Patrick Mahomes": {"pass_yds": 280, "td": 2.5, "int": 0.5},
            "Josh Allen": {"pass_yds": 260, "td": 2.3, "int": 0.6},
            "Lamar Jackson": {"pass_yds": 220, "td": 1.8, "int": 0.7, "rush_yds": 60},
        }
        self.team_ratings = {
            "KC": {"defense": 85},
            "BUF": {"defense": 88},
            "BAL": {"defense": 90},
        }

    def project_player(self, player_name: str, opponent: str) -> Dict:
        player = self.player_stats.get(player_name, {})
        defense_factor = self.team_ratings.get(opponent, {"defense": 80})["defense"] / 100
        pass_yds = player.get("pass_yds", 0) * (1.1 - defense_factor * 0.2)
        return {
            "player": player_name,
            "opponent": opponent,
            "projected_yards": round(pass_yds, 0),
            "projected_td": round(player.get("td", 0) * (1.1 - defense_factor * 0.15), 1),
            "timestamp": datetime.now().isoformat()
        }

    def project_game(self, home: str, away: str) -> Dict:
        home_players = [self.project_player(p, away) for p in self.player_stats.keys()]
        return {"home": home, "away": away, "home_players": home_players}

def project_nfl_game(home: str, away: str) -> Dict:
    return NFLRaptorEngine().project_game(home, away)
