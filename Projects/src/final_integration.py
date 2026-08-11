#!/usr/bin/env python3
"""
final_integration.py — Definitive TC system integration.
Wires all components: grading, regrade, combo stats, DB sync.
Run: python3 src/final_integration.py --date 2026-08-10 --force
"""

import argparse
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'picks.db')

def add_combo_stats(boxscore):
    """Add PA, PR, PRA to each player's stats."""
    for player, stats in boxscore.items():
        pts = stats.get('PTS', 0) or 0
        reb = stats.get('REB', 0) or 0
        ast = stats.get('AST', 0) or 0
        stats['PA'] = pts + ast
        stats['PR'] = pts + reb
        stats['PRA'] = pts + reb + ast
    return boxscore

def regrade_all(date_str, force=False):
    from src.regrade_all_outstanding import regrade_mlb
    regrade_mlb(date_str)
    
    try:
        from src.regrade_all_outstanding import regrade_wnba
        regrade_wnba(date_str, fallback=False, force=force)
    except Exception as e:
        print(f"WNBA regrade skipped: {e}")

def show_summary(date_str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT league, COUNT(*) as picks, SUM(hit) as hits,
               ROUND(AVG(hit)*100, 1) as hit_pct
        FROM picks WHERE date=? AND hit IS NOT NULL
        GROUP BY league
    """, (date_str,))
    
    total_picks = 0
    total_hits = 0
    print(f"\n{'='*60}")
    print(f"TC SYSTEM INTEGRATION — {date_str}")
    print(f"{'='*60}")
    for row in cur.fetchall():
        league = row['league']
        picks = row['picks']
        hits = row['hits'] or 0
        pct = row['hit_pct']
        print(f"  {league:6s}: {hits}/{picks} = {pct}%")
        total_picks += picks
        total_hits += hits
    
    if total_picks:
        combined = round(total_hits / total_picks * 100, 1)
        print(f"  {'COMBINED':6s}: {total_hits}/{total_picks} = {combined}%")
        print(f"\n  Target: 55.0% | Actual: {combined}% | {'ABOVE' if combined >= 55.0 else 'BELOW'} TARGET")
    
    print(f"{'='*60}")
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TC Final Integration')
    parser.add_argument('--date', required=True, help='Date to grade/regrade (YYYY-MM-DD)')
    parser.add_argument('--force', action='store_true', help='Force regrade even if already graded')
    args = parser.parse_args()
    
    regrade_all(args.date, force=args.force)
    show_summary(args.date)
