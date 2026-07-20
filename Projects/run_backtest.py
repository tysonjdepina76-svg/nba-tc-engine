#!/usr/bin/env python3
"""Backtest engine: grade picks against box score actuals and save results."""

import json
import sqlite3
import os
from datetime import date

DB = "/home/workspace/Projects/data/picks.db"
BOX_ALL = "/home/workspace/Daily_Log/boxscores/boxscore_all_20260720.json"
BOX_MLB = "/home/workspace/Daily_Log/boxscores/boxscore_mlb_20260720.json"
BOX_WNBA = "/home/workspace/Daily_Log/boxscores/boxscore_wnba_20260720.json"
PICKS_DATE = "2026-07-19"
OUT_DIR = f"/home/workspace/Daily_Log/backtests/{PICKS_DATE}"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load box scores ──
def load_box(path, sport_key):
    """Load box scores from SDIO-style JSON: {sports: {SPORT: {games: [...]}}}"""
    boxes = {}
    if not os.path.exists(path):
        return boxes
    with open(path) as f:
        raw = json.load(f)
    games = raw.get("sports", {}).get(sport_key, {}).get("games", [])
    for g in games:
        key = g.get("shortName", "").replace(" @ ", "@").replace(" ", "")
        players = {}
        for side in ("home", "away"):
            for p in g.get(side, {}).get("players", []):
                name = p.get("name", "")
                stats = p.get("stats", {})
                if not stats:
                    continue
                actuals = {}
                # MLB stats (SDIO uses baseball-specific names)
                mlb_stat_map = {
                    "AVG": "battingAverage", "H": "hits", "R": "runs", "RBI": "RBIs",
                    "HR": "homeRuns", "SB": "stolenBases", "BB": "walks", "SO": "strikeouts",
                    "TB": "totalBases", "OBP": "onBasePercentage"
                }
                # WNBA stats (SDIO uses basketball-specific names)
                wnba_stat_map = {
                    "PTS": "points", "AST": "assists", "REB": "rebounds",
                    "STL": "steals", "BLK": "blocks", "3PM": "threePointFieldGoalsMade",
                    "TO": "turnovers"
                }
                for tc_stat, box_stat in {**mlb_stat_map, **wnba_stat_map}.items():
                    v = stats.get(box_stat)
                    if v is not None:
                        actuals[tc_stat.lower()] = v
                players[name] = actuals
        boxes[key] = {"players": players}
    return boxes

box_mlb = load_box(BOX_MLB, "MLB")
box_wnba = load_box(BOX_WNBA, "WNBA")
boxes = {**box_mlb, **box_wnba}
print(f"Loaded {len(box_mlb)} MLB + {len(box_wnba)} WNBA box score games")

# ── Pull picks ──
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
picks = conn.execute(
    "SELECT * FROM picks WHERE date=? ORDER BY league, matchup, player", (PICKS_DATE,)
).fetchall()
conn.close()
print(f"Loaded {len(picks)} picks for {PICKS_DATE}")

# ── Grade ──
results = []
hit, miss, nodata = 0, 0, 0
by_sport = {}
by_stat = {}
by_signal = {}

for p in picks:
    league = p["league"]
    player = p["player"]
    stat = p["stat"].lower()
    direction = p["direction"]
    market_line = p["market_line"]
    tc_proj = p["tc_projection"]
    signal = p["signal"]
    matchup = p["matchup"].replace("@", "@").replace(" ", "")

    # Find box score
    game = boxes.get(matchup, {})
    player_stats = game.get("players", {}).get(player, {})

    actual = player_stats.get(stat, None)
    result = "NO_DATA" if actual is None else ("HIT" if (direction == "OVER" and actual > market_line) or (direction == "UNDER" and actual < market_line) else "MISS")

    if result == "HIT":
        hit += 1
    elif result == "MISS":
        miss += 1
    else:
        nodata += 1

    # Track by sport
    if league not in by_sport:
        by_sport[league] = {"hits": 0, "miss": 0, "nodata": 0}
    by_sport[league]["hits" if result == "HIT" else "miss" if result == "MISS" else "nodata"] += 1

    # Track by stat
    if stat not in by_stat:
        by_stat[stat] = {"hits": 0, "miss": 0, "nodata": 0}
    by_stat[stat]["hits" if result == "HIT" else "miss" if result == "MISS" else "nodata"] += 1

    # Track by signal
    if signal not in by_signal:
        by_signal[signal] = {"hits": 0, "miss": 0, "nodata": 0}
    by_signal[signal]["hits" if result == "HIT" else "miss" if result == "MISS" else "nodata"] += 1

    results.append({
        "date": PICKS_DATE,
        "league": league,
        "matchup": p["matchup"],
        "player": player,
        "stat": stat,
        "direction": direction,
        "market_line": market_line,
        "tc_projection": tc_proj,
        "signal": signal,
        "actual": actual,
        "result": result,
    })

graded = hit + miss
total = len(picks)
hit_pct = (hit / graded * 100) if graded else 0.0

summary = {
    "date": PICKS_DATE,
    "total_picks": total,
    "graded_picks": graded,
    "no_data_picks": nodata,
    "hits": hit,
    "misses": miss,
    "hit_rate": round(hit_pct, 1),
    "by_sport": {k: {
        "hits": v["hits"], "miss": v["miss"], "nodata": v["nodata"],
        "hit_rate": round(v["hits"] / (v["hits"] + v["miss"]) * 100, 1) if (v["hits"] + v["miss"]) else 0
    } for k, v in by_sport.items()},
    "by_stat": {k: {
        "hits": v["hits"], "miss": v["miss"], "nodata": v["nodata"],
        "hit_rate": round(v["hits"] / (v["hits"] + v["miss"]) * 100, 1) if (v["hits"] + v["miss"]) else 0
    } for k, v in by_stat.items()},
    "by_signal": {k: {
        "hits": v["hits"], "miss": v["miss"], "nodata": v["nodata"],
        "hit_rate": round(v["hits"] / (v["hits"] + v["miss"]) * 100, 1) if (v["hits"] + v["miss"]) else 0
    } for k, v in by_signal.items()},
}

# ── Save ──
with open(f"{OUT_DIR}/results.json", "w") as f:
    json.dump(results, f, indent=2)
with open(f"{OUT_DIR}/summary.json", "w") as f:
    json.dump(summary, f, indent=2)

# ── Report ──
print(f"\n=== BACKTEST {PICKS_DATE} ===")
print(f"Total: {total} | Graded: {graded} | No Data: {nodata}")
print(f"Hits: {hit} / Misses: {miss} | Hit Rate: {hit_pct:.1f}%")
print(f"\nBy Sport:")
for s, v in by_sport.items():
    graded_s = v["hits"] + v["miss"]
    if graded_s:
        print(f"  {s}: {v['hits']}/{graded_s} = {v['hits']/graded_s*100:.1f}% ({v['nodata']} no-data)")
    else:
        print(f"  {s}: no graded picks ({v['nodata']} no-data)")
print(f"\nBy Stat:")
for s, v in sorted(by_stat.items(), key=lambda x: -(x[1]["hits"] + x[1]["miss"])):
    graded_s = v["hits"] + v["miss"]
    if graded_s:
        print(f"  {s}: {v['hits']}/{graded_s} = {v['hits']/graded_s*100:.1f}%")
    else:
        print(f"  {s}: no graded")
print(f"\nBy Signal:")
for s, v in by_signal.items():
    graded_s = v["hits"] + v["miss"]
    print(f"  {s}: {v['hits']}/{graded_s} = {v['hits']/graded_s*100:.1f}% ({v['nodata']} no-data)")
print(f"\nSaved to: {OUT_DIR}/")

# ── Append to combined CSV ──
combined_csv = "/home/workspace/Daily_Log/backtests/combined_backtest.csv"
import csv
exists = os.path.exists(combined_csv)
with open(combined_csv, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["date","league","matchup","team","player","role","status","stat","direction","market_line","tc_projection","tc_target","edge","threshold","raw_average","source","actual","result"])
    if not exists:
        writer.writeheader()
    for r in results:
        writer.writerow({
            "date": r["date"], "league": r["league"], "matchup": r["matchup"],
            "team": "", "player": r["player"], "role": "", "status": "ACTIVE",
            "stat": r["stat"].upper(), "direction": r["direction"],
            "market_line": r["market_line"], "tc_projection": r["tc_projection"],
            "tc_target": r["market_line"], "edge": round(r["tc_projection"] - r["market_line"], 2),
            "threshold": 0, "raw_average": r["tc_projection"],
            "source": r["signal"], "actual": r.get("actual", ""), "result": r["result"]
        })

print(f"Appended {len(results)} rows to {combined_csv}")
