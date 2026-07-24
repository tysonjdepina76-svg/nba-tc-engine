#!/usr/bin/env python3
"""
WNBA Pre-Game Projection Generator
Fetches tonight's WNBA schedule from ESPN, pulls roster + season stats,
generates self-edge TC projections (Odds API quota is maxed).
Outputs Daily_Log/YYYY-MM-DD/proj_WNBA_{matchup}.json and proj_WNBA_YYYY-MM-DD.json
"""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import httpx

LOG = Path("/home/workspace/Daily_Log")
SPORT = "wnba"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"
# ESPN season stats endpoint per team
ESPN_TEAM_STATS = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{team_id}/statistics"

STAT_BUDGET_MAP = {
    "PTS": "pointsPerGame",
    "REB": "reboundsPerGame",
    "AST": "assistsPerGame",
    "STL": "stealsPerGame",
    "BLK": "blocksPerGame",
    "3PM": "threePointFieldGoalsMadePerGame",
    "TO": "turnoversPerGame",
    "FGM": "fieldGoalsMadePerGame",
    "FGA": "fieldGoalsAttemptedPerGame",
    "FTM": "freeThrowsMadePerGame",
    "FTA": "freeThrowsAttemptedPerGame",
    "PF": "foulsPerGame",
    "MIN": "minutesPerGame",
    "OREB": "offensiveReboundsPerGame",
    "DREB": "defensiveReboundsPerGame",
}


def fetch_json(url: str, timeout: int = 15) -> dict:
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠️  Failed: {url} — {e}")
        return {}


def fetch_todays_games() -> list:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    url = f"{ESPN_SCOREBOARD}?dates={today}"
    data = fetch_json(url)
    events = data.get("events", [])
    print(f"  ESPN scoreboard returned {len(events)} WNBA events for {today}")
    return events


def get_team_abbrev(team_data: dict) -> str:
    return team_data.get("abbreviation", "???")


def get_team_id(team_data: dict) -> str:
    return team_data.get("id", "")


def fetch_team_season_stats(team_id: str) -> dict:
    url = ESPN_TEAM_STATS.format(team_id=team_id)
    data = fetch_json(url)
    return data


def extract_player_stats(team_stats_data: dict) -> dict:
    player_map = {}
    categories = team_stats_data.get("splits", {}).get("categories", [])
    for cat in categories:
        stat_name = cat.get("name", "")
        stats_list = cat.get("stats", [])
        for s in stats_list:
            full_name = s.get("name", "")
            player_map.setdefault(full_name, {"name": full_name})
            player_map[full_name][stat_name] = s.get("value", 0.0)
    return player_map


def fetch_roster_from_summary(game_id: str) -> dict:
    url = f"{ESPN_SUMMARY}?event={game_id}"
    data = fetch_json(url)
    result = {"away": {"players": [], "team": ""}, "home": {"players": [], "team": ""}}

    boxscore = data.get("boxscore", {})
    teams = boxscore.get("teams", [])
    for t in teams:
        side = "away" if t.get("homeAway") == "away" else "home"
        team_info = t.get("team", {})
        result[side]["team"] = get_team_abbrev(team_info)

        stats_raw = t.get("statistics", [])
        if not stats_raw:
            continue
        names = stats_raw[0].get("names", [])
        athletes = t.get("athletes", [])
        for a in athletes:
            athlete_info = a.get("athlete", {})
            full_name = athlete_info.get("displayName", "")
            stats_vals = a.get("stats", [])
            if not stats_vals:
                continue
            player = {"name": full_name, "team": result[side]["team"]}
            for i, name in enumerate(names):
                if i < len(stats_vals):
                    player[name] = stats_vals[i]
            result[side]["players"].append(player)

    return result


def get_wnba_season_stats_from_espn() -> dict:
    teams_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams"
    data = fetch_json(teams_url)
    all_teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])

    all_players = defaultdict(dict)
    for team in all_teams:
        tid = team.get("team", {}).get("id", "")
        team_abbrev = get_team_abbrev(team.get("team", {}))
        if not tid:
            continue
        roster_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{tid}/roster"
        roster_data = fetch_json(roster_url)
        athletes = roster_data.get("athletes", [])
        for entry in athletes:
            items = entry.get("items", [])
            for item in items:
                display = item.get("displayName", "")
                pos = item.get("position", {}).get("abbreviation", "")
                all_players[display]["name"] = display
                all_players[display]["team"] = team_abbrev
                all_players[display]["position"] = pos
    return dict(all_players)


def build_self_edge_projections(players: list, team_abbrev: str) -> list:
    results = []
    for p in players:
        name = p.get("name", "")
        proj_list = []
        for stat_key in ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO", "PRA"]:
            val = p.get(f"avg_{stat_key}", 0)
            if not val and stat_key != "PRA":
                continue
            if stat_key == "PRA":
                val = p.get("avg_PTS", 0) + p.get("avg_REB", 0) + p.get("avg_AST", 0)
            proj_list.append({
                "stat": stat_key,
                "projection": round(val, 2),
                "line": round(val - 0.5, 2) if val else 0,
                "edge": 0,
                "period": "GAME",
            })
        if proj_list:
            results.append({
                "player": name,
                "team": team_abbrev,
                "position": p.get("position", ""),
                "starter": p.get("starter", False),
                "projections": proj_list,
            })
    return results


def generate_wnba_pre_game(date_str: str):
    print(f"\n{'='*60}")
    print(f"WNBA PRE-GAME PROJECTIONS — {date_str}")
    print(f"{'='*60}")

    date_dir = LOG / date_str
    date_dir.mkdir(exist_ok=True)

    events = fetch_todays_games()
    if not events:
        print("  No WNBA games today.")
        return []

    all_projections = []

    for event in events:
        game_id = event.get("id", "")
        competitions = event.get("competitions", [])
        if not competitions:
            continue

        comp = competitions[0]
        home_team = comp.get("competitors", [{}])[0]
        away_team = comp.get("competitors", [{}])[1] if len(comp.get("competitors", [])) > 1 else {}

        home_abbrev = get_team_abbrev(home_team.get("team", {}))
        away_abbrev = get_team_abbrev(away_team.get("team", {}))
        matchup = f"{away_abbrev}@{home_abbrev}"

        print(f"  Game: {matchup} (ID: {game_id})")

        home_tid = get_team_id(home_team.get("team", {}))
        away_tid = get_team_id(away_team.get("team", {}))

        home_players = fetch_team_roster_with_stats(home_tid)
        away_players = fetch_team_roster_with_stats(away_tid)

        result = {
            "away": {
                "all": {"players": build_self_edge_projections(away_players, away_abbrev), "team": away_abbrev},
                "starters": {"players": [p for p in build_self_edge_projections(away_players, away_abbrev) if p.get("starter")], "team": away_abbrev},
            },
            "home": {
                "all": {"players": build_self_edge_projections(home_players, home_abbrev), "team": home_abbrev},
                "starters": {"players": [p for p in build_self_edge_projections(home_players, home_abbrev) if p.get("starter")], "team": home_abbrev},
            },
        }

        proj_file = date_dir / f"proj_WNBA_{matchup}.json"
        with open(proj_file, "w") as f:
            json.dump(result, f, default=str)
        print(f"    ✅ Saved {proj_file} ({len(result['away']['all']['players'])+len(result['home']['all']['players'])} players)")

        for side in ["away", "home"]:
            for p in result[side]["all"]["players"]:
                for proj in p.get("projections", []):
                    all_projections.append({
                        "player": p["player"],
                        "team": p["team"],
                        "stat": proj["stat"],
                        "projection": proj["projection"],
                        "line": proj["line"],
                        "edge": proj["edge"],
                        "period": proj["period"],
                        "matchup": matchup,
                        "sport": "wnba",
                    })

    if all_projections:
        combined_file = date_dir / f"proj_WNBA_{date_str}.json"
        with open(combined_file, "w") as f:
            json.dump(all_projections, f, default=str)
        print(f"\n  ✅ Combined: {combined_file} ({len(all_projections)} total projections)")

    return all_projections


def fetch_team_roster_with_stats(team_id: str) -> list:
    roster_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{team_id}/roster"
    roster_data = fetch_json(roster_url)

    players = []
    athletes = roster_data.get("athletes", [])
    for entry in athletes:
        items = entry.get("items", [])
        for item in items:
            display = item.get("displayName", "")
            pos = item.get("position", {}).get("abbreviation", "")
            stats_list = item.get("statistics", {}).get("splits", {}).get("categories", [{}])[0].get("stats", [])
            player = {"name": display, "position": pos}

            for s in stats_list:
                stat_name = s.get("name", "")
                val = s.get("value", 0)
                if stat_name in STAT_BUDGET_MAP.values():
                    for key, espn_name in STAT_BUDGET_MAP.items():
                        if espn_name == stat_name:
                            try:
                                player[f"avg_{key}"] = float(val)
                            except (ValueError, TypeError):
                                player[f"avg_{key}"] = 0.0

            players.append(player)

    return players


if __name__ == "__main__":
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if len(sys.argv) > 1:
        today = sys.argv[1]
    generate_wnba_pre_game(today)
