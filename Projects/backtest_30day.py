#!/usr/bin/env python3
"""30-Day WNBA Backtest — Hit Rates by Stat, Team, Direction, Edge Tier.
Compares TC projections vs ESPN results + DK lines from The Odds API."""
import json, csv, requests, os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

LOG = Path("/home/workspace/Daily_Log")
OUT_DIR = LOG / "backtests" / "30day"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WNBA_ABBREV = {
    "ATL": "Atlanta Dream", "CHI": "Chicago Sky", "CON": "Connecticut Sun",
    "DAL": "Dallas Wings", "GS": "Golden State Valkyries", "IND": "Indiana Fever",
    "LV": "Las Vegas Aces", "LA": "Los Angeles Sparks", "MIN": "Minnesota Lynx",
    "NY": "New York Liberty", "PHX": "Phoenix Mercury", "POR": "Portland Fire",
    "SEA": "Seattle Storm", "TOR": "Toronto Tempo", "WSH": "Washington Mystics",
}
STATS = ["PTS", "REB", "AST", "3PM", "STL", "BLK"]

# =====================================================
# 1. Collect all picks from Daily_Log picks.csv
# =====================================================
rows = []
dates_seen = set()
for d in sorted(LOG.iterdir()):
    if not d.is_dir() or d.name.startswith(".") or d.name in ("backtests", "worldcup"):
        continue
    p = d / "picks.csv"
    if not p.exists():
        continue
    dir_date = d.name
    with open(p) as f:
        r = csv.DictReader(f)
        for row in r:
            dt = (row.get("date") or dir_date).strip()
            row["_date"] = dt
            dates_seen.add(dt)
            rows.append(row)

print(f"Picks loaded: {len(rows)} from {len(dates_seen)} dates")

# =====================================================
# 2. Get ESPN boxscore results from Daily_Log proj files
# =====================================================
def load_actuals(date_str, sport, matchup):
    safe = matchup.replace("@", "_at_")
    proj_path = LOG / date_str / f"proj_{sport}_{safe}.json"
    if not proj_path.exists():
        return {}
    with open(proj_path) as f:
        proj = json.load(f)
    actuals = {}
    for p in proj.get("valid_props", []):
        act = p.get("actual")
        if act is not None and act != "":
            actuals[(p["player"].strip().upper(), p["stat"].strip().upper())] = {
                "actual": float(act),
                "tc_projection": float(p.get("tc_projection", 0) or 0),
                "proj_direction": (p.get("direction", "") or "").strip().upper(),
            }
    return actuals

# Settle results where possible by cross-referencing proj files
settled_count = 0
for row in rows:
    if row.get("_won") is not None:
        continue
    dt = row.get("_date", "")
    sp = row.get("league", "WNBA").strip()
    mx = row.get("matchup", "").strip()
    ps = (row.get("player", "") or "").strip().upper()
    st = (row.get("stat", "") or "").strip().upper()
    actuals = load_actuals(dt, sp, mx)
    key = (ps, st)
    if key in actuals:
        a = actuals[key]
        mkt = float(row.get("market_line", 0) or 0)
        if mkt == 0:
            mkt = a["tc_projection"]
        direction = (row.get("direction", "") or "").strip().upper()
        actual_val = a["actual"]
        if direction == "OVER":
            won = actual_val > mkt
        elif direction == "UNDER":
            won = actual_val < mkt
        else:
            won = actual_val >= mkt  # default assume OVER
        row["actual"] = str(actual_val)
        row["_won"] = won
        settled_count += 1
    else:
        row["_won"] = None

print(f"Results settled from proj files: {settled_count}")

# =====================================================
# 3. Compute hit rates
# =====================================================
class C:
    total = 0
    correct = 0
    total_edge = 0.0
    def get_rate(self):
        return round(self.correct / self.total * 100, 1) if self.total > 0 else 0
    def avg_edge(self):
        return round(self.total_edge / self.total, 1) if self.total > 0 else 0

by_stat = {s: C() for s in STATS}
by_team = defaultdict(C)
by_direction = defaultdict(C)
by_edge_tier = defaultdict(C)

for row in rows:
    ps = row.get("player", "").strip()
    st = row.get("stat", "").strip()
    di = row.get("direction", "").strip().upper()
    tm = row.get("team", "").strip()
    dt = row.get("_date", "").strip()
    mx = row.get("matchup", "").strip()
    sp = row.get("league", "WNBA").strip()
    won = row.get("_won")
    edge = float(row.get("edge", 0) or 0)
    # Skip unsettled picks
    if won is None:
        continue

    if st not in by_stat:
        continue

    # Tier by edge strength
    if edge < 1:
        tier = "marginal (<1)"
    elif edge < 3:
        tier = "moderate (1-3)"
    elif edge < 5:
        tier = "strong (3-5)"
    else:
        tier = "elite (5+)"

    by_stat[st].total += 1
    by_stat[st].total_edge += edge
    by_team[tm].total += 1
    by_team[tm].total_edge += edge
    by_direction[di].total += 1
    by_direction[di].total_edge += edge
    by_edge_tier[tier].total += 1
    by_edge_tier[tier].total_edge += edge

    if won:
        by_stat[st].correct += 1
        by_team[tm].correct += 1
        by_direction[di].correct += 1
        by_edge_tier[tier].correct += 1

# =====================================================
# 4. Write report
# =====================================================
settled_picks = [r for r in rows if r.get("_won") is not None]
total_result_desc = f"{len(settled_picks)} settled (of {len(rows)} total) from {len(dates_seen)} dates"

md = f"""# TC 30-Day Backtest — All Sports
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Picks analyzed:** {total_result_desc}

## Hit Rates by Stat
| Stat | Picks | Hit Rate | Avg Edge |
|------|-------|----------|----------|
"""
for s in STATS:
    c = by_stat[s]
    md += f"| {s} | {c.total} | {c.get_rate()}% | {c.avg_edge()} |\n"

md += "\n## Hit Rates by Direction\n| Dir | Picks | Hit Rate | Avg Edge |\n|-----|-------|----------|----------|\n"
for d in sorted(by_direction):
    c = by_direction[d]
    md += f"| {d} | {c.total} | {c.get_rate()}% | {c.avg_edge()} |\n"

md += "\n## Hit Rates by Edge Tier\n| Tier | Picks | Hit Rate | Avg Edge |\n|------|-------|----------|----------|\n"
for t in ["marginal (<1)", "moderate (1-3)", "strong (3-5)", "elite (5+)"]:
    c = by_edge_tier.get(t)
    if c:
        md += f"| {t} | {c.total} | {c.get_rate()}% | {c.avg_edge()} |\n"

md += "\n## Hit Rates by Team (top 12)\n| Team | Picks | Hit Rate | Avg Edge |\n|------|-------|----------|----------|\n"
for tm, c in sorted(by_team.items(), key=lambda x: -x[1].total)[:12]:
    md += f"| {tm} | {c.total} | {c.get_rate()}% | {c.avg_edge()} |\n"

# Write CSV
csv_path = OUT_DIR / "30day_hitrates.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["category", "metric", "picks", "hit_rate_pct", "avg_edge"])
    for s in STATS:
        c = by_stat[s]
        w.writerow(["stat", s, c.total, c.get_rate(), c.avg_edge()])
    for d, c in by_direction.items():
        w.writerow(["direction", d, c.total, c.get_rate(), c.avg_edge()])
    for t, c in by_edge_tier.items():
        w.writerow(["edge_tier", t, c.total, c.get_rate(), c.avg_edge()])
    for tm, c in by_team.items():
        w.writerow(["team", tm, c.total, c.get_rate(), c.avg_edge()])

md_path = OUT_DIR / "30day_report.md"
md_path.write_text(md)
print(f"\nReport: {md_path}")
print(f"CSV:    {csv_path}")
print(md)
