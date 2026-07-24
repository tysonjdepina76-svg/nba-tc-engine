#!/usr/bin/env python3
"""Grade ALL WNBA picks — cross-match players across ALL games, handle DNP."""

import sqlite3
import requests
import json
from collections import defaultdict

DB = "/home/workspace/Projects/data/picks.db"

# ── Fetch all boxscores for 7/19 ──
GAME_IDS = {
    'CHI@ATL': '401857081',
    'CON@PHX': '401857082',
    'LA@DAL': '401857080',
}

STAT_MAP = {
    'PTS': 1,
    'REB': 5,
    'AST': 6,
    'STL': 8,
    'BLK': 9,
    'OREB': 10,
    'DREB': 11,
    'TO': 7,
    '3PM': 3,  # needs parse from "made-attempted"
}


def parse_fraction(val):
    """Parse '2-9' → 2, '31' → 31"""
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val)
    if '-' in val:
        return float(val.split('-')[0])
    try:
        return float(val)
    except ValueError:
        return 0.0


def compute_stat(stats, stat_key):
    """Compute a derived stat from raw stats list."""
    if stat_key == 'P+A':
        pts = parse_fraction(stats[1])
        ast = parse_fraction(stats[6])
        return pts + ast
    elif stat_key == 'P+R':
        pts = parse_fraction(stats[1])
        reb = parse_fraction(stats[5])
        return pts + reb
    elif stat_key == 'P+R+A':
        pts = parse_fraction(stats[1])
        reb = parse_fraction(stats[5])
        ast = parse_fraction(stats[6])
        return pts + reb + ast
    elif stat_key == 'R+A':
        reb = parse_fraction(stats[5])
        ast = parse_fraction(stats[6])
        return reb + ast
    elif stat_key == 'PRA':
        pts = parse_fraction(stats[1])
        reb = parse_fraction(stats[5])
        ast = parse_fraction(stats[6])
        return pts + reb + ast
    elif stat_key in STAT_MAP:
        stat_idx = STAT_MAP[stat_key]
        return parse_fraction(stats[stat_idx])
    else:
        return None


def main():
    # Fetch all boxscores
    player_stats = {}  # player_name → {game, stats_raw}
    for matchup, gid in GAME_IDS.items():
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={gid}'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = r.json()
        for team_data in data['boxscore']['players']:
            for stats_block in team_data.get('statistics', []):
                for athlete_data in stats_block.get('athletes', []):
                    name = athlete_data['athlete']['displayName']
                    stats = athlete_data.get('stats', [])
                    dnp = athlete_data.get('didNotPlay', False)
                    played = not dnp and stats and stats[0] != '0'
                    player_stats[name] = {
                        'stats': stats,
                        'dnp': dnp,
                        'played': played,
                        'min': stats[0] if stats else '0'
                    }

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all picks
    cursor.execute("SELECT * FROM picks WHERE date='2026-07-19'")
    picks = cursor.fetchall()

    graded = 0
    hits = 0
    misses = 0
    dnp_hits = 0
    ungradable = []
    by_stat = defaultdict(lambda: {'hits': 0, 'misses': 0})

    for pick in picks:
        player = pick['player']
        stat = pick['stat']
        direction = pick['direction']
        line = pick['market_line']
        matchup = pick['matchup']

        # Cross-match: find player in ANY boxscore
        actual_val = None
        if player in player_stats:
            ps = player_stats[player]
            if ps['played']:
                actual_val = compute_stat(ps['stats'], stat)
            else:
                # DNP — actual = 0 for counting stats
                actual_val = 0.0
        else:
            # Player not in any boxscore — DNP
            actual_val = 0.0

        if actual_val is None:
            ungradable.append((player, stat, matchup, 'composite stat unavailable'))
            continue

        # Grade
        if direction == 'OVER':
            is_hit = actual_val > line
        else:  # UNDER
            is_hit = actual_val < line

        profit = 0.91 if is_hit else -1.0  # -110 odds

        cursor.execute("""
            UPDATE picks SET actual = ?, hit = ?, profit = ?
            WHERE id = ?
        """, (round(actual_val, 1), 1 if is_hit else 0, round(profit, 2), pick['id']))

        graded += 1
        if is_hit:
            hits += 1
        else:
            misses += 1
        by_stat[stat]['hits' if is_hit else 'misses'] += 1
        if actual_val == 0.0 and is_hit:
            dnp_hits += 1

    conn.commit()
    conn.close()

    # Report
    hit_rate = (hits / graded * 100) if graded > 0 else 0
    print(f"Total picks: {len(picks)}")
    print(f"Graded: {graded}")
    print(f"Hits: {hits} | Misses: {misses} (DNP auto-hits: {dnp_hits})")
    print(f"Hit rate: {hit_rate:.1f}%")
    print(f"Ungradable: {len(ungradable)}")
    print(f"Profit: +${(hits * 0.91 - misses * 1.0):.2f}")

    print("\nBy stat:")
    for stat in sorted(by_stat.keys()):
        s = by_stat[stat]
        total = s['hits'] + s['misses']
        print(f"  {stat}: {s['hits']}/{total} ({s['hits']/total*100:.1f}%)")

    if ungradable:
        print(f"\n⚠️ Ungradable ({len(ungradable)}):")
        for player, stat, mup, reason in ungradable[:10]:
            print(f"  {player} {stat} ({mup}): {reason}")

if __name__ == '__main__':
    main()
