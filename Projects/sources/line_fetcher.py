"""
Central line fetcher — dispatches to per-sport fetchers.

Sport → fetcher mapping:
- mlb     → mlb_book_fetcher.fetch_mlb_book_lines
- wnba    → wnba_data_fetcher.fetch_wnba_lines
- soccer  → soccer_lines_fetcher.fetch_soccer_lines
- worldcup → soccer_lines_fetcher.fetch_soccer_lines (alias)
- nba     → espn_odds_fetcher (off-season aware)
- nfl     → espn_odds_fetcher (off-season aware)
- nhl     → espn_odds_fetcher (off-season aware)
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


SPORT_FETCHERS: Dict[str, str] = {
    "mlb": "sources.mlb_book_fetcher:fetch_mlb_book_lines",
    "wnba": "sources.wnba_data_fetcher:fetch_wnba_lines",
    "soccer": "sources.soccer_lines_fetcher:fetch_soccer_lines",
    "worldcup": "sources.soccer_lines_fetcher:fetch_soccer_lines",
}

OFF_SEASON_SPORTS = {"nba", "nfl", "nhl", "ncaa"}


class LineFetchError(Exception):
    pass


def _import_fetcher(path: str):
    """Import a fetcher function from 'module:function' path."""
    module_name, func_name = path.split(":")
    import importlib
    try:
        mod = importlib.import_module(module_name)
    except ImportError as e:
        raise LineFetchError(f"module {module_name} not importable: {e}")
    fn = getattr(mod, func_name, None)
    if fn is None:
        raise LineFetchError(f"function {func_name} not found in {module_name}")
    return fn


def _is_in_season(sport: str) -> bool:
    """Return True if sport is currently in season. Off-season sports return False."""
    if sport not in OFF_SEASON_SPORTS:
        return True
    from sources.sports_registry import REGISTRY
    cfg = REGISTRY.get(sport) if hasattr(REGISTRY, "get") else None
    if cfg is None:
        return True
    enabled = getattr(cfg, "enabled", True)
    if not enabled:
        return False
    return True


def fetch_lines(sport: str,
                matchup: Optional[str] = None,
                date: Optional[str] = None,
                dry_run: bool = False,
                **_extra: Any) -> Dict[str, Any]:
    """
    Fetch lines for a sport. Returns dict with at least:
    {source, sport, timestamp, games, players/odds, error?}

    Args:
        sport: mlb, wnba, soccer, worldcup, nba, nfl, nhl, ncaa
        matchup: optional 'AWAY@HOME' filter
        date: optional YYYY-MM-DD
        dry_run: bypass cache + network
    """
    sport = sport.lower().strip()
    ts = datetime.now().isoformat()
    base = {"source": "line_fetcher", "sport": sport, "timestamp": ts,
            "games": [], "players": [], "odds": []}

    if not sport:
        base["error"] = "sport required"
        return base

    if sport in OFF_SEASON_SPORTS and not _is_in_season(sport):
        base["status"] = "off_season"
        log.info("line_fetcher: %s off-season, skipping", sport)
        return base

    fetcher_path = SPORT_FETCHERS.get(sport)
    if not fetcher_path:
        try:
            from sources.espn_odds_fetcher import fetch_espn_odds
            result = fetch_espn_odds(sport=sport, date=date)
            base["source"] = "espn_odds_fetcher"
            base["odds"] = result.get("odds", [])
            base["games"] = result.get("games", [])
            return base
        except Exception as e:
            base["error"] = f"no fetcher registered for sport={sport}: {e}"
            return base

    try:
        fn = _import_fetcher(fetcher_path)
    except LineFetchError as e:
        base["error"] = str(e)
        return base

    try:
        if sport == "mlb":
            result = fn(matchup=matchup, dry_run=dry_run)
        elif sport == "wnba":
            result = fn(matchup=matchup, dry_run=dry_run)
        elif sport in ("soccer", "worldcup"):
            result = fn(date=date)
        else:
            result = fn()
    except TypeError as e:
        try:
            result = fn()
        except Exception as e2:
            base["error"] = f"fetcher {fetcher_path} failed: {e2}"
            return base
    except Exception as e:
        log.warning("line_fetcher: %s failed: %s", sport, e)
        base["error"] = str(e)
        return base

    if not isinstance(result, dict):
        result = {"raw": result}
    base.update({k: v for k, v in result.items() if k not in base})
    return base


def list_sports() -> list:
    """Return all sports this fetcher can route."""
    return list(SPORT_FETCHERS.keys()) + list(OFF_SEASON_SPORTS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("=== Supported sports ===")
    print(list_sports())
    print()
    for s in ("wnba", "mlb", "worldcup"):
        print(f"=== {s} ===")
        r = fetch_lines(s)
        print(f"  source={r.get('source')} status={r.get('status', 'ok')} "
              f"error={r.get('error', 'none')}")
