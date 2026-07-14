#!/usr/bin/env python3
"""
WC Picks Scorer — grades Daily_Log WORLD_CUP picks against available boxscores.
Since boxscores have team-level stats only, grades at game level:
  - Directional analysis (OVER/UNDER split)
  - Edge distribution  
  - Validates player names match known rosters
  - Flags the player-stat-level gap for when ESPN boxscores include player stats
"""

import csv
import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime

WORKSPACE = "/home/workspace"
DAILY_LOG = os.path.join(WORKSPACE, "Daily_Log")
BOXSCORE_DIR = os.path.join(DAILY_LOG, "wc_boxscores")

# Known WC teams (abbreviations used in picks)
WC_TEAMS = {
    "ALG", "ARG", "AUS", "AUT", "BEL", "BIH", "BRA", "CAN", "CPV", "CIV",
    "COD", "COL", "CRO", "CUW", "CZE", "ECU", "EGY", "ENG", "ESP", "FRA",
    "GER", "GHA", "HAI", "IRN", "IRQ", "JPN", "JOR", "KOR", "KSA", "MAR",
    "MEX", "NED", "NOR", "NZL", "PAN", "PAR", "POR", "QAT", "RSA", "SCO",
    "SEN", "SUI", "SWE", "TUN", "TUR", "URU", "USA", "UZB",
}

def load_boxscore_results():
    """Load game-level results (goals, cards) from cached boxscores."""
    results = {}
    if not os.path.isdir(BOXSCORE_DIR):
        return results
    for fname in sorted(os.listdir(BOXSCORE_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(BOXSCORE_DIR, fname)) as f:
            data = json.load(f)
        try:
            away = data["away"]["abbreviation"]
            home = data["home"]["abbreviation"]
            away_score = int(data["away"]["score"])
            home_score = int(data["home"]["score"])
            stats = data.get("home", {}).get("stats", {})
            key = f"{away}@{home}"
            results[key] = {
                "date": data.get("date", ""),
                "away_score": away_score,
                "home_score": home_score,
                "total_goals": away_score + home_score,
                "home_goals": int(stats.get("totalGoals", 0)),
                "home_assists": int(stats.get("goalAssists", 0)),
                "home_shots": int(stats.get("totalShots", 0)),
                "home_sot": int(stats.get("shotsOnTarget", 0)),
                "home_fouls": int(stats.get("foulsCommitted", 0)),
                "home_cards": int(stats.get("yellowCards", 0)),
            }
        except (KeyError, ValueError):
            continue
    return results


def grade_picks(date_str: str):
    """Grade all WC picks for a given date."""
    picks_file = os.path.join(DAILY_LOG, date_str, "picks.csv")
    if not os.path.exists(picks_file):
        print(f"No picks file for {date_str}")
        return None

    boxscore_results = load_boxscore_results()

    rows = []
    with open(picks_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sport_key = r.get('sport', r.get('league', 'UNKNOWN'))
            if sport_key.upper() in ("WORLD CUP", "WORLD_CUP"):
                rows.append(row)

    if not rows:
        print(f"No WC picks for {date_str}")
        return None

    print(f"\n{'='*70}")
    print(f"WC PICKS ANALYSIS — {date_str}")
    print(f"{'='*70}")
    print(f"Total picks: {len(rows)}")

    # Direction split
    directions = Counter(r.get("direction", "?") for r in rows)
    print(f"\nDirection split:")
    for d in ["OVER", "UNDER", "?"]:
        if d in directions:
            pct = directions[d] / len(rows) * 100
            print(f"  {d}: {directions[d]} ({pct:.1f}%)")

    # Stat type split
    stats = Counter(r.get("stat", "?") for r in rows)
    print(f"\nStat distribution:")
    for s, c in stats.most_common():
        print(f"  {s}: {c} ({c/len(rows)*100:.1f}%)")

    # Edge distribution
    edges = [float(r.get("edge", 0) or 0) for r in rows]
    edges_clean = [abs(e) for e in edges if e != 0]
    if edges_clean:
        print(f"\nEdge distribution:")
        print(f"  Mean: {sum(edges_clean)/len(edges_clean):.3f}")
        print(f"  Max:  {max(edges_clean):.3f}")
        print(f"  Min:  {min(edges_clean):.3f}")
        print(f"  Median: {sorted(edges_clean)[len(edges_clean)//2]:.3f}")

    # Game matchups
    matchups = Counter(r.get("matchup", "Unknown") for r in rows)
    print(f"\nGames ({len(matchups)}):")
    for m, c in matchups.most_common():
        # Check if we have a boxscore result
        result = boxscore_results.get(m)
        status = ""
        if result:
            status = f" → Final: {result['away_score']}-{result['home_score']} ({result['total_goals']} goals)"
        print(f"  {m}: {c} picks{status}")

    # Player uniqueness
    players = Counter(r.get("player", "?") for r in rows)
    print(f"\nUnique players: {len(players)}")

    # Source check
    sources = Counter(r.get("source", "?") for r in rows)
    print(f"\nSources: {dict(sources)}")

    # Identify pattern: all UNDER? all same edge?
    if len(directions) == 1:
        only_dir = list(directions.keys())[0]
        print(f"\n⚠️  All picks are {only_dir} — possible projection bias")

    # Validate player names (are they placeholders like "England_DEF_1"?)
    placeholder_patterns = []
    for p in players:
        if re.search(r'[A-Z]{3}_(DEF|MID|FWD|GK)_\d+', p):
            placeholder_patterns.append(p)
    if placeholder_patterns:
        print(f"\n⚠️  {len(placeholder_patterns)} placeholder-style player names found:")
        for pp in placeholder_patterns[:5]:
            print(f"    {pp} ({players[pp]} picks)")
        if len(placeholder_patterns) > 5:
            print(f"    ... and {len(placeholder_patterns) - 5} more")

    # Per-stat OVER/UNDER analysis
    stat_dir = defaultdict(lambda: {"OVER": 0, "UNDER": 0})
    for r in rows:
        s = r.get("stat", "?")
        d = r.get("direction", "?")
        stat_dir[s][d] = stat_dir[s].get(d, 0) + 1

    print(f"\nPer-stat direction split:")
    for s in sorted(stat_dir.keys()):
        d = stat_dir[s]
        print(f"  {s}: O={d.get('OVER',0)} U={d.get('UNDER',0)}")

    return rows


if __name__ == "__main__":
    # Grade last 3 days of WC picks
    for date_dir in sorted(os.listdir(DAILY_LOG))[-5:]:
        if date_dir.startswith("2026-") and os.path.isdir(os.path.join(DAILY_LOG, date_dir)):
            grade_picks(date_dir)
