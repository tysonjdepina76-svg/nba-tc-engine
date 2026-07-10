"""SportsGameOdds Adapters — MLB, WNBA, NFL, NBA, NHL."""
from .base import SGOBase
from .mlb import MLBAdapter
from .wnba import WNBAAdapter
from .nfl import NFLAdapter
from .nba import NBAAdapter
from .nhl import NHLAdapter

__all__ = ["SGOBase", "MLBAdapter", "WNBAAdapter", "NFLAdapter", "NBAAdapter", "NHLAdapter"]
