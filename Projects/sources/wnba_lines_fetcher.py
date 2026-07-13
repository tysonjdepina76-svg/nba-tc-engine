"""WNBA game-line fetcher (moneyline, spread, total) from ESPN.

Separate from wnba_tc_engine (which handles projections). This module
only fetches market lines for the slate, so the frontend can render
ML/spread columns next to projections.
"""
import requests
import logging
from typing import Dict, List, Any, Optional

log = logging.getLogger(__name__)

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
USER_AGENT = "Mozilla/5.0"


def fetch_wnba_lines(game_id: Optional[str] = None, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch moneyline, spread, and total for WNBA games on date_str (YYYY-MM-DD).
    Defaults to today ET. Returns list of dicts: {id, home, away, spread, moneyline, total, completed}.
    Empty list on failure. If game_id is given, filters to that event.
    """
    from datetime import datetime, timezone, timedelta
    if date_str is None:
        date_str = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime("%Y-%m-%d")
    try:
        # ESPN expects dates=YYYYMMDD
        dates_param = date_str.replace("-", "")
        url = ESPN_URL + f"?dates={dates_param}"
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning(f"ESPN WNBA lines fetch failed: {e}")
        return []

    games: List[Dict[str, Any]] = []
    for event in data.get("events", []):
        eid = event.get("id")
        if game_id and eid != game_id:
            continue
        comps = event.get("competitions", [{}])[0].get("competitors", [])
        home, away = "", ""
        for c in comps:
            abbr = c.get("team", {}).get("abbreviation") or c.get("team", {}).get("displayName", "")
            if c.get("homeAway") == "home":
                home = abbr
            else:
                away = abbr
        if not home or not away:
            continue

        game = {
            "id": eid,
            "home": home,
            "away": away,
            "spread": None,
            "moneyline": None,
            "total": None,
        }
        for od in event.get("odds", []) or []:
            market = (od.get("market") or "").lower()
            if market == "spread":
                game["spread"] = od.get("spread") or od.get("details")
            elif market in ("moneyline", "h2h"):
                game["moneyline"] = od.get("moneyline") or od.get("details")
            elif market == "total":
                game["total"] = od.get("total") or od.get("overUnder")
        games.append(game)
    return games
