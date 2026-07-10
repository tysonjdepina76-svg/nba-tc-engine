"""SportsGameOdds WNBA Adapter."""
from typing import Optional
from .base import SGOBase


class WNBAAdapter(SGOBase):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, sport="WNBA")

    def get_player_props(self, event_id: str):
        return super().get_player_props(event_id)

    def get_game_lines(self, event_id: str):
        return self.get_lines(event_id, market="game_lines")
