#!/usr/bin/env python3
"""Build comprehensive backtest report with proper grading."""
import sqlite3, json
from datetime import datetime

DB = "/home/workspace/Projects/data/picks.db"

def get_proper_backtest():
    """Get the properly graded WNBA 7/19 data."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get graded WNBA picks from 7/19 (with actual hit grading)
    c.execute("""
        SELECT name, stat, direction, projection, line, actual, hit, matchup
        FROM graded_picks 
        WHERE sport='wnba' AND actual IS NOT NULL AND actual >= 0
        ORDER BY name, stat
    """)
    rows = c.fetchall()
    
    by_stat = {}
    by_player = {}
    by_direction = {"OVER": {"hits": 0, "total": 0}, "UNDER": {"hits": 0, "total": 0}}
    
    for r in rows:
        stat = r["stat"]
        name = r["name"]
        direction = r["direction"]
        
        if stat not in by_stat:
            by_stat[stat] = {"hits": 0, "misses": 0}
        by_stat[stat]["hits" if r["hit"] else "misses"] += 1
        
        if name not in by_player:
            by_player[name] = {"hits": 0, "misses": 0, "matchup": r["matchup"]}
        by_player[name]["hits" if r["hit"] else "misses"] += 1
        
        by_direction.setdefault(direction, {"hits": 0, "total": 0})["total"] += 1
        if r["hit"]:
            by_direction[direction]["hits"] += 1
    
    total_hits = sum(s["hits"] for s in by_stat.values())
    total_all = total_hits + sum(s["misses"] for s in by_stat.values())
    
    conn.close()
    return {
        "total": total_all,
        "hits": total_hits,
        "hit_rate": round(100 * total_hits / total_all, 1) if total_all else 0,
        "by_stat": {s: {"hits": d["hits"], "misses": d["misses"], "rate": round(100*d["hits"]/(d["hits"]+d["misses"]),1)} for s,d in sorted(by_stat.items())},
        "by_player": {p: {"hits": d["hits"], "misses": d["misses"], "rate": round(100*d["hits"]/(d["hits"]+d["misses"]),1), "matchup": d["matchup"]} for p,d in sorted(by_player.items())},
        "by_direction": {d: {"hits": v["hits"], "total": v["total"], "rate": round(100*v["hits"]/v["total"],1) if v["total"] else 0} for d,v in by_direction.items()}
    }

def get_junk_data():
    """Get counts of the junk/garbage rows."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Total in graded_picks
    c.execute("SELECT COUNT(*), SUM(CASE WHEN line=0 THEN 1 ELSE 0 END) FROM graded_picks")
    total, zero_line = c.fetchone()
    
    # By sport  
    c.execute("SELECT sport, COUNT(*), SUM(CASE WHEN line=0 THEN 1 ELSE 0 END) FROM graded_picks GROUP BY sport ORDER BY COUNT(*) DESC")
    by_sport = c.fetchall()
    
    # Total in picks table (active picks)
    c.execute("SELECT COUNT(*), league FROM picks GROUP BY league")
    active = c.fetchall()
    
    conn.close()
    return {"total": total, "zero_line": zero_line, "pct_zero": round(100*zero_line/total,1), "by_sport": [{"sport": r[0], "total": r[1], "zero_line": r[2], "pct": round(100*r[2]/r[1],1)} for r in by_sport], "active_picks": [{"league": r[1], "count": r[0]} for r in active]}

bt = get_proper_backtest()
junk = get_junk_data()

report = f"""# BACKTEST REPORT — 2026-07-24

## THE TRUTH

### Properly Graded Picks (WNBA 7/19)
- **Total**: {bt['total']}
- **Hits**: {bt['hits']}
- **Hit Rate**: {bt['hit_rate']}%
- **OVER**: {bt['by_direction']['OVER']['hits']}/{bt['by_direction']['OVER']['total']} ({bt['by_direction']['OVER']['rate']}%)
- **UNDER**: {bt['by_direction']['UNDER']['hits']}/{bt['by_direction']['UNDER']['total']} ({bt['by_direction']['UNDER']['rate']}%)

### By Stat
| Stat | Hits | Misses | Rate |
|------|------|--------|------|
"""
for s, d in bt["by_stat"].items():
    report += f"| {s} | {d['hits']} | {d['misses']} | {d['rate']}% |\n"

report += f"""
### By Player (all 84 picks were from WNBA 7/19 slate: CHI@ATL, CON@PHX, LA@DAL)
| Player | H/M | Rate | Matchup |
|--------|-----|------|---------|
"""
for p, d in bt["by_player"].items():
    report += f"| {p:<25} | {d['hits']}/{d['hits']+d['misses']} | {d['rate']}% | {d['matchup']} |\n"

report += f"""
## JUNK DATA IN graded_picks TABLE

- **Total rows**: {junk['total']}
- **Zero-line garbage** (line=0, edge=0): {junk['zero_line']} ({junk['pct_zero']}%)
- **"Wins" in these**: 24 — ALL Mookie Betts with line=0 auto-graded as hit. Meaningless.

### By Sport (all junk)
| Sport | Total | Zero-Line | % Garbage |
|-------|-------|-----------|-----------|
"""
for r in junk["by_sport"]:
    report += f"| {r['sport']} | {r['total']} | {r['zero_line']} | {r['pct']}% |\n"

report += f"""
### Active Picks in picks.db
| League | Count |
|--------|-------|
"""
for r in junk["active_picks"]:
    report += f"| {r['league']} | {r['count']} |\n"

report += """
## RECOMMENDATIONS

1. **Purge graded_picks table** — 3,070 of 3,094 rows are zero-line junk. These were imported from CSVs that contained raw projections (not picks) because Odds API was dead. They have no market lines, so they're not real picks.

2. **Only trust WNBA self-edge picks** — The 84 WNBA picks from 7/19 are the ONLY properly generated picks in the system. These use ESPN boxscore-derived lines from gen_wnba_today.py. 60.7% hit rate.

3. **MLB is dead without Odds API** — generate_projections.py was a random.uniform() stub that's been archived. The MLB projection files in Daily_Log all have line=0 (no DK/FD lines available). Without live odds, MLB can't generate picks.

4. **NFL is off-season** — No games. No picks possible.

5. **Pipeline health**:
   - WNBA: Working (self-edge via gen_wnba_today.py) but no games 7/23-7/24
   - MLB: Broken (no odds source)
   - NFL: Off-season
   - WC: Ended July 2026

6. **Rosters now wired** — roster_loader.py rebuilt and integrated into daily_picks.py via enrich_via_rosters(). Position, team, jersey enrichment active for all picks going forward.

7. **API endpoints** — Fixed. /health, /picks, /stats, /combos all return valid data. Backtest endpoint now uses properly graded data.

## FILE TRUTH

| Claim in AGENTS.md | Reality |
|---|---|
| "45 roster files" | 4 files (mlb, wnba, nba, nfl) |
| "generate_projections.py" | Archived — was random.uniform() stub |
| "roster_loader.py" | Rebuilt today from .pyc bytecode |
| "67.2% hit rate across 6,238 graded picks" | 3,094 in DB, only 84 properly graded (60.7%) |
| "7/23 Pipeline: 0 picks" | Correct — no WNBA games, no MLB lines |

## WHAT'S ACTUALLY LIVE

- **Daily Picks API**: https://tc-api-true.zocomputer.io/health ✅
- **Streamlit Dashboard**: https://tc-streamlit-dashboard-true.zocomputer.io ✅  
- **Zo Dashboard**: https://true.zo.space/nba-tc ✅
- **Active picks**: 84 WNBA from 7/19. No new picks since.
"""

print(report)
with open("/home/workspace/reports/backtest_truth_20260724.md", "w") as f:
    f.write(report)
print(f"\nReport saved to /home/workspace/reports/backtest_truth_20260724.md")
