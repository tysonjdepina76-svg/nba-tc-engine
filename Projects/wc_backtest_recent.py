#!/usr/bin/env python3
# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
WC Backtest Grader — grades 2026-06-29 WC picks against pulled boxscores.

Inputs:
- /home/workspace/Daily_Log/worldcup/20260629/picks.csv   (player, stat, line, over_price)
- /home/workspace/Daily_Log/worldcup/20260629/props.json  (edge_pct per prop)
- /home/workspace/Reports/wc_player_stats_20260630.csv   (actual stats by player)

Direction rule (TC self-edge):
- edge_pct >= 0  → OVER lean
- edge_pct < 0   → UNDER lean
Fallback if edge_pct missing:
- over_price >= 0 (e.g. +110) → OVER lean
- over_price < 0 (e.g. -110)  → UNDER lean

Output:
- /home/workspace/Reports/wc_backtest_recent_20260630.csv
- Hit-rate summary printed + appended to /home/workspace/Daily_Log/wc_hitrate_log.json
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

PICKS_CSV = Path("/home/workspace/Daily_Log/worldcup/20260629/picks.csv")
PROPS_JSON = Path("/home/workspace/Daily_Log/worldcup/20260629/props.json")
BOX_CSV    = Path("/home/workspace/Reports/wc_player_stats_20260630.csv")
OUT_CSV    = Path("/home/workspace/Reports/wc_backtest_recent_20260630.csv")
LOG_JSON   = Path("/home/workspace/Daily_Log/wc_hitrate_log.json")

# map pick "stat" → boxscore column
STAT_MAP = {
    "fouls":      "foulsCommitted",
    "shots":      "totalShots",
    "sot":        "shotsOnTarget",
    "goals":      "totalGoals",
    "assists":    "goalAssists",
    "yellow":     "yellowCards",
    "red":        "redCards",
    "own_goals":  "ownGoals",
    "saves":      "saves",
    "shots_faced":"shotsFaced",
}

def load_edge_map():
    """edge_pct[(matchup_short, player, stat)] -> edge_pct."""
    p = json.loads(PROPS_JSON.read_text())
    edge = {}
    for match in p:
        short = match["short_name"]
        pp = match.get("player_props", {})
        for player, props in pp.items():
            for stat, info in props.items():
                edge[(short, player, stat)] = info.get("edge_pct", 0.0)
    return edge

def load_boxscores():
    """player_name -> {match_short: {stat_col: val}}"""
    box = defaultdict(dict)
    with open(BOX_CSV) as f:
        for row in csv.DictReader(f):
            key = row["player_name"].strip()
            box[key][row["match"]] = row
    return box

def normalize_name(n: str) -> str:
    """Strip accents + lower for fuzzy match."""
    import unicodedata
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    return n.lower().strip()

def find_actual(box, player, matchup_short):
    """Try exact then normalized name match."""
    if player in box and matchup_short in box[player]:
        return box[player][matchup_short]
    n = normalize_name(player)
    for pname, matches in box.items():
        if normalize_name(pname) == n and matchup_short in matches:
            return matches[matchup_short]
    # last try: across matches
    for pname, matches in box.items():
        if normalize_name(pname) == n:
            return list(matches.values())[0]
    return None

def main():
    edge_map = load_edge_map()
    box = load_boxscores()

    graded = []
    skipped = defaultdict(int)
    with open(PICKS_CSV) as f:
        for row in csv.DictReader(f):
            matchup = row["matchup"]
            player  = row["player"]
            stat    = row["stat"]
            line    = float(row["line"]) if row["line"] else 0.0
            over_price = float(row["over_price"]) if row["over_price"] else 0.0

            edge = edge_map.get((matchup, player, stat))
            if edge is None:
                direction = "OVER" if over_price >= 0 else "UNDER"
                edge_src  = "price-fallback"
            else:
                direction = "OVER" if edge >= 0 else "UNDER"
                edge_src  = "edge"

            actual_row = find_actual(box, player, matchup)
            if not actual_row:
                skipped["no_boxscore_match"] += 1
                continue

            col = STAT_MAP.get(stat)
            if not col or col not in actual_row:
                skipped["unknown_stat"] += 1
                continue

            try:
                actual = float(actual_row[col])
            except (ValueError, TypeError):
                skipped["non_numeric_actual"] += 1
                continue

            hit = (actual > line) if direction == "OVER" else (actual < line)
            graded.append({
                "matchup": matchup,
                "player": player,
                "stat": stat,
                "line": line,
                "direction": direction,
                "actual": actual,
                "edge_pct": edge if edge is not None else 0.0,
                "edge_src": edge_src,
                "result": "HIT" if hit else "MISS",
            })

    # write CSV
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        if graded:
            w = csv.DictWriter(f, fieldnames=list(graded[0].keys()))
            w.writeheader()
            w.writerows(graded)

    # summary
    total = len(graded)
    hits  = sum(1 for g in graded if g["result"] == "HIT")
    misses = total - hits
    hit_rate = (hits / total * 100) if total else 0.0

    by_dir = defaultdict(lambda: [0,0])  # dir -> [hits, total]
    by_stat = defaultdict(lambda: [0,0])
    by_match = defaultdict(lambda: [0,0])
    for g in graded:
        by_dir[g["direction"]][1] += 1
        by_dir[g["direction"]][0] += (g["result"]=="HIT")
        by_stat[g["stat"]][1] += 1
        by_stat[g["stat"]][0] += (g["result"]=="HIT")
        by_match[g["matchup"]][1] += 1
        by_match[g["matchup"]][0] += (g["result"]=="HIT")

    print("=" * 60)
    print(f"WC BACKTEST — graded {total} picks against boxscores")
    print(f"Hits: {hits} | Misses: {misses} | Hit rate: {hit_rate:.1f}%")
    print(f"Skipped: {dict(skipped)}")
    print()
    print("By direction:")
    for d,(h,t) in sorted(by_dir.items()):
        print(f"  {d:<6} {h}/{t} = {(h/t*100 if t else 0):.1f}%")
    print("By stat:")
    for s,(h,t) in sorted(by_stat.items(), key=lambda x: -x[1][1]):
        print(f"  {s:<12} {h}/{t} = {(h/t*100 if t else 0):.1f}%")
    print("By matchup:")
    for m,(h,t) in sorted(by_match.items()):
        print(f"  {m:<14} {h}/{t} = {(h/t*100 if t else 0):.1f}%")

    # log
    log = []
    if LOG_JSON.exists():
        try: log = json.loads(LOG_JSON.read_text())
        except: log = []
    log.append({
        "date": "2026-06-29",
        "graded_at": "2026-06-30",
        "total": total, "hits": hits, "misses": misses,
        "hit_rate": round(hit_rate, 2),
        "by_direction": {d: {"hits":h,"total":t,"rate":round(h/t*100,2) if t else 0}
                         for d,(h,t) in by_dir.items()},
        "by_stat": {s: {"hits":h,"total":t,"rate":round(h/t*100,2) if t else 0}
                    for s,(h,t) in by_stat.items()},
    })
    LOG_JSON.write_text(json.dumps(log, indent=2))
    print(f"\nWrote: {OUT_CSV}")
    print(f"Logged: {LOG_JSON}")

if __name__ == "__main__":
    main()