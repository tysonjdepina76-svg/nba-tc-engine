"""SportsGameOdds MLB Adapter."""
from typing import Optional
from .base import SGOBase


class MLBAdapter(SGOBase):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, sport="MLB")

    def get_pitcher_lines(self, event_id: str):
        return self.get_lines(event_id, market="pitcher_props")

    def get_batter_props(self, event_id: str):
        return self.get_player_props(event_id)
