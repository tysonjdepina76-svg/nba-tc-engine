"""WNBA data fetcher with tiered fallback:
  1. ESPN Core API (free, primary)
  2. SportsData.io (paid, fallback)
  3. Cache (last resort)

Returns a normalized dict: {'sport': 'WNBA', 'lines': [...], 'source': 'espn'|'sportsdata'|'cache'|'none'}
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

CACHE_DIR = Path("/home/workspace/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
WNBA_CACHE = CACHE_DIR / "wnba_lines.json"


def _load_cache() -> Optional[Dict[str, Any]]:
    """Return cached WNBA data if fresh (under 2h old)."""
    if not WNBA_CACHE.exists():
        return None
    try:
        age_sec = (CACHE_DIR.stat().st_mtime - WNBA_CACHE.stat().st_mtime) if False else \
                  (__import__('time').time() - WNBA_CACHE.stat().st_mtime)
        if age_sec > 7200:  # 2 hours
            return None
        return json.loads(WNBA_CACHE.read_text())
    except Exception as e:
        log.warning(f"WNBA cache read failed: {e}")
        return None


def _save_cache(data: Dict[str, Any]) -> None:
    try:
        WNBA_CACHE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        log.warning(f"WNBA cache write failed: {e}")


def fetch_espn_wnba() -> Optional[Dict[str, Any]]:
    """Pull WNBA games + DK lines from ESPN Core API."""
    try:
        from wnba_tc_engine import get_today_slate
        raw = get_today_slate() or []
        if not raw:
            return None
        lines = []
        for g in raw:
            away = g.get("away", "")
            home = g.get("home", "")
            if not away or not home:
                continue
            lines.append({
                "away": away,
                "home": home,
                "event_id": g.get("event_id"),
                "status": g.get("status", "scheduled"),
                "tip": g.get("tip"),
                "source": "espn",
            })
        if not lines:
            return None
        return {"sport": "WNBA", "lines": lines, "source": "espn"}
    except Exception as e:
        log.warning(f"ESPN WNBA fetch failed: {e}")
        return None


def fetch_sportsdata_wnba() -> Optional[Dict[str, Any]]:
    """Pull WNBA games from SportsData.io as fallback."""
    import requests
    api_key = os.environ.get("SPORTSDATAIO_API_KEY") or os.environ.get("SportsDataIo")
    if not api_key:
        return None
    try:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://api.sportsdata.io/v3/wnba/scores/json/GamesByDate/{today}"
        resp = requests.get(url, headers={"Ocp-Apim-Subscription-Key": api_key}, timeout=10)
        if resp.status_code != 200:
            log.info(f"SportsData.io WNBA returned {resp.status_code}")
            return None
        games = resp.json() or []
        if not games:
            return None
        lines = []
        for g in games:
            away = g.get("AwayTeam") or ""
            home = g.get("HomeTeam") or ""
            if not away or not home:
                continue
            lines.append({
                "away": away,
                "home": home,
                "event_id": g.get("GameID"),
                "status": g.get("Status", "Scheduled"),
                "tip": g.get("DateTime"),
                "source": "sportsdata",
            })
        if not lines:
            return None
        return {"sport": "WNBA", "lines": lines, "source": "sportsdata"}
    except Exception as e:
        log.warning(f"SportsData.io WNBA fetch failed: {e}")
        return None


def fetch_wnba_lines(matchup: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Public entry point — tries ESPN → SportsData.io → cache.

    Args:
        matchup: optional "AWAY@HOME" filter
        dry_run: if True, skip cache writes
    """
    # 1. ESPN
    data = fetch_espn_wnba()
    if data and data.get("lines"):
        if matchup:
            data["lines"] = [g for g in data["lines"] if f"{g['away']}@{g['home']}" == matchup]
        if not dry_run:
            _save_cache(data)
        return data

    # 2. SportsData.io
    data = fetch_sportsdata_wnba()
    if data and data.get("lines"):
        if matchup:
            data["lines"] = [g for g in data["lines"] if f"{g['away']}@{g['home']}" == matchup]
        if not dry_run:
            _save_cache(data)
        return data

    # 3. Basketball-Reference player stats (tier-3 fallback, cached)
    try:
        from sources.scrapers import BasketballReferenceScraper
        from sources.utils.cache import cache_fetch
        from datetime import datetime as _dt
        players = cache_fetch(
            "wnba_stats_br",
            lambda: BasketballReferenceScraper(season=2026).fetch_player_stats(),
            ttl_hours=6,
        ) or []
        if players:
            data = {
                "sport": "WNBA",
                "lines": [],
                "source": "basketball_reference",
                "timestamp": _dt.now().isoformat(),
                "games": [{"players": players}],
            }
            if not dry_run:
                _save_cache(data)
            return data
    except Exception as e:
        log.warning(f"Basketball-Reference scrape failed: {e}")

    # 4. Cache
    cached = _load_cache()
    if cached:
        cached["source"] = "cache"
        if matchup:
            cached["lines"] = [g for g in cached.get("lines", []) if f"{g['away']}@{g['home']}" == matchup]
        return cached

    # 5. Empty
    return {"sport": "WNBA", "lines": [], "source": "none"}
