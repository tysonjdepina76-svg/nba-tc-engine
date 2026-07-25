#!/usr/bin/env python3
"""Build NHL player stats from roster + ESPN API for season averages (off-season stub)."""
import json, sys, os, time
import requests

ROSTERS = "/home/workspace/data/rosters/nhl_rosters.json"
OUTPUT = "/home/workspace/data/nhl_player_stats.json"

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
                # Try ESPN player stats
                pid = p.get("id", "")
                if pid:
                    r = requests.get(
                        f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/athletes/{pid}/statistics",
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
                            # Map ESPN names to TC names
                            for espn_k, tc_k in {
                                "goals": "G", "assists": "A", "points": "PTS",
                                "shotsOnGoal": "SOG", "hits": "HITS",
                                "blocks": "BLK", "penaltyMinutes": "PIM",
                                "saves": "SAVES", "goalsAgainst": "GA"
                            }.items():
                                if espn_k in season_data:
                                    mapped[tc_k] = round(season_data[espn_k], 1)
                            
                            if mapped:
                                stats[init_name] = {
                                    "season": mapped,
                                    "recent5": mapped,
                                    "team": team_abbr,
                                }
                
                # Minimal stub if no ESPN data
                if init_name not in stats:
                    stats[init_name] = {
                        "season": {"G": 0.0, "A": 0.0, "PTS": 0.0},
                        "recent5": {"G": 0.0, "A": 0.0, "PTS": 0.0},
                        "team": team_abbr,
                    }
                
                done += 1
                if done % 50 == 0:
                    print(f"  {done}/{total} NHL players...")
                
                time.sleep(0.5)  # rate limit
            except Exception as e:
                # Stub
                stats[init_name] = {
                    "season": {"G": 0.0, "A": 0.0, "PTS": 0.0},
                    "recent5": {"G": 0.0, "A": 0.0, "PTS": 0.0},
                    "team": team_abbr,
                }
                done += 1
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"NHL stats: {len(stats)} players → {OUTPUT}")


if __name__ == "__main__":
    build()
