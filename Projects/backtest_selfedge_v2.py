#!/usr/bin/env python3
import json, hashlib, csv, os, sys
from collections import defaultdict

STAT_SPREAD = {
    "H": 0.30, "2B": 0.30, "3B": 0.30, "R": 0.20, "RBI": 0.20, "BB": 0.20,
    "HR": 0.25, "SB": 0.25, "K": 0.25, "ER": 0.25, "IP": 0.15,
    "AVG": 0.15, "OBP": 0.15, "SLG": 0.15, "OPS": 0.15, "ERA": 0.15, "WHIP": 0.15,
}
MIN_EDGE = 0.05

def self_edge(stat, proj_val, hash_seed):
    spread = STAT_SPREAD.get(stat, 0.20)
    direction = "OVER" if hash_seed % 2 == 0 else "UNDER"
    if direction == "OVER":
        line = round(proj_val * (1 - spread * 0.5), 4)
        line = min(line, proj_val - MIN_EDGE)
        if line <= 0:
            line = MIN_EDGE
    else:
        line = round(proj_val * (1 + spread * 0.5), 4)
        line = max(line, proj_val + MIN_EDGE)
    if line == 0:
        line = MIN_EDGE
    edge = max(round(abs(proj_val - line), 4), MIN_EDGE)
    return line, direction, edge

proj_dir = "/home/workspace/Daily_Log/2026-07-25"
graded_csv = "/home/workspace/data/picks/mlb_2026-07-25_statcast_regraded.csv"

# Load actuals from graded file
actuals = {}
with open(graded_csv) as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row["player"].strip()
        stat = row["market"].strip()
        matchup = row["matchup"].strip()
        actual = float(row["actual"]) if row["actual"] and row["actual"] != "" else None
        key = f"{name}|{stat}|{matchup}"
        actuals[key] = actual

# Generate new picks from projection JSONs
new_picks = []
old_picks_for_compare = []

for fname in sorted(os.listdir(proj_dir)):
    if not fname.startswith("proj_MLB_") or not fname.endswith(".json"):
        continue
    with open(os.path.join(proj_dir, fname)) as f:
        proj = json.load(f)
    matchup = fname.replace("proj_MLB_", "").replace(".json", "")
    game_id = proj.get("game_id", 0)

    for player in proj.get("players", []):
        name = player["name"]
        team = player.get("team", "")
        projs = player.get("projections", {})
        for stat, vals in projs.items():
            proj_val = vals["projection"]
            old_line = vals.get("line", 0)
            old_edge = vals.get("edge", 0)
            old_dir = vals.get("direction", "UNDER")

            key = f"{name}|{stat}|{matchup}"
            hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)

            new_line, new_dir, new_edge = self_edge(stat, proj_val, hash_val)

            # Skip if proj_val is trivially zero
            if proj_val < 0.001:
                continue

            new_picks.append({
                "name": name, "team": team, "stat": stat, "matchup": matchup,
                "projection": proj_val, "line": new_line,
                "edge": new_edge, "direction": new_dir,
                "old_line": old_line, "old_edge": old_edge, "old_dir": old_dir,
                "actual": actuals.get(key),
            })

print(f"Generated {len(new_picks)} picks from {len([f for f in os.listdir(proj_dir) if f.startswith('proj_MLB_')])} projection files")

# Grade
has_actual = [p for p in new_picks if p["actual"] is not None]
print(f"Picks with actuals: {len(has_actual)} / {len(new_picks)}")

# NEW hit rate (direction-aware)
new_hits = 0
old_hits = 0
new_dir_counts = defaultdict(int)
old_dir_counts = defaultdict(int)
stat_new = defaultdict(lambda: [0, 0])  # hits, total
stat_old = defaultdict(lambda: [0, 0])

for p in new_picks:
    if p["actual"] is None:
        continue
    actual = p["actual"]

    # New: use new direction
    new_dir_counts[p["direction"]] += 1
    if p["direction"] == "OVER":
        hit = actual >= p["projection"]
    else:
        hit = actual <= p["projection"]
    if hit:
        new_hits += 1
        stat_new[p["stat"]][0] += 1
    stat_new[p["stat"]][1] += 1

    # Old: use old direction (all UNDER in the 7/25 dataset)
    old_dir_counts[p["old_dir"]] += 1
    if p["old_dir"] == "OVER":
        hit = actual >= p["projection"]
    else:
        hit = actual <= p["projection"]
    if hit:
        old_hits += 1
        stat_old[p["stat"]][0] += 1
    stat_old[p["stat"]][1] += 1

total = len(has_actual)
print(f"\n{'='*60}")
print(f"BACKTEST RESULTS: 7/25 MLB (SELF-EDGE v2)")
print(f"{'='*60}")
print(f"Total picks considered: {total}")
print(f"\nNEW SELF-EDGE (stat-aware spread + MIN_EDGE={MIN_EDGE}):")
print(f"  Hit rate: {new_hits}/{total} = {new_hits/total*100:.1f}%")
print(f"  Direction: {dict(new_dir_counts)}")
print(f"\nOLD SELF-EDGE (±2% spread):")
print(f"  Hit rate: {old_hits}/{total} = {old_hits/total*100:.1f}%")
print(f"  Direction: {dict(old_dir_counts)}")

print(f"\nBy STAT (NEW):")
for stat in sorted(stat_new.keys()):
    h, t = stat_new[stat]
    print(f"  {stat:6s}: {h}/{t} = {h/t*100:.1f}%")

print(f"\nBy STAT (OLD):")
for stat in sorted(stat_old.keys()):
    h, t = stat_old[stat]
    print(f"  {stat:6s}: {h}/{t} = {h/t*100:.1f}%")

# Save backtest CSV
out_csv = "/home/workspace/data/picks/backtest_selfedge_v2_0725.csv"
with open(out_csv, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "team", "stat", "matchup",
        "projection", "new_line", "new_edge", "new_direction",
        "old_line", "old_edge", "old_direction", "actual",
        "new_hit", "old_hit"])
    writer.writeheader()
    for p in new_picks:
        if p["actual"] is None:
            continue
        new_hit = (p["actual"] >= p["projection"]) if p["direction"] == "OVER" else (p["actual"] <= p["projection"])
        old_hit = (p["actual"] >= p["projection"]) if p["old_dir"] == "OVER" else (p["actual"] <= p["projection"])
        writer.writerow({
            "name": p["name"], "team": p["team"], "stat": p["stat"],
            "matchup": p["matchup"],
            "projection": p["projection"],
            "new_line": p["line"], "new_edge": p["edge"],
            "new_direction": p["direction"],
            "old_line": p["old_line"], "old_edge": p["old_edge"],
            "old_direction": p["old_dir"],
            "actual": p["actual"],
            "new_hit": new_hit, "old_hit": old_hit,
        })

print(f"\nBacktest CSV saved: {out_csv}")
