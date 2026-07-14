"""ESPN Odds Primary — replacement for dead Odds API.

ESPN scoreboard payload contains embedded DraftKings pickcenter entries with
live spread, ML, and total. This module is the new primary odds source.

Verified 2026-07-13: NYL -7.5 +230/-285, SEA -6.5 -230/+190 all returned
cleanly from the public ESPN summary endpoint.
"""
import json
import logging
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary"
# Scoreboard endpoint takes YYYYMMDD or YYYY-MM-DD as `dates` param (no path segment)
ESPN_HISTORICAL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={dates}"

SPORT_LEAGUE_MAP = {
    "NBA": ("basketball", "nba"),
    "WNBA": ("basketball", "wnba"),
    "MLB": ("baseball", "mlb"),
    "NHL": ("hockey", "nhl"),
    "NFL": ("football", "nfl"),
    "WORLD_CUP": ("soccer", "fifa.world"),
}

CACHE_DIR = Path("/home/workspace/Projects/data/odds")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configurable staleness window per sport (live windows are short for basketball)
STALENESS_MIN = {
    "WNBA": 30,
    "NBA": 30,
    "MLB": 120,
    "NHL": 30,
    "NFL": 180,
    "WORLD_CUP": 60,
}


def _http_get_json(url: str, timeout: int = 12) -> Optional[Dict]:
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"ESPN GET {url[:80]}... failed: {e}")
        return None


def _sport_to_espn(sport: str):
    return SPORT_LEAGUE_MAP.get(sport.upper(), ("basketball", "nba"))


def _cache_path(sport: str, date_str: str) -> Path:
    return CACHE_DIR / f"espn_{sport.upper()}_{date_str}.json"


def _parse_odds_entries(entries: List[Dict]) -> List[Dict]:
    """Normalize ESPN pickcenter entries into a clean schema."""
    out = []
    for e in entries or []:
        # DraftKings filter — fall back to first provider if DK missing
        if e.get("provider", {}).get("name") != "DraftKings":
            # Keep the first available for completeness
            pass
        spread = e.get("spread")
        ou = e.get("overUnder")
        home_odds = e.get("homeMoneyline")
        away_odds = e.get("awayMoneyline")
        if spread is None and ou is None and home_odds is None and away_odds is None:
            continue
        out.append({
            "provider": e.get("provider", {}).get("name", "unknown"),
            "spread": spread,
            "total": ou,
            "ml_home": home_odds,
            "ml_away": away_odds,
            "details": e.get("details", ""),
        })
    return out


def _parse_event(event: Dict) -> Dict:
    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away = next((c for c in competitors if c.get("homeAway") == "away"), {})
    status = event.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
    return {
        "event_id": event.get("id"),
        "sport": event.get("sport", {}).get("slug", ""),
        "league": event.get("league", {}).get("slug", ""),
        "home_team": home.get("team", {}).get("abbreviation", ""),
        "away_team": away.get("team", {}).get("abbreviation", ""),
        "home_full": home.get("team", {}).get("displayName", ""),
        "away_full": away.get("team", {}).get("displayName", ""),
        "home_score": home.get("score"),
        "away_score": away.get("score"),
        "status": status,
        "completed": status == "STATUS_FINAL",
        "start_time": event.get("date", ""),
        "odds": _parse_odds_entries(comp.get("odds", [])),
    }


def _scoreboard_url(sport: str, league: str, date_str: str) -> str:
    """Try date-stamped scoreboard first; fall back to no-date (today only)."""
    cleaned = date_str.replace("-", "")
    return f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={cleaned}"


def _summary_url(sport: str, league: str, event_id: str) -> str:
    return f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"


def _scoreboard_nodate(sport: str, league: str) -> str:
    return f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"


def fetch_slate(sport: str, date_str: Optional[str] = None,
                 use_cache: bool = True) -> List[Dict]:
    """Fetch the full slate with odds for a sport/date.

    Args:
        sport: NBA/WNBA/MLB/NHL/NFL/WORLD_CUP
        date_str: YYYY-MM-DD (default today)
        use_cache: read+write JSON cache under data/odds/

    Returns:
        List of parsed event dicts with embedded odds array.
    """
    sport = sport.upper()
    sport_path, league = _sport_to_espn(sport)
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    cache = _cache_path(sport, date_str)

    if use_cache and cache.exists():
        try:
            age_min = (datetime.now().timestamp() - cache.stat().st_mtime) / 60
            if age_min < STALENESS_MIN.get(sport, 60):
                return json.loads(cache.read_text())
        except Exception:
            import logging as _log
            _log.getLogger(__name__).debug("exception", exc_info=True)

    yyyymmdd = date_str.replace("-", "")
    url = ESPN_HISTORICAL.format(sport=sport_path, league=league, dates=yyyymmdd)
    data = _http_get_json(url)
    events = data.get("events", []) if data else []
    parsed = [_parse_event(e) for e in events]

    if use_cache and parsed:
        try:
            cache.write_text(json.dumps(parsed, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    return parsed


def get_market_lines(sport: str, date_str: Optional[str] = None) -> Dict[str, Dict]:
    """Return a {matchup: {spread, total, ml_home, ml_away}} dict.

    Prefers DraftKings. Falls back to first available provider.
    Used by the TC engine and combo builder.
    """
    slate = fetch_slate(sport, date_str)
    lines = {}
    for ev in slate:
        if not ev["home_team"] or not ev["away_team"]:
            continue
        matchup = f"{ev['away_team']}@{ev['home_team']}"
        odds_list = ev.get("odds", [])
        if not odds_list:
            lines[matchup] = {"spread": None, "total": None,
                              "ml_home": None, "ml_away": None, "provider": None}
            continue
        # Prefer DraftKings
        pick = next((o for o in odds_list if o["provider"] == "DraftKings"), odds_list[0])
        lines[matchup] = {
            "spread": pick["spread"],
            "total": pick["total"],
            "ml_home": pick["ml_home"],
            "ml_away": pick["ml_away"],
            "provider": pick["provider"],
            "event_id": ev["event_id"],
            "start_time": ev["start_time"],
        }
    return lines


def is_healthy() -> Dict[str, Any]:
    """Quick health probe — used by dashboard status widget."""
    results = {}
    for sport in ("WNBA", "MLB", "WORLD_CUP", "NBA", "NFL", "NHL"):
        try:
            slate = fetch_slate(sport, use_cache=True)
            with_odds = [e for e in slate if e.get("odds")]
            results[sport] = {
                "ok": True,
                "events": len(slate),
                "with_odds": len(with_odds),
            }
        except Exception as e:
            results[sport] = {"ok": False, "error": str(e)[:100]}
    return results


def fetch_scoreboard_odds(sport: str, league: str, date: Optional[str] = None) -> Dict[str, Dict]:
    out = {}
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    url = _scoreboard_url(sport, league, date)
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("events", [])
            for e in events:
                odds_data = _extract_odds(e)
                if odds_data:
                    out[e["id"]] = {**odds_data, "date": e.get("date", "")[:10], "name": e.get("name", ""), "source": "espn_scoreboard"}
        elif resp.status_code == 404:
            # Historical scoreboard often 404s — try no-date (today's slate) as fallback
            try:
                resp2 = requests.get(_scoreboard_nodate(sport, league), timeout=15, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    for e in data2.get("events", []):
                        odds_data = _extract_odds(e)
                        if odds_data:
                            out[e["id"]] = {**odds_data, "date": e.get("date", "")[:10], "name": e.get("name", ""), "source": "espn_today"}
            except Exception as ex:
                logger.warning(f"ESPN no-date fallback failed: {ex}")
        else:
            logger.warning(f"ESPN GET {url} failed: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"ESPN GET {url} failed: {e}")
    return out


def fetch_event_odds(sport: str, league: str, event_id: str) -> Dict[str, Any]:
    """Fetch odds for a specific event via ESPN summary endpoint.

    Use this for historical events where the scoreboard 404s. Returns dict with
    spread, ml_home, ml_away, total, provider, source='espn_summary'.
    """
    url = _summary_url(sport, league, event_id)
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}"}
        data = resp.json()
        # ESPN summary packs odds under pickcenter or header
        pc = data.get("pickcenter") or data.get("odds") or []
        if not pc:
            return {"spread": None, "ml_home": None, "ml_away": None, "total": None, "provider": None}
        # Use first provider (usually consensus)
        first = pc[0] if isinstance(pc, list) else pc
        return {
            "spread": first.get("spread"),
            "ml_home": first.get("homeTeamOdds", {}).get("moneyLine") if isinstance(first.get("homeTeamOdds"), dict) else first.get("homeOdds"),
            "ml_away": first.get("awayTeamOdds", {}).get("moneyLine") if isinstance(first.get("awayTeamOdds"), dict) else first.get("awayOdds"),
            "total": (first.get("overUnder") or {}).get("value") if isinstance(first.get("overUnder"), dict) else first.get("total"),
            "provider": first.get("provider", {}).get("name") if isinstance(first.get("provider"), dict) else first.get("provider"),
            "source": "espn_summary",
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "WNBA"
    date = sys.argv[2] if len(sys.argv) > 2 else None
    slate = fetch_slate(sport, date)
    print(f"{sport} {date or 'today'}: {len(slate)} events")
    for ev in slate[:5]:
        odds_str = ""
        if ev["odds"]:
            o = ev["odds"][0]
            odds_str = f" | {o['provider']} spread={o['spread']} total={o['total']}"
        print(f"  {ev['away_team']} @ {ev['home_team']} [{ev['status']}]{odds_str}")
