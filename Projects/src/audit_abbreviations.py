#!/usr/bin/env python3
"""
audit_abbreviations.py - Audits team/player name consistency across all sources.
Saves report to logs/abbreviation_audit.txt.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from src.name_resolver import resolve_team

DB_PATH = Path("data/picks.db")
REPORT_PATH = Path("logs/abbreviation_audit.txt")
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

def audit_teams():
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("SELECT DISTINCT league, team FROM picks WHERE team IS NOT NULL AND team != ''", conn)
    conn.close()
    issues = []
    for _, row in df.iterrows():
        try:
            resolved = resolve_team(row['team'], row['league'])
        except:
            resolved = row['team']
        if resolved != row['team']:
            issues.append(f"Team '{row['team']}' in {row['league']} resolves to '{resolved}'")
    return issues

def main():
    issues = audit_teams()
    with open(REPORT_PATH, 'w') as f:
        f.write("Abbreviation Audit Report\n")
        f.write("=" * 40 + "\n")
        if issues:
            for issue in issues:
                f.write(issue + "\n")
        else:
            f.write("All team abbreviations are consistent.\n")
    print(f"Report saved to {REPORT_PATH}")

if __name__ == "__main__":
    main()
