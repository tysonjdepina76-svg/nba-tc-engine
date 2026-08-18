#!/usr/bin/env python3
"""
archive_orphans.py – Export all picks with NULL game_id to CSV/Parquet,
then mark them as 'archived' in the DB (or delete them if you prefer).
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "picks.db"
ARCHIVE_DIR = Path(__file__).parent.parent / "data" / "orphan"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

def archive_orphans():
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("SELECT * FROM picks WHERE game_id IS NULL", conn)
    if df.empty:
        print("No orphan picks found.")
        conn.close()
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = ARCHIVE_DIR / f"orphans_{timestamp}.csv"
    parquet_path = ARCHIVE_DIR / f"orphans_{timestamp}.parquet"
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    cursor = conn.cursor()
    cursor.execute("ALTER TABLE picks ADD COLUMN archived INTEGER DEFAULT 0")
    cursor.execute("UPDATE picks SET archived = 1 WHERE game_id IS NULL")
    conn.commit()
    conn.close()

    print(f"Archived {len(df)} orphan picks to {csv_path} and {parquet_path}")

if __name__ == "__main__":
    archive_orphans()
