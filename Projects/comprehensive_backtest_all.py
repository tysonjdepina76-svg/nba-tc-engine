#!/usr/bin/env python3
"""Comprehensive backtest — all workspace CSVs + Drive downloads. May 2026 → July 2026."""
import csv, json, os, glob, sys
from collections import defaultdict
from pathlib import Path

WORKSPACE = Path("/home/workspace")
PICKS_DIR = WORKSPACE / "data" / "picks"
DRIVE_DIR = WORKSPACE / "data" / "drive_backtests"

ALL_ROWS = []

def tryfloat(v):
    try: return float(v)
    except: return None

def load_csv(fp):
    rows = []
    with open(fp, errors='replace') as f:
        reader = csv.DictReader(f)
        for r in reader:
            r['_source'] = str(fp)
            rows.append(r)
    return rows

# 1. Workspace picks CSVs
for fp in sorted(PICKS_DIR.glob("*.csv")):
    try:
        rows = load_csv(fp)
        ALL_ROWS.extend(rows)
    except Exception as e:
        print(f"SKIP {fp}: {e}")

# 2. Drive downloads
for fp in sorted(DRIVE_DIR.glob("*.csv")):
    try:
        rows = load_csv(fp)
        ALL_ROWS.extend(rows)
    except Exception as e:
        print(f"SKIP {fp}: {e}")

# 3. Daily_Log directories — picks.csv, graded.csv, backtest CSVs
for sub in sorted(WORKSPACE.glob("Daily_Log/*/")):
    for pat in ["picks.csv", "*graded*", "*backtest*", "*picks*"]:
        for fp in sorted(sub.glob(pat)):
            if fp.suffix == '.csv':
                try:
                    rows = load_csv(fp)
                    ALL_ROWS.extend(rows)
                except Exception as e:
                    print(f"SKIP {fp}: {e}")

print(f"TOTAL RAW ROWS: {len(ALL_ROWS)}")

# --- STANDARDIZE ---
KEY_MAP = {
    'sport': ['sport', 'Sport', 'SPORT', 'league'],
    'player': ['player', 'Player', 'PLAYER', 'name', 'Name'],
    'stat': ['stat', 'Stat', 'prop', 'Prop', 'market', 'Market'],
    'direction': ['direction', 'Direction', 'pick', 'Pick', 'signal', 'Signal', 'pick_direction'],
    'projection': ['projection', 'Projection', 'tc_projection', 'model_projection'],
    'line': ['line', 'Line', 'market_line', 'sportsbook_line', 'book_line'],
    'edge': ['edge', 'Edge', 'edge_pct'],
    'actual': ['actual', 'Actual', 'result', 'Result'],
    'hit': ['hit', 'Hit', 'HIT', 'result_bool'],
    'date': ['date', 'Date', 'game_date'],
    'confidence': ['confidence', 'Confidence'],
}

def resolve_key(row, candidates):
    for c in candidates:
        if c in row and row[c] not in ('', None, 'None', 'nan'):
            return row[c]
    return None

def resolve_sport(row):
    src = str(row.get('_source','')).lower()
    if 'mlb' in src: return 'MLB'
    if 'wnba' in src: return 'WNBA'
    if 'nba' in src: return 'NBA'
    if 'nfl' in src: return 'NFL'
    if 'nhl' in src: return 'NHL'
    return resolve_key(row, KEY_MAP['sport'])

STANDARD = []
seen = set()

for row in ALL_ROWS:
    sport = resolve_sport(row)
    player = resolve_key(row, KEY_MAP['player'])
    stat = resolve_key(row, KEY_MAP['stat'])
    direction = resolve_key(row, KEY_MAP['direction'])
    projection = tryfloat(resolve_key(row, KEY_MAP['projection']))
    line = tryfloat(resolve_key(row, KEY_MAP['line']))
    edge = tryfloat(resolve_key(row, KEY_MAP['edge']))
    actual = tryfloat(resolve_key(row, KEY_MAP['actual']))
    hit = resolve_key(row, KEY_MAP['hit'])
    date = resolve_key(row, KEY_MAP['date'])
    confidence = resolve_key(row, KEY_MAP['confidence'])

    # Normalize direction
    if direction:
        d = str(direction).strip().upper()
        if 'OVER' in d: direction = 'OVER'
        elif 'UNDER' in d: direction = 'UNDER'
        else: direction = d

    # Normalize hit
    if hit:
        h = str(hit).strip().upper()
        if h in ('TRUE','1','WIN','HIT'): hit = True
        elif h in ('FALSE','0','LOSS','MISS'): hit = False
        else: hit = None
    else:
        hit = None

    # Deduplicate
    key = (str(sport or ''), str(player or ''), str(stat or ''), str(direction or ''), str(date or ''),
           str(projection or 0), str(line or 0), str(actual or 0))
    if key in seen:
        continue
    seen.add(key)

    STANDARD.append({
        'sport': sport,
        'player': player,
        'stat': stat,
        'direction': direction,
        'projection': projection,
        'line': line,
        'edge': edge,
        'actual': actual,
        'hit': hit,
        'date': date,
        'confidence': confidence,
    })

print(f"DEDUPED: {len(STANDARD)}")

# --- GRADE IF NOT ALREADY GRADED ---
graded = 0
for row in STANDARD:
    if row['hit'] is None and row['actual'] is not None and row['projection'] is not None:
        if row['direction'] == 'OVER':
            row['hit'] = row['actual'] >= row['projection']
        elif row['direction'] == 'UNDER':
            row['hit'] = row['actual'] <= row['projection']
        elif row['line'] and row['line'] > 0:
            row['hit'] = row['actual'] >= row['line'] if row['direction'] == 'OVER' else row['actual'] <= row['line']
        gradable = True
        if row['hit'] is not None:
            graded += 1

print(f"GRADED: {graded}")

# --- ANALYSIS ---
gradable = [r for r in STANDARD if r['hit'] is not None]
print(f"GRADABLE ROWS: {len(gradable)}")

# By sport
sport_stats = defaultdict(lambda: {'hits':0, 'total':0, 'over_hits':0, 'over_total':0, 'under_hits':0, 'under_total':0})
for r in gradable:
    s = r['sport'] or 'UNKNOWN'
    sport_stats[s]['total'] += 1
    if r['hit']:
        sport_stats[s]['hits'] += 1
    if r['direction'] == 'OVER':
        sport_stats[s]['over_total'] += 1
        if r['hit']: sport_stats[s]['over_hits'] += 1
    elif r['direction'] == 'UNDER':
        sport_stats[s]['under_total'] += 1
        if r['hit']: sport_stats[s]['under_hits'] += 1

print("\n=== BY SPORT ===")
for s in sorted(sport_stats, key=lambda x: sport_stats[x]['total'], reverse=True):
    st = sport_stats[s]
    print(f"{s:8s} | Total: {st['total']:5d} | Hit: {st['hits']/st['total']*100:5.1f}%"
          f" | OVER: {st['over_hits']/max(st['over_total'],1)*100:5.1f}% ({st['over_total']})"
          f" | UNDER: {st['under_hits']/max(st['under_total'],1)*100:5.1f}% ({st['under_total']})")

# By sport + stat + direction (combos)
combo_stats = defaultdict(lambda: {'hits':0, 'total':0})
for r in gradable:
    s = r['sport'] or 'UNKNOWN'
    stat = r['stat'] or 'UNKNOWN'
    d = r['direction'] or 'UNKNOWN'
    key = f"{s}|{stat}|{d}"
    combo_stats[key]['total'] += 1
    if r['hit']: combo_stats[key]['hits'] += 1

# Best combos (min 10 picks)
print("\n=== BEST COMBOS (MIN 10 PICKS) ===")
best = [(k, v['hits']/v['total']*100, v['total']) for k,v in combo_stats.items() if v['total'] >= 10]
best.sort(key=lambda x: x[1], reverse=True)
for sport_stat_dir, rate, total in best[:30]:
    print(f"  {sport_stat_dir:40s} | {rate:5.1f}% | N={total}")

# By edge bucket
print("\n=== BY EDGE BUCKET ===")
edge_buckets = defaultdict(lambda: {'hits':0, 'total':0})
for r in gradable:
    e = r['edge']
    if e is None: bucket = 'NO_EDGE'
    elif e < 0.05: bucket = '0-5%'
    elif e < 0.10: bucket = '5-10%'
    elif e < 0.15: bucket = '10-15%'
    elif e < 0.20: bucket = '15-20%'
    else: bucket = '20%+'
    edge_buckets[bucket]['total'] += 1
    if r['hit']: edge_buckets[bucket]['hits'] += 1

for b in ['NO_EDGE', '0-5%', '5-10%', '10-15%', '15-20%', '20%+']:
    if b in edge_buckets:
        eb = edge_buckets[b]
        print(f"  {b:10s} | {eb['hits']/eb['total']*100:5.1f}% | N={eb['total']}")

# By date (daily hit rates)
date_stats = defaultdict(lambda: {'hits':0, 'total':0})
for r in gradable:
    d = r['date'] or 'UNKNOWN'
    date_stats[d]['total'] += 1
    if r['hit']: date_stats[d]['hits'] += 1

print("\n=== DAILY HIT RATES ===")
for d in sorted(date_stats):
    ds = date_stats[d]
    if ds['total'] >= 5:
        print(f"  {d:15s} | {ds['hits']/ds['total']*100:5.1f}% | N={ds['total']}")

# Overall
total_hits = sum(1 for r in gradable if r['hit'])
print(f"\n=== OVERALL: {total_hits}/{len(gradable)} = {total_hits/len(gradable)*100:.1f}% ===")

# Save unified CSV
out_path = WORKSPACE / "data" / "picks" / "comprehensive_backtest_MAY_JULY_2026.csv"
with open(out_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['sport','player','stat','direction','projection','line','edge','actual','hit','date','confidence'])
    writer.writeheader()
    for r in gradable:
        writer.writerow(r)
print(f"\nSaved: {out_path}")
print(f"Rows: {len(gradable)}")
