#!/usr/bin/env python3
"""Generate WNBA projections from ESPN boxscores for a given date."""
import json
import os
import sys
from datetime import datetime
import requests

DAILY_LOG = "/home/workspace/Daily_Log"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"

WNBA_STATS = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO", "OREB", "DREB", "PF"]
ESPN_TO_TC_STAT = {"3PT": "3PM"}

def fetch_scoreboard(date_str):
    """Fetch WNBA scoreboard for a date (YYYY-MM-DD or YYYYMMDD)."""
    if "-" in date_str:
        date_param = date_str.replace("-", "")
    else:
        date_param = date_str
        date_str = f"{date_param[:4]}-{date_param[4:6]}-{date_param[6:]}"

    url = f"{ESPN_SCOREBOARD}?dates={date_param}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return date_str, r.json()

def fetch_boxscore(game_id):
    """Fetch boxscore for a game."""
    url = f"{ESPN_SUMMARY}?event={game_id}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def extract_players(boxscore, team_side):
    """Extract player stats from boxscore for a team (home/away).
    Matches by team displayName from header.competitions, since the
    boxscore team dict no longer carries homeAway in the new API format."""
    players = []
    team_data = boxscore.get("boxscore", {}).get("players", [])

    competitors = (boxscore.get("header", {}).get("competitions", [{}])[0]
                   .get("competitors", []))

    target_team_name = None
    for comp in competitors:
        if comp.get("homeAway") == team_side:
            target_team_name = comp.get("team", {}).get("displayName", "")
            break

    if not target_team_name:
        return players, "Unknown"

    for team_entry in team_data:
        entry_team_name = team_entry.get("team", {}).get("displayName", "")
        if entry_team_name != target_team_name:
            continue

        stats_list = team_entry.get("statistics", [])
        for cat in stats_list:
            stat_names = cat.get("names", [])
            athletes = cat.get("athletes", [])
            for athlete in athletes:
                athlete_data = athlete.get("athlete", {})
                stats_raw = athlete.get("stats", [])

                projections = []
                for i, val in enumerate(stats_raw):
                    stat_name = stat_names[i] if i < len(stat_names) else "UNK"
                    stat_name_tc = ESPN_TO_TC_STAT.get(stat_name, stat_name)
                    if stat_name_tc in WNBA_STATS:
                        try:
                            proj = float(val) if val not in (None, "", "-") else 0.0
                        except (ValueError, TypeError):
                            proj = 0.0
                        projections.append({
                            "stat": stat_name_tc,
                            "projection": proj,
                            "line": proj - 0.5 if proj > 0 else -0.5,
                            "edge": 0,
                            "period": "GAME"
                        })

                if projections:
                    players.append({
                        "player": athlete_data.get("displayName", "Unknown"),
                        "team": target_team_name,
                        "starter": athlete.get("starter", False),
                        "did_not_play": athlete.get("didNotPlay", False),
                        "status": "Active" if not athlete.get("didNotPlay", False) else "DNP",
                        "projections": projections
                    })
        break

    return players, target_team_name

def build_game_projection(date_str, matchup, away_players, home_players, away_team, home_team):
    """Build projection JSON for a single game."""
    return {
        "away": {
            "all": {"players": away_players},
            "starters": {"players": [p for p in away_players if p.get("starter")]}
        },
        "home": {
            "all": {"players": home_players},
            "starters": {"players": [p for p in home_players if p.get("starter")]}
        }
    }

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    
    date_str, scoreboard = fetch_scoreboard(date_str)
    events = scoreboard.get("events", [])
    
    if not events:
        print(f"No WNBA games on {date_str}")
        return
    
    print(f"Found {len(events)} WNBA games for {date_str}")
    
    date_dir = os.path.join(DAILY_LOG, date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    all_players = []
    per_game_files = []
    
    for event in events:
        game_id = event["id"]
        competitors = event.get("competitions", [{}])[0].get("competitors", [])
        
        away_team_abbr = ""
        home_team_abbr = ""
        for comp in competitors:
            if comp.get("homeAway") == "away":
                away_team_abbr = comp.get("team", {}).get("abbreviation", "AWAY")
            else:
                home_team_abbr = comp.get("team", {}).get("abbreviation", "HOME")
        
        matchup = f"{away_team_abbr}_at_{home_team_abbr}"
        print(f"  {matchup} (ID: {game_id})")
        
        try:
            boxscore = fetch_boxscore(game_id)
        except Exception as e:
            print(f"    ⚠️ Failed to fetch boxscore: {e}")
            continue
        
        away_players, away_team = extract_players(boxscore, "away")
        home_players, home_team = extract_players(boxscore, "home")
        
        print(f"    {len(away_players)} away + {len(home_players)} home players")
        
        game_proj = build_game_projection(date_str, matchup, away_players, home_players, away_team, home_team)
        
        out_path = os.path.join(date_dir, f"proj_WNBA_{matchup}.json")
        with open(out_path, "w") as f:
            json.dump(game_proj, f, indent=2)
        print(f"    ✅ Saved {out_path}")
        
        per_game_files.append(out_path)
        
        for p in away_players:
            p['matchup'] = matchup
            all_players.append(p)
        for p in home_players:
            p['matchup'] = matchup
            all_players.append(p)
    
    combined_path = os.path.join(date_dir, f"proj_WNBA_.json")
    combined = {
        "date": date_str,
        "sport": "WNBA",
        "per_game_files": per_game_files,
        "players": all_players
    }
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"  ✅ Combined: {combined_path} ({len(all_players)} total players)")

if __name__ == "__main__":
    main()
