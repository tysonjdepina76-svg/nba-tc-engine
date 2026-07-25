#!/usr/bin/env python3
"""Build per-player NBA stats from ESPN actuals backtest data."""
import json, os, statistics
from collections import defaultdict

backtest_dir = '/home/workspace/Daily_Log/backtests/'
stats = defaultdict(lambda: {
    'pts': [], 'reb': [], 'ast': [], 'stl': [], 'blk': [], '3pm': [], 'min': [], 'to': [],
    'team': '', 'games': 0, 'active_games': 0
})

for bt in sorted(os.listdir(backtest_dir)):
    path = os.path.join(backtest_dir, bt, 'espn_actuals_nba.json')
    if not os.path.exists(path): continue
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list): continue
    for entry in data:
        name = entry.get('name', '')
        if not name: continue
        s = stats[name]
        s['pts'].append(entry.get('PTS', 0) or 0)
        s['reb'].append(entry.get('REB', 0) or 0)
        s['ast'].append(entry.get('AST', 0) or 0)
        s['stl'].append(entry.get('STL', 0) or 0)
        s['blk'].append(entry.get('BLK', 0) or 0)
        s['3pm'].append(entry.get('3PM', 0) or 0)
        min_played = entry.get('MIN', 0) or 0
        s['min'].append(min_played)
        s['to'].append(entry.get('TO', 0) or 0)
        s['games'] += 1
        if min_played > 0: s['active_games'] += 1
        team = entry.get('team', '')
        if team and not s['team']: s['team'] = team


def safe_avg(values, recent=5):
    subset = values[-recent:]
    non_zero = [v for v in subset if v > 0]
    if not non_zero and recent < len(values):
        return round(statistics.mean(values), 1) if values else 0.0
    if not non_zero:
        return round(statistics.mean(values), 1) if values else 0.0
    return round(statistics.mean(non_zero), 1)


output = {}
for name, s in stats.items():
    if s['active_games'] < 3:
        continue
    output[name] = {
        'team': s['team'],
        'games': s['games'],
        'active_games': s['active_games'],
        'avg_min': round(statistics.mean([m for m in s['min'] if m > 0]), 1) if s['active_games'] > 0 else 0.0,
        'season': {
            'PTS': round(statistics.mean(s['pts']), 1),
            'REB': round(statistics.mean(s['reb']), 1),
            'AST': round(statistics.mean(s['ast']), 1),
            'STL': round(statistics.mean(s['stl']), 1),
            'BLK': round(statistics.mean(s['blk']), 1),
            '3PM': round(statistics.mean(s['3pm']), 1),
            'TO': round(statistics.mean(s['to']), 1),
        },
        'recent5': {
            'PTS': safe_avg(s['pts']),
            'REB': safe_avg(s['reb']),
            'AST': safe_avg(s['ast']),
            'STL': safe_avg(s['stl']),
            'BLK': safe_avg(s['blk']),
            '3PM': safe_avg(s['3pm']),
            'TO': safe_avg(s['to']),
        },
    }
    s_pts = output[name]['season']
    output[name]['season']['PRA'] = round(s_pts['PTS'] + s_pts['REB'] + s_pts['AST'], 1)
    output[name]['season']['P+R'] = round(s_pts['PTS'] + s_pts['REB'], 1)
    output[name]['season']['P+A'] = round(s_pts['PTS'] + s_pts['AST'], 1)
    r5 = output[name]['recent5']
    output[name]['recent5']['PRA'] = round(r5['PTS'] + r5['REB'] + r5['AST'], 1)
    output[name]['recent5']['P+R'] = round(r5['PTS'] + r5['REB'], 1)
    output[name]['recent5']['P+A'] = round(r5['PTS'] + r5['AST'], 1)

out_path = '/home/workspace/data/nba_player_stats.json'
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Built stats for {len(output)} NBA players (3+ active games)")
print(f"Saved to {out_path}")
