#!/usr/bin/env python3
"""WNBA Player Combo Stats -- PRA, PR, PA, RA per player from ESPN stats."""

import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime
import csv

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
BASE = 'http://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/seasons/2026'
STAT_TYPE = '2'  # season totals

def resolve(url, session):
    r = session.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def get_teams(session):
    """Resolve all WNBA teams, filter out All-Star."""
    url = f'{BASE}/teams?limit=50'
    items = resolve(url, session)['items']
    team_ids = []
    for item in items:
        ref = item['$ref']
        t = resolve(ref, session)
        if not t.get('isAllStar', False):
            team_ids.append((t['id'], t['abbreviation'], t['displayName']))
    return sorted(team_ids, key=lambda x: x[2])

def get_roster(team_id, session):
    """Get athletes for a team."""
    url = f'{BASE}/teams/{team_id}/athletes?limit=30'
    items = resolve(url, session)['items']
    athletes = []
    for item in items:
        ref = item['$ref']
        a = resolve(ref, session)
        athletes.append((a['id'], a['displayName']))
    return athletes

def get_player_stats(athlete_id, session):
    """Get season totals for a player. Returns (pts, reb, ast, gp, mpg) or None."""
    url = f'{BASE}/types/{STAT_TYPE}/athletes/{athlete_id}/statistics/0'
    try:
        data = resolve(url, session)
    except Exception:
        return None

    stat_map = {}
    for cat in data['splits']['categories']:
        for s in cat.get('stats', []):
            stat_map[s['name']] = s['value']

    pts = stat_map.get('points', 0)
    reb = stat_map.get('rebounds', 0)
    ast = stat_map.get('assists', 0)
    gp = stat_map.get('gamesPlayed', 1)
    mpg = stat_map.get('avgMinutes', 0)

    if gp == 0:
        return None

    return (pts, reb, ast, int(gp), mpg)

def main():
    print("Fetching WNBA teams...")
    session = requests.Session()

    teams = get_teams(session)
    print(f"Found {len(teams)} teams")

    # Collect all athletes
    all_players = []
    for tid, abbr, name in teams:
        print(f"  {abbr} ({name})...")
        roster = get_roster(tid, session)
        all_players.extend([(aid, aname, abbr, name) for aid, aname in roster])

    print(f"\nTotal players: {len(all_players)}. Fetching stats...")

    # Fetch stats in parallel
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {}
        for aid, aname, abbr, tname in all_players:
            f = pool.submit(get_player_stats, aid, session)
            futures[f] = (aname, abbr, tname)

        done = 0
        for f in concurrent.futures.as_completed(futures):
            aname, abbr, tname = futures[f]
            stats = f.result()
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(all_players)}...")
            if stats:
                pts, reb, ast, gp, mpg = stats
                results.append({
                    'player': aname,
                    'team': abbr,
                    'team_name': tname,
                    'GP': gp,
                    'MPG': round(mpg, 1),
                    'PTS': round(pts, 1),
                    'REB': round(reb, 1),
                    'AST': round(ast, 1),
                    'P+R+A': round(pts + reb + ast, 1),
                    'P+R': round(pts + reb, 1),
                    'P+A': round(pts + ast, 1),
                    'R+A': round(reb + ast, 1),
                })

    print(f"\nGot stats for {len(results)} players")

    # Sort by PRA
    results.sort(key=lambda x: x['P+R+A'], reverse=True)

    # Print top 25 by PRA
    print("\n" + "="*80)
    print("TOP 25 WNBA PLAYERS BY P+R+A (Season Totals)")
    print("="*80)
    print(f"{'Rank':4s} {'Player':25s} {'Tm':3s} {'GP':3s} {'MPG':5s} {'PTS':6s} {'REB':5s} {'AST':5s} {'P+R+A':6s} {'P+R':6s} {'P+A':6s} {'R+A':6s}")
    print("-"*80)
    for i, r in enumerate(results[:25], 1):
        print(f"{i:4d} {r['player']:25s} {r['team']:3s} {r['GP']:3d} {r['MPG']:5.1f} {r['PTS']:6.1f} {r['REB']:5.1f} {r['AST']:5.1f} {r['P+R+A']:6.1f} {r['P+R']:6.1f} {r['P+A']:6.1f} {r['R+A']:6.1f}")

    # ---- Per-game averages ----
    for r in results:
        gp = r['GP'] if r['GP'] > 0 else 1
        r['PTS_pg'] = round(r['PTS'] / gp, 1)
        r['REB_pg'] = round(r['REB'] / gp, 1)
        r['AST_pg'] = round(r['AST'] / gp, 1)
        r['PRA_pg'] = round(r['P+R+A'] / gp, 1)
        r['PR_pg'] = round(r['P+R'] / gp, 1)
        r['PA_pg'] = round(r['P+A'] / gp, 1)
        r['RA_pg'] = round(r['R+A'] / gp, 1)

    # Sort by PRA per game
    results.sort(key=lambda x: x['PRA_pg'], reverse=True)

    # ---- Per-game leaders ----
    print("\n" + "="*80)
    print("TOP 25 WNBA PLAYERS BY P+R+A PER GAME")
    print("="*80)
    print(f"{'Rank':4s} {'Player':25s} {'Tm':3s} {'GP':3s} {'PTS':6s} {'REB':5s} {'AST':5s} {'PRA':6s} {'PR':6s} {'PA':6s} {'RA':6s}")
    print("-"*80)
    for i, r in enumerate(results[:25], 1):
        print(f"{i:4d} {r['player']:25s} {r['team']:3s} {r['GP']:3d} {r['PTS_pg']:6.1f} {r['REB_pg']:5.1f} {r['AST_pg']:5.1f} {r['PRA_pg']:6.1f} {r['PR_pg']:6.1f} {r['PA_pg']:6.1f} {r['RA_pg']:6.1f}")

    # ---- Per-game ranks for each combo ----
    for combo_label, combo_key in [('P+R+A', 'PRA_pg'), ('P+R', 'PR_pg'), ('P+A', 'PA_pg'), ('R+A', 'RA_pg')]:
        sorted_combo = sorted(results, key=lambda x: x[combo_key], reverse=True)
        print(f"\n{'='*60}")
        print(f"TOP 15 WNBA PLAYERS — {combo_label} PER GAME")
        print(f"{'='*60}")
        print(f"{'Rank':4s} {'Player':25s} {'Tm':3s} {'GP':3s} {'PTS':5s} {'REB':5s} {'AST':5s} {combo_label:6s}")
        print("-"*60)
        for i, r in enumerate(sorted_combo[:15], 1):
            print(f"{i:4d} {r['player']:25s} {r['team']:3s} {r['GP']:3d} {r['PTS_pg']:5.1f} {r['REB_pg']:5.1f} {r['AST_pg']:5.1f} {r[combo_key]:6.1f}")

    # ---- Consistency (hit rate) ----
    # For each player, what percentage of games do they hit a threshold?
    # We approximate by checking CV (coefficient of variation) on per-game data
    # Since we don't have game logs, we use total variation estimate
    # Instead: flag players with >= 20 GP who rank high in multiple combos
    print(f"\n{'='*80}")
    print("MOST CONSISTENT WNBA PLAYERS (≥20 GP, top-30 in ≥2 combos)")
    print("="*80)

    qualified = [r for r in results if r['GP'] >= 20]
    top30_pra = set(r['player'] for r in sorted(qualified, key=lambda x: x['PRA_pg'], reverse=True)[:30])
    top30_pr = set(r['player'] for r in sorted(qualified, key=lambda x: x['PR_pg'], reverse=True)[:30])
    top30_pa = set(r['player'] for r in sorted(qualified, key=lambda x: x['PA_pg'], reverse=True)[:30])
    top30_ra = set(r['player'] for r in sorted(qualified, key=lambda x: x['RA_pg'], reverse=True)[:30])

    consistent = []
    for r in qualified:
        p = r['player']
        hits = 0
        combos = []
        if p in top30_pra: hits += 1; combos.append('PRA')
        if p in top30_pr: hits += 1; combos.append('PR')
        if p in top30_pa: hits += 1; combos.append('PA')
        if p in top30_ra: hits += 1; combos.append('RA')
        if hits >= 2:
            consistent.append({**r, 'combo_hits': hits, 'top_combos': ', '.join(combos)})

    consistent.sort(key=lambda x: x['combo_hits'], reverse=True)
    print(f"{'Player':25s} {'Tm':3s} {'GP':3s} {'PRA':6s} {'PR':6s} {'PA':6s} {'RA':6s} {'#Combos':8s} {'Top In'}")
    print("-"*90)
    for r in consistent[:30]:
        print(f"{r['player']:25s} {r['team']:3s} {r['GP']:3d} {r['PRA_pg']:6.1f} {r['PR_pg']:6.1f} {r['PA_pg']:6.1f} {r['RA_pg']:6.1f} {r['combo_hits']:8d} {r['top_combos']}")

    # ---- Save to CSV ----
    date_str = datetime.now().strftime('%Y-%m-%d')
    out_dir = Path('/home/workspace/Daily_Log')
    csv_path = out_dir / f'wnba_combo_stats_{date_str}.csv'
    with open(csv_path, 'w', newline='') as f:
        fields = ['player', 'team', 'team_name', 'GP', 'MPG', 'PTS', 'REB', 'AST',
                  'P+R+A', 'P+R', 'P+A', 'R+A',
                  'PTS_pg', 'REB_pg', 'AST_pg', 'PRA_pg', 'PR_pg', 'PA_pg', 'RA_pg']
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in sorted(results, key=lambda x: x['PRA_pg'], reverse=True):
            w.writerow(r)

    print(f"\nCSV saved: {csv_path}")
    return results

if __name__ == '__main__':
    main()
