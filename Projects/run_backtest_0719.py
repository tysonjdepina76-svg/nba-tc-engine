#!/usr/bin/env python3
"""Backtest: grade 2026-07-19 picks against 2026-07-20 box scores"""
import json, sqlite3, csv, os, sys
from datetime import date
from collections import defaultdict

TODAY = '2026-07-19'
BOX_DATE = '2026-07-20'
OUT_DIR = f'/home/workspace/Daily_Log/backtests/{TODAY}'
BOX_PATH = f'/home/workspace/Daily_Log/boxscores/boxscore_all_{BOX_DATE}.json'

STAT_MAP = {"PTS": "points", "AST": "assists", "REB": "totalRebounds", "STL": "steals", "BLK": "blocks", "3PM": "threePointersMade"}
MLB_STAT_MAP = {"H": "hits", "RBI": "rbi", "HR": "hr", "K": "k", "SB": "sb", "R": "runs"}
WC_STAT_MAP = {"G": "goals", "A": "assists", "SH": "shots", "SOT": "sot", "PAS": "passes", "TKL": "tackles", "YC": "yellow_cards"}
SPORT_MAP = {"WNBA": STAT_MAP, "MLB": MLB_STAT_MAP, "WC": WC_STAT_MAP}

# ─── Load picks ───
conn = sqlite3.connect('/home/workspace/Projects/data/picks.db')
rows = conn.execute('SELECT * FROM picks WHERE date=?', [TODAY]).fetchall()
cols = [d[0] for d in conn.execute('PRAGMA table_info(picks)')]
conn.close()
picks = [dict(zip(cols, row)) for row in rows]
print(f'Found {len(picks)} picks for {TODAY}')

# ─── Load box scores ───
with open(BOX_PATH) as f:
    box = json.load(f)

# Build lookup: (sport, team_abbrev, player_name) -> stats dict
actuals = {}
for sport_key in box.get('sports', {}):
    sport_data = box['sports'][sport_key]
    sport = sport_key  # WNBA, MLB, WC
    for game in sport_data.get('games', []):
        for side in ['home', 'away']:
            team_data = game[side]
            team_abbrev = team_data.get('abbrev', team_data.get('abbreviation', ''))
            for p in team_data.get('players', []):
                name = p.get('name', '').strip()
                stats = p.get('stats', {})
                pteam = p.get('team', team_abbrev)
                key = (sport, pteam.upper() if pteam else '', name.lower())
                actuals[key] = stats

# ─── Grade each pick ───
results = []
stats_counts = defaultdict(lambda: {'total': 0, 'hit': 0})

for p in picks:
    sport = p['league']
    player = p['player']
    team = p.get('team', '')
    stat = p['stat']
    direction = p['direction']  # OVER or UNDER
    projection = float(p['tc_projection']) if p['tc_projection'] else 0
    
    key = (sport, team.upper(), player.lower())
    
    # Also try partial name match
    actual_val = None
    matched_key = None
    for (s, t, n), stats in actuals.items():
        if s == sport:
            if player.lower() in n or n in player.lower():
                matched_key = (s, t, n)
                # Map stat name to box score field
                mapper = SPORT_MAP.get(sport, {})
                field = mapper.get(stat, stat.lower())
                v = stats.get(field)
                if v is None:
                    # Try lowercase
                    v = stats.get(field.lower())
                if v is None:
                    # Try direct stat name
                    v = stats.get(stat)
                if v is not None:
                    actual_val = float(v)
                break
    
    if actual_val is None:
        result = 'NO_DATA'
    elif direction == 'OVER':
        result = 'HIT' if actual_val >= projection else 'MISS'
    else:  # UNDER
        result = 'HIT' if actual_val <= projection else 'MISS'
    
    results.append({
        **p,
        'actual': actual_val if actual_val is not None else 'N/A',
        'result': result,
    })
    
    s = (sport, stat, direction)
    stats_counts[s]['total'] += 1
    if result == 'HIT':
        stats_counts[s]['hit'] += 1

# ─── Summary ───
total = len(results)
hits = sum(1 for r in results if r['result'] == 'HIT')
misses = sum(1 for r in results if r['result'] == 'MISS')
no_data = sum(1 for r in results if r['result'] == 'NO_DATA')
graded = hits + misses
hit_rate = (hits / graded * 100) if graded > 0 else 0

print(f'\n=== BACKTEST RESULTS for {TODAY} ===')
print(f'Total picks: {total}')
print(f'Hits: {hits} | Misses: {misses} | No Data: {no_data}')
print(f'Graded: {graded} | Hit Rate: {hit_rate:.1f}%')

for (sport, stat, direc), c in sorted(stats_counts.items()):
    if c['total'] > 0:
        rate = c['hit'] / c['total'] * 100
        print(f'  {sport} {stat} {direc}: {c["hit"]}/{c["total"]} = {rate:.1f}%')

# ─── Save ───
os.makedirs(OUT_DIR, exist_ok=True)

# Detailed CSV
csv_path = f'{OUT_DIR}/backtest_results.csv'
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

# Summary JSON
summary = {
    'date': TODAY,
    'boxscore_date': BOX_DATE,
    'total': total,
    'hits': hits,
    'misses': misses,
    'no_data': no_data,
    'graded': graded,
    'hit_rate': round(hit_rate, 1),
    'by_sport': {},
}
for (sport, stat, direc), c in sorted(stats_counts.items()):
    if c['total'] > 0:
        summary['by_sport'].setdefault(sport, {'total': 0, 'hits': 0})
        summary['by_sport'][sport]['total'] += c['total']
        summary['by_sport'][sport]['hits'] += c['hit']

for sport, counts in summary['by_sport'].items():
    counts['rate'] = round(counts['hits'] / counts['total'] * 100, 1) if counts['total'] > 0 else 0

json_path = f'{OUT_DIR}/backtest_summary.json'
with open(json_path, 'w') as f:
    json.dump(summary, f, indent=2)

# Update combined CSV
combined_path = '/home/workspace/Daily_Log/backtests/combined_backtest.csv'
combine_cols = ['date', 'league', 'matchup', 'team', 'player', 'role', 'status', 'stat',
                'direction', 'market_line', 'tc_projection', 'tc_target', 'edge',
                'threshold', 'raw_average', 'source', 'actual', 'result']
file_exists = os.path.exists(combined_path)
with open(combined_path, 'a', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=combine_cols)
    if not file_exists or os.path.getsize(combined_path) == 0:
        writer.writeheader()
    for r in results:
        row = {k: r.get(k, '') for k in combine_cols}
        row['date'] = TODAY
        row['league'] = r['league']
        row['role'] = r.get('role', '')
        row['status'] = r.get('status', '')
        row['tc_target'] = r.get('tc_target', '')
        row['threshold'] = r.get('threshold', '')
        row['raw_average'] = r.get('raw_average', '')
        row['source'] = r.get('signal', 'SELF_EDGE')
        row['actual'] = r['actual']
        row['result'] = r['result']
        writer.writerow(row)

print(f'\nSaved: {csv_path}')
print(f'Saved: {json_path}')
print(f'Appended to: {combined_path}')
print(f'Done.')
