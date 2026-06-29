"""Adapter registry. Each adapter fetches + parses data into domain entities.

Adapters NEVER compute math. They only return Player/Game objects.
"""
from .espn import ESPNAdapter
from .sgo import SGOAdapter
from .odds_api import OddsAPIAdapter

__all__ = ["ESPNAdapter", "SGO