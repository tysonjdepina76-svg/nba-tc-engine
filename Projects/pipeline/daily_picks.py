"""
Daily pick generation with edge calculation.
"""

from datetime import datetime
import pandas as pd
from sources.sports_registry import REGISTRY
from sources.line_fetcher import fetch_lines
from sources.utils.logging import get_logger

logger = get_logger(__name__)

def compute_edge(projection: float, line: float) -> float:
    """Compute edge as projection minus line."""
    if line is None or projection is None:
        return 0.0
    try:
        return float(projection) - float(line)
    except (ValueError, TypeError):
        return 0.0

def add_edge_to_picks(picks: list) -> list:
    """Add edge to each pick."""
    for pick in picks:
        pick["edge"] = compute_edge(
            pick.get("projection", 0),
            pick.get("line", 0)
        )
    return picks

def generate_daily_picks(sport: str) -> dict:
    """Generate daily picks for a sport."""
    config = REGISTRY.get(sport)
    if not config.enabled:
        return {"error": f"{sport} is disabled"}

    logger.info(f"Generating picks for {sport}")

    if config.source.value == "tc_engine":
        from sources.wnba_tc_engine import project_game
        data = project_game()
    else:
        data = config.fetcher()

    lines = fetch_lines(sport)

    if data and lines:
        logger.info(f"Processing {sport}: {len(data.get('players', []))} players, {len(lines.get('games', []))} games")

    result = {
        "sport": sport,
        "timestamp": datetime.now().isoformat(),
        "picks": [],
        "count": 0
    }
    return result
