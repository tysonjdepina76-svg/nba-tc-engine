"""
WNBA Game Markets — full breakdown with ML, spread, game total O/U.
Pulls lines from /home/workspace/Daily_Log/2026-07-13/ JSON projections
or falls back to DK odds scrape.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

CSV = "/home/workspace/Daily_Log/2026-07-13/picks.csv"
DASH = Path("/home/workspace/sports_betting_dashboard/data")
GAMEDIR = Path("/home/workspace/Daily_Log/2026-07-13")

rows = []
with open(CSV) as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)

by_game = defaultdict(list)
for row in rows:
    if row.get("matchup"):
        by_game[row["matchup"]].append(row)

def load_game_lines(matchup):
    """Try to load ML/spread/total from any available source."""
    safe = re.sub(r"[^A-Z0-9]+", "_", matchup).strip("_")
    for fname in [f"proj_wnba_{safe}.json", f"game_{safe}.json", f"{safe}.json"]:
        p = GAMEDIR / fname
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
    return {}

def seen(p):
    return (p.get("player", ""), p.get("stat", ""), p.get("direction", ""), p.get("market_line", ""))

print("=" * 72)
print(f"WNBA TODAY — {len(by_game)} GAMES, {len(rows)} PICKS")
print("=" * 72)

for mu in sorted(by_game, key=lambda m: -len(by_game[m])):
    picks = by_game[mu]
    gp = load_game_lines(mu)

    home, away = mu.split("@") if "@" in mu else ("?", "?")
    print(f"\n{away} @ {home}  ({len(picks)} player props)")
    print("-" * 72)

    # ML / SPREAD / TOTAL
    ml_away = ml_home = sp = tot = None
    if gp:
        ml_away = gp.get("ml_away") or gp.get("away_ml")
        ml_home = gp.get("ml_home") or gp.get("home_ml")
        sp = gp.get("spread") or gp.get("home_spread")
        tot = gp.get("total") or gp.get("game_total")

    if ml_away or ml_home:
        print(f"  MONEYLINE:    {away} {ml_away or '?'}  /  {home} {ml_home or '?'}")
    else:
        print(f"  MONEYLINE:    (no DK line — quota exhausted)")
    if sp is not None:
        side = home if sp > 0 else away
        print(f"  SPREAD:       {side} {sp:+.1f}")
    else:
        print(f"  SPREAD:       (no DK line — quota exhausted)")
    if tot:
        line = tot.get("line") if isinstance(tot, dict) else tot
        over_odds = tot.get("over") if isinstance(tot, dict) else None
        under_odds = tot.get("under") if isinstance(tot, dict) else None
        print(f"  GAME TOTAL:   O/U {line}  (over {over_odds or '?'} / under {under_odds or '?'})")
    else:
        print(f"  GAME TOTAL:   (no DK line — quota exhausted)")

    # Projected total from our player projections
    pts = [p for p in picks if p.get("stat", "").upper() in ("PTS", "POINTS", "")]
    home_pts = sum(float(p.get("tc_projection") or 0) for p in pts if p.get("team") == home or p.get("team") == "HOME")
    away_pts = sum(float(p.get("tc_projection") or 0) for p in pts if p.get("team") == away or p.get("team") == "AWAY")
    if home_pts + away_pts > 0:
        proj_total = home_pts + away_pts
        print(f"  OUR PROJECTED TOTAL:  {home} {home_pts:5.1f} + {away} {away_pts:5.1f} = {proj_total:5.1f}")
        if tot:
            line = tot.get("line") if isinstance(tot, dict) else tot
            try:
                diff = proj_total - float(line)
                rec = f"OVER {proj_total:5.1f} (+{diff:+.1f} vs line)" if diff > 0 else f"UNDER {proj_total:5.1f} ({diff:+.1f} vs line)"
                print(f"  PLAY: {rec}")
            except Exception:
                pass

    # Top 8 deduped player props
    print(f"  TOP 10 PLAYER PROPS (edge≥10%, deduped):")
    above = [p for p in picks if float(p.get("edge") or 0) > 0.10]
    above.sort(key=lambda p: -float(p.get("edge") or 0))
    seen_keys = set()
    shown = 0
    for p in above:
        k = seen(p)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        sig = p.get("signal", "")
        d = p.get("direction", "")
        stat = p.get("stat", "")
        line = p.get("market_line", "?")
        edge = float(p.get("edge") or 0) * 100
        player = (p.get("player", "") or "")[:22]
        team = p.get("team", "")
        print(f"    [{sig:6}] {player:22} {team:4} {stat} {d} {line:>5}  edge {edge:5.1f}%")
        shown += 1
        if shown >= 10:
            break
