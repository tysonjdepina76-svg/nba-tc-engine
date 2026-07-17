#!/usr/bin/env python3
"""Grade picks against final box scores."""
import json
import sqlite3
import csv
from datetime import datetime
from pathlib import Path
from src.utils.logging import get_logger

logger = get_logger(__name__)
PROJECTS = Path("/home/workspace/Projects")

def load_picks_for_date(date_str: str):
    csv_path = Path(f"/home/workspace/Daily_Log/{date_str}/picks.csv")
    if not csv_path.exists():
        return []
    picks = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            picks.append(row)
    return picks

def grade_picks(picks, boxscore_data=None):
    graded = []
    for p in picks:
        player = p.get("player", "")
        stat = p.get("stat", "pts")
        projection = float(p.get("tc_projection", p.get("projection", 0)) or 0)
        direction = p.get("direction", "OVER")
        actual = 0
        if boxscore_data and player in boxscore_data:
            actual = boxscore_data[player].get(stat, 0)
        hit = (actual > projection) if direction == "OVER" else (actual < projection)
        graded.append({**p, "actual": actual, "hit": hit, "graded_at": datetime.now().isoformat()})
    return graded

def save_graded(date_str, graded):
    db = PROJECTS / "data" / "tc_pipeline.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""CREATE TABLE IF NOT EXISTS graded_picks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player TEXT, stat TEXT, sport TEXT, projection REAL, actual REAL,
        direction TEXT, hit INTEGER, edge REAL, date TEXT, graded_at TEXT
    )""")
    for g in graded:
        conn.execute("""INSERT OR IGNORE INTO graded_picks
            (player, stat, sport, projection, actual, direction, hit, edge, date, graded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (g.get("player"), g.get("stat"), g.get("sport"),
             float(g.get("tc_projection", 0) or 0), float(g.get("actual", 0) or 0),
             g.get("direction"), int(g.get("hit", False)),
             float(g.get("edge", 0) or 0), g.get("date"), g.get("graded_at")))
    conn.commit()
    conn.close()
    logger.info(f"Graded {len(graded)} picks for {date_str}")
    return len(graded)

def main(date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    picks = load_picks_for_date(date_str)
    if not picks:
        print("No picks to grade")
        return
    graded = grade_picks(picks)
    count = save_graded(date_str, graded)
    hits = sum(1 for g in graded if g.get("hit"))
    hit_rate = hits / len(graded) * 100 if graded else 0
    print(f"Graded {count} picks — {hits}/{len(graded)} ({hit_rate:.1f}%)")

if __name__ == "__main__":
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(date_arg)
