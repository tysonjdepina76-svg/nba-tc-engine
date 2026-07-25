#!/usr/bin/env python3
"""Build NFL player stats from roster + ESPN API (pre-season stub)."""
import json, sys, os, time
import requests

ROSTERS = "/home/workspace/data/rosters/nfl_rosters.json"
OUTPUT = "/home/workspace/data/nfl_player_stats.json"

def build():
    with open(ROSTERS) as f:
        rosters = json.load(f)
    
    stats = {}
    total = sum(len(v.get("players", [])) for v in rosters.values())
    done = 0
    
    for team_abbr, team_data in rosters.items():
        for p in team_data.get("players", []):
            name = p["name"]
            if not name or name.startswith("-"):
                continue
            parts = name.split()
            if len(parts) < 2:
                continue
            init_name = f"{parts[0][0]}. {parts[-1]}"
            
            try:
                pid = p.get("id", "")
                if pid:
                    r = requests.get(
                        f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/athletes/{pid}/statistics",
                        timeout=10
                    )
                    if r.status_code == 200:
                        d = r.json()
                        splits = d.get("splits", {}).get("categories", [])
                        season_data = {}
                        for cat in splits:
                            for split in cat.get("splits", []):
                                for s in split.get("stats", []):
                                    k = s.get("name", "")
                                    v = s.get("value", 0)
                                    try:
                                        season_data[k] = float(v)
                                    except (ValueError, TypeError):
                                        pass
                        
                        if season_data:
                            mapped = {}
                            for espn_k, tc_k in {
                                "passingYards": "PASS_YDS", "passingTouchdowns": "TD",
                                "rushingYards": "RUSH_YDS", "receivingYards": "REC_YDS",
                                "receptions": "REC", "totalTackles": "TACKLES",
                                "sacks": "SACKS", "interceptions": "INT",
                                "fieldGoalsMade": "FG"
                            }.items():
                                if espn_k in season_data:
                                    mapped[tc_k] = round(season_data[espn_k], 1)
                            
                            if mapped:
                                stats[init_name] = {
                                    "season": mapped,
                                    "recent5": mapped,
                                    "team": team_abbr,
                                }
                
                if init_name not in stats:
                    stats[init_name] = {
                        "season": {"PASS_YDS": 0.0, "RUSH_YDS": 0.0, "REC_YDS": 0.0},
                        "recent5": {"PASS_YDS": 0.0, "RUSH_YDS": 0.0, "REC_YDS": 0.0},
                        "team": team_abbr,
                    }
                
                done += 1
                if done % 20 == 0:
                    print(f"  {done}/{total} NFL players...")
                
                time.sleep(0.5)
            except Exception:
                stats[init_name] = {
                    "season": {"PASS_YDS": 0.0, "RUSH_YDS": 0.0, "REC_YDS": 0.0},
                    "recent5": {"PASS_YDS": 0.0, "RUSH_YDS": 0.0, "REC_YDS": 0.0},
                    "team": team_abbr,
                }
                done += 1
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"NFL stats: {len(stats)} players → {OUTPUT}")


if __name__ == "__main__":
    build()
