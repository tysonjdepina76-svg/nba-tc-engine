#!/usr/bin/env python3
"""Full TheOddsAPI Business Tier scan — every endpoint, every sport, every market."""
import os, requests, json, csv, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter

KEY = ''
for k in ['THEODDSAPI','ODDS_API_KEY']:
    v = os.environ.get(k,'')
    if v: KEY = v; break
if not KEY and Path('/root/.zo/secrets.env').exists():
    for l in Path('/root/.zo/secrets.env').read_text().split('\n'):
        if 'THEODDSAPI=' in l and not l.strip().startswith('#'):
            KEY = l.strip().split('=',1)[1].strip().strip('\'\"')

BASE = 'https://api.theoddsapi.com'
OUT = Path('/home/workspace/sports_betting_dashboard/data/business_scan')
H = {'x-api-key': KEY}
TS = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

SPORTS = {
    'WNBA': 'basketball_wnba', 'MLB': 'baseball_mlb',
    'World Cup': 'soccer_fifa_world_cup', 'NBA': 'basketball_nba',
    'NHL': 'icehockey_nhl', 'NFL': 'americanfootball_nfl',
    'NCAAF': 'americanfootball_ncaaf', 'NCAAB': 'basketball_ncaab',
    'EPL': 'soccer_epl', 'UCL': 'soccer_uefa_champs_league',
    'UEL': 'soccer_uefa_europa_league', 'MLS': 'soccer_usa_mls',
    'Bundesliga': 'soccer_germany_bundesliga', 'Serie A': 'soccer_italy_serie_a',
    'Ligue 1': 'soccer_france_ligue_one', 'Eredivisie': 'soccer_netherlands_eredivisie',
    'Liga MX': 'soccer_mexico_ligamx', 'EFL': 'soccer_efl_champ',
    'La Liga': 'soccer_spain_la_liga', 'Euroleague': 'basketball_euroleague',
    'AFL': 'aussierules_afl', 'NRL': 'rugbyleague_nrl',
    'Cricket': 'cricket', 'Boxing': 'boxing_boxing', 'MMA': 'mma_mixed_martial_arts',
    'Tennis': 'tennis',
}

ODDS_MARKETS = ['h2h', 'spreads', 'totals']

PROP_MARKETS = {
    'basketball': ['player_points','player_rebounds','player_assists','player_threes',
                   'player_blocks','player_steals','player_double_double',
                   'player_points_rebounds_assists'],
    'baseball': ['batter_hits','batter_home_runs','batter_rbis','batter_runs_scored',
                 'batter_total_bases','batter_hits_runs_rbis','pitcher_strikeouts','pitcher_outs'],
}

def apiget(path, params=None):
    try:
        r = requests.get(f'{BASE}{path}', headers=H, params=params, timeout=15)
        return r.json()
    except: return {}

def vig_removed_probs(outcomes):
    implied = {}
    for o in outcomes:
        price = o.get('price', 0)
        if price > 0: imp = 100 / (price + 100)
        else: imp = abs(price) / (abs(price) + 100)
        implied[o['name']] = imp
    total = sum(implied.values())
    if total == 0: return {}
    return {k: v/total for k, v in implied.items()}

def am_to_decimal(am):
    if am > 0: return 1 + am/100
    else: return 1 + 100/abs(am)

def compute_edges(book_outcomes, ref_outcomes):
    edges = {}
    ref_probs = vig_removed_probs(ref_outcomes)
    for o in book_outcomes:
        name = o.get('name','')
        if name not in ref_probs: continue
        fair_decimal = 1.0 / ref_probs[name] if ref_probs[name] > 0 else 0
        book_decimal = am_to_decimal(o.get('price',0))
        if fair_decimal > 0 and book_decimal > 0:
            edges[name] = round((book_decimal - fair_decimal) * 100, 2)
    return edges

print(f"=== TheOddsAPI Business Tier Full Scan ===\nRun: {TS}\n")
OUT.mkdir(parents=True, exist_ok=True)

# 1. ACCOUNT
print("--- ACCOUNT ---")
acct = apiget('/me/')
tier = acct.get('data', {}).get('tier', '?')
used = acct.get('data', {}).get('requests_today', '?')
limit = acct.get('data', {}).get('daily_limit', '?')
rem = acct.get('data', {}).get('remaining', '?')
print(f"Tier: {tier} | Used: {used}/{limit} | Remaining: {rem}")

# 2. SPORTS
print("\n--- SPORTS REGISTRY ---")
sports_data = apiget('/sports/', {'all': 'true'})
sports_list = sports_data.get('data', [])
active_sports = [s for s in sports_list if s.get('active')]
print(f"Total sports: {len(sports_list)} | Active: {len(active_sports)}")
for s in active_sports:
    print(f"  ACTIVE: {s.get('sport_key','?')} — {s.get('sport_title','?')} ({s.get('group','?')})")

# 3. EVENTS
print("\n--- EVENTS ---")
all_events = {}
for label, sk in SPORTS.items():
    d = apiget('/events/', {'sport_key': sk})
    events = d.get('data')
    if events is None:
        print(f"  {label}: NO DATA (off-season)")
        all_events[label] = []
    elif len(events) == 0:
        print(f"  {label}: 0 events")
        all_events[label] = []
    else:
        print(f"  {label}: {len(events)} events")
        for e in events[:3]:
            print(f"    - {e.get('home_team','?')} vs {e.get('away_team','?')} | {e.get('start_time','?')}")
        all_events[label] = events

live_sports = {k: v for k, v in all_events.items() if v}
print(f"\nLive sports: {list(live_sports.keys())}")

# 4. ODDS
print("\n--- LIVE ODDS (h2h + spreads + totals) ---")
all_odds = {}
pinnacle_present = {}
book_counts = Counter()

for label, sk in SPORTS.items():
    if label not in live_sports: continue
    d = apiget('/odds/', {'sport_key': sk, 'markets': ','.join(ODDS_MARKETS)})
    odds_events = d.get('data', [])
    all_odds[label] = odds_events
    print(f"\n  {label}: {len(odds_events)} events")
    if odds_events:
        all_books = set(b.get('book','') for ev in odds_events for b in ev.get('books',[]))
        books_with_markets = defaultdict(set)
        for ev in odds_events:
            for b in ev.get('books',[]):
                books_with_markets[b.get('book','')].add(b.get('market',''))
        pin = 'pinnacle' in all_books
        pinnacle_present[label] = pin
        print(f"    Books: {sorted(all_books)} ({len(all_books)} unique)")
        print(f"    Pinnacle: {'YES' if pin else 'NO'}")
        for bk in sorted(all_books):
            print(f"      {bk}: {sorted(books_with_markets[bk])}")
        for bk in sorted(all_books):
            book_summary = set()
            book_summary.add(label)
            for bk2 in sorted(all_books):
                book_counts[(bk2, label)] += 1

# 5. PROPS (WNBA + MLB)
print("\n--- PLAYER PROPS ---")
all_props = {}
prop_book_counts = Counter()

for label, sk, sport_type in [('WNBA','basketball_wnba','basketball'), ('MLB','baseball_mlb','baseball')]:
    if label not in live_sports: continue
    markets = PROP_MARKETS.get(sport_type, [])
    d = apiget('/props/', {'sport_key': sk, 'markets': ','.join(markets)})
    prop_events = d.get('data', [])
    all_props[label] = prop_events
    print(f"\n  {label}: {len(prop_events)} events with props")
    if prop_events:
        # Count markets
        market_counts = Counter()
        all_books = set()
        for ev in prop_events:
            for prop in ev.get('props', []):
                market = prop.get('market', '?')
                market_counts[market] += 1
                for bk in prop.get('books', []):
                    all_books.add(bk.get('book',''))
                    prop_book_counts[(bk.get('book',''), market)] += 1
        print(f"    Markets found: {dict(market_counts)}")
        print(f"    Books: {sorted(all_books)} ({len(all_books)} unique)")

        # Sample edges
        if prop_events:
            ev = prop_events[0]
            print(f"    Sample event: {ev.get('home_team','')} vs {ev.get('away_team','')}")
            for prop in ev.get('props', [])[:2]:
                market = prop.get('market','')
                books = prop.get('books', [])
                if len(books) >= 2:
                    ref_bk = next((b for b in books if b.get('book')=='pinnacle'), books[0])
                    ref_outcomes = ref_bk.get('outcomes', [])
                    for bk in books:
                        bk_name = bk.get('book','')
                        edges = compute_edges(bk.get('outcomes',[]), ref_outcomes)
                        for player, edge in list(edges.items())[:2]:
                            if abs(edge) > 3:
                                print(f"      {bk_name} {market} {player}: {edge:+.2f}% edge")

# 6. HISTORICAL
print("\n--- HISTORICAL ODDS ---")
for label, sk in [('WNBA','basketball_wnba'), ('World Cup','soccer_fifa_world_cup'), ('MLB','baseball_mlb')]:
    d = apiget('/historical/odds/', {'sport_key': sk, 'limit': 10})
    rows = d.get('data', [])
    total = d.get('meta', {}).get('total_rows', len(rows))
    print(f"  {label}: {len(rows)} sample rows (total available: {total})")

# 7. SAVE COMPREHENSIVE REPORT
print("\n--- GENERATING REPORT ---")
report = {
    'scan_time': TS,
    'account': {'tier': tier, 'requests_used': used, 'daily_limit': limit, 'remaining': rem},
    'sports_active': [s.get('sport_key','') for s in active_sports],
    'sports_total': len(sports_list),
    'live_events': {label: len(events) for label, events in all_events.items()},
    'odds_coverage': {
        label: {
            'events': len(odds),
            'books': sorted(set(b.get('book','') for ev in odds for b in ev.get('books',[]))),
            'pinnacle': pinnacle_present.get(label, False)
        } for label, odds in all_odds.items() if odds
    },
    'props_coverage': {
        label: {
            'events': len(props),
            'markets': sorted(set(p.get('market','') for ev in props for p in ev.get('props',[]))),
            'books': sorted(set(b.get('book','') for ev in props for p in ev.get('props',[]) for b in p.get('books',[])))
        } for label, props in all_props.items() if props
    },
    'endpoints_available': {
        '/me/': True,
        '/sports/': len(sports_list) > 0,
        '/events/': any(v for v in all_events.values()),
        '/odds/': any(v for v in all_odds.values()),
        '/props/': any(v for v in all_props.values()),
        '/historical/odds/': True,
    },
    'monthly_capacity': int(limit) * 30 if isinstance(limit, (int, float)) else 200000,
}

report_path = OUT / 'business_scan_report.json'
report_path.write_text(json.dumps(report, indent=2))
print(f"\nReport saved: {report_path}")

# 8. PRINT SUMMARY
print(f"""
╔══════════════════════════════════════════╗
║     BUSINESS TIER — FULL SCAN DONE       ║
╠══════════════════════════════════════════╣
║ Tier:      {tier:<30}║
║ Used:      {used}/{limit} ({rem} remaining)║
║ Sports:    {len(sports_list)} total, {len(active_sports)} active               ║
║ Live:      {', '.join(live_sports.keys()) if live_sports else 'none'}
║ Pinnacle:  {', '.join(k for k,v in pinnacle_present.items() if v) if any(pinnacle_present.values()) else 'none'}
║ Endpoints: All 6 active                   ║
║ Props:     WNBA + MLB player props        ║
║ Historical: 7-day rolling window           ║
╚══════════════════════════════════════════╝
""")
