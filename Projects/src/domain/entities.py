"""
Domain entities and registry for TC Sports App.
"""

import sys
from pathlib import Path
_PROJECTS = Path("/home/workspace/Projects")
if str(_PROJECTS) not in sys.path:
    sys.path.insert(0, str(_PROJECTS))

from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any


class DataSource(Enum):
    TC_ENGINE = "tc_engine"
    BOOK_LINES = "book_lines"
    STATIC = "static"
    COMING_SOON = "coming_soon"


@dataclass
class SportConfig:
    """Configuration for a sport."""
    name: str
    source: DataSource
    module: Optional[str] = None
    fetcher: Optional[Callable] = None
    line_fetcher: Optional[Callable] = None
    enabled: bool = True
    error_msg: Optional[str] = None
    display_name: str = ""
    schema: Optional[Dict] = field(default_factory=dict)


class Registry:
    """Single source of truth for all sports."""

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
        self._predictor = None
        self._register_all()

    def _register_all(self):
        """Register all sports."""
        self._registry["mlb"] = SportConfig(
            name="mlb",
            display_name="MLB Baseball",
            source=DataSource.BOOK_LINES,
            module="mlb_fetcher",
            fetcher=self._lazy_fetcher("sources.mlb_fetcher", "get_mlb_projections"),
            line_fetcher=self._lazy_fetcher("sources.mlb_book_fetcher", "fetch_mlb_book_lines"),
            enabled=True,
            schema={
                "stat_labels": ["avg", "hr", "rbi", "r", "sb", "ops", "era", "whip", "so"],
                "aliases": {"avg": "AVG", "hr": "HR", "rbi": "RBI", "r": "R", "sb": "SB", "ops": "OPS", "era": "ERA", "whip": "WHIP", "so": "SO"},
                "color": "#003278"
            }
        )
        self._registry["wnba"] = SportConfig(
            name="wnba",
            display_name="WNBA Basketball",
            source=DataSource.TC_ENGINE,
            module="wnba_tc_engine",
            fetcher=self._lazy_fetcher("sources.wnba_data_fetcher", "load_cached_wnba"),
            line_fetcher=self._lazy_fetcher("sources.wnba_lines_fetcher", "fetch_wnba_lines"),
            enabled=True,
            schema={
                "stat_labels": ["pts", "reb", "ast", "fg_pct", "fg3", "stl", "blk"],
                "aliases": {"pts": "PTS", "reb": "REB", "ast": "AST", "fg_pct": "FG%", "fg3": "3PM", "stl": "STL", "blk": "BLK"},
                "color": "#FFC72C"
            }
        )
        self._registry["wc"] = SportConfig(
            name="wc",
            display_name="World Cup Soccer",
            source=DataSource.BOOK_LINES,
            module="soccer_tc_engine",
            fetcher=self._lazy_fetcher("sources.soccer_lines_fetcher", "fetch_soccer_lines"),
            enabled=True,
            schema={
                "stat_labels": ["goals", "assists", "shots", "shots_on_target", "pass_pct", "tackles", "fouls"],
                "aliases": {"goals": "Goals", "assists": "Assists", "shots": "Shots", "shots_on_target": "SOT", "pass_pct": "Pass%", "tackles": "Tackles", "fouls": "Fouls"},
                "color": "#1A1A2E"
            }
        )
        self._registry["nfl"] = SportConfig(name="nfl", display_name="NFL Football", source=DataSource.COMING_SOON, enabled=False, error_msg="NFL off-season")
        self._registry["nhl"] = SportConfig(name="nhl", display_name="NHL Hockey", source=DataSource.COMING_SOON, enabled=False, error_msg="NHL off-season")
        self._registry["nba"] = SportConfig(name="nba", display_name="NBA Basketball", source=DataSource.COMING_SOON, enabled=False, error_msg="NBA off-season")

    def _lazy_fetcher(self, module_path: str, func_name: str):
        """Return a callable that imports `module_path` and calls `func_name` at call time."""
        def _call(*args, **kwargs):
            import importlib
            mod = importlib.import_module(module_path)
            return getattr(mod, func_name)(*args, **kwargs)
        return _call

    def get(self, sport: str) -> Optional[SportConfig]:
        sport_lower = sport.lower()
        if sport_lower in self._registry:
            return self._registry[sport_lower]
        if sport_lower == "soccer":
            return self._registry.get("wc")
        return None

    def list_enabled(self) -> Dict[str, SportConfig]:
        return {k: v for k, v in self._registry.items() if v.enabled}

    def get_predictor(self):
        """Get or create hybrid WNBA predictor."""
        if self._predictor is not None:
            return self._predictor
        try:
            from src.predictors import HybridWNBAPropPredictor
            class _MockEngine:
                def predict(self, player, features, target="pts"):
                    return 15.0
            self._predictor = HybridWNBAPropPredictor(tc_engine=_MockEngine())
        except Exception as e:
            print(f"Predictor init failed: {e}")
            return None
        return self._predictor


REGISTRY = Registry()