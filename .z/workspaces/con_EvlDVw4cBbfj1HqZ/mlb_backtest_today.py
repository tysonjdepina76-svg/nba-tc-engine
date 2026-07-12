#!/usr/bin/env python3
"""MLB backtest today: compare proj_MLB_*.json (7/11) to actual boxscores."""
import json, unicodedata
from pathlib import Path
from collections import defaultdict

ws = Path("/home/workspace")
log = ws / "Daily_Log"
bx_dir = log / "mlb_boxscores"
proj_dir = log / "2026-07-11"
out_dir = ws / "Reports"
out_dir.mkdir(exist_ok=True)

def norm(n):
    return unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii").lower().strip()

TEAM_ABBR = {
    "Arizona Diamondbacks": "ARI", "Athletics": "ATH", "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS", "Chicago Cubs": "CHC",
    "Chicago White Sox": "CHW", "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL", "Detroit Tigers": "DET", "Houston Astros": "HOU",
    "Kansas City Royals": "KC", "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA", "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN",
    "New York Mets": "NYM", "New York Yankees": "NYY", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

# Load boxscores - need to map "ARI at LAD" -> file
box = {}  # short_matchup -> {player_norm: stats}
for f in bx_dir.glob("mlb_*_final_*.json"):
    d = json.loads(f.read_text())
    pl = d.get("players", d.get("boxscore", {}).get("players", {}))
    if not pl:
        continue
    aw = d.get("away_team", "")
    hm = d.get("home_team", "")
    away_abbr = TEAM_ABBR.get(aw, aw[:3].upper())
    home_abbr = TEAM_ABBR.get(hm, hm[:3].upper())
    short = f"{away_abbr}@{home_abbr}"
    inner = {}
    for name, p in pl.items():
        if isinstance(p, dict):
            inner[norm(name)] = p
    box[short] = inner

print(f"Boxscores loaded: {len(box)} matchups")

# Load projections
STAT_MAP = {"pts": "pts", "runs": "runs", "rbi": "rbi", "hits": "hits",
            "hr": "hr", "sb": "sb", "avg": "avg", "obp": "obp",
            "total_bases": "total_bases", "hits_allowed": "hits_allowed"}

graded = []
skipped = defaultdict(int)
for proj_file in sorted(proj_dir.glob("proj_MLB_*.json")):
    d = json.loads(proj_file.read_text())
    matchup = d.get("matchup", "")
    if " at " in matchup:
        parts = matchup.split(" at ")
        short = f"{parts[0]}@{parts[1]}"
    else:
        continue
    if short not in box:
        skipped["no_boxscore"] += 1
        continue
    bx = box[short]
    for side in ["away", "home"]:
        roster = d.get(side, {})
        for cat in ["starters", "bench", "lineup", "batting_order", "pitchers"]:
            players = roster.get(cat, [])
            if isinstance(players, dict):
                plist = []
                for v in players.values():
                    if isinstance(v, list):
                        plist.extend(v)
                    else:
                        plist.append(v)
            else:
                plist = players or []
            for p in plist:
                if not isinstance(p, dict):
                    continue
                name = p.get("name", "")
                nm = norm(name)
                if nm not in bx:
                    skipped["no_player_boxscore"] += 1
                    continue
                actual = bx[nm]
                for stat in ["pts", "runs", "rbi", "hits", "hr", "sb", "avg",
                             "total_bases", "hits_allowed", "walks", "strikeouts"]:
                    proj_val = p.get(stat) or p.get(f"proj_{stat}") or p.get("projected_" + stat)
                    if proj_val is None:
                        continue
                    actual_val = actual.get(stat)
                    if actual_val is None:
                        skipped["no_actual"] += 1
                        continue
                    try:
                        pv = float(proj_val)
                        av = float(actual_val)
                    except (ValueError, TypeError):
                        continue
                    hit = av >= pv if stat not in ["era", "whip"] else av <= pv
                    err = av - pv
                    graded.append({
                        "matchup": short, "side": side, "cat": cat, "player": name,
                        "stat": stat, "proj": round(pv, 3), "actual": round(av, 3),
                        "err": round(err, 3), "hit": int(hit)
                    })

print(f"Graded picks: {len(graded)}")
print(f"Skipped: {dict(skipped)}")

# Aggregate by stat
by_stat = defaultdict(lambda: {"n": 0, "hits": 0, "mae": 0.0, "bias": 0.0})
for g in graded:
    s = by_stat[g["stat"]]
    s["n"] += 1
    s["hits"] += g["hit"]
    s["mae"] += abs(g["err"])
    s["bias"] += g["err"]

print("\n=== MLB BACKTEST 2026-07-11 (today) ===")
print(f"{'Stat':<15} {'N':>5} {'Hit%':>7} {'MAE':>8} {'Bias':>8}")
print("-" * 50)
for stat, s in sorted(by_stat.items()):
    n = s["n"]
    if n == 0: continue
    hp = s["hits"]/n*100
    mae = s["mae"]/n
    bias = s["bias"]/n
    print(f"{stat:<15} {n:>5} {hp:>6.1f}% {mae:>8.2f} {bias:>+8.2f}")

# Save report
report = out_dir / "MLB_Backtest_Today_20260711.md"
with report.open("w") as f:
    f.write(f"# MLB Backtest — 2026-07-11\n\n")
    f.write(f"Matchups: {len(box)} | Picks graded: {len(graded)}\n\n")
    f.write(f"## Hit Rate by Stat\n\n")
    f.write(f"| Stat | N | Hit% | MAE | Bias |\n|---|---:|---:|---:|---:|\n")
    for stat, s in sorted(by_stat.items()):
        n = s["n"]
        if n == 0: continue
        hp = s["hits"]/n*100
        mae = s["mae"]/n
        bias = s["bias"]/n
        f.write(f"| {stat} | {n} | {hp:.1f}% | {mae:.2f} | {bias:+.2f} |\n")
    f.write(f"\n## Matchups Covered\n\n")
    for m in sorted(box.keys()):
        f.write(f"- {m}\n")

print(f"\nReport: {report}")
