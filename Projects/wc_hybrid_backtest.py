#!/usr/bin/env python3
"""
WC Hybrid Backtest — applies v1 (raw TC), v2 (shrinkage), hybrid (ensemble),
and ensemble_of_hybrids to World Cup projections vs. actuals from cached boxscores.

APIs are capped — uses ONLY local files:
  - Daily_Log/wc_boxscores/*.json (35 cached final boxscores)
  - Daily_Log/wc_boxscore_registry.json (93 ESPN event IDs)
  - Daily_Log/YYYY-MM-DD/proj_WORLD_CUP_*.json (TC projections per game)

Output: wc_hybrid_backtest.csv with one row per player-stat per algorithm
"""

import json
import csv
import os
import math
from collections import defaultdict
from datetime import datetime

WORKSPACE = "/home/workspace"
BOXSCORE_DIR = os.path.join(WORKSPACE, "Daily_Log", "wc_boxscores")
DAILY_LOG = os.path.join(WORKSPACE, "Daily_Log")

STAT_MAP = {
    "totalGoals": "goals",
    "goalAssists": "ast",
    "totalShots": "shots",
    "shotsOnTarget": "sot",
    "foulsCommitted": "fouls",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "tackles": "tackles",
    "passes": "passes",
}

REVERSE_STAT_MAP = {v: k for k, v in STAT_MAP.items()}

# ── v1: raw TC baseline ──
def v1_raw(tc_proj: float) -> float:
    return tc_proj

# ── v2: shrinkage toward league average ──
def v2_shrinkage(tc_proj: float, league_avg: float, factor: float = 0.30) -> float:
    if tc_proj <= 0 or league_avg <= 0:
        return tc_proj
    return tc_proj * (1 - factor) + league_avg * factor

# ── hybrid: blend v1 + v2 ──
def hybrid_blend(v1: float, v2: float, weight_v2: float = 0.4) -> float:
    return v1 * (1 - weight_v2) + v2 * weight_v2

# ── ensemble_of_hybrids: average of v1, v2, hybrid ──
def ensemble(v1: float, v2: float, hyb: float) -> float:
    return (v1 + v2 + hyb) / 3.0


def load_boxscore_player_stats(boxscore_file: str) -> list:
    """Extract player-level actual stats from a boxscore JSON."""
    with open(boxscore_file) as f:
        data = json.load(f)

    players = []
    summary = data.get("summary_api", {}).get("boxscore", {})

    # Check for player stats in the boxscore form
    # ESPN v2 boxscore has players nested in 'players' array per team
    for team_data in summary.get("form", []):
        team_name = team_data.get("team", {}).get("displayName", "?")
        for player_data in team_data.get("players", []):
            stats = {}
            for stat_entry in player_data.get("statistics", []):
                name = stat_entry.get("name", "")
                if name in STAT_MAP:
                    stats[STAT_MAP[name]] = float(stat_entry.get("value", 0))
            if stats:
                players.append({
                    "player": player_data.get("athlete", {}).get("displayName", "?"),
                    "team": team_name,
                    "stats": stats,
                })
    return players


def load_tc_projections(proj_file: str) -> dict:
    """Load TC projections from a proj file, keyed by player name."""
    with open(proj_file) as f:
        data = json.load(f)

    projections = {}
    for side in ["away", "home"]:
        team_data = data.get(side, {})
        for player in team_data.get("all", {}).get("players", []):
            name = player.get("name", "")
            if not name:
                continue
            proj = {}
            for stat_key in ["goals", "shots", "sot", "passes", "tackles",
                           "yellow_cards", "red_cards", "ast"]:
                tc_val = player.get(f"tc_{stat_key}")
                if tc_val is not None:
                    proj[stat_key] = float(tc_val)
            if proj:
                projections[name] = proj
    return projections


def match_players(actual_players: list, tc_projections: dict) -> list:
    """Fuzzy-match actual players to TC projections by name."""
    matched = []
    for ap in actual_players:
        name = ap["player"].strip().lower()
        # Try exact match first
        tc_name = None
        for tc_key in tc_projections:
            if tc_key.strip().lower() == name:
                tc_name = tc_key
                break
        # Try partial match (last name)
        if tc_name is None:
            last_name = name.split()[-1] if name.split() else name
            for tc_key in tc_projections:
                if last_name in tc_key.strip().lower():
                    tc_name = tc_key
                    break
        if tc_name:
            matched.append({
                "actual_player": ap["player"],
                "tc_player": tc_name,
                "team": ap["team"],
                "actual_stats": ap["stats"],
                "tc_proj": tc_projections[tc_name],
            })
    return matched


def run_backtest():
    """Main backtest: walk all boxscores, find matching projections, grade."""
    if not os.path.isdir(BOXSCORE_DIR):
        print(f"ERROR: Boxscore dir not found: {BOXSCORE_DIR}")
        return

    boxscore_files = sorted([
        f for f in os.listdir(BOXSCORE_DIR) if f.endswith(".json")
    ])

    print(f"Found {len(boxscore_files)} boxscore files")

    # Collect all proj files
    proj_files = {}
    for date_dir in sorted(os.listdir(DAILY_LOG)):
        dir_path = os.path.join(DAILY_LOG, date_dir)
        if not os.path.isdir(dir_path) or not date_dir.startswith("2026-"):
            continue
        for fname in os.listdir(dir_path):
            if fname.startswith("proj_WORLD_CUP_") and fname.endswith(".json"):
                proj_files[fname] = os.path.join(dir_path, fname)

    print(f"Found {len(proj_files)} WC projection files")

    results = []
    league_stats = defaultdict(list)
    graded_games = 0

    for bfile in boxscore_files:
        full_path = os.path.join(BOXSCORE_DIR, bfile)
        try:
            # Get matchup from filename: "760414_Czechia_South_Korea.json"
            parts = bfile.replace(".json", "").split("_")
            if len(parts) >= 3:
                away = parts[1]
                home = parts[2]
            else:
                continue

            # Find matching proj file
            matching_proj = None
            for fname, fpath in proj_files.items():
                if away.lower() in fname.lower() and home.lower() in fname.lower():
                    matching_proj = fpath
                    break

            if not matching_proj:
                continue

            # Load both
            actual_players = load_boxscore_player_stats(full_path)
            tc_projections = load_tc_projections(matching_proj)
            matched = match_players(actual_players, tc_projections)

            if not matched:
                continue

            graded_games += 1

            for m in matched:
                for stat in ["goals", "shots", "sot", "ast", "tackles",
                           "yellow_cards", "red_cards"]:
                    actual = m["actual_stats"].get(stat)
                    tc = m["tc_proj"].get(stat)
                    if actual is None or tc is None or tc <= 0:
                        continue

                    # Compute all 4 algorithms
                    league_avg = 0.5 if stat == "goals" else (
                        1.5 if stat == "shots" else 1.0
                    )

                    v1 = v1_raw(tc)
                    v2 = v2_shrinkage(tc, league_avg, factor=0.30)
                    hyb = hybrid_blend(v1, v2, weight_v2=0.4)
                    ens = ensemble(v1, v2, hyb)

                    results.append({
                        "game": f"{away}@{home}",
                        "date": bfile[:6],  # YYMMDD from filename prefix
                        "player": m["actual_player"],
                        "team": m["team"],
                        "stat": stat,
                        "actual": actual,
                        "v1_raw": round(v1, 3),
                        "v2_shrinkage": round(v2, 3),
                        "hybrid": round(hyb, 3),
                        "ensemble": round(ens, 3),
                    })

        except Exception as e:
            print(f"  Error processing {bfile}: {e}")
            continue

    if not results:
        print("No matched results — boxscore format may not contain player stats")
        return

    # ── Write CSV ──
    out_path = os.path.join(WORKSPACE, "reports", "wc_hybrid_backtest_results.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "game", "date", "player", "team", "stat", "actual",
            "v1_raw", "v2_shrinkage", "hybrid", "ensemble"
        ])
        writer.writeheader()
        writer.writerows(results)

    # ── Compute hit rates ──
    def hit_rate(proj: float, actual: float) -> bool:
        if abs(actual - proj) / max(proj, 0.01) <= 0.50:
            return True
        return False

    algo_counts = defaultdict(lambda: {"hits": 0, "total": 0})
    for r in results:
        actual = r["actual"]
        for algo in ["v1_raw", "v2_shrinkage", "hybrid", "ensemble"]:
            algo_counts[algo]["total"] += 1
            if hit_rate(r[algo], actual):
                algo_counts[algo]["hits"] += 1

    print(f"\n=== WC HYBRID BACKTEST RESULTS ===\n")
    print(f"Games graded: {graded_games}")
    print(f"Player-stat rows: {len(results)}")
    print(f"Output: {out_path}\n")
    print(f"{'Algorithm':<20} {'Hits':>6} {'Total':>6} {'Hit Rate':>10}")
    print("-" * 45)
    for algo in ["v1_raw", "v2_shrinkage", "hybrid", "ensemble"]:
        c = algo_counts[algo]
        hr = (c["hits"] / c["total"] * 100) if c["total"] > 0 else 0
        print(f"{algo:<20} {c['hits']:>6} {c['total']:>6} {hr:>9.1f}%")

    # ── Per-stat breakdown ──
    print(f"\n=== Per-Stat Hit Rates ===\n")
    stat_counts = defaultdict(lambda: defaultdict(lambda: {"hits": 0, "total": 0}))
    for r in results:
        stat = r["stat"]
        for algo in ["v1_raw", "v2_shrinkage", "hybrid", "ensemble"]:
            stat_counts[stat][algo]["total"] += 1
            if hit_rate(r[algo], r["actual"]):
                stat_counts[stat][algo]["hits"] += 1

    print(f"{'Stat':<15}", end="")
    for algo in ["v1_raw", "v2_shrinkage", "hybrid", "ensemble"]:
        print(f" {algo:>10}", end="")
    print()
    print("-" * 60)
    for stat in sorted(stat_counts.keys()):
        print(f"{stat:<15}", end="")
        for algo in ["v1_raw", "v2_shrinkage", "hybrid", "ensemble"]:
            c = stat_counts[stat][algo]
            hr = (c["hits"] / c["total"] * 100) if c["total"] > 0 else 0
            print(f" {hr:>9.1f}%", end="")
        print()

    return results


if __name__ == "__main__":
    run_backtest()
