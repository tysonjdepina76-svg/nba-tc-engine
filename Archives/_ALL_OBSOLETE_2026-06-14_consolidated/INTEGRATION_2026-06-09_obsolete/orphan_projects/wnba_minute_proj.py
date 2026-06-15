import os, sys, json, requests
import math
from collections import defaultdict
from datetime import datetime
import csv

BASE_URL = "https://true.zo.space/api/tc"

def fetch_wnba_games():
    r = requests.get(BASE_URL, params={"sport": "WNBA", "mode": "live-stats"},
                     timeout=30, headers={"Accept": "application/json"})
    return r.json()

def get_player_minutes(player_name, sport, season_avg_min=None):
    if season_avg_min is None:
        if "Williams" in player_name or "Copper" in player_name or "Bueckers" in player_name:
            return 30
        elif "Akoa" in player_name or "Miles" in player_name:
            return 28
        elif "Johnson" in player_name:
            return 25
        else:
            return 22
    return season_avg_min

def project_with_minutes(tc_pts, minutes, league_avg_ppm=0.536):
    ppm_per_min = tc_pts / 30.0
    return round(ppm_per_min * minutes, 1)

def main():
    games = fetch_wnba_games()
    game_list = games.get("games", [])
    print(f"=== WNBA LIVE SCRAPE - MINUTE PROJECTION ({len(game_list)} games) ===")
    rows = []
    for g in game_list:
        away = g.get("away", {})
        home = g.get("home", {})
        matchup = g.get("matchup") or g.get("name", "")
        sport = "WNBA"
        for team_dict in [away, home]:
            leaders = team_dict.get("leaders", [])
            for l in leaders:
                if not isinstance(l, dict): continue
                pname = l.get("name") or l.get("athlete", {}).get("displayName", "?")
                pts = l.get("pts") or l.get("value")
                if pts is None: continue
                minutes = get_player_minutes(pname, sport)
                tc_old = pts
                tc_new = project_with_minutes(pts, minutes)
                edge = round(tc_new - (round(tc_new*0.88)), 1)
                result = "PENDING"
                if g.get("completed"):
                    actual = l.get("actual") or l.get("score", pts)
                    result = "HIT" if actual >= tc_new else "MISS"
                rows.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "league": sport,
                    "matchup": matchup,
                    "player": pname,
                    "team": team_dict.get("team", "?"),
                    "minutes_projected": minutes,
                    "tc_old": tc_old,
                    "tc_with_minutes": tc_new,
                    "line": round(tc_new*0.88, 1),
                    "edge": edge,
                    "result": result,
                })
                print(f"  {pname:30s} Min={minutes:2d} TC_old={tc_old:5.1f} TC_new={tc_new:5.1f} Line={round(tc_new*0.88,1):4.1f} [{result}]")
    out = f"/home/workspace/Daily_Log/wnba_minute_proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        if rows: w.writeheader(); w.writerows(rows)
    print(f"Saved: {out}")
    print(f"Total picks: {len(rows)}")

if __name__ == "__main__":
    main()
