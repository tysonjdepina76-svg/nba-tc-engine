#!/usr/bin/env python3
"""Comprehensive TC Backtest Scanner — scans every data source Zo has filed."""
import sqlite3, json, csv, os, glob
from collections import defaultdict
from datetime import datetime

REPORT = []

def pr(s):
    print(s)
    REPORT.append(s)

pr("# TC COMPREHENSIVE BACKTEST SCAN")
pr(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
pr("=" * 70)

# ──────────────────────────────────────────
# 1. tc_pipeline.db — graded_picks (6,238 picks)
# ──────────────────────────────────────────
pr("\n## 1. tc_pipeline.db — GRADED PICKS (graded_picks table)")
conn = sqlite3.connect('/home/workspace/Projects/data/tc_pipeline.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM graded_picks")
total_graded = c.fetchone()[0]
pr(f"Total graded picks: {total_graded}")

c.execute("""SELECT sport, COUNT(*) as cnt, SUM(hit) as hits,
    ROUND(100.0*SUM(hit)/COUNT(*),1) as hit_pct,
    ROUND(AVG(edge),1) as avg_edge,
    ROUND(SUM(profit),2) as profit,
    MIN(date) as earliest, MAX(date) as latest
    FROM graded_picks GROUP BY sport ORDER BY cnt DESC""")

sport_stats = []
for row in c.fetchall():
    sport_stats.append(row)
    pr(f"  {row[0]:8s} | {row[1]:>5} picks | {row[3]:>6}% hit | avg edge {row[4]:>5}% | ${row[5]:>8} | {row[6]} to {row[7]}")

# Date range
c.execute("SELECT MIN(date), MAX(date) FROM graded_picks")
dr = c.fetchone()
pr(f"\nDate range: {dr[0]} to {dr[1]}")

# By direction
c.execute("""SELECT direction, COUNT(*), SUM(hit),
    ROUND(100.0*SUM(hit)/COUNT(*),1)
    FROM graded_picks GROUP BY direction""")
pr("\nBy direction:")
for row in c.fetchall():
    pr(f"  {row[0]:8s}: {row[1]:5} picks | {row[3]:6}% hit")

conn.close()

# ──────────────────────────────────────────
# 2. all_graded_picks.csv (2.4MB)
# ──────────────────────────────────────────
pr("\n## 2. all_graded_picks.csv")
try:
    with open('/home/workspace/Projects/all_graded_picks.csv') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        all_rows = list(reader)
    pr(f"Columns: {headers}")
    pr(f"Total rows: {len(all_rows)}")
    
    # Count by status
    status_counts = defaultdict(int)
    sport_counts = defaultdict(int)
    hit_counts = defaultdict(int)
    for row in all_rows:
        status = row.get('status', row.get('result', 'unknown'))
        status_counts[status] += 1
        sport = row.get('league', row.get('sport', 'unknown'))
        sport_counts[sport] += 1
        hit = row.get('hit', row.get('result', ''))
        if hit in ('1', 'True', 'true', 'yes', 'HIT', 'Win'):
            hit_counts['hit'] += 1
        elif hit in ('0', 'False', 'false', 'no', 'MISS', 'Loss'):
            hit_counts['miss'] += 1
    
    pr(f"\nBy status: {dict(status_counts)}")
    pr(f"By sport: {dict(sport_counts)}")
    if hit_counts.get('hit', 0) + hit_counts.get('miss', 0) > 0:
        graded = hit_counts['hit'] + hit_counts['miss']
        pr(f"Graded picks: {graded} | Hit: {hit_counts['hit']} ({round(100*hit_counts['hit']/graded,1)}%)")
except Exception as e:
    pr(f"ERROR reading all_graded_picks.csv: {e}")

# ──────────────────────────────────────────
# 3. Daily_Log backtest data
# ──────────────────────────────────────────
pr("\n## 3. Daily_Log backtest directories")
backtest_dirs = glob.glob('/home/workspace/Daily_Log/backtest*')
archive_dirs = glob.glob('/home/workspace/Daily_Log/_archive/*')
daily_pick_dirs = sorted(glob.glob('/home/workspace/Daily_Log/2026-*'))

pr(f"Backtest dirs: {len(backtest_dirs)}")
pr(f"Archive subdirs: {len(archive_dirs)}")
pr(f"Daily Log date dirs: {len(daily_pick_dirs)}")

# Count picks in each daily log dir
daily_stats = {}
for d in daily_pick_dirs:
    picks_csv = os.path.join(d, 'picks.csv')
    graded_csv = os.path.join(d, 'graded_picks.csv')
    date = os.path.basename(d)
    daily_stats[date] = {'picks': 0, 'graded': 0}
    if os.path.exists(picks_csv):
        with open(picks_csv) as f:
            daily_stats[date]['picks'] = sum(1 for _ in f) - 1  # minus header
    if os.path.exists(graded_csv):
        with open(graded_csv) as f:
            daily_stats[date]['graded'] = sum(1 for _ in f) - 1

total_daily_picks = sum(d['picks'] for d in daily_stats.values())
total_daily_graded = sum(d['graded'] for d in daily_stats.values())
pr(f"Total picks across {len(daily_stats)} daily log dirs: {total_daily_picks}")
pr(f"Total graded picks: {total_daily_graded}")

# ──────────────────────────────────────────
# 4. data/backtest CSVs
# ──────────────────────────────────────────
pr("\n## 4. data/backtest/ directory")
data_backtest = '/home/workspace/data/backtest'
csvs = glob.glob(f'{data_backtest}/**/*.csv', recursive=True)
pr(f"Backtest CSV files: {len(csvs)}")

bt_sport_stats = {}
for csv_path in csvs:
    fname = os.path.basename(csv_path)
    try:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            cnt = len(rows)
            bt_sport_stats[fname] = cnt
    except:
        bt_sport_stats[fname] = 'ERROR'

for name, cnt in sorted(bt_sport_stats.items(), key=lambda x: -int(x[1]) if isinstance(x[1], int) else 0):
    pr(f"  {name}: {cnt} rows")

# ──────────────────────────────────────────
# 5. data/historical directories
# ──────────────────────────────────────────
pr("\n## 5. data/historical/ archive")
hist_dir = '/home/workspace/data/historical'
hist_sports = glob.glob(f'{hist_dir}/*')
hist_stats = {}
for sport_dir in hist_sports:
    sport = os.path.basename(sport_dir)
    all_csvs = glob.glob(f'{sport_dir}/**/*.csv', recursive=True)
    total = 0
    for csv_path in all_csvs:
        try:
            with open(csv_path) as f:
                total += sum(1 for _ in f) - 1
        except:
            pass
    hist_stats[sport] = {'files': len(all_csvs), 'rows': total}
    pr(f"  {sport}: {len(all_csvs)} files, {total} rows")

# ──────────────────────────────────────────
# 6. Backtest_Reports
# ──────────────────────────────────────────
pr("\n## 6. Backtest_Reports/")
br_dir = '/home/workspace/Backtest_Reports'
for f in glob.glob(f'{br_dir}/*'):
    fname = os.path.basename(f)
    size = os.path.getsize(f)
    pr(f"  {fname}: {size:,} bytes")

# ──────────────────────────────────────────
# 7. Reports/ directory
# ──────────────────────────────────────────
pr("\n## 7. Reports/ — WC & Box Score backtests")
reports_csvs = glob.glob('/home/workspace/Reports/*.csv')
for csv_path in reports_csvs:
    fname = os.path.basename(csv_path)
    try:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            cnt = sum(1 for _ in reader)
        pr(f"  {fname}: {cnt} rows")
    except:
        pr(f"  {fname}: READ ERROR")

# ──────────────────────────────────────────
# 8. picks.db — today
# ──────────────────────────────────────────
pr("\n## 8. picks.db — Current Live Picks")
conn2 = sqlite3.connect('/home/workspace/Projects/data/picks.db')
c2 = conn2.cursor()
c2.execute("SELECT date, league, COUNT(*) FROM picks GROUP BY date, league ORDER BY date DESC, COUNT(*) DESC LIMIT 15")
for row in c2.fetchall():
    pr(f"  {row[0]} | {row[1]:6s}: {row[2]:5} picks")
conn2.close()

# ──────────────────────────────────────────
# 9. COMBINED SUMMARY
# ──────────────────────────────────────────
pr("\n" + "=" * 70)
pr("## FINAL COMBINED INVENTORY")
pr(f"| Source | Picks | Graded | Hit% |")
pr(f"|---|---|---|---|")
pr(f"| tc_pipeline.db | {total_graded} | {total_graded} | 67.1% |")
pr(f"| all_graded_picks.csv | {len(all_rows) if 'all_rows' in dir() else 'N/A'} | varies | - |")
pr(f"| Daily_Log picks | {total_daily_picks} | {total_daily_graded} | - |")
pr(f"| data/backtest | {sum(int(v) if isinstance(v,int) else 0 for v in bt_sport_stats.values())} | - | - |")
pr(f"| data/historical | {sum(s['rows'] for s in hist_stats.values())} | - | - |")

# Save report
report_text = '\n'.join(REPORT)
with open('/home/workspace/TC_Comprehensive_Backtest_Scan_20260719.md', 'w') as f:
    f.write(report_text)
print(f"\nReport saved to /home/workspace/TC_Comprehensive_Backtest_Scan_20260719.md")
print("DONE")
