"""Full TheOddsAPI scraper — all endpoints, live + historical."""
import os, requests, json, csv, time
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SECRETS_FILE = Path('/root/.zo/secrets.env')

def get_key():
    key = os.environ.get('ODDS_API_KEY', '')
    if SECRETS_FILE.exists() and not key:
        for line in SECRETS_FILE.read_text().split('\n'):
            if 'ODDS_API_KEY=' in line and not line.strip().startswith('#'):
                key = line.strip().split('=',1)[1].strip().strip('"').strip("'")
                break
    return key

BASE = 'https://api.theoddsapi.com'
OUTDIR = Path('/home/workspace/sports_betting_dashboard/data')

SPORTS = {
    'wnba': 'basketball_wnba',
    'nba': 'basketball_nba',
    'mlb': 'baseball_mlb',
    'nhl': 'icehockey_nhl',
    'nfl': 'americanfootball_nfl',
    'ncaaf': 'americanfootball_ncaaf',
    'ncaab': 'basketball_ncaab',
    'epl': 'soccer_epl',
    'world_cup': 'soccer_fifa_world_cup',
    'bundesliga': 'soccer_germany_bundesliga',
    'serie_a': 'soccer_italy_serie_a',
    'ligue_one': 'soccer_france_ligue_one',
    'ligamx': 'soccer_mexico_ligamx',
    'efl': 'soccer_efl_champ',
    'afl': 'aussierules_afl',
    'euroleague': 'basketball_euroleague',
    'boxing': 'boxing_boxing',
    'mma': 'mma_mixed_martial_arts',
    'cricket': 'cricket',
    'nrl': 'rugbyleague_nrl',
}

PROP_MARKETS = {
    'basketball': ['player_points', 'player_rebounds', 'player_assists',
                   'player_threes', 'player_blocks', 'player_steals',
                   'player_double_double', 'player_points_rebounds_assists'],
    'baseball': ['batter_hits', 'batter_home_runs', 'batter_rbis',
                 'batter_runs_scored', 'batter_total_bases',
                 'batter_hits_runs_rbis', 'pitcher_strikeouts', 'pitcher_outs'],
}

def headers():
    return {'x-api-key': get_key()}

def api_get(path, params=None):
    r = requests.get(f'{BASE}{path}', headers=headers(), params=params)
    return r

def fetch_account():
    r = api_get('/me/')
    data = r.json()
    OUTDIR.joinpath('account/status.json').write_text(json.dumps(data, indent=2))
    return data

def fetch_sports():
    r = api_get('/sports/', params={'all': 'true'})
    data = r.json()
    sports_list = data.get('data', [])
    active = [s for s in sports_list if s.get('active')]
    print(f"Sports: {len(sports_list)} total, {len(active)} active")
    OUTDIR.joinpath('sports/all_sports.json').write_text(json.dumps(sports_list, indent=2))
    return sports_list

def fetch_events(sport_key, label):
    r = api_get('/events/', params={'sport_key': sport_key})
    data = r.json()
    events = data.get('data')
    if events is None:
        print(f"  {label}: no events (off-season or error)")
        return []
    filepath = OUTDIR / f'events/{sport_key}.json'
    filepath.write_text(json.dumps(events, indent=2))
    print(f"  {label}: {len(events)} events")
    return events

def fetch_odds(sport_key, markets=None):
    params = {'sport_key': sport_key, 'markets': markets or 'h2h,spreads,totals'}
    r = api_get('/odds/', params=params)
    data = r.json()
    return data.get('data', [])

def fetch_props(sport_key, prop_markets=None):
    params = {'sport_key': sport_key}
    if prop_markets:
        params['markets'] = ','.join(prop_markets)
    r = api_get('/props/', params=params)
    data = r.json()
    return data.get('data', [])

def fetch_historical(sport_key, markets=None, limit=100):
    all_rows = []
    offset = 0
    while True:
        params = {'sport_key': sport_key, 'limit': limit, 'offset': offset}
        if markets:
            params['markets'] = markets
        r = api_get('/historical/odds/', params=params)
        data = r.json()
        rows = data.get('data', [])
        meta = data.get('meta', {})
        if not rows:
            break
        all_rows.extend(rows)
        offset += len(rows)
        if offset % 5000 == 0:
            print(f"  ... {offset} rows ...")
        if len(rows) < limit:
            break
        if offset >= meta.get('total_rows', 0):
            break
    return all_rows

def save_props_json(props_data, sport_key, label):
    filepath = OUTDIR / f'props/{label}_live.json'
    filepath.write_text(json.dumps(props_data, indent=2))
    
    # Also save flattened CSV
    csv_rows = []
    for event in props_data:
        ev_id = event.get('event_id','')
        home = event.get('home_team','')
        away = event.get('away_team','')
        start = event.get('start_time','')
        for prop in event.get('props', []):
            market = prop.get('market','')
            for book in prop.get('books', []):
                bk = book.get('book','')
                for outcome in book.get('outcomes', []):
                    csv_rows.append({
                        'event_id': ev_id, 'home': home, 'away': away,
                        'start_time': start, 'market': market, 'book': bk,
                        'player': outcome.get('description',''),
                        'side': outcome.get('name',''),
                        'point': outcome.get('point',''),
                        'price': outcome.get('price',''),
                        'updated': book.get('updated_at','')
                    })
    if csv_rows:
        csvpath = OUTDIR / f'props/{label}_live.csv'
        with open(csvpath, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            w.writeheader()
            w.writerows(csv_rows)
        print(f"  Saved {len(csv_rows)} prop rows to {csvpath}")

def save_historical_csv(rows, sport_key, label):
    csvpath = OUTDIR / f'historical/{label}_historical.csv'
    if rows:
        with open(csvpath, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"  Saved {len(rows)} historical rows to {csvpath}")

def build_api_schema():
    schema = {
        'base_url': BASE,
        'auth': 'x-api-key header',
        'account': {
            'tier': 'business',
            'daily_limit': 6667,
            'endpoint': '/me/'
        },
        'endpoints': {
            '/sports/': {'params': ['all'], 'desc': 'List all sports'},
            '/events/': {'params': ['sport_key'], 'desc': 'Upcoming events'},
            '/odds/': {'params': ['sport_key', 'markets'], 'desc': 'Standard odds (h2h/spreads/totals)'},
            '/props/': {'params': ['sport_key', 'markets'], 'desc': 'Player props (Business+)'},
            '/historical/odds/': {'params': ['sport_key', 'date', 'markets', 'limit', 'offset'],
                                  'desc': 'Historical odds (7-day rolling window)', 'note': 'date param ignored, always returns last 7 days'},
            '/me/': {'desc': 'Account status + tier'},
        },
        'prop_markets': PROP_MARKETS,
        'sports': SPORTS,
        'coverage': {
            'live': 'All sports with h2h/spreads/totals. WNBA/MLB with full player props.',
            'historical': '7-day rolling window of h2h/spreads/totals only. No historical player props.',
            'start_date': '2026-04-16'
        }
    }
    OUTDIR.joinpath('historical/api_schema.json').write_text(json.dumps(schema, indent=2))
    return schema

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for sub in ['account', 'events', 'odds', 'props', 'sports', 'historical']:
        OUTDIR.joinpath(sub).mkdir(exist_ok=True)
    
    print("=== TheOddsAPI Full Scrape ===")
    
    acct = fetch_account()
    tier = acct.get('data', {}).get('tier', 'unknown') if isinstance(acct, dict) else 'unknown'
    print(f"Account tier: {tier}")
    
    build_api_schema()
    
    # Events
    print("\n--- EVENTS ---")
    for label, sk in [('WNBA', SPORTS['wnba']), ('MLB', SPORTS['mlb']),
                       ('World Cup', SPORTS['world_cup']), ('NBA', SPORTS['nba'])]:
        fetch_events(sk, label)
    
    # Live odds
    print("\n--- LIVE ODDS ---")
    for label, sk in [('WNBA', SPORTS['wnba']), ('World Cup', SPORTS['world_cup']),
                       ('MLB', SPORTS['mlb'])]:
        odds = fetch_odds(sk)
        filepath = OUTDIR / f'odds/{sk}_live.json'
        filepath.write_text(json.dumps(odds, indent=2))
        print(f"  {label}: {len(odds)} odds events")
    
    # Live props
    print("\n--- LIVE PROPS ---")
    for label, sk, sport_type in [('WNBA', SPORTS['wnba'], 'basketball'),
                                   ('MLB', SPORTS['mlb'], 'baseball')]:
        markets = PROP_MARKETS.get(sport_type, [])
        props = fetch_props(sk, markets)
        save_props_json(props, sk, label.lower())
        print(f"  {label}: {len(props)} events with props")
    
    # Historical (sample - not full pagination to save requests)
    print("\n--- HISTORICAL ---")
    for label, sk in [('WNBA', SPORTS['wnba']), ('World Cup', SPORTS['world_cup'])]:
        rows = fetch_historical(sk, limit=200)
        save_historical_csv(rows, sk, label.lower().replace(' ','_'))
        print(f"  {label}: {len(rows)} historical rows")
    
    print("\n=== Complete ===")
    acct2 = fetch_account()
    requests_today = acct2.get('data', {}).get('requests_today', '?')
    remaining = acct2.get('data', {}).get('remaining', '?')
    print(f"Requests today: {requests_today}, Remaining: {remaining}")

if __name__ == '__main__':
    main()
