#!/usr/bin/env python3
"""Comprehensive TC Backtest Scanner — 2023-2026 all sports, all archives."""

import sqlite3
import csv
import json
import os
import glob
import re
from collections import defaultdict
from datetime import datetime

OUTPUT = {}
STATS = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'hits': 0, 'profit': 0.0, 'graded': 0}))

def grade_row(row, sport_key='league', dir_key='direction', proj_key='tc_projection', 
              actual_key=None, edge_key='edge', result_key='result', hit_val='HIT',
              market_key='market_line', player_key='player', stat_key='stat'):
    s = row.get(sport_key, row.get('sport', 'UNKNOWN')).upper().strip()
    r = row.get(result_key, row.get('hit', '')).upper().strip()
    d = row.get(dir_key, row.get('over_under', '')).upper().strip()
    e = float(row.get(edge_key, 0) or 0)
    p = row.get(player_key, row.get('name', 'UNKNOWN'))
    st = row.get(stat_key, row.get('category', 'UNKNOWN'))
    dt = row.get('date', row.get('game_date', 'unknown'))[:10] if row.get('date') or row.get('game_date') else 'unknown'
    
    is_hit = r == hit_val or r == 'HIT' or r == '1' or r == 'TRUE'
    is_graded = r in ('HIT', 'MISS', '1', '0', 'TRUE', 'FALSE', 'H', 'M')
    
    return s, dt, p, st, d, e, is_hit, is_graded

# 1. TC_PIPELINE.DB — our core graded data
print("1. Scanning tc_pipeline.db...")
try:
    conn = sqlite3.connect('/home/workspace/Projects/data/tc_pipeline.db')
    c = conn.cursor()
    c.execute("SELECT sport, date, player, stat, direction, edge, hit FROM graded_picks")
    rows = c.fetchall()
    for row in rows:
        sport = (row[0] or '').upper().strip()
        date = (row[1] or '')[:10]
        direction = (row[4] or '').upper().strip()
        edge = float(row[5] or 0)
        is_hit = row[6] == 1
        
        STATS['tc_pipeline_db'][sport]['total'] += 1
        STATS['tc_pipeline_db'][sport]['graded'] += 1
        if is_hit:
            STATS['tc_pipeline_db'][sport]['hits'] += 1
        
        STATS['tc_pipeline_db']['__BY_DATE__'][date]['total'] += 1
        if is_hit:
            STATS['tc_pipeline_db']['__BY_DATE__'][date]['hits'] += 1
            
    conn.close()
    print(f"   tc_pipeline.db: {sum(v['total'] for k,v in STATS['tc_pipeline_db'].items() if k != '__BY_DATE__')} graded picks")
except Exception as e:
    print(f"   ERROR tc_pipeline.db: {e}")

# 2. All_graded_picks.csv
print("\n2. Scanning all_graded_picks.csv...")
try:
    with open('/home/workspace/Projects/all_graded_picks.csv') as f:
        reader = csv.DictReader(f)
        count = 0
        graded_count = 0
        for row in reader:
            s, dt, p, st, d, e, is_hit, is_graded = grade_row(row, sport_key='league')
            count += 1
            if is_graded:
                graded_count += 1
                STATS['all_graded'][s]['total'] += 1
                STATS['all_graded'][s]['graded'] += 1
                if is_hit:
                    STATS['all_graded'][s]['hits'] += 1
    print(f"   all_graded_picks.csv: {count} rows, {graded_count} graded")
except Exception as e:
    print(f"   ERROR all_graded: {e}")

# 3. Daily_Log/YYYY-MM-DD/picks.csv — all daily pick logs
print("\n3. Scanning Daily_Log daily picks...")
daily_log_dirs = sorted(glob.glob('/home/workspace/Daily_Log/202[56]-*/'))
pick_files = []
for d in daily_log_dirs:
    pf = os.path.join(d, 'picks.csv')
    if os.path.exists(pf):
        pick_files.append(pf)
    pf2 = os.path.join(d, 'picks_enhanced.csv')
    if os.path.exists(pf2):
        pick_files.append(pf2)

for pf in pick_files:
    try:
        with open(pf) as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = (row.get('league', row.get('sport', '')).upper().strip())
                r = (row.get('result', row.get('hit', '')).upper().strip())
                dt = pf.split('/')[-2]
                is_hit = r in ('HIT', '1', 'TRUE', 'H')
                is_graded = r in ('HIT', 'MISS', '1', '0', 'TRUE', 'FALSE', 'H', 'M')
                if is_graded:
                    STATS['daily_logs'][s]['total'] += 1
                    STATS['daily_logs'][s]['graded'] += 1
                    if is_hit:
                        STATS['daily_logs'][s]['hits'] += 1
                else:
                    STATS['daily_logs'][s]['total'] += 1
    except Exception as e:
        pass
print(f"   {len(pick_files)} daily pick files scanned")

# 4. Daily_Log/YYYY-MM-DD/graded_picks.csv — graded daily files
print("\n4. Scanning Daily_Log graded_picks...")
graded_files = glob.glob('/home/workspace/Daily_Log/202[56]-*/graded_picks.csv')
for gf in graded_files:
    try:
        with open(gf) as f:
            reader = csv.DictReader(f)
            for row in reader:
                s, dt, p, st, d, e, is_hit, is_graded = grade_row(row, sport_key='league')
                STATS['graded_logs'][s]['total'] += 1
                STATS['graded_logs'][s]['graded'] += 1
                if is_hit:
                    STATS['graded_logs'][s]['hits'] += 1
    except Exception as e:
        pass
print(f"   {len(graded_files)} graded pick files scanned")

# 5. data/historical/ — sport-specific archives (NBA, WNBA, MLB, Soccer)
print("\n5. Scanning data/historical archives...")
hist_files = glob.glob('/home/workspace/data/historical/**/picks.csv', recursive=True)
for hf in hist_files:
    path_parts = hf.split('/')
    try:
        sport = path_parts[-3].upper()
        season = path_parts[-2]
    except:
        continue
    try:
        with open(hf) as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = sport
                r = (row.get('result', row.get('hit', '')).upper().strip())
                is_hit = r in ('HIT', '1', 'TRUE', 'H')
                is_graded = r in ('HIT', 'MISS', '1', '0', 'TRUE', 'FALSE', 'H', 'M')
                STATS['historical'][s]['total'] += 1
                if is_graded:
                    STATS['historical'][s]['graded'] += 1
                    if is_hit:
                        STATS['historical'][s]['hits'] += 1
    except Exception as e:
        pass
print(f"   {len(hist_files)} historical pick files scanned")

# 6. data/backtest/ — sport-specific backtest CSVs
print("\n6. Scanning data/backtest...")
bt_files = glob.glob('/home/workspace/data/backtest/*.csv')
for bf in bt_files:
    fname = os.path.basename(bf)
    try:
        with open(bf) as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            for row in reader:
                s = 'UNKNOWN'
                if 'wnba' in fname.lower():
                    s = 'WNBA'
                elif 'nba' in fname.lower():
                    s = 'NBA'
                elif 'mlb' in fname.lower():
                    s = 'MLB'
                elif 'soccer' in fname.lower() or 'wc' in fname.lower():
                    s = 'WC'
                
                r = (row.get('result', row.get('hit', '')).upper().strip())
                is_hit = r in ('HIT', '1', 'TRUE', 'H')
                is_graded = r in ('HIT', 'MISS', '1', '0', 'TRUE', 'FALSE', 'H', 'M')
                STATS['backtest_data'][s]['total'] += 1
                if is_graded:
                    STATS['backtest_data'][s]['graded'] += 1
                    if is_hit:
                        STATS['backtest_data'][s]['hits'] += 1
    except Exception as e:
        pass
print(f"   {len(bt_files)} backtest CSV files scanned")

# 7. Reports/wc_*.csv, Reports/mlb_*.csv
print("\n7. Scanning Reports/...")
report_files = glob.glob('/home/workspace/Reports/wc_*.csv') + glob.glob('/home/workspace/Reports/MLB_*.csv')
for rf in report_files:
    try:
        with open(rf) as f:
            reader = csv.DictReader(f)
            s = 'WC' if 'wc_' in rf.lower() else 'MLB'
            for row in reader:
                r = (row.get('result', row.get('hit', '')).upper().strip())
                is_hit = r in ('HIT', '1', 'TRUE', 'H')
                is_graded = r in ('HIT', 'MISS', '1', '0', 'TRUE', 'FALSE', 'H', 'M')
                STATS['reports'][s]['total'] += 1
                if is_graded:
                    STATS['reports'][s]['graded'] += 1
                    if is_hit:
                        STATS['reports'][s]['hits'] += 1
    except:
        pass
print(f"   {len(report_files)} report CSVs scanned")

# 8. Backtest_Reports/ 
print("\n8. Scanning Backtest_Reports...")
br_file = '/home/workspace/Backtest_Reports/BACKTEST_RECONCILIATION_20260715.json'
if os.path.exists(br_file):
    try:
        with open(br_file) as f:
            data = json.load(f)
            print(f"   Loaded BACKTEST_RECONCILIATION: {len(str(data))} chars")
            OUTPUT['reconciliation'] = data
    except Exception as e:
        print(f"   ERROR: {e}")

# 9. Combined backtest from Daily_Log/backtests/
print("\n9. Scanning Daily_Log/backtests/...")
cbt = '/home/workspace/Daily_Log/backtests/combined_backtest.csv'
if os.path.exists(cbt):
    try:
        with open(cbt) as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = (row.get('league', row.get('sport', '')).upper().strip())
                r = (row.get('result', 'hit').upper().strip())
                is_hit = r in ('HIT', '1', 'TRUE')
                is_graded = r in ('HIT', 'MISS', '1', '0')
                STATS['combined_bt'][s]['total'] += 1
                if is_graded:
                    STATS['combined_bt'][s]['graded'] += 1
                    if is_hit:
                        STATS['combined_bt'][s]['hits'] += 1
        print(f"   combined_backtest.csv scanned")
    except Exception as e:
        print(f"   ERROR: {e}")

# 10. Daily_Log/backtests/30day/
print("\n10. Scanning 30-day hit rates...")
h30 = '/home/workspace/Daily_Log/backtests/30day/30day_hitrates.csv'
if os.path.exists(h30):
    try:
        with open(h30) as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = (row.get('sport', row.get('league', '')).upper().strip())
                r = (row.get('result', row.get('hit', '')).upper().strip())
                is_hit = r in ('HIT', '1', 'TRUE')
                is_graded = r in ('HIT', 'MISS', '1', '0')
                STATS['30day'][s]['total'] += 1
                if is_graded:
                    STATS['30day'][s]['graded'] += 1
                    if is_hit:
                        STATS['30day'][s]['hits'] += 1
    except:
        pass

# ====== BUILD REPORT ======
print("\n\n============ COMPREHENSIVE BACKTEST REPORT ============")
print(f"Generated: {datetime.now().isoformat()}")
print()

TOTAL_ALL = defaultdict(lambda: {'total': 0, 'hits': 0, 'graded': 0})

for source, sports in sorted(STATS.items()):
    print(f"\n=== SOURCE: {source} ===")
    for sport, data in sorted(sports.items()):
        if sport.startswith('__'):
            continue
        graded = data.get('graded', data['total'])
        total = data['total']
        hits = data['hits']
        rate = 100 * hits / graded if graded > 0 else 0
        print(f"  {sport:12s}: {total:5d} total | {graded:5d} graded | {hits:5d} HIT | {rate:5.1f}%")
        
        TOTAL_ALL[sport]['total'] += total
        TOTAL_ALL[sport]['graded'] += graded
        TOTAL_ALL[sport]['hits'] += hits

print(f"\n============ AGGREGATE BY SPORT (ALL SOURCES) ============")
for sport in sorted(TOTAL_ALL.keys()):
    d = TOTAL_ALL[sport]
    rate = 100 * d['hits'] / d['graded'] if d['graded'] > 0 else 0
    print(f"  {sport:12s}: {d['total']:6d} total | {d['graded']:6d} graded | {d['hits']:5d} HIT | {rate:5.1f}%")

# Save to JSON
output_path = '/home/workspace/Backtest_Reports/COMPREHENSIVE_SCAN_20260719.json'
os.makedirs('/home/workspace/Backtest_Reports', exist_ok=True)
with open(output_path, 'w') as f:
    json.dump({
        'generated': datetime.now().isoformat(),
        'aggregate': {s: dict(d) for s, d in TOTAL_ALL.items()},
        'sources': {src: {s: dict(d) for s, d in sp.items() if not s.startswith('__')} 
                    for src, sp in STATS.items()}
    }, f, indent=2)

print(f"\nFull JSON saved to: {output_path}")
print(f"Total picks across all sources: {sum(d['total'] for d in TOTAL_ALL.values())}")
print(f"Total graded: {sum(d['graded'] for d in TOTAL_ALL.values())}")
print(f"Total HIT: {sum(d['hits'] for d in TOTAL_ALL.values())}")
all_rate = 100 * sum(d['hits'] for d in TOTAL_ALL.values()) / sum(d['graded'] for d in TOTAL_ALL.values()) if sum(d['graded'] for d in TOTAL_ALL.values()) else 0
print(f"OVERALL HIT RATE: {all_rate:.1f}%")
