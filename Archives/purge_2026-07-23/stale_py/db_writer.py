import sqlite3
import os
from typing import Dict, List, Any

PICKS_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "picks.db")
PIPELINE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tc_pipeline.db")


def init_databases():
    os.makedirs(os.path.dirname(PICKS_DB), exist_ok=True)
    os.makedirs(os.path.dirname(PIPELINE_DB), exist_ok=True)

    conn = sqlite3.connect(PICKS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            league TEXT,
            player TEXT,
            team TEXT,
            stat TEXT,
            tc_projection REAL,
            market_line REAL,
            edge REAL,
            reason TEXT,
            direction TEXT,
            matchup TEXT,
            period TEXT,
            signal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    conn = sqlite3.connect(PIPELINE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS graded_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sport TEXT,
            player TEXT,
            stat TEXT,
            projection REAL,
            actual REAL,
            hit INTEGER,
            edge REAL,
            direction TEXT,
            date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bet_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sport TEXT,
            player TEXT,
            stat TEXT,
            line REAL,
            stake REAL DEFAULT 1.0,
            odds INTEGER DEFAULT -110,
            profit REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def write_picks_to_db(picks: List[Dict[str, Any]], log_date: str):
    init_databases()

    conn = sqlite3.connect(PICKS_DB)
    for p in picks:
        conn.execute("""
            INSERT OR REPLACE INTO picks
            (date, league, player, team, stat, tc_projection, market_line, edge, reason, direction, matchup, period, signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p.get("date", log_date),
            p.get("league", ""),
            p.get("player", ""),
            p.get("team", ""),
            p.get("stat", ""),
            p.get("tc_projection", 0),
            p.get("market_line", 0),
            round(p.get("edge", 0) * 100, 2),
            p.get("why", ""),
            p.get("direction", ""),
            p.get("matchup", ""),
            p.get("period", "GAME"),
            p.get("signal", ""),
        ))
    conn.commit()
    conn.close()
    print(f"Wrote {len(picks)} picks to {PICKS_DB}")
