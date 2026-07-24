import sys, os
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPT_DIR)

import json, csv
from datetime import datetime
from typing import Dict, List, Any, Optional

ET_TZ = __import__("zoneinfo").ZoneInfo("America/New_York")


def api_picks_top(sport_filter: Optional[str] = None) -> List[Dict]:
    picks_db = os.path.join(SCRIPT_DIR, "data", "picks.db")
    if not os.path.exists(picks_db):
        return _fallback_from_csv()
    import sqlite3
    conn = sqlite3.connect(picks_db)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='picks'")
        if not cursor.fetchone():
            conn.close()
            return _fallback_from_csv()
        if sport_filter:
            cursor.execute("""
                SELECT player, team, sport AS sport_ref, stat, projection, line, edge, reason, direction, matchup, period, signal
                FROM picks WHERE signal != 'PROJECTION ONLY' OR signal IS NULL
                AND league = ? ORDER BY ABS(edge) DESC LIMIT 50
            """, (sport_filter,))
        else:
            cursor.execute("""
                SELECT player, team, sport AS sport_ref, stat, projection, line, edge, reason, direction, matchup, period, signal
                FROM picks WHERE signal != 'PROJECTION ONLY' OR signal IS NULL
                ORDER BY ABS(edge) DESC LIMIT 50
            """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        if rows:
            for r in rows:
                if "sport_ref" in r and "sport" not in r:
                    r["sport"] = r.pop("sport_ref")
            return rows
    except Exception as e:
        conn.close()
        print(f"DB picks query failed: {e}")
    return _fallback_from_csv()


def _fallback_from_csv() -> List[Dict]:
    today = datetime.now(ET_TZ).date().isoformat()
    csv_path = os.path.join("/home/workspace/Daily_Log", today, "picks.csv")
    if os.path.exists(csv_path):
        with open(csv_path, "r") as f:
            rows = list(csv.DictReader(f))
        results = []
        for r in rows[:50]:
            results.append({
                "player": r.get("player", ""),
                "team": r.get("team", ""),
                "sport": r.get("league", ""),
                "stat": r.get("stat", ""),
                "projection": float(r.get("tc_projection", 0)),
                "line": float(r.get("market_line", 0)),
                "edge": float(r.get("edge", 0)),
                "reason": r.get("why", ""),
                "direction": r.get("direction", ""),
                "matchup": r.get("matchup", ""),
                "signal": r.get("signal", ""),
            })
        return results
    return []
