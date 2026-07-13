"""
Fetch live soccer games with lineups and live stats.
"""

import requests
from sources.utils.cache import cache_fetch

STAT_MAP = {
    "goals": "goals",
    "assists": "assists",
    "shots": "shots",
    "shotsOnGoal": "shots_on_target",
    "passesCompletedPercentage": "pass_pct",
    "tackles": "tackles",
    "fouls": "fouls"
}

def fetch_soccer_live_summary():
    """Fetch live soccer games with lineups and live stats."""
    scoreboard_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(scoreboard_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"source": "error", "games": [], "error": str(e)}

    live_games = []
    for event in data.get("events", []):
        status = event.get("status", {}).get("type", {}).get("state")
        if status not in ["in", "live"]:
            continue

        event_id = event.get("id")
        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/summary?event={event_id}"

        try:
            summary_resp = requests.get(summary_url, headers=headers, timeout=10)
            summary_resp.raise_for_status()
            summary = summary_resp.json()
        except Exception:
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
            "minute": event.get("status", {}).get("period", 0),
            "players": []
        }

        boxscore = summary.get("boxscore", {})

        for team_box in boxscore.get("teams", []):
            team_abbr = team_box.get("team", {}).get("abbreviation")
            for player in team_box.get("players", []):
                athlete = player.get("athlete", {})
                stats = player.get("stats", {})

                live_stats = {}
                for stat_group in stats.get("groups", []):
                    if stat_group.get("displayName") == "Game Stats":
                        for stat in stat_group.get("stats", []):
                            key = stat.get("name", "").lower()
                            if key in STAT_MAP:
                                try:
                                    live_stats[STAT_MAP[key]] = float(stat.get("value", 0))
                                except (ValueError, TypeError):
                                    live_stats[STAT_MAP[key]] = 0
                        break

                if live_stats:
                    game_info["players"].append({
                        "name": athlete.get("displayName", "Unknown"),
                        "team": team_abbr,
                        **live_stats
                    })

        live_games.append(game_info)

    return {"source": "ESPN Summary", "games": live_games}

def fetch_soccer_live_cached():
    return cache_fetch("soccer_live_summary", fetch_soccer_live_summary, ttl_hours=0.0167)
