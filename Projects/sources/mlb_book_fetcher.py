"""MLB book lines fetcher with tiered fallback:
  1. SportsData.io (paid, primary for MLB props)
  2. ESPN DK lines (free, fallback for totals/spread/ML)
  3. mlb_sdio_props (existing TC engine wrapper)
  4. Cache (last resort)

Returns normalized dict: {'sport': 'MLB', 'lines': [...], 'source': 'sportsdata'|'espn'|'tc_engine'|'cache'|'none'}
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

CACHE_DIR = Path("/home/workspace/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
MLB_CACHE = CACHE_DIR / "mlb_lines.json"


def _load_cache() -> Optional[Dict[str, Any]]:
    if not MLB_CACHE.exists():
        return None
    try:
        import time
        age_sec = time.time() - MLB_CACHE.stat().st_mtime
        if age_sec > 10800:  # 3 hours
            return None
        return json.loads(MLB_CACHE.read_text())
    except Exception as e:
        log.warning(f"MLB cache read failed: {e}")
        return None


def _save_cache(data: Dict[str, Any]) -> None:
    try:
        MLB_CACHE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        log.warning(f"MLB cache write failed: {e}")


def fetch_sportsdata_mlb() -> Optional[Dict[str, Any]]:
    """Pull MLB games from SportsData.io (props + lines)."""
    import requests
    api_key = os.environ.get("SPORTSDATAIO_API_KEY") or os.environ.get("SportsDataIo")
    if not api_key:
        return None
    try:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://api.sportsdata.io/v3/mlb/scores/json/GamesByDate/{today}"
        resp = requests.get(url, headers={"Ocp-Apim-Subscription-Key": api_key}, timeout=10)
        if resp.status_code != 200:
            log.info(f"SportsData.io MLB returned {resp.status_code}")
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
                "first_pitch": g.get("DateTime"),
                "source": "sportsdata",
            })
        if not lines:
            return None
        return {"sport": "MLB", "lines": lines, "source": "sportsdata"}
    except Exception as e:
        log.warning(f"SportsData.io MLB fetch failed: {e}")
        return None


def fetch_espn_mlb() -> Optional[Dict[str, Any]]:
    """Pull MLB games from ESPN scoreboard."""
    try:
        import requests
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={today}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json() or {}
        events = data.get("events", [])
        if not events:
            return None
        lines = []
        for e in events:
            comps = e.get("competitions", [{}])[0].get("competitors", [])
            away, home = "", ""
            for c in comps:
                abbr = c.get("team", {}).get("abbreviation", "")
                if c.get("homeAway") == "home":
                    home = abbr
                else:
                    away = abbr
            if not away or not home:
                continue
            lines.append({
                "away": away,
                "home": home,
                "event_id": e.get("id"),
                "status": e.get("status", {}).get("type", {}).get("description", "Scheduled"),
                "first_pitch": e.get("date"),
                "source": "espn",
            })
        if not lines:
            return None
        return {"sport": "MLB", "lines": lines, "source": "espn"}
    except Exception as e:
        log.warning(f"ESPN MLB fetch failed: {e}")
        return None


def fetch_mlb_book_lines(matchup: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Public entry point — tries SportsData.io → ESPN → mlb_sdio_props → cache."""
    # 1. SportsData.io
    data = fetch_sportsdata_mlb()
    if data and data.get("lines"):
        if matchup:
            data["lines"] = [g for g in data["lines"] if f"{g['away']}@{g['home']}" == matchup]
        if not dry_run:
            _save_cache(data)
        return data

    # 2. ESPN
    data = fetch_espn_mlb()
    if data and data.get("lines"):
        if matchup:
            data["lines"] = [g for g in data["lines"] if f"{g['away']}@{g['home']}" == matchup]
        if not dry_run:
            _save_cache(data)
        return data

    # 3. mlb_sdio_props (existing TC engine)
    try:
        from mlb_sdio_props import fetch_all_mlb_props
        props = fetch_all_mlb_props() or {}
        games = props.get("games", [])
        if games:
            lines = [{"away": g.get("away", ""), "home": g.get("home", ""),
                      "event_id": g.get("event_id"), "source": "tc_engine"} for g in games]
            data = {"sport": "MLB", "lines": lines, "source": "tc_engine"}
            if not dry_run:
                _save_cache(data)
            return data
    except Exception as e:
        log.warning(f"mlb_sdio_props fetch failed: {e}")

    # 4. Cache
    cached = _load_cache()
    if cached:
        cached["source"] = "cache"
        if matchup:
            cached["lines"] = [g for g in cached.get("lines", []) if f"{g['away']}@{g['home']}" == matchup]
        return cached

    return {"sport": "MLB", "lines": [], "source": "none"}
