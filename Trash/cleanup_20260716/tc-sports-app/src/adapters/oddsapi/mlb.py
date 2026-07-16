"""TheOddsAPI MLB Adapter."""

from typing import List, Dict, Optional
from .base import OddsAPIBase


class MLBOddsAdapter(OddsAPIBase):
    """MLB data adapter for TheOddsAPI."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("mlb", api_key)

    def get_events(self) -> List[Dict]:
        return self.fetch_events()

    def get_odds(self) -> List[Dict]:
        return self.fetch_odds()

    def get_player_props(self, event_id: str = None) -> List[Dict]:
        markets = "pitcher_strikeouts,batter_hits,batter_home_runs,batter_rbis,batter_runs,batter_total_bases,batter_stolen_bases"
        if event_id:
            return self.fetch_event_odds(event_id, markets)
        return self.fetch_odds(markets)
