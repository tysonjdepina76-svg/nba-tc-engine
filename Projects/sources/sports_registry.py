"""
Single source of truth for all sports.
"""

from enum import Enum
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass

class DataSource(Enum):
    TC_ENGINE = "tc_engine"
    BOOK_LINES = "book_lines"
    STATIC = "static"
    COMING_SOON = "coming_soon"

@dataclass
class SportConfig:
    name: str
    source: DataSource
    module: Optional[str] = None
    fetcher: Optional[Callable] = None
    line_fetcher: Optional[Callable] = None
    enabled: bool = True
    error_msg: Optional[str] = None
    display_name: str = ""
    schema: Optional[Dict] = None

class SportsRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._registry: Dict[str, SportConfig] = {}
        self._register_all()

    def _register_all(self):
        def stub_fetcher():
            return {"source": "stub", "players": []}
        def stub_lines():
            return {"source": "stub", "games": []}

        self._registry["mlb"] = SportConfig(
            name="mlb", display_name="MLB Baseball",
            source=DataSource.BOOK_LINES, module=None,
            fetcher=stub_fetcher, line_fetcher=stub_lines, enabled=True,
            schema={"stat_labels": ["AVG", "HR", "RBI", "R", "SB", "OPS", "ERA", "WHIP", "SO"], "color": "#003278"}
        )
        self._registry["wnba"] = SportConfig(
            name="wnba", display_name="WNBA Basketball",
            source=DataSource.TC_ENGINE, module="wnba_tc_engine",
            fetcher=None, line_fetcher=stub_lines, enabled=True,
            schema={"stat_labels": ["PTS", "REB", "AST", "FG%", "3PM", "STL", "BLK"], "color": "#FFC72C"}
        )
        self._registry["wc"] = SportConfig(
            name="wc", display_name="World Cup Soccer",
            source=DataSource.BOOK_LINES, module=None,
            fetcher=stub_fetcher, line_fetcher=stub_lines, enabled=True,
            schema={"stat_labels": ["Goals", "Assists", "Shots", "SOT", "Pass%", "Tackles", "Fouls"], "color": "#1A1A2E"}
        )
        self._registry["soccer"] = self._registry["wc"]
        self._registry["nba"] = SportConfig(name="nba", display_name="NBA Basketball", source=DataSource.COMING_SOON, enabled=False, error_msg="NBA off-season")
        self._registry["nfl"] = SportConfig(name="nfl", display_name="NFL Football", source=DataSource.COMING_SOON, enabled=False, error_msg="NFL off-season")
        self._registry["nhl"] = SportConfig(name="nhl", display_name="NHL Hockey", source=DataSource.COMING_SOON, enabled=False, error_msg="NHL off-season")

    def get(self, sport: str) -> SportConfig:
        sport_lower = sport.lower()
        if sport_lower in self._registry:
            return self._registry[sport_lower]
        if sport_lower == "soccer":
            return self._registry["wc"]
        return SportConfig(name=sport, display_name=sport.upper(), source=DataSource.STATIC, enabled=False, error_msg=f"Unknown sport: {sport}")

    def get_schema(self, sport: str) -> Dict:
        return self.get(sport).schema or {}

    def list_enabled(self) -> Dict[str, SportConfig]:
        return {k: v for k, v in self._registry.items() if v.enabled}

REGISTRY = SportsRegistry()
