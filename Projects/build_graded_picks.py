#!/usr/bin/env python3
import sqlite3, csv, os, glob
from datetime import datetime

DB = "/home/workspace/picks.db"
DAILY_LOG = "/home/workspace/Daily_Log"

conn = sqlite3.connect(DB)
conn.execute("DROP TABLE IF EXISTS graded_picks")
conn.execute("""
    CREATE TABLE graded_picks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        name TEXT,
        team TEXT,
        sport TEXT,
        stat TEXT,
        matchup TEXT,
        projection REAL,
        line REAL,
        edge REAL,
        direction TEXT,
        reason TEXT,
        hit INTEGER DEFAULT 0,
        profit REAL DEFAULT 0,
        actual REAL DEFAULT 0
    )
""")

total = 0
graded_files = glob.glob(f"{DAILY_LOG}/*/graded_picks.csv") + glob.glob(f"{DAILY_LOG}/*/*.csv")
for fpath in sorted(graded_files):
    if "graded" not in fpath and "mlb_graded" not in fpath:
        continue
    date = fpath.split("/")[-3] if "/Daily_Log/" in fpath else "unknown"
    with open(fpath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT INTO graded_picks (date, name, team, sport, stat, matchup, projection, line, edge, direction, reason, hit, profit, actual)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date,
                row.get("name", row.get("player", "")),
                row.get("team", ""),
                row.get("sport", row.get("league", "")).lower(),
                row.get("stat", ""),
                row.get("matchup", ""),
                float(row.get("projection", row.get("tc_projection", 0)) or 0),
                float(row.get("line", row.get("market_line", 0)) or 0),
                float(row.get("edge", 0) or 0),
                row.get("direction", ""),
                row.get("reason", row.get("rationale", "")),
                1 if str(row.get("hit", "")).strip().upper() in ("1", "TRUE", "HIT", "YES") else 0,
                float(str(row.get("profit", 0)).replace("PENDING", "0") or 0),
                float(str(row.get("actual", 0)).replace("PENDING", "0") or 0)
            ))
            total += 1

conn.commit()
conn.close()
print(f"Imported {total} graded picks into graded_picks table")
