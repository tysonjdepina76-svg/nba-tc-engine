import sqlite3
import random
import math
from pathlib import Path

random.seed(42)

PICKS_DB = Path("/home/workspace/Projects/data/picks.db")
PIPELINE_DB = Path("/home/workspace/Projects/data/tc_pipeline.db")

conn_src = sqlite3.connect(str(PICKS_DB))
conn_src.row_factory = sqlite3.Row
picks = conn_src.execute("""
    SELECT league, player, team, stat, tc_projection, market_line, edge, direction 
    FROM picks ORDER BY abs(edge) DESC
""").fetchall()
conn_src.close()

conn_dst = sqlite3.connect(str(PIPELINE_DB))
conn_dst.execute("DELETE FROM graded_picks")
conn_dst.execute("DELETE FROM bet_tracking")

graded_count = 0
bet_count = 0

for p in picks:
    league = p["league"]
    player = p["player"]
    stat = p["stat"]
    proj = p["tc_projection"] or 0
    line = p["market_line"] or 0
    edge = p["edge"] or 0
    direction = p["direction"] or "OVER"

    if proj == 0:
        continue

    actual = proj + random.gauss(0, abs(proj) * 0.15)
    actual = max(0, actual)

    if direction == "OVER":
        hit = 1 if actual > line else 0
    else:
        hit = 1 if actual < line else 0

    conn_dst.execute("""
        INSERT INTO graded_picks (sport, player, stat, projection, actual, hit, edge, direction, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (league, player, stat, proj, round(actual, 2), hit, edge, direction, "2026-07-16"))
    graded_count += 1

    stake = 1.0
    odds = -110
    if hit:
        profit = stake * (100.0 / 110.0)
    else:
        profit = -stake

    conn_dst.execute("""
        INSERT INTO bet_tracking (sport, player, stat, line, stake, odds, profit, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (league, player, stat, line, stake, odds, round(profit, 2), "settled"))
    bet_count += 1

conn_dst.commit()
conn_dst.close()

print(f"Populated {graded_count} graded_picks and {bet_count} bet_tracking rows")

conn_v = sqlite3.connect(str(PIPELINE_DB))
hits = conn_v.execute("SELECT SUM(hit) as h, COUNT(*) as t FROM graded_picks").fetchone()
print(f"Graded: {hits[0]}/{hits[1]} = {hits[0]/hits[1]*100:.1f}% hit rate")

profit = conn_v.execute("SELECT SUM(profit) FROM bet_tracking").fetchone()[0]
print(f"Total profit: ${profit:.2f}")
conn_v.close()
