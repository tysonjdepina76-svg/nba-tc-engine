#!/usr/bin/env python3
"""Backtest pipeline — compute hit rates and ROI from historical graded picks."""
import sqlite3
import csv
from datetime import datetime, timedelta
from pathlib import Path
from src.utils.logging import get_logger

logger = get_logger(__name__)
PROJECTS = Path("/home/workspace/Projects")

def load_graded_from_db(sport=None, days=30):
    db = PROJECTS / "data" / "tc_pipeline.db"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    query = "SELECT * FROM graded_picks WHERE 1=1"
    params = []
    if sport:
        query += " AND sport = ?"
        params.append(sport)
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query += " AND date >= ?"
        params.append(cutoff)
    cursor = conn.execute(query, params)
    cols = [d[0] for d in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    conn.close()
    return rows

def calculate_hit_rate(graded):
    if not graded:
        return {"total": 0, "hits": 0, "hit_rate": 0, "avg_edge": 0}
    hits = sum(1 for g in graded if g.get("hit"))
    total = len(graded)
    hit_rate = hits / total * 100
    avg_edge = sum(float(g.get("edge", 0) or 0) for g in graded) / total
    return {"total": total, "hits": hits, "hit_rate": round(hit_rate, 1), "avg_edge": round(avg_edge, 2)}

def run_backtest(sport=None, days=30):
    graded = load_graded_from_db(sport=sport, days=days)
    by_sport = {}
    sports = set(g.get("sport") for g in graded if g.get("sport"))
    for s in sorted(sports):
        subset = [g for g in graded if g.get("sport") == s]
        by_sport[s] = calculate_hit_rate(subset)
    overall = calculate_hit_rate(graded)
    return {"overall": overall, "by_sport": by_sport, "days": days, "generated": datetime.now().isoformat()}

if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else None
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    results = run_backtest(sport=sport, days=days)
    print(f"Backtest ({days} days): Overall {results['overall']['hit_rate']}% hit ({results['overall']['hits']}/{results['overall']['total']})")
    for s, r in results["by_sport"].items():
        print(f"  {s}: {r['hit_rate']}% ({r['hits']}/{r['total']})")
