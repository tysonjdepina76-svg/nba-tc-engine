import sys, json
sys.path.insert(0, '/home/workspace/Projects')
from consensus_engine import fetch_consensus_for_matchup

r = fetch_consensus_for_matchup('MLB', 'CHW', 'BAL')
print('source:', r.get('source'))
print('error:', r.get('error'))
print('players:', len(r.get('players', {})))
print('first 3 players:')
for name, stats in list(r.get('players', {}).items())[:3]:
    print(f'  {name}: {stats}')
