#!/usr/bin/env python3
"""
Backfill projection files for dates with no projections.
1. Pull ESPN boxscore data for each game on a date
2. Convert boxscore stats into the projection file format daily_picks expects
3. Run daily_picks to generate picks
4. Run grade_daily_picks to grade results
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

LOG = Path("/home/workspace/Daily_Log")
PROJ_DIR = Path("/home/workspace/Projects")
ESPN_WNBA_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates="
ESPN_MLB_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates="

STAT_MAP_ESPN_TO_TC = {
    "points": "PTS",
    "rebounds": "REB", 
    "assists": "AST",
    "steals": "STL",
    "blocks": "BLK",
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted": "3PM",
    "turnovers": "TO",
    "offensiveRebounds": "OREB",
    "defensiveRebounds": "DREB",
    "fouls": "PF",
    "minutes": "MIN",
}

TEAM_ABBREV_MAP = {
    "GSV": "Golden State Valkyries",
    "ATL": "Atlanta Dream", "NY": "New York Liberty", "MIN": "Minnesota Lynx",
    "CON": "Connecticut Sun", "SEA": "Seattle Storm", "PHX": "Phoenix Mercury",
    "CHI": "Chicago Sky", "IND": "Indiana Fever", "WSH": "Washington Mystics",
    "DAL": "Dallas Wings", "LA": "Los Angeles Sparks", "LV": "Las Vegas Aces",
    "TOR": "Toronto Tempo", "POR": "Portland Fire",
}

def fetch_espn_events(date_str):
    """Fetch ESPN scoreboard for a given date."""
    espn_date = date_str.replace("-", "")
    url = ESPN_WNBA_URL + espn_date
    print(f"  Fetching {url}...")
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        events = data.get("events", [])
        print(f"  ESPN returned {len(events)} events")
        return events
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return []


def fetch_espn_boxscore(game_id):
    """Fetch full boxscore from ESPN."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={game_id}"
    print(f"    Fetching boxscore {game_id}...")
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"    ERROR fetching boxscore {game_id}: {e}")
        return {}


def boxscore_to_projections(raw):
    """Convert ESPN boxscore to projection format."""
    box = raw.get("boxscore", {})
    players = box.get("players", [])
    
    if not players:
        return {}
    
    result = {"away": {"all": {}, "starters": {}}, "home": {"all": {}, "starters": {}}}
    
    for team_entry in players:
        team_abbrev = team_entry.get("team", {}).get("abbreviation", "?")
        team_name = team_entry.get("team", {}).get("displayName", team_abbrev)
        side = None
        
        competitions = raw.get("gameInfo", {}).get("competitions", [])
        if competitions:
            comp = competitions[0]
            if comp.get("competitors", [{}])[0].get("team", {}).get("abbreviation") == team_abbrev:
                side = "away"
            elif comp.get("competitors", [{}])[1].get("team", {}).get("abbreviation") == team_abbrev:
                side = "home"
        
        if not side:
            # Fallback: first entry is away, second is home
            side = "away" if team_entry == players[0] else "home"
        
        stats_list = team_entry.get("statistics", [])
        if not stats_list:
            continue
        
        stat_cat = stats_list[0]
        keys_list = stat_cat.get("keys", [])
        athletes = stat_cat.get("athletes", [])
        
        all_players = []
        starter_players = []
        
        for a in athletes:
            name = a.get("athlete", {}).get("displayName", "?")
            stats_vals = a.get("stats", [])
            did_not_play = a.get("didNotPlay", False)
            starter = a.get("starter", False)
            
            # Build player record
            player = {
                "player": name,
                "team": team_name,
                "starter": starter,
                "did_not_play": did_not_play,
                "status": "DNP" if did_not_play else "Active",
                "projections": []  # We'll use final stats as "projections"
            }
            
            if not did_not_play and len(keys_list) == len(stats_vals):
                stats_dict = dict(zip(keys_list, stats_vals))
                for espn_key, tc_stat in STAT_MAP_ESPN_TO_TC.items():
                    val = stats_dict.get(espn_key, "0")
                    try:
                        if tc_stat == "3PM":
                            made = int(val.split("-")[0]) if "-" in val else 0
                            player["projections"].append({
                                "stat": tc_stat,
                                "projection": made,
                                "line": max(0, made - 0.5),
                                "edge": 0,
                                "period": "GAME",
                            })
                        else:
                            num = float(val) if val.replace(".", "").replace("+", "").replace("-", "").isdigit() else 0
                            player["projections"].append({
                                "stat": tc_stat,
                                "projection": num,
                                "line": num - 0.5,
                                "edge": 0,
                                "period": "GAME",
                            })
                    except (ValueError, IndexError):
                        pass
            
            all_players.append(player)
            if starter:
                starter_players.append(player)
        
        result[side]["all"] = {"players": all_players, "team": team_name}
        result[side]["starters"] = {"players": starter_players, "team": team_name}
    
    return result


def convert_projections_for_daily_picks(proj_data):
    """
    Convert the boxscore-derived projections into the format daily_picks expects.
    The TC projection format has:
    {
        "away": {
            "all": {"players": [{"player":..., "projections": [{"stat":..., "projection":..., "line":...}]}]},
            "starters": {"players": [...]}
        },
        "home": {...}
    }
    """
    return proj_data


def main():
    dates = [datetime.now().strftime("%Y-%m-%d")]
    
    for date_str in dates:
        print(f"\n{'='*60}")
        print(f"BACKFILLING {date_str}")
        print(f"{'='*60}")
        
        date_dir = LOG / date_str
        date_dir.mkdir(exist_ok=True)
        
        # Step 1: Get games from ESPN
        events = fetch_espn_events(date_str)
        if not events:
            print(f"  No ESPN events for {date_str}, skipping.")
            continue
        
        all_projections = []
        per_game_files = []
        
        for event in events:
            comp = event.get("competitions", [{}])[0]
            away_abbrev = comp.get("competitors", [{}])[0].get("team", {}).get("abbreviation", "?")
            home_abbrev = comp.get("competitors", [{}])[1].get("team", {}).get("abbreviation", "?")
            game_id = event.get("id", "?")
            matchup_key = f"{away_abbrev}_at_{home_abbrev}"
            
            print(f"  Game: {matchup_key} (ID: {game_id})")
            
            # Step 2: Fetch boxscore
            raw = fetch_espn_boxscore(game_id)
            if not raw:
                continue
            
            # Step 3: Convert to projections
            proj = boxscore_to_projections(raw)
            if not proj:
                print(f"    No boxscore data extracted")
                continue
            
            # Step 4: Save per-game projection file
            proj_file = date_dir / f"proj_WNBA_{matchup_key}.json"
            with open(proj_file, "w") as f:
                json.dump(proj, f, indent=2)
            print(f"    ✅ Saved {proj_file}")
            per_game_files.append(str(proj_file))
            
            # Step 5: Flatten for combined file
            for side in ("away", "home"):
                for group in ("all", "starters"):
                    players = proj.get(side, {}).get(group, {}).get("players", [])
                    for p in players:
                        p["_matchup"] = matchup_key
                        p["_side"] = side
                        p["_group"] = group
                        all_projections.append(p)
        
        # Step 6: Save combined file
        if all_projections:
            combined_file = date_dir / f"proj_WNBA_.json"
            combined = {
                "date": date_str,
                "sport": "WNBA",
                "players": all_projections,
                "per_game_files": per_game_files,
            }
            with open(combined_file, "w") as f:
                json.dump(combined, f, indent=2)
            print(f"  ✅ Combined proj: {combined_file} ({len(all_projections)} total players)")
        
        if not per_game_files:
            print(f"  ⚠️ No game files created for {date_str}")
    
    print(f"\n{'='*60}")
    print(f"BACKFILL COMPLETE — Now run daily_picks and grade")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
