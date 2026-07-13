"""
Schedule fetcher — pulls today's slate for all sports with start times,
home/away, status, and (where available) starting pitcher / starting XI.
"""

import logging
import requests
from datetime import datetime, date as date_cls
from typing import Dict, List, Optional

from sources.utils.cache import cache_fetch

logger = logging.getLogger(__name__)

ESPN_PATHS = {
    "mlb":   ("baseball/mlb",          "baseball/mlb"),
    "wnba":  ("basketball/wnba",       "basketball/wnba"),
    "nba":   ("basketball/nba",        "basketball/nba"),
    "nfl":   ("football/nfl",          "football/nfl"),
    "nhl":   ("hockey/nhl",            "hockey/nhl"),
    "soccer":("soccer/usa.1",          "soccer/usa.1"),
    "wc":    ("soccer/usa.1",          "soccer/usa.1"),
}


def _esn_date(d: Optional[str] = None) -> str:
    if d:
        return d.replace("-", "")
    return datetime.now().strftime("%Y%m%d")


def _fetch_schedule(sport: str, target_date: Optional[str]) -> Dict:
    score_path, summary_path = ESPN_PATHS.get(sport, (None, None))
    if not score_path:
        return {"sport": sport, "games": [], "error": f"unknown sport: {sport}"}
    url = f"https://site.api.espn.com/apis/site/v2/sports/{score_path}/scoreboard?dates={_esn_date(target_date)}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error(f"schedule fetch failed for {sport}: {exc}")
        return {"sport": sport, "games": [], "error": str(exc)}

    games: List[Dict] = []
    for event in data.get("events", []) or []:
        comp = (event.get("competitions") or [{}])[0]
        competitors = comp.get("competitors", []) or []
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        status = comp.get("status", {}) or {}
        game = {
            "id": event.get("id") or comp.get("id"),
            "sport": sport,
            "home": (home.get("team") or {}).get("abbreviation"),
            "away": (away.get("team") or {}).get("abbreviation"),
            "start_time": event.get("date"),
            "status": (status.get("type") or {}).get("description", "Scheduled"),
            "clock": status.get("displayClock"),
            "venue": (comp.get("venue") or {}).get("fullName"),
            "broadcast": (comp.get("broadcasts") or [{}])[0].get("media", {}).get("shortName") if comp.get("broadcasts") else None,
            "home_record": ((home.get("records") or [{}])[0]).get("summary"),
            "away_record": ((away.get("records") or [{}])[0]).get("summary"),
            "starting_pitcher_home": None,
            "starting_pitcher_away": None,
            "starting_xi_home": None,
            "starting_xi_away": None,
        }
        notes = comp.get("notes") or []
        for n in notes:
            if n.get("type") == "news":
                game["note"] = n.get("headline")
        games.append(game)
    return {
        "sport": sport,
        "date": target_date or datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "games": games,
        "count": len(games),
    }


def _enrich_with_starters(payload: Dict, target_date: Optional[str]) -> Dict:
    """Add starting pitcher (MLB) / starting XI (soccer) to games via summary endpoint."""
    sport = payload.get("sport")
    summary_path = ESPN_PATHS.get(sport, (None, None))[1]
    if not summary_path:
        return payload
    for game in payload.get("games", []):
        gid = game.get("id")
        if not gid:
            continue
        url = f"https://site.api.espn.com/apis/site/v2/sports/{summary_path}/summary?event={gid}"
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.debug(f"summary fetch failed for game {gid}: {exc}")
            continue

        if sport == "mlb":
            for team_box in (data.get("boxscore") or {}).get("teams", []) or []:
                side = "home" if (team_box.get("team") or {}).get("id") == game.get("home_id") else "away"
                for grp in team_box.get("players", []) or []:
                    for p in grp.get("athletes", []) or []:
                        stats = {s.get("name"): s.get("value") for s in (p.get("stats") or [])}
                        if "starting" in (p.get("athlete", {}).get("description") or "").lower() or stats.get("starting") == 1:
                            key = f"starting_pitcher_{side}"
                            game[key] = (p.get("athlete") or {}).get("displayName")
                            break

        elif sport in ("soccer", "wc"):
            rosters = data.get("rosters") or []
            for r in rosters:
                side = "home" if r.get("homeAway") == "home" else "away"
                xi = []
                for p in (r.get("roster") or []):
                    if p.get("starter"):
                        xi.append({
                            "name": (p.get("athlete") or {}).get("displayName"),
                            "position": (p.get("athlete") or {}).get("position", {}).get("abbreviation"),
                            "jersey": (p.get("athlete") or {}).get("jersey"),
                        })
                if xi:
                    game[f"starting_xi_{side}"] = xi[:11]
    return payload


def fetch_schedule(sport: str, target_date: Optional[str] = None, enrich: bool = True) -> Dict:
    """Public entrypoint — fetches schedule, optionally enriches with starters."""
    base = _fetch_schedule(sport, target_date)
    if enrich and base.get("games"):
        try:
            base = _enrich_with_starters(base, target_date)
        except Exception as exc:
            logger.warning(f"enrichment failed for {sport}: {exc}")
    return base


def fetch_schedule_cached(sport: str, target_date: Optional[str] = None) -> Dict:
    return cache_fetch(
        key=f"schedule_{sport}_{target_date or 'today'}",
        fetch_func=lambda: fetch_schedule(sport, target_date),
        ttl_hours=0.5,
    )


def fetch_all_schedules(target_date: Optional[str] = None) -> Dict[str, Dict]:
    """Fetch all sports' schedules for the date."""
    out = {}
    for sport in ESPN_PATHS.keys():
        out[sport] = fetch_schedule_cached(sport, target_date)
    return out
