import csv
from collections import defaultdict

csv_path = "/home/workspace/Daily_Log/2026-07-13/picks.csv"

games = defaultdict(list)
with open(csv_path) as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = row.get("matchup", "?")
        games[key].append(row)

print("=" * 60)
print(f"WNBA PICKS — GAME BY GAME")
print(f"Total games: {len(games)} | Total picks: {sum(len(v) for v in games.values())}")
print("=" * 60)

for game, picks in sorted(games.items()):
    print(f"\n{game}  ({len(picks)} picks)")
    signals = defaultdict(int)
    for p in picks:
        sig = p.get("signal", "?")
        stat = p.get("stat", "?")
        direction = p.get("direction", "?")
        line = p.get("market_line", "?")
        player = p.get("player", "?")
        edge = p.get("edge", "?")
        signals[sig] += 1
        print(f"  {sig:8} {player:22} {stat:6} {direction:5} {line:6}  edge {edge}")
    print(f"  Signals: {dict(signals)}")
