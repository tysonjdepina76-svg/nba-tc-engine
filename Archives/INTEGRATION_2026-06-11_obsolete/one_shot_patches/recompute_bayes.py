"""Recompute WNBA projections with Bayesian shrinkage, compare to old TC projections.

Reads the picks files for ATL@CHI and DAL@MIN, and the matching final boxes,
and shows what the hit/miss verdict WOULD have been if the picks had been
generated with Bayesian shrinkage (per-stat alpha) instead of raw × 0.85 × norm.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tc_math import project_stat

LOG_DIR = Path("/home/workspace/Daily_Log")
FINAL_DIR = LOG_DIR / "final"

# load a final box to read actual stats
def load_box(path):
    d = json.loads(path.read_text())
    team_blocks = d.get("teams") or []
    name = d.get("name", "")
    away, home = (name.split(" at ", 1) + ["", ""])[:2] if " at " in name else ("", "")
    players = {}
    for t in team_blocks:
        for a in t.get("players", []):
            nm = (a.get("name") or "").lower()
            if not nm:
                continue
            try:
                minutes = float(a.get("minutes") or 0)
            except (ValueError, TypeError):
                minutes = 0.0
            players[nm] = {
                "points": int(a.get("points") or 0),
                "rebounds": int(a.get("rebounds") or 0),
                "assists": int(a.get("assists") or 0),
                "steals": int(a.get("steals") or 0),
                "blocks": int(a.get("blocks") or 0),
                "3pm": int(a.get("threePointMade") or 0),
                "minutes": minutes,
                "team": t.get("team", ""),
            }
    return players, away, home

STAT_KEY = {"PTS": "points", "REB": "rebounds", "AST": "assists", "STL": "steals", "BLK": "blocks", "3PM": "3pm"}

results = {"old_hit": 0, "old_miss": 0, "new_hit": 0, "new_miss": 0, "flipped": 0}

for game in ["proj_WNBA_ATL_at_CHI", "proj_WNBA_DAL_at_MIN"]:
    picks_file = LOG_DIR / "2026-06-09" / f"{game}.json"
    if not picks_file.exists():
        continue
    data = json.loads(picks_file.read_text())
    picks = data["picks"]

    # find matching final box
    box_file = None
    away = (data.get("away_team") or (data.get("matchup","@").split("@")[0] if "@" in data.get("matchup","") else "")).upper()
    home = (data.get("home_team") or (data.get("matchup","@").split("@")[1] if "@" in data.get("matchup","") else "")).upper()
    # filename uses full names: AtlantaDream_AT_ChicagoSky
    team_codes = {"ATL": "Atlanta", "CHI": "Chicago", "DAL": "Dallas", "MIN": "Minnesota", "PHX": "Phoenix", "GS": "GoldenState", "LV": "Las", "LA": "Los", "NY": "NewYork", "CON": "Connecticut", "IND": "Indiana", "SEA": "Seattle", "WAS": "Washington"}
    away_full = team_codes.get(away, away)
    home_full = team_codes.get(home, home)
    for f in FINAL_DIR.glob("*final*.json"):
        n = f.name.lower()
        if away_full.lower() in n and home_full.lower() in n:
            box_file = f
            break
    if not box_file:
        print(f"  no box for {game}")
        continue
    box, away_full, home_full = load_box(box_file)

    print(f"\n=== {game} (final box: {box_file.name}) ===")
    print(f"{'player':<22} {'stat':<5} {'dir':<5} {'old_tc':<7} {'new_tc':<7} {'actual':<6} {'old':<4} {'new':<4}")

    for p in picks:
        player = p["player"]
        stat = p["stat"].upper()
        direction = p["direction"].upper()
        old_tc = p.get("tc_projection", 0)
        raw_avg = p.get("raw_average", 0)
        status = p.get("status", "ACTIVE")

        # new projection with Bayesian
        new_tc = project_stat(STAT_KEY.get(stat, "points").replace("points", "pts").replace("rebounds", "reb").replace("assists", "ast").replace("steals", "stl").replace("blocks", "blk").replace("3pm", "3pm"), raw_avg, status, "WNBA")

        # find player in box (last-name match)
        last = player.split()[-1].lower()
        actual = None
        for k, v in box.items():
            if last in k:
                actual = v.get(STAT_KEY.get(stat, "points"), 0)
                break

        if actual is None:
            old_v = new_v = "?"
        else:
            old_v = "HIT" if (direction == "OVER" and actual > old_tc) or (direction == "UNDER" and actual < old_tc) else "MISS"
            new_v = "HIT" if (direction == "OVER" and actual > new_tc) or (direction == "UNDER" and actual < new_tc) else "MISS"
            if old_v == "HIT": results["old_hit"] += 1
            if old_v == "MISS": results["old_miss"] += 1
            if new_v == "HIT": results["new_hit"] += 1
            if new_v == "MISS": results["new_miss"] += 1
            if old_v != new_v:
                results["flipped"] += 1

        print(f"{player:<22} {stat:<5} {direction:<5} {old_tc:<7.2f} {new_tc:<7.2f} {actual!s:<6} {old_v:<4} {new_v:<4}")

print(f"\n=== Summary ===")
print(f"Old (no Bayes): {results['old_hit']}H / {results['old_miss']}M  ({results['old_hit']/(results['old_hit']+results['old_miss'])*100:.1f}%)")
print(f"New (Bayes):    {results['new_hit']}H / {results['new_miss']}M  ({results['new_hit']/(results['new_hit']+results['new_miss'])*100:.1f}%)")
print(f"Flipped:        {results['flipped']}")
