#!/usr/bin/env python3
import sqlite3, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.game_id_resolver import resolve_game_id

DB = Path(__file__).parent.parent / "data" / "picks.db"

def backfill():
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    cur.execute("SELECT rowid, league, date, matchup, team, game_id FROM picks WHERE game_id IS NULL")
    rows = cur.fetchall()
    print(f"Found {len(rows)} picks with NULL game_id")
    resolved = 0
    failed = 0
    for row in rows:
        rid = row[0]
        league = (row[1] or '').lower()
        date = row[2]
        matchup = row[3] or ''
        parts = re.split(r'\s+[@_]+at[_]+\s+|\s+@\s+|\s+_at_\s+', matchup.strip())
        if len(parts) < 2:
            failed += 1
            continue
        away, home = parts[0].strip(), parts[1].strip()
        gid = resolve_game_id(league, date, home, away)
        if not gid:
            gid = resolve_game_id(league, date, away, home)
        if gid:
            cur.execute("UPDATE picks SET game_id = ? WHERE rowid = ?", (gid, rid))
            resolved += 1
        else:
            failed += 1
    conn.commit()
    conn.close()
    print(f"Resolved: {resolved}, Still NULL: {failed}")
backfill()
