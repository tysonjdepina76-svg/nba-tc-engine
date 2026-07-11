#!/usr/bin/env python3
"""Quick health check for TC pipeline — 2026-07-11."""
import csv, json, requests
from collections import Counter
from pathlib import Path

LOG = Path("/home/workspace/Daily_Log")
TODAY = "2026-07-11"

print("=" * 50)
print(f"HEALTH CHECK — {TODAY}")
print("=" * 50)

# Dashboard
try:
    r = requests.get("http://localhost:8510", timeout=3)
    print(f"✅ Dashboard: {r.status_code}")
except Exception as e:
    print(f"❌ Dashboard: {e}")

# Graded picks
gcsv = LOG / TODAY / "graded_picks.csv"
if gcsv.exists():
    with open(gcsv) as f:
        rows = list(csv.DictReader(f))
    print(f"✅ Graded picks: {len(rows)} total")
    res = Counter(r["result"] for r in rows)
    league = Counter()
    for r in rows:
        if r["result"] in ("H", "M"):
            league[(r["league"], r["result"])] += 1
    for lg in set(r["league"] for r in rows):
        h = league.get((lg, "H"), 0)
        m = league.get((lg, "M"), 0)
        if h + m > 0:
            print(f"   {lg}: {h}H / {m}M = {h/(h+m)*100:.1f}%")
else:
    print(f"❌ No graded_picks.csv for {TODAY}")

# Boxscores
bs = list((LOG / "mlb_boxscores").glob(f"*20260711*"))
print(f"✅ MLB boxscores today: {len(bs)}")

print("=" * 50)
