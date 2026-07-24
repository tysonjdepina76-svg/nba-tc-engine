"""
DK LIVE ODDS ADAPTER
Primary: theOddsAPI (THEODDSAPI_KEY in secrets) — DK + FD comparison
Fallback: direct DK sportsbook endpoint (may require session/proxy)
"""

import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("dk_live")

DB_PATH = Path("/home/workspace/Projects/data/picks.db")
SPORT_KEYS = {"mlb": "baseball_mlb", "wnba": "basketball_wnba", "nfl": "americanfootball_nfl"}


def fetch_live_comparison(sport: str) -> Dict[str, Any]:
    """
    Fetch DK + FD live odds comparison using theOddsAPI.
    Returns {comparisons: [...], timestamp: ISO, sport: str}
    """
    try:
        from src.adapters.theoddsapi_adapter import fetch_live_odds
        raw = fetch_live_odds(sport, bookmakers="draftkings,fanduel")
    except Exception:
        raw = {"error": "adapter not available", "games": []}

    if raw.get("error"):
        logger.warning(f"theOddsAPI failed for {sport}: {raw['error']}")
        return {"comparisons": [], "timestamp": datetime.utcnow().isoformat(), "sport": sport, "source": "none"}

    comparisons = []
    for game in raw.get("games", []):
        dk_spread = None
        dk_total = None
        fd_spread = None
        fd_total = None

        for book_key, markets in game.get("books", {}).items():
            if book_key == "draftkings":
                dk_spread = _extract_line(markets, "spreads")
                dk_total = _extract_line(markets, "totals")
            elif book_key == "fanduel":
                fd_spread = _extract_line(markets, "spreads")
                fd_total = _extract_line(markets, "totals")

        comparisons.append({
            "home": game.get("home_team", ""),
            "away": game.get("away_team", ""),
            "start": game.get("start_time", ""),
            "dk_spread": dk_spread,
            "dk_total": dk_total,
            "fd_spread": fd_spread,
            "fd_total": fd_total,
        })

    return {
        "comparisons": comparisons,
        "timestamp": datetime.utcnow().isoformat(),
        "sport": sport,
        "source": "theoddsapi",
    }


def _extract_line(markets: Dict, market_type: str) -> Optional[Dict]:
    """Extract the best line from a market's outcomes."""
    if market_type not in markets:
        return None
    outcomes = markets[market_type]
    if not outcomes:
        return None
    best = outcomes[0]
    return {"line": best.get("line"), "odds": best.get("odds"), "side": best.get("side", "")}


def update_db_with_live_odds(sport: str = "wnba"):
    """
    Pull live odds and update picks.db with current market lines.
    Adds dk_line, fd_line, odds_updated columns to the picks table if needed.
    """
    data = fetch_live_comparison(sport)
    comparisons = data.get("comparisons", [])
    if not comparisons:
        logger.info(f"No live odds comparisons for {sport}")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(picks)")
    columns = [row[1] for row in cursor.fetchall()]

    if "dk_line" not in columns:
        cursor.execute("ALTER TABLE picks ADD COLUMN dk_line REAL DEFAULT NULL")
    if "fd_line" not in columns:
        cursor.execute("ALTER TABLE picks ADD COLUMN fd_line REAL DEFAULT NULL")
    if "odds_updated" not in columns:
        cursor.execute("ALTER TABLE picks ADD COLUMN odds_updated TEXT DEFAULT NULL")

    updated = 0
    now = datetime.utcnow().isoformat()
    for comp in comparisons:
        home = comp.get("home", "")
        away = comp.get("away", "")
        dk = comp.get("dk_spread", {}) or {}
        fd = comp.get("fd_spread", {}) or {}
        dk_line = dk.get("line")
        fd_line = fd.get("line")

        cursor.execute(
            "UPDATE picks SET dk_line = ?, fd_line = ?, odds_updated = ? WHERE matchup LIKE ? AND matchup LIKE ?",
            (dk_line, fd_line, now, f"%{home}%", f"%{away}%"),
        )
        updated += cursor.rowcount

    conn.commit()
    conn.close()
    logger.info(f"Updated {updated} picks with live odds for {sport}")
    return updated
