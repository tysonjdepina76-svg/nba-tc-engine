"""Adapter registry — exposes DK, FD, ESPN, OddsAPI, SGO uniformly."""
from .draftkings import DraftKingsAdapter
from .fanduel import FanDuelAdapter
from .espn import ESPNAdapter
from .odds_api import OddsAPIAdapter
from .sgo import SGOAdapter

ADAPTERS = {
    "draftkings": DraftKingsAdapter,
    "dk": DraftKingsAdapter,
    "fanduel": FanDuelAdapter,
    "fd": FanDuelAdapter,
    "espn": ESPNAdapter,
    "odds_api": OddsAPIAdapter,
    "sgo": SGOAdapter,
}


def get_adapter(name: str):
    """Return an instantiated adapter by name (case-insensitive)."""
    if not name:
        raise ValueError("adapter name required")
    key = name.lower().strip()
    if key not in ADAPTERS:
        raise KeyError(f"unknown adapter: {name}. known: {sorted(ADAPTERS)}")
    return ADAPTERS[key]()


__all__ = [
    "DraftKingsAdapter",
    "FanDuelAdapter",
    "ESPNAdapter",
    "OddsAPIAdapter",
    "SGOAdapter",
    "get_adapter",
    "ADAPTERS",
]