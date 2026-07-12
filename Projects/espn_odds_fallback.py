"""ESPN results scraper with 3 fallback strategies for game results and totals."""
import requests
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary"
ESPN_HISTORICAL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard/{dates}"

SPORT_LEAGUE_MAP = {
    "NBA": ("basketball", "nba"),
    "WNBA": ("basketball", "wnba"),
    "MLB": ("baseball", "mlb"),
    "NHL": ("hockey", "nhl"),
    "NFL": ("football", "nfl"),
    "WORLD_CUP": ("soccer", "fifa.world"),
}


def _sport_to_espn(sport: str) -> tuple:
    return SPORT_LEAGUE_MAP.get(sport.upper(), ("basketball", "nba"))


def _get_events_for_date(sport: str, date_str: str) -> List[Dict]:
    """Fallback 1: ESPN scoreboard endpoint for a specific date."""
    sport_path, league = _sport_to_espn(sport)
    yyyymmdd = date_str.replace("-", "")
    url = ESPN_HISTORICAL.format(sport=sport_path, league=league, dates=yyyymmdd)
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("events", [])
    except Exception as e:
        logger.warning(f"ESPN scoreboard fetch failed: {e}")
        return []


def _get_event_summary(sport: str, event_id: str) -> Optional[Dict]:
    """Fallback 2: ESPN summary endpoint for a specific event."""
    sport_path, league = _sport_to_espn(sport)
    url = ESPN_SUMMARY.format(sport=sport_path, league=league) + f"?event={event_id}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"ESPN summary fetch failed for {event_id}: {e}")
        return None


def _parse_event_result(event: Dict) -> Dict:
    """Parse an ESPN event into a normalized result dict."""
    comp = event.get("competitions", [{}])[0]
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away = next((c for c in competitors if c.get("homeAway") == "away"), {})
    status = event.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
    completed = status == "STATUS_FINAL"
    return {
        "event_id": event.get("id"),
        "home_team": home.get("team", {}).get("abbreviation", ""),
        "away_team": away.get("team", {}).get("abbreviation", ""),
        "home_score": int(home.get("score", 0) or 0),
        "away_score": int(away.get("score", 0) or 0),
        "total": int(home.get("score", 0) or 0) + int(away.get("score", 0) or 0),
        "completed": completed,
        "status": status,
    }


def get_game_results(sport: str, date_str: str) -> List[Dict]:
    """Get game results for a sport on a given date. Tries 3 fallback strategies.

    Returns list of dicts with: event_id, home_team, away_team, home_score,
    away_score, total, completed, status.
    """
    events = _get_events_for_date(sport, date_str)
    results = []
    for ev in events:
        parsed = _parse_event_result(ev)
        if parsed["event_id"]:
            results.append(parsed)

    # Fallback 3: if scoreboard empty, try individual event summaries by date range
    if not results:
        logger.info(f"No events from scoreboard for {sport} {date_str}, trying date sweep")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            yyyymmdd = dt.strftime("%Y%m%d")
            sport_path, league = _sport_to_espn(sport)
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/{league}/scoreboard?dates={yyyymmdd}-{yyyymmdd}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            for ev in r.json().get("events", []):
                parsed = _parse_event_result(ev)
                if parsed["event_id"]:
                    results.append(parsed)
        except Exception as e:
            logger.warning(f"Date sweep fallback failed: {e}")

    return results


def get_player_boxscore(sport: str, event_id: str) -> List[Dict]:
    """Get player boxscore for a specific event. Returns list of player stat lines."""
    summary = _get_event_summary(sport, event_id)
    if not summary:
        return []
    players = []
    for team in summary.get("boxscore", {}).get("players", []):
        team_abbr = team.get("team", {}).get("abbreviation", "")
        for stat_group in team.get("statistics", []):
            for athlete in stat_group.get("athletes", []):
                player = athlete.get("athlete", {})
                stats = athlete.get("stats", [])
                players.append({
                    "team": team_abbr,
                    "player_id": player.get("id"),
                    "name": player.get("displayName", ""),
                    "stats": stats,
                })
    return players


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "NBA"
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    results = get_game_results(sport, date)
    print(f"Found {len(results)} games for {sport} on {date}")
    for r in results[:5]:
        print(f"  {r['away_team']} {r['away_score']} @ {r['home_team']} {r['home_score']} (total={r['total']}, done={r['completed']})")
