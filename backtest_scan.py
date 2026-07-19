#!/usr/bin/env python3
"""TC Backtest Monolith — scans ALL Zo-filed backtest data across 2023-2025 WNBA/NBA/NFL + 2025-2026 NBA/NFL/MLB/WC/WNBA"""

import sqlite3, csv, json, os, re
from collections import defaultdict
from pathlib import Path

WORKSPACE = Path('/home/workspace')
RESULTS = defaultdict(lambda: defaultdict(lambda: {'total':0,'hit':0,'push':0,'miss':0,'profit':0.0}))

# ── 1. TC_PIPELINE.DB (graded_picks) ──────────────────────────────
print("=" * 60)
print("📊 STRATA 1: tc_pipeline.db (graded_picks)")
print("=" * 60)
try:
    conn = sqlite3.connect(str(WORKSPACE / 'Projects/data/tc_pipeline.db'))
    c = conn.cursor()
    c.execute("SELECT sport, COUNT(*), SUM(hit), ROUND(100.0*SUM(hit)/COUNT(*),1) FROM graded_picks GROUP BY sport")
    for sport, total, hits, rate in c.fetchall():
        RESULTS['tc_pipeline_db'][sport] = {'total':total,'hit':hits or 0,'rate':rate or 0}
        print(f"  {sport}: {total} picks, {hits or 0} HIT ({rate or 0}%)")
    c.execute("SELECT COUNT(*), SUM(hit), SUM(profit) FROM graded_picks")
    t,h,p = c.fetchone()
    print(f"  ═══ TOTAL: {t} picks, {h or 0} HIT ({round(100*(h or 0)/t,1) if t else 0}%), ${p or 0:.0f} profit")
    conn.close()
except Exception as e:
    print(f"  ERROR: {e}")

# ── 2. ALL_GRADED_PICKS.CSV ───────────────────────────────────────
print("\n" + "=" * 60)
print("📊 STRATA 2: all_graded_picks.csv")
print("=" * 60)
try:
    with open(WORKSPACE / 'Projects/all_graded_picks.csv') as f:
        reader = csv.DictReader(f)
        stats = defaultdict(lambda: {'total':0,'hit':0,'push':0,'miss':0,'graded':0})
        for row in reader:
            league = row['league']
            stats[league]['total'] += 1
            result = row.get('result','PENDING')
            if result == 'HIT':
                stats[league]['hit'] += 1
                stats[league]['graded'] += 1
            elif result == 'MISS':
                stats[league]['miss'] += 1
                stats[league]['graded'] += 1
            elif result == 'PUSH':
                stats[league]['push'] += 1
                stats[league]['graded'] += 1
    for league, s in sorted(stats.items()):
        r = 100*s['hit']/s['graded'] if s['graded'] else 0
        RESULTS['all_graded_csv'][league] = {'total':s['total'],'hit':s['hit'],'graded':s['graded'],'rate':r}
        print(f"  {league}: {s['total']} total, {s['graded']} graded, {s['hit']} HIT ({r:.1f}%)")
except Exception as e:
    print(f"  ERROR: {e}")

# ── 3. DATA/BACKTEST CSVs ────────────────────────────────────────
print("\n" + "=" * 60)
print("📊 STRATA 3: data/backtest/ CSVs")
print("=" * 60)
bt_dir = WORKSPACE / 'data/backtest'
for csvf in sorted(bt_dir.glob('*.csv')):
    try:
        with open(csvf) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            cols = reader.fieldnames or []
            has_hit = 'hit' in cols or 'result' in cols or 'actual' in cols
            print(f"  {csvf.name}: {len(rows)} rows, cols={cols[:5]}...{' HAS_RESULT' if has_hit else ''}")
            if has_hit:
                hits = sum(1 for r in rows if str(r.get('hit','')).upper() in ('1','TRUE','HIT') or str(r.get('result','')).upper() == 'HIT')
                print(f"    → {hits}/{len(rows)} hits ({round(100*hits/len(rows),1)}% of total)") if len(rows) else None
    except Exception as e:
        print(f"  {csvf.name}: ERROR {e}")

# ── 4. DAILY_LOG BACKTEST CSVs ──────────────────────────────────
print("\n" + "=" * 60)
print("📊 STRATA 4: Daily_Log/backtest + backtests/")
print("=" * 60)
for bt_path in [WORKSPACE / 'Daily_Log/backtest', WORKSPACE / 'Daily_Log/backtests']:
    for csvf in sorted(bt_path.rglob('*.csv')):
        try:
            with open(csvf) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                cols = reader.fieldnames or []
                relpath = csvf.relative_to(WORKSPACE)
                print(f"  {relpath}: {len(rows)} rows, cols={cols[:5]}...")
        except Exception as e:
            print(f"  {csvf.relative_to(WORKSPACE)}: ERROR {e}")

# ── 5. HISTORICAL DATA (data/historical/) ───────────────────────
print("\n" + "=" * 60)
print("📊 STRATA 5: data/historical/")
print("=" * 60)
hist_dir = WORKSPACE / 'data/historical'
hist_summary = defaultdict(lambda: {'days':0,'picks':0,'hits':0})
for sport_dir in sorted(hist_dir.iterdir()):
    if not sport_dir.is_dir(): continue
    for season_dir in sorted(sport_dir.iterdir()):
        if not season_dir.is_dir(): continue
        for day_dir in sorted(season_dir.iterdir()):
            if not day_dir.is_dir(): continue
            picks_file = day_dir / 'picks.csv'
            if picks_file.exists():
                with open(picks_file) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    cols = reader.fieldnames or []
                    has_hit = any(c for c in cols if 'hit' in c.lower() or 'result' in c.lower())
                    hits = 0
                    if has_hit:
                        for r in rows:
                            if str(r.get('hit','')).upper() in ('1','TRUE','HIT') or str(r.get('result','')).upper() == 'HIT':
                                hits += 1
                    key = f"{sport_dir.name}/{season_dir.name}"
                    hist_summary[key]['days'] += 1
                    hist_summary[key]['picks'] += len(rows)
                    hist_summary[key]['hits'] += hits
                    RESULTS['historical'][key] = {'days':hist_summary[key]['days'],'picks':hist_summary[key]['picks'],'hits':hist_summary[key]['hits']}
for k,v in sorted(hist_summary.items()):
    r = 100*v['hits']/v['picks'] if v['picks'] else 0
    print(f"  {k}: {v['days']} days, {v['picks']} picks, {v['hits']} HIT ({r:.1f}%)")

# ── 6. DAILY_LOG PICK FILES (all dates) ─────────────────────────
print("\n" + "=" * 60)
print("📊 STRATA 6: Daily_Log/YYYY-MM-DD/picks.csv")
print("=" * 60)
dl_dir = WORKSPACE / 'Daily_Log'
dl_summary = defaultdict(lambda: {'files':0,'rows':0,'hits':0})
for day_dir in sorted(dl_dir.iterdir()):
    if not day_dir.is_dir(): continue
    if not re.match(r'\d{4}-\d{2}-\d{2}', day_dir.name): continue
    picks_file = day_dir / 'picks.csv'
    if not picks_file.exists(): continue
    with open(picks_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = reader.fieldnames or []
        # Get sport from league column if present
        sport = 'unknown'
        if rows and 'league' in cols:
            sport = rows[0].get('league','unknown')
        has_result = any(c for c in cols if 'result' in c.lower() or 'actual' in c.lower())
        hits = 0
        if has_result:
            for r in rows:
                res = str(r.get('result','')).upper()
                if res in ('HIT','1','TRUE'):
                    hits += 1
        dl_summary[day_dir.name]['files'] += 1
        dl_summary[day_dir.name]['rows'] += len(rows)
        dl_summary[day_dir.name]['hits'] += hits

for dt in sorted(dl_summary.keys()):
    v = dl_summary[dt]
    r = 100*v['hits']/v['rows'] if v['rows'] else 0
    RESULTS['daily_log'][dt] = dict(v)
    if v['rows'] > 100:  # Only print substantial days
        print(f"  {dt}: {v['rows']} picks, {v['hits']} HIT ({r:.1f}%)")

# ── 7. BACKTEST_REPORTS / RECONCILIATION ─────────────────────────
print("\n" + "=" * 60)
print("📊 STRATA 7: Backtest_Reports + Reports")
print("=" * 60)
for report_dir in [WORKSPACE / 'Backtest_Reports', WORKSPACE / 'Reports']:
    if not report_dir.exists(): continue
    for f in sorted(report_dir.glob('*.json')):
        try:
            with open(f) as jf:
                data = json.load(jf)
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"  {f.name}: JSON with keys {keys}")
                elif isinstance(data, list):
                    print(f"  {f.name}: JSON list, {len(data)} items")
        except: pass
    for f in sorted(report_dir.glob('*.md')):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes markdown")

# ── 8. FINAL AGGREGATE ───────────────────────────────────────────
print("\n" + "=" * 60)
print("📊 FINAL TRUTH TABLE")
print("=" * 60)
print(f"{'SOURCE':<30} {'SPORTS':<25} {'PICKS':>8} {'HITS':>8} {'RATE':>8}")
print("-" * 85)

# tc_pipeline.db
for s, v in sorted(RESULTS['tc_pipeline_db'].items()):
    print(f"{'tc_pipeline.db':<30} {s:<25} {v['total']:>8} {v['hit']:>8} {v['rate']:>7.1f}%")
t_pipe = RESULTS['tc_pipeline_db']
total_pipe = sum(v['total'] for v in t_pipe.values())
hits_pipe = sum(v['hit'] for v in t_pipe.values())
print(f"{'tc_pipeline.db':<30} {'═══ ALL':<25} {total_pipe:>8} {hits_pipe:>8} {round(100*hits_pipe/total_pipe,1) if total_pipe else 0:>7.1f}%")

# all_graded_csv
for s, v in sorted(RESULTS['all_graded_csv'].items()):
    if v['graded'] > 0:
        print(f"{'all_graded.csv':<30} {s:<25} {v['graded']:>8} {v['hit']:>8} {v['rate']:>7.1f}%")

# Save results
out = dict(RESULTS)
out['_timestamp'] = '2026-07-19T05:30:00-04:00'
out['_total_pipeline'] = {'picks': total_pipe, 'hits': hits_pipe, 'rate': round(100*hits_pipe/total_pipe,1) if total_pipe else 0}
with open(WORKSPACE / 'backtest_truth_20260719.json', 'w') as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n✅ Saved to backtest_truth_20260719.json")
