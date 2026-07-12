#!/usr/bin/env python3
"""MLB backtest: compare today's projections to actual boxscores."""
import json, unicodedata
from pathlib import Path
from collections import defaultdict

ws = Path("/home/workspace")
log = ws / "Daily_Log"
box_dir = log / "mlb_boxscores"
out = ws / "Reports"
out.mkdir(exist_ok=True)

TODAY = "2026-07-11"

# Team full name -> abbr
TEAM_ABBR = {
    "Arizona Diamondbacks": "ARI", "Athletics": "ATH", "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS", "Chicago Cubs": "CHC",
    "Chicago White Sox": "CHW", "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL", "Detroit Tigers": "DET", "Houston Astros": "HOU",
    "Kansas City Royals": "KC", "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA", "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN",
    "New York Mets": "NYM", "New York Yankees": "NYY", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

def norm(n):
    return unicodedata.normalize("NFKD", n).encode("ascii","ignore").decode("ascii").lower().strip()

def first_last(n):
    p = norm(n).split()
    return f"{p[0]} {p[-1]}" if len(p) >= 2 else norm(n)

# Load boxscores: short matchup -> {normalized_firstlast: {stat: val}}
box = {}
for f in box_dir.glob(f"mlb_*_final_*.json"):
    # filename: mlb_AwayAtHome_final_*.json  -> team names are CamelCase (no spaces)
    stem = f.stem  # mlb_AwayAtHome_final_xxx
    parts = stem.split("_final_")[0]
    # parts: ['mlb', 'AwayTeamAtHomeTeam']  (AwayTeamAtHomeTeam has no separator because team names have no spaces in this dataset)
    rest = stem.split("_final_")[0]
    if not rest.startswith("mlb_") or "_at_" not in rest:
        continue
    aw, hm = rest.split("_at_", 1); aw = aw.replace("mlb_", "")
    # Add spaces before uppercase (CamelCase -> Camel Case)
    import re
    def split_camel(s):
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    aw_full = split_camel(aw)
    hm_full = split_camel(hm)
    aw_abbr = TEAM_ABBR.get(aw_full, aw[:3].upper())
    hm_abbr = TEAM_ABBR.get(hm_full, hm[:3].upper())
    short = f"{aw_abbr}@{hm_abbr}"

    d = json.loads(f.read_text())
    inner = {}
    for sec in ("batting", "pitching"):
        sec_d = d.get(sec, {})
        if isinstance(sec_d, dict):
            for pname, stats in sec_d.items():
                if not isinstance(stats, dict):
                    continue
                key = first_last(pname)
                # store with stat names converted to int where possible
                rec = {}
                for k, v in stats.items():
                    if k in ("name","team","pos"):
                        continue
                    try:
                        rec[k] = int(v) if str(v).lstrip("-").isdigit() else (float(v) if v not in (None,"") else 0)
                    except Exception:
                        pass
                inner.setdefault(key, {}).update(rec)
    if inner:
        box[short] = inner

print(f"Boxscores loaded: {len(box)} matchups -> {sorted(box.keys())}")

# Load projections for TODAY
graded = []
skipped = defaultdict(int)
proj_dir = log / TODAY
for proj in proj_dir.glob("proj_MLB_*.json"):
    d = json.loads(proj.read_text())
    short = d.get("matchup", "")
    if short not in box:
        # try to remap via away/home team names
        aw_full = d.get("away_team", "")
        hm_full = d.get("home_team", "")
        aw_abbr = TEAM_ABBR.get(aw_full, aw_full[:3].upper())
        hm_abbr = TEAM_ABBR.get(hm_full, hm_full[:3].upper())
        short = f"{aw_abbr}@{hm_abbr}"
    if short not in box:
        skipped["no_boxscore"] += 1
        continue
    bx = box[short]
    for prop in d.get("valid_props", []):
        nm = first_last(prop.get("player", ""))
        if nm not in bx:
            skipped["no_player_box"] += 1
            continue
        actual = bx[nm]
        stat = prop.get("stat", "")
        line = prop.get("market_line", 0) or 0
        tc = prop.get("tc_projection", 0) or 0
        direction = prop.get("direction", "OVER")
        # find actual value
        # stat mapping
        stat_key = {
            "hits":"h", "runs":"r", "rbi":"rbi", "hr":"hr", "total_bases":"tb",
            "sb":"sb", "singles":"1b", "doubles":"2b", "triples":"3b", "walks":"bb",
            "strikeouts":"k", "hits_allowed":"h", "earned_runs":"er", "outs":"ipOuts",
        }.get(stat, stat)
        actual_val = actual.get(stat_key, 0)
        hit = (actual_val > line) if direction == "OVER" else (actual_val < line)
        graded.append({
            "matchup": short,
            "player": prop.get("player"),
            "stat": stat,
            "line": line,
            "tc_projection": tc,
            "direction": direction,
            "actual": actual_val,
            "hit": hit,
            "mae": abs(tc - actual_val),
            "bias": tc - actual_val,
            "edge": prop.get("edge", 0),
        })

print(f"Graded picks: {len(graded)}")
print(f"Skipped: {dict(skipped)}")

# Aggregate by stat
by_stat = defaultdict(list)
for g in graded:
    by_stat[g["stat"]].append(g)

lines = []
lines.append(f"# MLB Backtest {TODAY}\n")
lines.append(f"Boxscores: {len(box)} matchups graded against projections\n")
lines.append(f"Total graded picks: {len(graded)}\n")
lines.append(f"Skipped: {dict(skipped)}\n\n")
lines.append("| Stat | N | Hit% | MAE | Bias | Over% |\n")
lines.append("|---|---:|---:|---:|---:|---:|\n")
for stat, gs in sorted(by_stat.items()):
    n = len(gs)
    hits = sum(1 for g in gs if g["hit"])
    hit_pct = 100*hits/n if n else 0
    mae = sum(g["mae"] for g in gs)/n if n else 0
    bias = sum(g["bias"] for g in gs)/n if n else 0
    over = sum(1 for g in gs if g["direction"]=="OVER")
    lines.append(f"| {stat} | {n} | {hit_pct:.1f}% | {mae:.2f} | {bias:+.2f} | {over} |\n")

# by direction
lines.append("\n## By Direction\n")
lines.append("| Direction | N | Hit% |\n|---|---:|---:|\n")
for d in ["OVER","UNDER"]:
    gs = [g for g in graded if g["direction"]==d]
    if not gs: continue
    hits = sum(1 for g in gs if g["hit"])
    lines.append(f"| {d} | {len(gs)} | {100*hits/len(gs):.1f}% |\n")

# by matchup
lines.append("\n## By Matchup\n")
lines.append("| Matchup | N | Hit% |\n|---|---:|---:|\n")
by_mu = defaultdict(list)
for g in graded: by_mu[g["matchup"]].append(g)
for mu, gs in sorted(by_mu.items()):
    hits = sum(1 for g in gs if g["hit"])
    lines.append(f"| {mu} | {len(gs)} | {100*hits/len(gs):.1f}% |\n")

# Top edges hit/miss
lines.append("\n## Top 10 Edges - Hits\n")
hits_sorted = sorted(graded, key=lambda g: -abs(g["edge"]))
for g in hits_sorted[:10]:
    if g["hit"]:
        lines.append(f"- {g['player']} {g['stat']} {g['direction']} {g['line']} (TC {g['tc_projection']}, actual {g['actual']}, edge {g['edge']:+.2f}) ✓\n")

lines.append("\n## Top 10 Edges - Misses\n")
misses = [g for g in hits_sorted if not g["hit"]]
for g in misses[:10]:
    lines.append(f"- {g['player']} {g['stat']} {g['direction']} {g['line']} (TC {g['tc_projection']}, actual {g['actual']}, edge {g['edge']:+.2f}) ✗\n")

report = "".join(lines)
rpath = out / f"MLB_Backtest_Today_{TODAY.replace('-','')}.md"
rpath.write_text(report)
print(f"Report: {rpath}")

# CSV
csv = out / f"MLB_Backtest_Today_{TODAY.replace('-','')}.csv"
with csv.open("w") as f:
    f.write("matchup,player,stat,line,tc_projection,direction,actual,hit,mae,bias,edge\n")
    for g in graded:
        f.write(f"{g['matchup']},{g['player']},{g['stat']},{g['line']},{g['tc_projection']},{g['direction']},{g['actual']},{g['hit']},{g['mae']:.2f},{g['bias']:+.2f},{g['edge']:+.2f}\n")
print(f"CSV: {csv}")

# console summary
print(f"\n=== MLB BACKTEST {TODAY} ===")
print(f"{'Stat':<15} {'N':>4} {'Hit%':>7} {'MAE':>7} {'Bias':>7}")
print("-"*45)
for stat, gs in sorted(by_stat.items()):
    n=len(gs); hits=sum(1 for g in gs if g['hit'])
    mae=sum(g['mae'] for g in gs)/n; bias=sum(g['bias'] for g in gs)/n
    print(f"{stat:<15} {n:>4} {100*hits/n:>6.1f}% {mae:>7.2f} {bias:>+7.2f}")
