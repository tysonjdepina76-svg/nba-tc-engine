"""Public scrapers for sports lines and stats.

Tier 2 fallback after SportsData.io + Odds API:
  - DraftKingsWebScraper  (sportsbook.draftkings.com lines)
  - BaseballReferenceScraper  (batting/pitching leaderboards)
  - BasketballReferenceScraper (WNBA per-game stats)
  - FanGraphsScraper  (advanced stats)
"""
import os
import sys

_THIS = os.path.abspath(__file__)
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS)))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

from .baseball_reference import BaseballReferenceScraper, clean_name
from .basketball_reference import BasketballReferenceScraper
from .draftkings_web import DraftKingsWebScraper
from .fangraphs import FanGraphsScraper

__all__ = [
    "DraftKingsWebScraper",
    "BaseballReferenceScraper",
    "BasketballReferenceScraper",
    "FanGraphsScraper",
    "clean_name",
]
