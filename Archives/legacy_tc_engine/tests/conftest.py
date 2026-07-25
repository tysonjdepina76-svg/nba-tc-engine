"""Test Configuration — shared fixtures for all TC engine tests."""
import pytest
import sqlite3
import tempfile
from pathlib import Path


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            player TEXT,
            team TEXT,
            league TEXT,
            stat TEXT,
            tc_projection REAL,
            market_line REAL,
            edge REAL,
            direction TEXT,
            reason TEXT,
            matchup TEXT,
            signal TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS graded_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sport TEXT,
            player TEXT,
            stat TEXT,
            projection REAL,
            actual REAL,
            hit INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bet_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sport TEXT,
            player TEXT,
            stat TEXT,
            status TEXT,
            profit REAL
        )
    """)
    conn.commit()
    conn.close()
    yield path
    import os
    os.unlink(path)


@pytest.fixture
def sample_picks():
    return [
        {"name": "Shohei Ohtani", "team": "LAD", "sport": "mlb", "stat": "HR",
         "matchup": "LAD@SF", "projection": 1.5, "line": 0.8, "edge": 0.7,
         "direction": "OVER", "reason": "Elite power hitter vs favorable matchup"},
        {"name": "A'ja Wilson", "team": "LV", "sport": "wnba", "stat": "PTS",
         "matchup": "LV@NY", "projection": 22.5, "line": 20.0, "edge": 2.5,
         "direction": "OVER", "reason": "Dominant post scorer"},
        {"name": "Spencer Strider", "team": "ATL", "sport": "mlb", "stat": "K",
         "matchup": "ATL@NYM", "projection": 6.2, "line": 8.0, "edge": -1.8,
         "direction": "UNDER", "reason": "Facing disciplined lineup"},
    ]


@pytest.fixture
def sample_projections(tmp_path):
    data = {
        "players": [
            {
                "player": "Test Player",
                "team": "TST",
                "projections": {
                    "PTS": {"tc_projection": 18.5, "market_line": 16.0, "edge": 2.5, "direction": "OVER"},
                    "REB": {"tc_projection": 7.2, "market_line": 8.0, "edge": -0.8, "direction": "UNDER"},
                },
            },
        ],
    }
    import json
    proj_file = tmp_path / "proj_WNBA_TEST.json"
    proj_file.write_text(json.dumps(data))
    return proj_file
