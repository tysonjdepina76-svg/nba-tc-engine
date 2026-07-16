"""TheOddsAPI NBA Adapter."""

from typing import List, Dict, Optional
from .base import OddsAPIBase


class NBAOddsAdapter(OddsAPIBase):
    """NBA data adapter for TheOddsAPI."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("nba", api_key)

    def get_events(self) -> List[Dict]:
        return self.fetch_events()

    def get_odds(self) -> List[Dict]:
        return self.fetch_odds()

    def get_player_props(self, event_id: str = None) -> List[Dict]:
        markets = "player_points,player_rebounds,player_assists,player_threes,player_blocks,player_steals"
        if event_id:
            return self.fetch_event_odds(event_id, markets)
        return self.fetch_odds(markets)
