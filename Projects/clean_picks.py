#!/usr/bin/env python3
"""Deduplicate picks.db — keep best matchup per player+stat, drop garbage."""
import sqlite3

DB = "/home/workspace/Projects/data/picks.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT id, date, league, player, stat, matchup, edge FROM picks ORDER BY date, league, player, stat")
rows = c.fetchall()
print(f"Total rows: {len(rows)}")

# Group by (date, league, player, stat)
groups = {}
for r in rows:
    key = (r["date"], r["league"], r["player"], r["stat"])
    if key not in groups:
        groups[key] = []
    groups[key].append(r)

to_delete = []
to_keep = []
bad_matchups = {"merged", "???", "", None}

for key, group in groups.items():
    if len(group) == 1:
        to_keep.append(group[0]["id"])
        continue

    good = [r for r in group if r["matchup"] and r["matchup"].strip() not in bad_matchups]
    bad = [r for r in group if not r["matchup"] or r["matchup"].strip() in bad_matchups]

    if good:
        best = max(good, key=lambda r: abs(r["edge"] or 0))
        to_keep.append(best["id"])
        to_delete.extend(r["id"] for r in group if r["id"] != best["id"])
    elif bad:
        best = max(bad, key=lambda r: abs(r["edge"] or 0))
        to_keep.append(best["id"])
        to_delete.extend(r["id"] for r in bad if r["id"] != best["id"])

print(f"To keep: {len(to_keep)}")
print(f"To delete: {len(to_delete)}")

for pid in to_delete:
    c.execute("DELETE FROM picks WHERE id = ?", (pid,))

conn.commit()

c.execute("SELECT COUNT(*) FROM picks")
new_count = c.fetchone()[0]
print(f"New total: {new_count}")

c.execute("SELECT league, COUNT(*) as cnt FROM picks GROUP BY league ORDER BY cnt DESC")
for r in c.fetchall():
    print(f"  {r['league']}: {r['cnt']} picks")

c.execute("SELECT league, COUNT(DISTINCT matchup) as games FROM picks WHERE matchup IS NOT NULL AND matchup != '' GROUP BY league")
for r in c.fetchall():
    print(f"  {r['league']} games: {r['games']}")

conn.close()
print("\nDONE — picks.db cleaned")
