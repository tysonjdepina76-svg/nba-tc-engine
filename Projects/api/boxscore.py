"""ESPN Box Score Aggregator — single-call live player stats for WNBA/MLB."""
import requests
import json
from typing import Optional

ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"

SPORT_PATHS = {
    "wnba": "basketball/leagues/wnba",
    "mlb": "baseball/leagues/mlb",
    "nba": "basketball/leagues/nba",
}

BASKETBALL_STATS = [
    "minutes", "points", "rebounds", "assists",
    "threePointFieldGoalsMade", "steals", "blocks",
    "turnovers", "fouls", "fieldGoalsMade",
    "fieldGoalsAttempted", "threePointFieldGoalsAttempted",
    "freeThrowsMade", "freeThrowsAttempted",
]

MLB_BATTING_STATS = [
    "atBats", "runs", "hits", "rbi", "baseOnBalls",
    "strikeouts", "homeRuns", "stolenBases",
    "battingAverage", "onBasePercentage", "sluggingPercentage",
    "totalBases", "doubles", "triples",
]

MLB_PITCHING_STATS = [
    "inningsPitched", "hitsAllowed", "runsAllowed", "earnedRuns",
    "strikeouts", "baseOnBallsAllowed", "homeRunsAllowed",
    "pitchesThrown", "strikesThrown", "era",
]

POSITION_NAMES = {
    "1": "PG", "2": "SG", "3": "SF", "4": "PF", "5": "C",
    "6": "G", "7": "F", "8": "G-F", "9": "F-C",
    "10": "SP", "11": "RP", "12": "C", "13": "1B",
    "14": "2B", "15": "3B", "16": "SS", "17": "LF",
    "18": "CF", "19": "RF", "20": "DH", "21": "P",
}


def _fetch_json(url, params="?lang=en&region=us"):
    try:
        r = requests.get(f"{url}{params}", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _get_athlete_name(sport_path, season, athlete_id):
    """Fetch athlete full name."""
    url = f"{ESPN_CORE}/{sport_path}/seasons/{season}/athletes/{athlete_id}"
    data = _fetch_json(url)
    if data:
        return data.get("fullName") or data.get("displayName") or f"#{athlete_id}"
    return f"#{athlete_id}"


def _get_position_name(sport_path, pos_id):
    """Fetch position display name."""
    url = f"{ESPN_CORE}/{sport_path}/positions/{pos_id}"
    data = _fetch_json(url)
    if data:
        return data.get("abbreviation") or data.get("name") or POSITION_NAMES.get(str(pos_id), "")
    return POSITION_NAMES.get(str(pos_id), "")


def _player_basketball_stats(sport_path, event_id, comp_id, team_id, player_id):
    """Get individual player basketball stats."""
    url = f"{ESPN_CORE}/{sport_path}/events/{event_id}/competitions/{comp_id}/competitors/{team_id}/roster/{player_id}/statistics/0"
    data = _fetch_json(url)
    if not data:
        return {}

    stats = {}
    for cat in data.get("splits", {}).get("categories", []):
        for s in cat.get("stats", []):
            name = s.get("name", "")
            if name in BASKETBALL_STATS:
                stats[name] = s.get("value", 0)
    return stats


def _player_mlb_stats(sport_path, event_id, comp_id, team_id, player_id):
    """Get individual player MLB stats (batting and pitching)."""
    url = f"{ESPN_CORE}/{sport_path}/events/{event_id}/competitions/{comp_id}/competitors/{team_id}/roster/{player_id}/statistics/0"
    data = _fetch_json(url)
    if not data:
        return {"batting": {}, "pitching": {}}

    batting = {}
    pitching = {}
    for cat in data.get("splits", {}).get("categories", []):
        for s in cat.get("stats", []):
            name = s.get("name", "")
            val = s.get("value", 0)
            if name in MLB_BATTING_STATS:
                batting[name] = val
            elif name in MLB_PITCHING_STATS:
                pitching[name] = val
    return {"batting": batting, "pitching": pitching}


def get_team_players(sport_path, season, event_id, comp_id, team_id):
    """Get all players for a team with their game stats."""
    url = f"{ESPN_CORE}/{sport_path}/events/{event_id}/competitions/{comp_id}/competitors/{team_id}/roster"
    data = _fetch_json(url)
    if not data:
        return []

    entries = data.get("entries", data.get("items", []))
    players = []
    for entry in entries:
        pid = entry.get("playerId")
        jersey = entry.get("jersey", "")
        starter = entry.get("starter", False)
        pos_id = entry.get("position", {}).get("$ref", "").rstrip("?").split("/")[-1] if entry.get("position") else ""

        name = _get_athlete_name(sport_path, season, pid)
        position = _get_position_name(sport_path, pos_id) if pos_id else ""

        # Parse position_id from ref URL
        if not position and "positions/" in str(entry.get("position", {})):
            pos_ref = entry.get("position", {}).get("$ref", "")
            pos_id = pos_ref.split("positions/")[-1].split("?")[0]
            position = POSITION_NAMES.get(pos_id, "")

        stats = {}
        batting = {}
        mlb_pitching = {}

        if sport_path.startswith("basketball"):
            stats = _player_basketball_stats(sport_path, event_id, comp_id, team_id, pid)
        elif sport_path.startswith("baseball"):
            mlb = _player_mlb_stats(sport_path, event_id, comp_id, team_id, pid)
            batting = mlb.get("batting", {})
            mlb_pitching = mlb.get("pitching", {})

        player_data = {
            "id": pid,
            "name": name,
            "jersey": jersey,
            "position": position,
            "starter": starter,
        }

        if sport_path.startswith("basketball"):
            player_data["stats"] = {
                "MIN": stats.get("minutes", 0),
                "PTS": int(stats.get("points", 0)),
                "REB": int(stats.get("rebounds", 0)),
                "AST": int(stats.get("assists", 0)),
                "3PM": int(stats.get("threePointFieldGoalsMade", 0)),
                "STL": int(stats.get("steals", 0)),
                "BLK": int(stats.get("blocks", 0)),
                "TO": int(stats.get("turnovers", 0)),
                "PF": int(stats.get("fouls", 0)),
                "FGM": int(stats.get("fieldGoalsMade", 0)),
                "FGA": int(stats.get("fieldGoalsAttempted", 0)),
                "FTM": int(stats.get("freeThrowsMade", 0)),
                "FTA": int(stats.get("freeThrowsAttempted", 0)),
            }
            player_data["PRA"] = player_data["stats"]["PTS"] + player_data["stats"]["REB"] + player_data["stats"]["AST"]
        elif sport_path.startswith("baseball"):
            player_data["batting"] = batting
            player_data["pitching"] = mlb_pitching

        players.append(player_data)

    return players


def get_boxscore(sport: str, event_id: int) -> Optional[dict]:
    """Get full box score for a game by sport and ESPN event ID."""
    sport_path = SPORT_PATHS.get(sport.lower())
    if not sport_path:
        return None

    season = 2026
    comp_id = event_id

    # Fetch competition to get teams
    comp_url = f"{ESPN_CORE}/{sport_path}/events/{event_id}/competitions/{comp_id}/competitors"
    comp_data = _fetch_json(comp_url)
    if not comp_data:
        return None

    items = comp_data.get("items", [])
    teams = []
    for item in items:
        team_id = item.get("id")
        home_away = item.get("homeAway", "")
        score_data = _fetch_json(item.get("score", {}).get("$ref", "") if item.get("score") else None) or {}
        team_abbr = ""

        # Try to get team abbreviation from the team ref
        team_ref = item.get("team", {}).get("$ref", "")
        if team_ref:
            team_info = _fetch_json(team_ref)
            if team_info:
                team_abbr = team_info.get("abbreviation", "")

        score = score_data.get("value", 0) or 0
        players = get_team_players(sport_path, season, event_id, comp_id, team_id)

        # Sort: starters first, then by name
        players.sort(key=lambda p: (not p.get("starter"), p.get("name", "")))

        teams.append({
            "team_id": team_id,
            "abbreviation": team_abbr,
            "home_away": home_away,
            "score": int(score) if score else 0,
            "players": players,
        })

    # Get status
    status_url = f"{ESPN_CORE}/{sport_path}/events/{event_id}/competitions/{comp_id}"
    status_data = _fetch_json(status_url) or {}
    status = status_data.get("status", {})
    period = status.get("period", 0)
    clock = status.get("displayClock", "")
    state = status.get("type", {}).get("name", "")

    return {
        "sport": sport.upper(),
        "event_id": event_id,
        "status": state,
        "period": period,
        "clock": clock,
        "teams": teams,
    }


def get_active_events(sport: str) -> list:
    """Get list of active (live + today) ESPN event IDs for a sport."""
    sport_path = SPORT_PATHS.get(sport.lower())
    if not sport_path:
        return []

    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard"
    data = _fetch_json(scoreboard_url)
    if not data:
        return []

    events = []
    for ev in data.get("events", []):
        comps = ev.get("competitions", [])
        if not comps:
            continue
        status = comps[0].get("status", {}).get("type", {}).get("name", "")
        events.append({
            "id": int(ev.get("id", 0)),
            "shortName": ev.get("shortName", ""),
            "status": status,
            "home": comps[0].get("competitors", [{}])[0].get("team", {}).get("abbreviation", ""),
            "away": comps[0].get("competitors", [{}])[1].get("team", {}).get("abbreviation", "") if len(comps[0].get("competitors", [])) > 1 else "",
            "home_score": comps[0].get("competitors", [{}])[0].get("score", "0"),
            "away_score": comps[0].get("competitors", [{}])[1].get("score", "0") if len(comps[0].get("competitors", [])) > 1 else "0",
        })
    return events
