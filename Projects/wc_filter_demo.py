#!/usr/bin/env python3
"""
WC filter dry-run against stored picks.csv (2026-06-29).
Applies: WC UNDER-only, fouls+shots only.
"""
import csv, json
from pathlib import Path
from collections import defaultdict

PICKS = Path("/home/workspace/Daily_Log/worldcup/20260629/picks.csv")
PROPS = Path("/home/workspace/Daily_Log/worldcup/20260629/props.json")
BOX   = Path("/home/workspace/Reports/wc_player_stats_20260630.csv")

# load props for edge_pct
props = json.loads(PROPS.read_text())
edge_map = {}
for m in props:
    short = m.get("short_name", "")
    for pname, pprops in m.get("player_props", {}).items():
        for stat, info in pprops.items():
            ep = info.get("edge_pct")
            if ep is not None:
                edge_map[(short, pname, stat)] = ep

# load boxscores: player → match → row
box = defaultdict(dict)
with open(BOX) as f:
    for r in csv.DictReader(f):
        box[r["player_name"].strip()][r["match"]] = r

STAT_MAP = {"fouls":"foulsCommitted","shots":"totalShots","sot":"shotsOnTarget"}

ALLOWED_STATS = {"fouls","shots"}

hits = misses = blocked = 0
over_blocked = 0
stat_blocked = 0

for r in csv.DictReader(open(PICKS)):
    matchup = r["matchup"]
    player  = r["player"].strip()
    stat    = r["stat"]
    line    = float(r["line"] or 0)
    edge    = edge_map.get((matchup, player, stat))

    # WC filter: stats only
    if stat not in ALLOWED_STATS:
        stat_blocked += 1
        continue

    # WC filter: UNDER only — if edge says OVER, block
    direction = "UNDER" if (edge is None or edge <= 0.05) else "OVER"
    if direction == "OVER":
        over_blocked += 1
        continue

    # grade against boxscore
    actual_row = box.get(player, {}).get(matchup)
    if not actual_row:
        blocked += 1
        continue
    col = STAT_MAP.get(stat)
    if not col:
        blocked += 1
        continue
    actual = float(actual_row.get(col, 0) or 0)
    if actual < line:
        hits += 1
    else:
        misses += 1

total = hits + misses
print(f"Filtered picks: {total}")
print(f"  Hits: {hits}")
print(f"  Misses: {misses}")
print(f"  Hit rate: {hits/total*100:.1f}%" if total else "no graded")
print(f"  Stat blocked (non-fouls/shots): {stat_blocked}")
print(f"  OVER blocked: {over_blocked}")
print(f"  No boxscore match: {blocked}")
