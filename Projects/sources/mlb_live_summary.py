"""
MLB Live Summary - Fetches live games with lineups, pitchers, and batting stats.
"""

import requests
from sources.utils.cache import cache_fetch
from sources.utils.logging import get_logger

logger = get_logger(__name__)

STAT_MAP = {
    "avg": "avg",
    "homeRuns": "hr",
    "rbi": "rbi",
    "runs": "r",
    "stolenBases": "sb",
    "ops": "ops",
    "era": "era",
    "whip": "whip",
    "strikeouts": "so",
    "hits": "h",
    "atBats": "ab",
    "doubles": "2b",
    "triples": "3b",
    "walks": "bb",
    "hitByPitch": "hbp"
}

def fetch_mlb_live_summary() -> dict:
    """Fetch live MLB games with lineups, pitchers, and live batting stats."""
    scoreboard_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(scoreboard_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Scoreboard fetch failed: {e}")
        return {"source": "error", "games": [], "error": str(e)}
    live_games = []
    for event in data.get("events", []):
        status = event.get("status", {}).get("type", {}).get("state")
        if status not in ["in", "live"]:
            continue
        event_id = event.get("id")
        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={event_id}"
        try:
            summary_resp = requests.get(summary_url, headers=headers, timeout=10)
            summary_resp.raise_for_status()
            summary = summary_resp.json()
        except Exception as e:
            logger.warning(f"Summary fetch failed for {event_id}: {e}")
            continue
        comp = event["competitions"][0]
        competitors = comp["competitors"]
        away_team = next(c for c in competitors if c["homeAway"] == "away")
        home_team = next(c for c in competitors if c["homeAway"] == "home")
        game_info = {
            "id": event_id,
            "away": away_team["team"]["displayName"],
            "home": home_team["team"]["displayName"],
            "away_score": away_team["score"],
            "home_score": home_team["score"],
            "inning": event.get("status", {}).get("period", 0),
            "away_pitcher": None,
            "home_pitcher": None,
            "lineup": [],
            "players": []
        }
        boxscore = summary.get("boxscore", {})
        for team_box in boxscore.get("teams", []):
            team_abbr = team_box.get("team", {}).get("abbreviation")
            lineup_players = []
            for player in team_box.get("players", []):
                athlete = player.get("athlete", {})
                pos = athlete.get("position", {}).get("abbreviation")
                if pos == "P" and player.get("starter"):
                    player_name = athlete.get("displayName")
                    if team_abbr == away_team["team"]["abbreviation"]:
                        game_info["away_pitcher"] = player_name
                    else:
                        game_info["home_pitcher"] = player_name
                if player.get("starter") and pos != "P" and pos:
                    lineup_players.append({
                        "name": athlete.get("displayName"),
                        "position": pos,
                        "batting_order": player.get("battingOrder", 999)
                    })
                stats = player.get("stats", {})
                batting_stats = {}
                for stat_group in stats.get("groups", []):
                    if stat_group.get("displayName") == "Batting":
                        for stat in stat_group.get("stats", []):
                            key = stat.get("name", "").lower()
                            if key in STAT_MAP:
                                try:
                                    batting_stats[STAT_MAP[key]] = float(stat.get("value", 0))
                                except (ValueError, TypeError):
                                    batting_stats[STAT_MAP[key]] = 0
                        break
                if batting_stats:
                    game_info["players"].append({
                        "name": athlete.get("displayName", "Unknown"),
                        "team": team_abbr,
                        **batting_stats
                    })
            lineup_players.sort(key=lambda x: x.get("batting_order", 999))
            if lineup_players:
                game_info["lineup"] = lineup_players
        live_games.append(game_info)
    return {"source": "ESPN Summary", "games": live_games}

def fetch_mlb_live_cached() -> dict:
    """Cached version with 60-second TTL for live data."""
    return cache_fetch("mlb_live_summary", fetch_mlb_live_summary, ttl_hours=0.0167)
