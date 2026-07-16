"""SportsDataIO Adapters — WNBA, NFL, MLB (and aliases for back-compat)."""

from .wnba import WNBAAdapter, WNBAData
from .nfl import NFLAdapter, NFLData
from .mlb import MLBAdapter, MLBData

__all__ = [
    "WNBAAdapter", "WNBAData",
    "NFLAdapter", "NFLData",
    "MLBAdapter", "MLBData",
]
