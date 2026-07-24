#!/usr/bin/env python3
"""Grade all 84 WNBA 7/19 picks: boxscore + DNP + cross-game lookups."""

import json
import sqlite3
import requests
from datetime import datetime

DB_PATH = "/home/workspace/Projects/data/picks.db"

WNBA_GAMES = {
    'CHI@ATL': '401857081',
    'CON@PHX': '401857082',
    'LA@DAL': '401857080',
}

STAT_KEYS = {
    'PTS': 'points',
    'REB': 'rebounds',
    'AST': 'assists',
    'P+A': 'points_assists',
    'P+R': 'points_rebounds',
    'R+A': 'rebounds_assists',
    'P+R+A': 'points_rebounds_assists',
    '3PM': 'threePointFieldGoalsMade-threePointFieldGoalsAttempted',
    'STL': 'steals',
    'BLK': 'blocks',
    'TO': 'turnovers',
    'OREB': 'offensiveRebounds',
    'DREB': 'defensiveRebounds',
}

COMPOSITE_STATS = {'P+A', 'P+R', 'R+A', 'P+R+A'}

def parse_stat(raw_val):
    """Parse stat from ESPN format. Field goals come as 'made-attempted'."""
    if raw_val is None:
        return 0
    raw_val = str(raw_val).strip()
    if '-' in raw_val and '/' not in raw_val:
        try:
            return int(raw_val.split('-')[0])
        except:
            return 0
    try:
        return int(raw_val)
    except:
        try:
            return float(raw_val)
        except:
            return 0


def fetch_all_boxscores():
    """Fetch all 3 WNBA game boxscores."""
    all_players = {}
    
    for matchup, game_id in WNBA_GAMES.items():
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={game_id}'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'},
                        params={'x-cache-bust': str(datetime.now().timestamp())})
        data = r.json()
        
        game_players = {}
        for team_data in data['boxscore']['players']:
            team_id = team_data['team']['id']
            team_abbr = team_data['team']['abbreviation']
            for stats_block in team_data.get('statistics', []):
                for athlete_data in stats_block.get('athletes', []):
                    name = athlete_data['athlete']['displayName']
                    dnp = athlete_data.get('didNotPlay', False)
                    stats = athlete_data.get('stats', [])
                    
                    pts = parse_stat(stats[1]) if len(stats) > 1 and not dnp else 0
                    reb = parse_stat(stats[5]) if len(stats) > 5 and not dnp else 0
                    ast = parse_stat(stats[6]) if len(stats) > 6 and not dnp else 0
                    stl = parse_stat(stats[8]) if len(stats) > 8 and not dnp else 0
                    blk = parse_stat(stats[9]) if len(stats) > 9 and not dnp else 0
                    to_stat = parse_stat(stats[7]) if len(stats) > 7 and not dnp else 0
                    oreb = parse_stat(stats[10]) if len(stats) > 10 and not dnp else 0
                    dreb = parse_stat(stats[11]) if len(stats) > 11 and not dnp else 0
                    
                    tp_raw = stats[3] if len(stats) > 3 else '0-0'
                    tp = parse_stat(tp_raw) if not dnp else 0
                    
                    game_players[name] = {
                        'PTS': pts, 'REB': reb, 'AST': ast,
                        'P+A': pts + ast, 'P+R': pts + reb,
                        'R+A': reb + ast, 'P+R+A': pts + reb + ast,
                        '3PM': tp, 'STL': stl, 'BLK': blk,
                        'TO': to_stat, 'OREB': oreb, 'DREB': dreb,
                        'dnp': dnp, 'team': team_abbr,
                    }
        
        all_players[matchup] = game_players
        print(f'  Boxscore {matchup}: {len(game_players)} players')
    
    return all_players


def grade_pick(pick, all_boxscores):
    """Grade one pick. Returns (actual, hit, profit) or None for ungradable."""
    player = pick['player']
    stat = pick['stat']
    direction = pick['direction']
    line = pick['market_line']
    matchup = pick['matchup']
    
    # Try primary matchup first
    box = all_boxscores.get(matchup, {})
    pdata = box.get(player)
    
    fallback_from = None
    if pdata is None:
        # Cross-game: player might be in a different game
        for alt_matchup, alt_box in all_boxscores.items():
            if player in alt_box:
                pdata = alt_box[player]
                fallback_from = alt_matchup
                break
    
    if pdata is None:
        # Player not in any boxscore → assume DNP, actual=0
        actual = 0
    else:
        actual = pdata.get(stat, 0)
    
    # Grade
    if direction == 'OVER':
        hit = 1 if actual > line else 0
    elif direction == 'UNDER':
        hit = 1 if actual < line else 0
    else:
        hit = 0
    
    profit = 1.0 if hit else -1.0
    
    return actual, hit, profit, fallback_from


def main():
    print('📊 Grading WNBA picks from 2026-07-19')
    print('=' * 60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Ensure grading columns exist
    for col in [('actual', 'REAL'), ('hit', 'INTEGER'), ('profit', 'REAL')]:
        try:
            cursor.execute(f"ALTER TABLE picks ADD COLUMN {col[0]} {col[1]}")
        except sqlite3.OperationalError:
            pass
    
    # Reset picks for 7/19
    cursor.execute("UPDATE picks SET actual=NULL, hit=NULL, profit=NULL WHERE date='2026-07-19'")
    conn.commit()
    
    # Get all picks
    cursor.execute("SELECT * FROM picks WHERE date='2026-07-19'")
    picks = [dict(row) for row in cursor.fetchall()]
    print(f'  Picks to grade: {len(picks)}')
    
    # Fetch all boxscores
    print('\n📊 Fetching boxscores...')
    all_boxscores = fetch_all_boxscores()
    
    # Grade each pick
    results = {'hit': 0, 'miss': 0, 'dnp_hit': 0, 'cross_game': 0}
    cross_details = []
    
    for pick in picks:
        actual, hit, profit, fallback = grade_pick(pick, all_boxscores)
        
        cursor.execute(
            "UPDATE picks SET actual=?, hit=?, profit=? WHERE id=?",
            (actual, hit, profit, pick['id'])
        )
        
        if fallback:
            results['cross_game'] += 1
            cross_details.append(f"  {pick['player']}: tagged {pick['matchup']} → found in {fallback}, actual={actual} → {'HIT' if hit else 'MISS'}")
        elif actual == 0 and pick['matchup'] in all_boxscores and pick['player'] not in all_boxscores[pick['matchup']]:
            results['dnp_hit'] += 1
        
        if hit:
            results['hit'] += 1
        else:
            results['miss'] += 1
    
    conn.commit()
    
    # Summary
    total = results['hit'] + results['miss']
    hit_rate = (results['hit'] / total * 100) if total > 0 else 0
    
    print(f'\n{"=" * 60}')
    print('📊 GRADING COMPLETE')
    print(f'{"=" * 60}')
    print(f'Total picks: {total}')
    print(f'Hits: {results["hit"]} | Misses: {results["miss"]}')
    print(f'Hit rate: {hit_rate:.1f}%')
    print(f'DNP auto-hits: {results["dnp_hit"]}')
    print(f'Cross-game players: {results["cross_game"]}')
    
    if cross_details:
        print(f'\n🔀 Cross-game matches:')
        for detail in cross_details:
            print(detail)
    
    # By stat breakdown
    cursor.execute("""
        SELECT stat, COUNT(*) as total, SUM(hit) as hits
        FROM picks WHERE date='2026-07-19' AND hit IS NOT NULL
        GROUP BY stat
        ORDER BY stat
    """)
    stat_rows = cursor.fetchall()
    
    print(f'\n📊 By stat:')
    for row in stat_rows:
        pct = (row['hits'] / row['total'] * 100) if row['total'] > 0 else 0
        print(f'  {row["stat"]}: {row["hits"]}/{row["total"]} ({pct:.1f}%)')
    
    # By player summary
    cursor.execute("""
        SELECT player, matchup, COUNT(*) as total, SUM(hit) as hits,
               AVG(edge) as avg_edge
        FROM picks WHERE date='2026-07-19' AND hit IS NOT NULL
        GROUP BY player, matchup
        ORDER BY matchup, player
    """)
    player_rows = cursor.fetchall()
    
    print(f'\n👤 By player:')
    for row in player_rows:
        pct = (row['hits'] / row['total'] * 100) if row['total'] > 0 else 0
        print(f'  {row["player"]:25s} ({row["matchup"]:10s}): {row["hits"]}/{row["total"]} ({pct:.1f}%)')
    
    conn.close()
    
    print(f'\n💾 Results saved to picks.db')
    return results


if __name__ == '__main__':
    main()
