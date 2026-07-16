"""TheOddsAPI NHL Adapter."""

from typing import List, Dict, Optional
from .base import OddsAPIBase


class NHLOddsAdapter(OddsAPIBase):
    """NHL data adapter for TheOddsAPI."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("nhl", api_key)

    def get_events(self) -> List[Dict]:
        return self.fetch_events()

    def get_odds(self) -> List[Dict]:
        return self.fetch_odds()

    def get_player_props(self, event_id: str = None) -> List[Dict]:
        markets = "player_points,player_shots,player_shots_on_goal,player_goals,player_assists,player_power_play_points,player_blocked_shots"
        if event_id:
            return self.fetch_event_odds(event_id, markets)
        return self.fetch_odds(markets)
