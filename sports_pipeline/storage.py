#!/usr/bin/env python3
"""
SQLite storage - persists pipeline runs for historical analysis.
"""
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any

from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_games INTEGER,
            total_props INTEGER,
            mlb_games INTEGER,
            wnba_games INTEGER,
            runtime_seconds REAL,
            raw_data TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS player_prop_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            player TEXT,
            team TEXT,
            stat TEXT,
            line REAL,
            projection REAL,
            edge REAL,
            league TEXT,
            matchup TEXT,
            confidence INTEGER,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs (id)
        )
    """)
    conn.commit()
    conn.close()

def append_historical_record(pipeline_result: Dict[str, Any]) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    summary = pipeline_result.get("summary", {})
    c.execute("""
        INSERT INTO pipeline_runs (
            timestamp, total_games, total_props, mlb_games, wnba_games,
            runtime_seconds, raw_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        pipeline_result.get("timestamp"),
        summary.get("total_games", 0),
        summary.get("total_props", 0),
        summary.get("mlb_games", 0),
        summary.get("wnba_games", 0),
        pipeline_result.get("runtime_seconds", 0),
        json.dumps(pipeline_result)
    ))
    run_id = c.lastrowid
    for prop in pipeline_result.get("player_props", []):
        c.execute("""
            INSERT INTO player_prop_history (
                run_id, player, team, stat, line, projection, edge, league, matchup, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            prop.get("player"),
            prop.get("team"),
            prop.get("stat"),
            prop.get("line"),
            prop.get("projection"),
            prop.get("edge"),
            prop.get("league"),
            prop.get("matchup"),
            prop.get("confidence", 70)
        ))
    conn.commit()
    conn.close()
    return run_id
