"""TheOddsAPI NFL Adapter."""

from typing import List, Dict, Optional
from .base import OddsAPIBase


class NFLOddsAdapter(OddsAPIBase):
    """NFL data adapter for TheOddsAPI."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("nfl", api_key)

    def get_events(self) -> List[Dict]:
        return self.fetch_events()

    def get_odds(self) -> List[Dict]:
        return self.fetch_odds()

    def get_player_props(self, event_id: str = None) -> List[Dict]:
        markets = "player_pass_yds,player_pass_tds,player_rush_yds,player_receptions,player_reception_yds,player_anytime_td"
        if event_id:
            return self.fetch_event_odds(event_id, markets)
        return self.fetch_odds(markets)
