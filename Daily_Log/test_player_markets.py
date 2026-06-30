import requests
from pathlib import Path

key = None
for line in Path('/root/.zo/secrets.env').read_text().split('\n'):
    if line.startswith('ODDS_API_KEY='):
        key = line.split('=', 1)[1].strip().strip('"').strip("'")
        break

# Test player markets param
r = requests.get('https://api.theoddsapi.com/odds/', params={
    'sport_key': 'baseball_mlb',
    'regions': 'us',
    'apiKey': key,
    'markets': 'player_points,player_home_runs,player_hits,player_stolen_bases,player_rbis,player_runs_scored'
}, timeout=15)
print('status:', r.status_code)
print('len:', len(r.text))
data = r.json()
if data.get('data'):
    e = data['data'][0]
    markets = sorted(set(b['market'] for b in e.get('books', [])))
    print('markets:', markets)
    # Sample player prop
    for b in e.get('books', []):
        if b['market'].startswith('player_') and b.get('outcomes'):
            print(f"sample {b['book']} {b['market']}: {b['outcomes'][0]}")
            break
else:
    print('no data')
