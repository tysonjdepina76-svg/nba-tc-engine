"""TheOddsAPI Adapters — WNBA, NFL, MLB, NBA, NHL."""

from .wnba import WNBAOddsAdapter
from .nfl import NFLOddsAdapter
from .mlb import MLBOddsAdapter
from .nba import NBAOddsAdapter
from .nhl import NHLOddsAdapter
from .base import OddsAPIMonitor

__all__ = [
    "WNBAOddsAdapter",
    "NFLOddsAdapter",
    "MLBOddsAdapter",
    "NBAOddsAdapter",
    "NHLOddsAdapter",
    "OddsAPIMonitor",
]
