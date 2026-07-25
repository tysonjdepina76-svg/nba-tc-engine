import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class LineHistoryTracker:
    def __init__(self, db_path="data/picks.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pick_id INTEGER,
                game_key TEXT,
                sport TEXT,
                book TEXT,
                line_type TEXT,
                line_value REAL,
                timestamp TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS closing_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pick_id INTEGER,
                game_key TEXT,
                book TEXT,
                closing_spread REAL,
                closing_ml REAL,
                closing_total REAL,
                closing_ts TEXT
            )
        """)

        for col in ['opening_line', 'closing_line', 'line_movement', 'won']:
            try:
                cursor.execute(f"ALTER TABLE picks ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass

        conn.commit()
        conn.close()

    def record_closing_line(self, pick_id, game_key, book, spread, ml, total):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO closing_lines (pick_id, game_key, book, closing_spread, closing_ml, closing_total, closing_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pick_id, game_key, book, spread, ml, total, datetime.now().isoformat()))

        cursor.execute("""
            UPDATE picks 
            SET closing_line = ?,
                line_movement = CASE 
                    WHEN pick_value IS NOT NULL THEN ? - pick_value 
                    ELSE NULL 
                END
            WHERE id = ?
        """, (spread, spread, pick_id))

        conn.commit()
        conn.close()

    def get_line_movement(self, pick_id, line_type="spread"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM line_history 
            WHERE pick_id = ? AND line_type = ?
            ORDER BY timestamp ASC
        """, (pick_id, line_type))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"has_history": False, "message": "No history found"}

        columns = ['id', 'pick_id', 'game_key', 'sport', 'book', 'line_type', 'line_value', 'timestamp']
        history = [dict(zip(columns, row)) for row in rows]

        first = history[0]
        last = history[-1]

        return {
            "has_history": True,
            "first_line": first['line_value'],
            "first_time": first['timestamp'],
            "last_line": last['line_value'],
            "last_time": last['timestamp'],
            "movement": round(last['line_value'] - first['line_value'], 2),
            "total_records": len(history)
        }
