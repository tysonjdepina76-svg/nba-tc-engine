import csv
from collections import defaultdict
from itertools import combinations

csv_path = "/home/workspace/Daily_Log/2026-07-13/picks.csv"

games = defaultdict(list)
with open(csv_path) as f:
    reader = csv.DictReader(f)
    for row in reader:
        games[row.get("matchup", "?")].append(row)

print("=" * 60)
print("WNBA COMBOS — TOP 3-LEG PARLAYS PER GAME")
print("=" * 60)

for game, picks in sorted(games.items()):
    seen = set()
    valid = []
    for p in picks:
        try:
            edge = float(p.get("edge", 0))
            pl = p.get("player")
            st = p.get("stat")
            ln = p.get("market_line")
            key = (pl, st)
            if edge > 0.14 and p.get("direction") == "OVER" and key not in seen:
                seen.add(key)
                valid.append((edge, pl, st, ln))
        except:
            pass
    valid.sort(reverse=True)

    print(f"\n{game}  ({len(picks)} picks, {len(valid)} unique above 14% edge)")
    print("-" * 60)
    print("Top 5 singles by edge:")
    for e, pl, st, ln in valid[:5]:
        print(f"  {pl:25} {st:4} OVER {ln:5}  edge {e*100:.1f}%")
    print("\nTop 5 unique-player 3-leg combos:")
    shown = 0
    for combo in combinations(valid[:12], 3):
        players = [c[1] for c in combo]
        if len(set(players)) != 3:
            continue
        combined = 1.0
        for e, pl, st, ln in combo:
            combined *= (1 + e)
        legs = " + ".join(f"{pl.split()[-1]} {st}" for _, pl, st, _ in combo)
        print(f"  {combined:.2f}x combined  | {legs}")
        shown += 1
        if shown >= 5:
            break
