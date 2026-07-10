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


def _fetch_espn_odds_for_event(event_id: str) -> dict:
    """Fetch DraftKings moneyline/spread/total from ESPN's dedicated odds endpoint.

    ESPN's scoreboard endpoint does NOT include odds inline — they live at
    `sports.core.api.espn.com/.../events/{id}/competitions/{id}/odds`.
    Returns: {'ml_home': int|None, 'ml_away': int|None, 'spread': float|None, 'total': float|None, 'source': str}
    """
    if not event_id:
        return {"ml_home": None, "ml_away": None, "spread": None, "total": None, "source": "none"}
    import requests as _r
    url = f"https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/events/{event_id}/competitions/{event_id}/odds"
    try:
        resp = _r.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code != 200:
            return {"ml_home": None, "ml_away": None, "spread": None, "total": None, "source": "none"}
        items = (resp.json() or {}).get("items") or []
        if not items:
            return {"ml_home": None, "ml_away": None, "spread": None, "total": None, "source": "none"}
        # Prefer DraftKings (provider.id=100), fall back to first item
        pick = next((o for o in items if (o.get("provider") or {}).get("name", "").lower() == "draftkings"), items[0])
        provider_name = (pick.get("provider") or {}).get("name", "")
        out = {"ml_home": None, "ml_away": None, "spread": None, "total": None, "source": provider_name}
        # ML/spread live on awayTeamOdds / homeTeamOdds
        for side_key, ml_key in (("homeTeamOdds", "ml_home"), ("awayTeamOdds", "ml_away")):
            side = pick.get(side_key) or {}
            ml = side.get("moneyLine")
            if ml is not None:
                try: out[ml_key] = int(ml)
                except (TypeError, ValueError): pass
        # Spread — ESPN stores it at top-level `spread` (home-favored convention).
        # Fall back to homeTeamOdds.current.pointSpread.alternateDisplayValue.
        top_spread = pick.get("spread")
        if top_spread is not None:
            try: out["spread"] = float(top_spread)
            except (TypeError, ValueError): pass
        if out["spread"] is None:
            for side_key in ("homeTeamOdds", "awayTeamOdds"):
                side = pick.get(side_key) or {}
                ps = side.get("pointSpread")
                if ps is None: continue
                if isinstance(ps, dict):
                    raw = ps.get("alternateDisplayValue") or ps.get("displayValue")
                else:
                    raw = ps
                try: out["spread"] = float(raw); break
                except (TypeError, ValueError): pass
        # Total
        total = pick.get("overUnder")
        if total is not None:
            try: out["total"] = float(total)
            except (TypeError, ValueError): pass
        return out
    except Exception as e:
        log.warning(f"ESPN core odds fetch failed for {event_id}: {e}")
        return {"ml_home": None, "ml_away": None, "spread": None, "total": None, "source": "none"}


def _extract_espn_odds(event: dict) -> dict:
    """Pull h2h/spread/total from ESPN event odds array.

    ESPN returns odds per bookmaker under competitions[0].odds[].
    Each item has: provider.id, details, over/under, spread, moneyline.
    Returns: {'ml_home': int|None, 'ml_away': int|None,
              'spread': float|None, 'total': float|None}
    """
    comp = (event.get("competitions") or [{}])[0]
    odds_list = comp.get("odds") or []
    if not odds_list:
        return {"ml_home": None, "ml_away": None, "spread": None, "total": None}

    preferred = {"draftkings": None, "fanduel": None, "betmgm": None}
    for o in odds_list:
        prov = (o.get("provider") or {}).get("id", "").lower()
        if prov in preferred and preferred[prov] is None:
            preferred[prov] = o

    pick = next((v for v in preferred.values() if v), odds_list[0])

    out = {"ml_home": None, "ml_away": None, "spread": None, "total": None}

    home_team = next((c for c in (comp.get("competitors") or []) if c.get("homeAway") == "home"), {})
    away_team = next((c for c in (comp.get("competitors") or []) if c.get("homeAway") == "away"), {})

    home_odds = home_team.get("odds") or {}
    away_odds = away_team.get("odds") or {}

    if "moneyLine" in home_odds:
        try: out["ml_home"] = int(home_odds["moneyLine"])
        except (TypeError, ValueError): pass
    if "moneyLine" in away_odds:
        try: out["ml_away"] = int(away_odds["moneyLine"])
        except (TypeError, ValueError): pass

    if "pointSpread" in home_odds:
        ps = home_odds["pointSpread"]
        if isinstance(ps, dict):
            try: out["spread"] = float(ps.get("alternateDisplayValue") or ps.get("displayValue") or 0)
            except (TypeError, ValueError): pass
        elif isinstance(ps, (int, float)):
            out["spread"] = float(ps)
    if "spread" in home_odds:
        sp = home_odds["spread"]
        if isinstance(sp, dict) and out["spread"] is None:
            try: out["spread"] = float(sp.get("alternateDisplayValue") or sp.get("displayValue") or 0)
            except (TypeError, ValueError): pass

    if "total" in pick:
        try: out["total"] = float(pick["total"].get("close", {}).get("displayValue") or pick["total"].get("displayValue") or 0)
        except (TypeError, ValueError, AttributeError): pass

    return out


def fetch_espn_mlb() -> Optional[Dict[str, Any]]:
    """Pull MLB games from ESPN scoreboard + extract DK ML/spread/total."""
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
            odds = _fetch_espn_odds_for_event(e.get("id"))
            lines.append({
                "away": away,
                "home": home,
                "event_id": e.get("id"),
                "status": e.get("status", {}).get("type", {}).get("description", "Scheduled"),
                "first_pitch": e.get("date"),
                "ml_home": odds["ml_home"],
                "ml_away": odds["ml_away"],
                "spread": odds["spread"],
                "total": odds["total"],
                "source": odds["source"],
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
    try:
        data = fetch_sportsdata_mlb()
        if data and data.get("lines"):
            if matchup:
                data["lines"] = [g for g in data["lines"] if f"{g['away']}@{g['home']}" == matchup]
            if not dry_run:
                _save_cache(data)
            return data
    except Exception as e:
        log.warning(f"SportsData.io MLB fetch failed: {e}")

    # 2. ESPN
    try:
        data = fetch_espn_mlb()
        if data and data.get("lines"):
            if matchup:
                data["lines"] = [g for g in data["lines"] if f"{g['away']}@{g['home']}" == matchup]
            if not dry_run:
                _save_cache(data)
            return data
    except Exception as e:
        log.warning(f"ESPN MLB fetch failed: {e}")

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

    # 4. Baseball-Reference leaderboards (tier-3 player-stats fallback, cached)
    try:
        from sources.scrapers import BaseballReferenceScraper
        from sources.utils.cache import cache_fetch
        batters = cache_fetch(
            "mlb_batting_br",
            lambda: BaseballReferenceScraper(season=2026).fetch_batting(),
            ttl_hours=6) or []
        pitchers = cache_fetch(
            "mlb_pitching_br",
            lambda: BaseballReferenceScraper(season=2026).fetch_pitching(),
            ttl_hours=6) or []
        if batters or pitchers:
            data = {
                "sport": "MLB",
                "lines": [],
                "source": "baseball_reference",
                "player_stats": {"batters": batters, "pitchers": pitchers},
            }
            if not dry_run:
                _save_cache(data)
            return data
    except Exception as e:
        log.warning(f"Baseball-Reference scrape failed: {e}")

    # 5. Cache
    cached = _load_cache()
    if cached:
        cached["source"] = "cache"
        if matchup:
            cached["lines"] = [g for g in cached.get("lines", []) if f"{g['away']}@{g['home']}" == matchup]
        return cached

    return {"sport": "MLB", "lines": [], "source": "none"}
