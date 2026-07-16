"""SportsGameOdds NBA Adapter."""
from typing import Optional
from .base import SGOBase


class NBAAdapter(SGOBase):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, sport="NBA")

    def get_player_props(self, event_id: str):
        return super().get_player_props(event_id)
