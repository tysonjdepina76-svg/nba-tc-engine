import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PICKS_DB = os.path.join(DB_DIR, "picks.db")
PIPELINE_DB = os.path.join(DB_DIR, "tc_pipeline.db")


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)

    conn = sqlite3.connect(PICKS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date TEXT NOT NULL,
            sport TEXT NOT NULL,
            player TEXT NOT NULL,
            team TEXT,
            stat TEXT DEFAULT 'PTS',
            projection REAL NOT NULL,
            line REAL DEFAULT 0.0,
            edge REAL DEFAULT 0.0,
            signal TEXT DEFAULT 'WEAK',
            reason TEXT,
            outcome TEXT DEFAULT 'Pending',
            actual_value REAL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_picks_date ON picks(date)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_picks_sport ON picks(sport)
    """)
    conn.commit()
    conn.close()

    conn = sqlite3.connect(PIPELINE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS graded_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            sport TEXT NOT NULL,
            player TEXT NOT NULL,
            team TEXT,
            stat TEXT DEFAULT 'PTS',
            projection REAL,
            line REAL,
            actual REAL,
            hit INTEGER DEFAULT 0,
            edge REAL DEFAULT 0.0,
            reason TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_graded_date ON graded_picks(date)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bet_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date TEXT NOT NULL,
            sport TEXT NOT NULL,
            player TEXT NOT NULL,
            bet_type TEXT DEFAULT 'OVER',
            stake REAL DEFAULT 100.0,
            odds TEXT DEFAULT '-110',
            profit REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            pick_id INTEGER
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_bet_tracking_date ON bet_tracking(date)
    """)
    conn.commit()
    conn.close()

    return PICKS_DB, PIPELINE_DB


if __name__ == "__main__":
    p, t = init_db()
    print(f"Picks DB: {p}")
    print(f"Pipeline DB: {t}")
    print("Tables: picks, graded_picks, bet_tracking")
