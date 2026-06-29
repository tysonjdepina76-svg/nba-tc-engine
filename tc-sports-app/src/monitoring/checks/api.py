"""
API health checks — ESPN, Odds API, DK/FD.
"""

import os
import requests
from pathlib import Path
from typing import Dict

# Auto-load ODDS_API_KEY from secrets if not already in env
_SECRETS = Path("/root/.zo/secrets.env")
if _SECRETS.exists():
    for _line in _SECRETS.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))


def check_espn() -> Dict:
    try:
        from src.adapters.espn import ESPNAdapter
        adapter = ESPNAdapter("NBA")
        games = adapter.fetch_games("2026-06-29")
        count = len(games) if games else 0
        if games is None:
            return {"status": "warning", "games_found": 0, "message": "ESPN returned None"}
        return {"status": "healthy", "games_found": count}
    except Exception as e:
        return {"status": "critical", "message": str(e)}


def check_odds_api() -> Dict:
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        return {"status": "critical", "message": "ODDS_API_KEY not set"}
    # Kill switch — skip live call when quota is known to be dead.
    try:
        from src.adapters.odds_api import _quota_dead
        if _quota_dead():
            deadline = os.environ.get("ODDS_API_QUOTA_DEADLINE") or "next billing cycle (Jul 1)"
            return {
                "status": "warning",
                "message": (
                    "Odds API disabled (quota exhausted). "
                    "Set ODDS_API_DISABLED=0 (or unset ODDS_API_QUOTA_DEADLINE) "
                    f"after {deadline} to re-enable."
                ),
                "quota_dead": True,
            }
    except Exception:
        pass
    try:
        url = "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/"
        params = {"apiKey": api_key, "regions": "us", "markets": "player_points"}
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            return {"status": "healthy"}
        if r.status_code == 401:
            return {
                "status": "critical",
                "message": "401 Unauthorized — key invalid. Check https://the-odds-api.com/account",
            }
        if r.status_code == 429:
            return {"status": "warning", "message": "429 rate limited"}
        return {"status": "warning", "code": r.status_code, "message": "HTTP " + str(r.status_code)}
    except Exception as e:
        return {"status": "warning", "message": str(e)}


def check_draftkings() -> Dict:
    """Probe MarketLinesProvider for the supported sport (currently WNBA).

    Returns healthy only if the provider fetches at least one row.
    """
    try:
        from src.domain.market_line_provider import MarketLinesProvider
        provider = MarketLinesProvider(sport="WNBA")
        rows = provider.fetch_lines(use_cache=True)
        if rows:
            return {
                "status": "healthy",
                "rows": len(rows),
                "cached": True,
                "message": f"MarketLinesProvider returned {len(rows)} rows (cache)",
            }
        # Try a live fetch as a fallback before declaring warning.
        rows = provider.fetch_lines(use_cache=False)
        if rows:
            return {
                "status": "healthy",
                "rows": len(rows),
                "cached": False,
                "message": f"MarketLinesProvider returned {len(rows)} rows (live)",
            }
        return {
            "status": "warning",
            "rows": 0,
            "message": "MarketLinesProvider active but fetched 0 rows — SGO unreachable",
            "errors": provider.errors[-3:] if provider.errors else [],
        }
    except Exception as e:
        return {"status": "critical", "message": f"MarketLinesProvider failed: {e}"}
