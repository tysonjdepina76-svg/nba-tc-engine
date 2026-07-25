import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

class CacheManager:
    def __init__(self, db_path="data/picks.db"):
        self.db_path = db_path
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._init_cache_tables()

    def _init_cache_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_metadata (
                cache_key TEXT PRIMARY KEY,
                data_type TEXT,
                timestamp TEXT,
                ttl_seconds INTEGER,
                expires_at TEXT,
                size_bytes INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_key TEXT,
                sport TEXT,
                book TEXT,
                line_type TEXT,
                line_value REAL,
                direction TEXT,
                movement REAL,
                timestamp TEXT,
                is_sharp BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT,
                snapshot_time TEXT,
                sport TEXT,
                game_key TEXT,
                book TEXT,
                line_type TEXT,
                line_value REAL,
                player_name TEXT,
                market TEXT
            )
        """)

        conn.commit()
        conn.close()

    def get(self, cache_key: str) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT expires_at FROM cache_metadata 
            WHERE cache_key = ? AND expires_at > datetime('now')
        """, (cache_key,))

        row = cursor.fetchone()
        conn.close()

        if row:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
        return None

    def set(self, cache_key: str, data: Dict, ttl_seconds: int = 3600):
        data_json = json.dumps(data)
        expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO cache_metadata 
            (cache_key, data_type, timestamp, ttl_seconds, expires_at, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cache_key, "unknown", datetime.now().isoformat(),
              ttl_seconds, expires_at, len(data_json)))

        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            f.write(data_json)

        conn.commit()
        conn.close()

    def clear_expired(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cache_metadata WHERE expires_at < datetime('now')")
        cursor.execute("SELECT cache_key FROM cache_metadata")
        active_keys = {row[0] for row in cursor.fetchall()}

        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.stem not in active_keys:
                cache_file.unlink()

        conn.commit()
        conn.close()

    def record_line_movement(self, game_key: str, sport: str, book: str,
                            line_type: str, line_value: float,
                            previous_value: float = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        direction = "NEUTRAL"
        movement = 0

        if previous_value is not None:
            movement = round(line_value - previous_value, 2)
            if movement > 0:
                direction = "UP"
            elif movement < 0:
                direction = "DOWN"

        cursor.execute("""
            INSERT INTO line_movements 
            (game_key, sport, book, line_type, line_value, direction, movement, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_key, sport, book, line_type, line_value, direction, movement,
              datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def take_snapshot(self, sport: str, game_key: str, book: str,
                      line_type: str, line_value: float, player_name: str = None,
                      market: str = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO daily_snapshots 
            (snapshot_date, snapshot_time, sport, game_key, book, line_type, line_value, player_name, market)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat(),
              sport, game_key, book, line_type, line_value, player_name, market))

        conn.commit()
        conn.close()
