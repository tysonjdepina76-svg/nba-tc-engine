"""SportsGameOdds NHL Adapter."""
from typing import Optional
from .base import SGOBase


class NHLAdapter(SGOBase):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, sport="NHL")

    def get_goalie_props(self, event_id: str):
        return self.get_lines(event_id, market="goalie_props")
