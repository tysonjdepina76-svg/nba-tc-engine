"""WNBA backtest v2: derive picks from proj_WNBA_*.json, grade against boxscores."""
import json, unicodedata
from pathlib import Path
from collections import defaultdict

ws = Path("/home/workspace")
log = ws / "Daily_Log"
final = log / "final"
half = log / "halftime"
out = ws / "Reports"
out.mkdir(exist_ok=True)

# Load boxscores: map "matchup_short" -> player -> stat -> val
def normalize_name(n):
    return unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii").lower().strip()

box = {}  # matchup_short -> {normalized_name: {stat: val}}
def abbr(t):  # team name -> abbr
    mapping = {
        "Las Vegas Aces": "LV", "Los Angeles Sparks": "LA", "Seattle Storm": "SEA",
        "Minnesota Lynx": "MIN", "Connecticut Sun": "CON", "Chicago Sky": "CHI",
        "Indiana Fever": "IND", "Atlanta Dream": "ATL", "Washington Mystics": "WSH",
        "New York Liberty": "NY", "Dallas Wings": "DAL", "Phoenix Mercury": "PHX",
        "Golden State Valkyries": "GS", "Portland Fire": "POR", "Toronto Tempo": "TOR",
    }
    return mapping.get(t, t.split()[-1][:3].upper())

STAT_MAP = {"pts": "pts", "reb": "reb", "ast": "ast", "tpm": "fg3m", "stl": "stl", "blk": "blk"}

for f in final.glob("wnba_*_final_*.json"):
    d = json.loads(f.read_text())
    pl = d.get("players", {})
    if not pl:
        continue
    aw = d.get("away_team") or d.get("away", {}).get("name", "")
    hm = d.get("home_team") or d.get("home", {}).get("name", "")
    short = f"{abbr(aw)}@{abbr(hm)}"
    inner = {}
    for name, p in pl.items():
        inner[normalize_name(name)] = p
    box[short] = inner

print(f"Boxscores loaded: {len(box)} matchups")

# Derive picks from proj_WNBA_*.json
graded = []
skipped = defaultdict(int)
for proj in log.glob("*/proj_WNBA_*.json"):
    d = json.loads(proj.read_text())
    matchup = d.get("matchup", "")
    # proj matchup format: "SEA at LV" -> "SEA@LV"
    if " at " in matchup:
        parts = matchup.split(" at ")
        short = f"{parts[0]}@{parts[1]}"
    else:
        short = matchup.replace(" ", "@")
    if short not in box:
        skipped["no_boxscore"] += 1
        continue
    bx = box[short]
    for side in ["away", "home"]:
        roster = d.get(side, {})
        for cat, players in [("starters", roster.get("starters", {})),
                              ("bench", roster.get("bench", {}))]:
            if isinstance(players, dict):
                plist = []
                for k, v in players.items():
                    if isinstance(v, list):
                        plist.extend(v)
                    else:
                        plist.append(v)
            else:
                plist = players or []
            for p in plist:
                name = p.get("name", "")
                nm = normalize_name(name)
                if nm not in bx:
                    skipped["no_player_boxscore"] += 1
                    continue
                actual_player = bx[nm]
                for stat, col in STAT_MAP.items():
                    tc = p.get(f"tc_{stat}")
                    ln = p.get(f"line_{stat}")
                    if tc is None or ln is None:
                        continue
                    if tc == ln:
                        continue  # no edge
                    actual_val = actual_player.get(col)
                    if actual_val is None:
                        skipped["no_actual"] += 1
                        continue
                    try:
                        actual = float(actual_val)
                        line = float(ln)
                        proj_v = float(tc)
                    except (ValueError, TypeError):
                        skipped["non_numeric"] += 1
                        continue
                    direction = "OVER" if proj_v > line else "UNDER"
                    hit = (actual > line) if direction == "OVER" else (actual < line)
                    graded.append({
                        "date": d.get("timestamp", "")[:10],
                        "matchup": short,
                        "player": name,
                        "category": cat,
                        "stat": stat,
                        "direction": direction,
                        "line": line,
                        "proj": round(proj_v, 2),
                        "actual": actual,
                        "edge": round(proj_v - line, 2),
                        "result": "HIT" if hit else "MISS",
                    })

print(f"\nGraded: {len(graded)}, Skipped: {dict(skipped)}")

# Summary
by_dir = defaultdict(lambda: [0, 0])
by_stat = defaultdict(lambda: [0, 0])
by_match = defaultdict(lambda: [0, 0])
by_date = defaultdict(lambda: [0, 0])
for g in graded:
    by_dir[g["direction"]][1 if g["result"] == "HIT" else 0] += 1
    by_dir[g["direction"]][0] = by_dir[g["direction"]][0]  # placeholder
    by_stat[g["stat"]][1 if g["result"] == "HIT" else 0] += 1
    by_match[g["matchup"]][1 if g["result"] == "HIT" else 0] += 1
    by_date[g["date"]][1 if g["result"] == "HIT" else 0] += 1
    by_dir[g["direction"]][0] += 1
    by_stat[g["stat"]][0] += 1
    by_match[g["matchup"]][0] += 1
    by_date[g["date"]][0] += 1

total = len(graded)
hits = sum(1 for g in graded if g["result"] == "HIT")
print(f"\nTotal graded: {total}, Hits: {hits}/{total} = {hits/total*100:.1f}%" if total else "no graded")
print("\nBy direction:")
for k, (t, h) in sorted(by_dir.items()):
    print(f"  {k}: {h}/{t} = {h/t*100:.1f}%" if t else f"  {k}: 0")
print("\nBy stat:")
for k, (t, h) in sorted(by_stat.items(), key=lambda x: -x[1][0]):
    print(f"  {k}: {h}/{t} = {h/t*100:.1f}%" if t else f"  {k}: 0")
print("\nBy matchup:")
for k, (t, h) in sorted(by_match.items(), key=lambda x: -x[1][0])[:15]:
    print(f"  {k}: {h}/{t} = {h/t*100:.1f}%" if t else f"  {k}: 0")
print("\nBy date:")
for k, (t, h) in sorted(by_date.items()):
    print(f"  {k}: {h}/{t} = {h/t*100:.1f}%" if t else f"  {k}: 0")

# Save CSV
if graded:
    import csv
    csvp = out / "wnba_backtest_full_20260630.csv"
    with open(csvp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(graded[0].keys()))
        w.writeheader()
        w.writerows(graded)
    print(f"\nSaved: {csvp}")