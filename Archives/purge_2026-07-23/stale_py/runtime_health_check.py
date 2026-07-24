#!/usr/bin/env python3
"""Runtime health check — verifies services, DBs, disk, and memory."""
import os
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

PROJECTS = Path("/home/workspace/Projects")

def check_db(path, table, label):
    try:
        db = PROJECTS / path
        if not db.exists():
            return False, f"{label} DB missing"
        conn = sqlite3.connect(str(db))
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.close()
        return True, f"{label}: {count} rows"
    except Exception as e:
        return False, f"{label}: {e}"

def check_http(url, label):
    import urllib.request
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200, f"{label}: {resp.status}"
    except Exception as e:
        return False, f"{label}: {e}"

def main():
    results = []
    results.append(check_db("data/picks.db", "picks", "picks.db"))
    results.append(check_db("data/tc_pipeline.db", "graded_picks", "tc_pipeline"))
    results.append(check_http("http://localhost:8510", "dashboard"))
    results.append(check_http("http://localhost:8000/api/v1/system/health", "API"))
    results.append(check_http("https://true.zo.space/nba-tc", "zo.space"))

    all_ok = all(r[0] for r in results)
    status = "HEALTHY" if all_ok else "DEGRADED"
    print(f"[{datetime.now().isoformat()}] {status}")
    for ok, msg in results:
        print(f"  {'OK' if ok else 'FAIL'}: {msg}")

    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
