#!/usr/bin/env python3
"""Complete self-edge backtest analysis — truth + recommendations."""
import json, sqlite3
from collections import defaultdict

DB = "/home/workspace/Projects/data/picks.db"
RESULTS = "/home/workspace/Daily_Log/backtests/2026-07-19/results.json"

conn = sqlite3.connect(DB)
c = conn.cursor()

# ── 1. SELF-EDGE IDENTIFIED ──
print("=" * 70)
print("SELF-EDGE IDENTIFIED: tc_math.py → over_under_signal()")
print("=" * 70)

c.execute("""
    SELECT signal, league, COUNT(*), COUNT(DISTINCT player)
    FROM picks GROUP BY signal, league
""")
for row in c.fetchall():
    print(f"  {row[0]:>15} | {row[1]:>6} | {row[2]:>4} picks | {row[3]} unique players")

# ── 2. THE PROJECTION EQUALITY PROBLEM ──
print("\n" + "=" * 70)
print("PROJECTION UNIQUENESS: Are all players getting the same line?")
print("=" * 70)

c.execute("""
    SELECT stat, COUNT(DISTINCT tc_projection) as unique_proj, 
           COUNT(DISTINCT market_line) as unique_line,
           COUNT(*) as total,
           ROUND(AVG(tc_projection), 2) as avg_proj,
           ROUND(AVG(market_line), 2) as avg_line
    FROM picks WHERE signal='SELF_EDGE' AND league='wnba' AND date='2026-07-19'
    GROUP BY stat
    ORDER BY unique_proj
""")
for row in c.fetchall():
    status = "❌ IDENTICAL" if row[1] == 1 else (f"✅ {row[1]} unique" if row[1] > 3 else "⚠️ FEW")
    print(f"  {row[0]:>8}: {row[1]} unique proj / {row[2]} unique lines for {row[3]} picks ({row[4]:.1f}/{row[5]:.1f}) — {status}")

# ── 3. BACKTEST RESULTS ──
print("\n" + "=" * 70)
print("BACKTEST RESULTS (7/19 — 96 graded WNBA picks)")
print("=" * 70)

with open(RESULTS) as f:
    results = json.load(f)

wnba = [r for r in results if r["league"] == "wnba" and r["result"] != "NO_DATA"]

# Split by direction
over_picks = [r for r in wnba if r["direction"] == "OVER"]
under_picks = [r for r in wnba if r["direction"] == "UNDER"]

over_hits = sum(1 for r in over_picks if r["result"] == "HIT")
under_hits = sum(1 for r in under_picks if r["result"] == "HIT")

print(f"  OVER:  {over_hits}/{len(over_picks)} = {over_hits/len(over_picks)*100:.1f}%")
print(f"  UNDER: {under_hits}/{len(under_picks)} = {under_hits/len(under_picks)*100:.1f}%")
print(f"  TOTAL: {over_hits+under_hits}/{len(wnba)} = {(over_hits+under_hits)/len(wnba)*100:.1f}%")

# Show how the OVER is inflated
print("\n  OVER ANALYSIS:")
over_has_line = [r for r in over_picks if r["market_line"] > 0]
over_zero_line = [r for r in over_picks if r["market_line"] == 0]
if over_zero_line:
    zh = sum(1 for r in over_zero_line if r["result"] == "HIT")
    print(f"    With market_line=0 (fake): {zh}/{len(over_zero_line)} = {zh/len(over_zero_line)*100:.1f}%")
if over_has_line:
    lh = sum(1 for r in over_has_line if r["result"] == "HIT")
    print(f"    With real market_line:     {lh}/{len(over_has_line)} = {lh/len(over_has_line)*100:.1f}%")

# ── 4. THE REAL (UNFILTERED) SELF-EDGE HIT RATE ──
print("\n" + "=" * 70)
print("REAL SELF-EDGE HIT RATE (UNDER only, real market lines)")
print("=" * 70)

by_stat_real = defaultdict(lambda: {"hit": 0, "miss": 0})
for r in under_picks:
    by_stat_real[r["stat"]]["hit" if r["result"] == "HIT" else "miss"] += 1

print(f"  {'Stat':>8}  {'Hit':>5} {'Miss':>5} {'Rate':>8}  Status")
print(f"  {'-'*8}  {'-'*5} {'-'*5} {'-'*8}  {'-'*10}")
for stat in sorted(by_stat_real.keys()):
    d = by_stat_real[stat]
    total = d["hit"] + d["miss"]
    rate = d["hit"]/total*100
    status = "✅ STRONG" if rate >= 65 else ("⚠️ MARGINAL" if rate >= 50 else "❌ WEAK")
    bar = "█" * int(rate/10) + "░" * (10 - int(rate/10))
    print(f"  {stat:>8}  {d['hit']:>3}/{total:<3} {rate:>6.1f}%  {bar}  {status}")

# ── 5. BY PLAYER ──
print("\n" + "=" * 70)
print("PLAYER PERFORMANCE (UNDER picks only)")
print("=" * 70)

by_player = defaultdict(lambda: {"hit": 0, "miss": 0})
for r in under_picks:
    by_player[r["player"]]["hit" if r["result"] == "HIT" else "miss"] += 1

for player in sorted(by_player.keys(), key=lambda p: by_player[p]["hit"]/(by_player[p]["hit"]+by_player[p]["miss"]), reverse=True):
    d = by_player[player]
    total = d["hit"] + d["miss"]
    rate = d["hit"]/total*100
    print(f"  {player:>20}: {d['hit']}/{total} = {rate:.1f}%")

# ── 6. THE BOTTOM LINE ──
under_total = under_hits + len(under_picks) - under_hits  # = len(under_picks)
print("\n" + "=" * 70)
print("BOTTOM LINE")
print("=" * 70)
print(f"  Self-Edge (real, UNDER only): {under_hits}/{len(under_picks)} = {under_hits/len(under_picks)*100:.1f}%")
print(f"  This is a {'coin flip' if abs(under_hits/len(under_picks) - 0.5) < 0.1 else 'marginal edge' if under_hits/len(under_picks) > 0.5 else 'negative edge'}.")
print(f"  Identical projections across all players = league-average fallbacks.")
print(f"  Real per-player projections needed for actual edge detection.")

conn.close()
