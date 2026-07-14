"""Build backtest_data.db from /home/workspace/Daily_Log.
picks.csv has: date,league,matchup,team,player,role,status,stat,direction,market_line,tc_projection,tc_target,edge,threshold,raw_average,source,actual,result
"""
import sqlite3
import csv
from pathlib import Path
import os
import shutil

LOG_DIR = Path("/home/workspace/Daily_Log")
DB_PATH = "/home/workspace/Projects/backtest_data.db"

# Fresh DB
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, sport TEXT, league_raw TEXT, matchup TEXT, team TEXT,
    player TEXT, role TEXT, status TEXT, stat TEXT, direction TEXT,
    market_line REAL, tc_projection REAL, tc_target REAL,
    edge REAL, threshold REAL, raw_average REAL,
    source TEXT, actual REAL, result TEXT
)
""")

cur.execute("""
CREATE TABLE backtest_summary (
    sport TEXT, date TEXT, total INTEGER, wins INTEGER, losses INTEGER,
    pending INTEGER, winrate REAL, avg_edge REAL, roi REAL,
    PRIMARY KEY (sport, date)
)
""")

picks_files = sorted(LOG_DIR.rglob("picks.csv"))
print(f"Found {len(picks_files)} picks.csv files")

imported = 0
for f in picks_files:
    date = f.parent.name
    with open(f) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            def _f(k):
                try: return float(row.get(k, "") or 0)
                except: return 0.0
            league = row.get("league", "Unknown")
            sport = league
            cur.execute("""INSERT INTO picks
                (date, sport, league_raw, matchup, team, player, role, status,
                 stat, direction, market_line, tc_projection, tc_target,
                 edge, threshold, raw_average, source, actual, result)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (date, sport, league, row.get("matchup",""), row.get("team",""),
                 row.get("player",""), row.get("role",""), row.get("status",""),
                 row.get("stat",""), row.get("direction",""),
                 _f("market_line"), _f("tc_projection"), _f("tc_target"),
                 _f("edge"), _f("threshold"), _f("raw_average"),
                 row.get("source",""), _f("actual"), row.get("result","")))
            imported += 1
conn.commit()
print(f"Imported {imported:,} picks")

# Build summary from picks (result column is the truth)
cur.execute("""
INSERT OR REPLACE INTO backtest_summary
(sport, date, total, wins, losses, pending, winrate, avg_edge, roi)
SELECT sport, date,
       COUNT(*),
       SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
       SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END),
       SUM(CASE WHEN result='PENDING' OR result='' OR result IS NULL THEN 1 ELSE 0 END),
       ROUND(100.0 * SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) /
             NULLIF(SUM(CASE WHEN result IN ('WIN','LOSS') THEN 1 ELSE 0 END), 0), 2),
       ROUND(AVG(edge), 3),
       ROUND(100.0 * (SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) * 0.91 -
                      SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END)) /
             COUNT(*), 2)
FROM picks
GROUP BY sport, date
""")
conn.commit()

# CSV exports
os.system(f'sqlite3 -header -csv {DB_PATH} "SELECT * FROM backtest_summary ORDER BY date DESC, sport;" > backtest_full_export.csv')
os.system(f'sqlite3 -header -csv {DB_PATH} "SELECT * FROM picks WHERE date >= \'2026-06-01\' ORDER BY date DESC, sport;" > backtest_picks_export.csv')

# Final stats
print("\n=== OVERALL STATS ===")
cur.execute("""SELECT
    COUNT(*) as total,
    SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN result='PENDING' OR result='' THEN 1 ELSE 0 END) as pending
    FROM picks""")
t, w, l, p = cur.fetchone()
graded = w + l
print(f"Total picks: {t:,} | Wins: {w:,} | Losses: {l:,} | Pending: {p:,}")
if graded:
    print(f"Winrate (graded only): {100*w/graded:.2f}%")

print("\n=== BY SPORT ===")
for row in cur.execute("""SELECT sport, COUNT(*),
    SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
    SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END),
    SUM(CASE WHEN result='PENDING' OR result='' THEN 1 ELSE 0 END),
    ROUND(100.0*SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END)/
          NULLIF(SUM(CASE WHEN result IN ('WIN','LOSS') THEN 1 ELSE 0 END), 0), 2)
    FROM picks GROUP BY sport ORDER BY sport"""):
    sport, total, w, l, p, wr = row
    print(f"  {sport:10} total={total:6} W={w or 0:5} L={l or 0:5} P={p or 0:6} winrate={wr or 0:5.1f}%")

print(f"\nDB: {DB_PATH}")
print(f"Exports: backtest_full_export.csv, backtest_picks_export.csv")
conn.close()
