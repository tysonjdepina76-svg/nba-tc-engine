"""SportsGameOdds NFL Adapter."""
from typing import Optional
from .base import SGOBase


class NFLAdapter(SGOBase):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, sport="NFL")

    def get_passing_props(self, event_id: str):
        return self.get_lines(event_id, market="passing_props")

    def get_rushing_props(self, event_id: str):
        return self.get_lines(event_id, market="rushing_props")

    def get_receiving_props(self, event_id: str):
        return self.get_lines(event_id, market="receiving_props")
