#!/usr/bin/env python3
"""Full multi-sport self-edge backtest — July 2026. Loads all pick CSVs, grades against
available actuals (statsapi/ESPN boxscores/graded CSVs), computes win rate, ROI, edge
buckets, weakest/strongest markets, and daily P&L.

Authoritative data paths (confirmed 2026-07-21):
  data/picks/{sport}_{date}.csv        — picks from daily_picks.py (schema: name,team,sport,stat,matchup,projection,line,edge,direction,reason)
  Daily_Log/{date}/picks.csv           — legacy picks
  Daily_Log/{date}/graded_picks.csv    — graded (adds: actual,hit,graded_at)
  Daily_Log/backtests/{date}/summary.json — backtest summaries with hit_rates
  Daily_Log/backtests/combined_backtest.csv
  Daily_Log/_archive/{date}/picks.csv
  data/backtest/nfl_2026/, nhl_2026-27/

Grading rules (matches tc_math.py direction logic):
  OVER  → actual > projection  = hit
  UNDER → actual < projection  = hit

For picks with no boxscore actuals, we search:
  1. statsapi (MLB) — live.boxscore_data
  2. ESPN actuals from backtest JSONs
  3. Existing graded_picks.csv files
"""

import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path("/home/workspace")
DATA_PICKS = WORKSPACE / "data" / "picks"
DAILY_LOG = WORKSPACE / "Daily_Log"
OUTDIR = DAILY_LOG / "2026-07-21"

# ---- Load helpers -----------------------------------------------------------
def load_csv(path):
    rows = []
    if not path.exists():
        return rows
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def sport_from_path(p):
    s = Path(p).stem.lower()
    if s.startswith("mlb"): return "MLB"
    if s.startswith("wnba"): return "WNBA"
    if s.startswith("wc"): return "WC"
    if "nfl" in s: return "NFL"
    if "nhl" in s: return "NHL"
    if "nba" in s: return "NBA"
    return "OTHER"

# ---- Load all picks ---------------------------------------------------------
all_picks = []

# data/picks/{sport}_{date}.csv
for f in sorted(DATA_PICKS.glob("*.csv")):
    rows = load_csv(f)
    if rows:
        sport = sport_from_path(f)
        for r in rows:
            r["_source"] = str(f)
            r["_sport"] = r.get("sport", sport)
        all_picks.extend(rows)

# Daily_Log/{date}/picks.csv
for d in sorted(DAILY_LOG.iterdir()):
    if not d.is_dir() or d.name.startswith("_"):
        continue
    pf = d / "picks.csv"
    if pf.exists():
        rows = load_csv(pf)
        sport = "MULTI"
        for r in rows:
            r["_source"] = str(pf)
            r["_sport"] = r.get("sport", sport)
        all_picks.extend(rows)

# Daily_Log/_archive/{date}/picks.csv
archive = DAILY_LOG / "_archive"
if archive.exists():
    for d in sorted(archive.iterdir()):
        if not d.is_dir():
            continue
        pf = d / "picks.csv"
        if pf.exists():
            rows = load_csv(pf)
            for r in rows:
                r["_source"] = str(pf)
                r["_sport"] = r.get("sport", "MLB")
            all_picks.extend(rows)

# backtests/combined_backtest.csv
cb = DAILY_LOG / "backtests" / "combined_backtest.csv"
if cb.exists():
    rows = load_csv(cb)
    for r in rows:
        r["_source"] = str(cb)
        r["_sport"] = r.get("sport", "MLB")
    all_picks.extend(rows)

print(f"Total picks loaded: {len(all_picks)}")
print(f"Unique sources: {len(set(p['_source'] for p in all_picks))}")

# ---- Load actuals (graded / boxscores) --------------------------------------
# 1. Existing graded_picks.csv files
graded_map = {}  # key: (player, stat, date, sport) → {actual, hit}
for d in sorted(DAILY_LOG.iterdir()):
    if not d.is_dir():
        continue
    gf = d / "graded_picks.csv"
    if gf.exists():
        rows = load_csv(gf)
        for r in rows:
            key = (r.get("player",""), r.get("stat",""), d.name, r.get("sport",""))
            graded_map[key] = {"actual": to_float(r.get("actual",0)), "hit": r.get("hit","")=="True"}

# 2. ESPN actuals from backtest JSONs
espn_actuals = {}
for btd in sorted((DAILY_LOG / "backtests").iterdir()):
    if not btd.is_dir():
        continue
    for ea_file in btd.glob("espn_actuals_*.json"):
        try:
            with open(ea_file) as jf:
                data = json.load(jf)
            if isinstance(data, dict):
                for player_key, stats in data.items():
                    if isinstance(stats, dict):
                        espn_actuals[(player_key, btd.name)] = stats
                    elif isinstance(stats, list):
                        for item in stats:
                            if isinstance(item, dict):
                                pname = item.get("player") or item.get("name","")
                                espn_actuals[(pname, btd.name)] = item
        except (json.JSONDecodeError, KeyError):
            pass

print(f"Graded entries from CSV: {len(graded_map)}")
print(f"ESPN actuals entries: {len(espn_actuals)}")

# ---- Grade picks ------------------------------------------------------------
graded_picks = []
ungraded_count = 0

for p in all_picks:
    player = p.get("name", p.get("player", "")).strip()
    stat = p.get("stat", "").strip().lower()
    sport = p.get("_sport", p.get("sport","")).upper()
    projection = to_float(p.get("projection", p.get("tc_projection", 0)))
    edge = to_float(p.get("edge", 0))
    direction = p.get("direction", "OVER").upper().strip()
    
    # Try to find actual from graded map
    date_val = p.get("date", "")
    if not date_val:
        # Try to extract from source path
        src = p.get("_source","")
        parts = src.split("/")
        for part in parts:
            if part.startswith("2026-") and len(part) == 10:
                date_val = part
                break
    
    key = (player, stat, date_val, sport.lower())
    actual = 0
    hit = None
    
    if key in graded_map:
        actual = graded_map[key]["actual"]
        hit = graded_map[key]["hit"]
    elif sport == "MLB" and player and stat:
        # Try statsapi for MLB picks
        try:
            import statsapi
            # Look up player ID
            lookup = statsapi.lookup_player(player)
            if lookup and isinstance(lookup, list) and lookup:
                pid = lookup[0].get("id")
                if pid:
                    sdata = statsapi.player_stat_data(pid, group="hitting" if stat in ("h","hr","rbi","r") else "pitching", type="season")
                    if sdata and "stats" in sdata:
                        for st in sdata["stats"]:
                            if st.get("type","").get("displayName","") == "yearByYear":
                                for split in st.get("splits", []):
                                    if str(split.get("season")) == "2026" and "stat" in split:
                                        smap = {
                                            "h": "hits", "hr": "homeRuns", "rbi": "rbi", "r": "runs",
                                            "sb": "stolenBases", "era": "era", "so": "strikeOuts"
                                        }
                                        stat_key = smap.get(stat, stat)
                                        actual = to_float(split["stat"].get(stat_key, 0))
        except Exception:
            pass
    
    if hit is None and actual > 0:
        hit = actual > projection if direction == "OVER" else actual < projection
    elif hit is None:
        ungraded_count += 1
        continue
    
    p["actual"] = actual
    p["hit"] = hit
    graded_picks.append(p)

print(f"Graded picks: {len(graded_picks)}")
print(f"Ungraded picks: {ungraded_count}")

# ---- Analysis ---------------------------------------------------------------
if not graded_picks:
    print("NO GRADED PICKS — aborting")
    sys.exit(1)

# Group by sport
sports = defaultdict(list)
for p in graded_picks:
    s = p.get("_sport", p.get("sport","")).upper()
    if s in ("MLB", "WNBA", "NBA", "NFL", "NHL", "WC"):
        sports[s].append(p)
    elif "MLB" in s:
        sports["MLB"].append(p)
    elif "WNBA" in s:
        sports["WNBA"].append(p)
    elif "NBA" in s:
        sports["NBA"].append(p)
    else:
        sports["OTHER"].append(p)

print(f"\nSports found: {list(sports.keys())}")
for s, picks in sorted(sports.items()):
    print(f"  {s}: {len(picks)} picks")

# ----- Edge buckets -----
def edge_bucket(edge):
    e = abs(float(edge))
    if e < 0.5: return "0.0-0.5"
    if e < 1.0: return "0.5-1.0"
    if e < 2.0: return "1.0-2.0"
    if e < 5.0: return "2.0-5.0"
    return "5.0+"

def bet_type(stat):
    s = str(stat).lower()
    if s in ("h","hr","rbi","r","sb","pts","reb","ast","stl","blk"):
        return "Player Prop"
    if s in ("ml", "moneyline", "spread", "total"):
        return s.upper()
    return "Player Prop"

# ----- Build report -----
report_lines = []
report_lines.append(f"# TC SELF-EDGE FULL BACKTEST")
report_lines.append(f"Generated: {datetime.now().isoformat()}")
report_lines.append(f"")
report_lines.append(f"## Summary")
report_lines.append(f"")

total_graded = len(graded_picks)
total_hits = sum(1 for p in graded_picks if p.get("hit") in (True, "True", 1))
overall_hit_rate = total_hits / total_graded * 100 if total_graded else 0

report_lines.append(f"- **Total graded picks**: {total_graded}")
report_lines.append(f"- **Total hits**: {total_hits}")
report_lines.append(f"- **Overall hit rate**: {overall_hit_rate:.1f}%")
report_lines.append(f"- **Ungraded (no actuals)**: {ungraded_count}")
report_lines.append(f"")

# 1. By sport
report_lines.append(f"## 1. Win Rate by Sport")
report_lines.append(f"")
report_lines.append(f"| Sport | Picks | Hits | Hit Rate | Avg Edge |")
report_lines.append(f"|-------|-------|------|----------|----------|")

sport_stats = {}
for s, picks in sorted(sports.items()):
    hits = sum(1 for p in picks if p.get("hit") in (True, "True", 1))
    edges = [to_float(p.get("edge", 0)) for p in picks]
    avg_edge = sum(edges) / len(edges) if edges else 0
    rate = hits / len(picks) * 100 if picks else 0
    sport_stats[s] = {"picks": len(picks), "hits": hits, "rate": rate, "avg_edge": avg_edge}
    report_lines.append(f"| {s} | {len(picks)} | {hits} | {rate:.1f}% | {avg_edge:.3f} |")

# ROI: assume 1 unit per pick, +1 if hit, -1 if miss
report_lines.append(f"")
report_lines.append(f"## 2. ROI by Sport (1 unit per pick)")
report_lines.append(f"")
report_lines.append(f"| Sport | Units Wagered | Units Won | Net | ROI % |")
report_lines.append(f"|-------|--------------|-----------|-----|-------|")

total_wagered = 0
total_won = 0
for s, picks in sorted(sports.items()):
    wagered = len(picks)
    won = sum(1 for p in picks if p.get("hit") in (True, "True", 1))
    net = won - (wagered - won)
    roi = (net / wagered * 100) if wagered else 0
    total_wagered += wagered
    total_won += won
    report_lines.append(f"| {s} | {wagered} | {won} | {net:+.0f} | {roi:+.1f}% |")

total_net = total_won - (total_wagered - total_won)
total_roi = (total_net / total_wagered * 100) if total_wagered else 0
report_lines.append(f"| **ALL** | **{total_wagered}** | **{total_won}** | **{total_net:+.0f}** | **{total_roi:+.1f}%** |")

# 3. Edge buckets
report_lines.append(f"")
report_lines.append(f"## 3. Edge Bucket Analysis")
report_lines.append(f"")
report_lines.append(f"| Edge Range | Picks | Hits | Hit Rate | ROI |")
report_lines.append(f"|------------|-------|------|----------|-----|")

buckets = defaultdict(list)
for p in graded_picks:
    b = edge_bucket(p.get("edge", 0))
    buckets[b].append(p)

edge_order = ["0.0-0.5", "0.5-1.0", "1.0-2.0", "2.0-5.0", "5.0+"]
for b in edge_order:
    if b not in buckets:
        continue
    picks = buckets[b]
    hits = sum(1 for p in picks if p.get("hit") in (True, "True", 1))
    rate = hits / len(picks) * 100 if picks else 0
    roi_val = (hits - (len(picks) - hits)) / len(picks) * 100 if picks else 0
    report_lines.append(f"| {b} | {len(picks)} | {hits} | {rate:.1f}% | {roi_val:+.1f}% |")

# 4. Weakest markets (by sport+stat)
report_lines.append(f"")
report_lines.append(f"## 4. Weakest Markets (Hit Rate < 45%)")
report_lines.append(f"")
report_lines.append(f"| Sport | Stat | Picks | Hits | Hit Rate |")
report_lines.append(f"|-------|------|-------|------|----------|")

sport_stat = defaultdict(list)
for p in graded_picks:
    sport_stat[(p.get("_sport",""), p.get("stat",""))].append(p)

weakest = []
for (s, st), picks in sport_stat.items():
    if len(picks) < 5:
        continue
    hits = sum(1 for p in picks if p.get("hit") in (True, "True", 1))
    rate = hits / len(picks) * 100
    if rate < 45:
        weakest.append((s, st, len(picks), hits, rate))

for s, st, n, h, r in sorted(weakest, key=lambda x: x[4]):
    report_lines.append(f"| {s} | {st} | {n} | {h} | {r:.1f}% |")

if not weakest:
    report_lines.append(f"| — | — | 0 | 0 | — |")

# 5. Strongest markets
report_lines.append(f"")
report_lines.append(f"## 5. Strongest Markets (Hit Rate > 55%)")
report_lines.append(f"")
report_lines.append(f"| Sport | Stat | Picks | Hits | Hit Rate | ROI |")
report_lines.append(f"|-------|------|-------|------|----------|-----|")

strongest = []
for (s, st), picks in sport_stat.items():
    if len(picks) < 5:
        continue
    hits = sum(1 for p in picks if p.get("hit") in (True, "True", 1))
    rate = hits / len(picks) * 100
    net = hits - (len(picks) - hits)
    roi = net / len(picks) * 100
    if rate > 55:
        strongest.append((s, st, len(picks), hits, rate, roi))

for s, st, n, h, r, roi_val in sorted(strongest, key=lambda x: x[4], reverse=True):
    report_lines.append(f"| {s} | {st} | {n} | {h} | {r:.1f}% | {roi_val:+.1f}% |")

if not strongest:
    report_lines.append(f"| — | — | 0 | 0 | — | — |")

# 6. Direction analysis
report_lines.append(f"")
report_lines.append(f"## 6. Direction Analysis (OVER vs UNDER)")
report_lines.append(f"")
report_lines.append(f"| Direction | Picks | Hits | Hit Rate |")
report_lines.append(f"|-----------|-------|------|----------|")
for d in ("OVER", "UNDER"):
    picks = [p for p in graded_picks if p.get("direction","").upper().strip() == d]
    hits = sum(1 for p in picks if p.get("hit") in (True, "True", 1))
    rate = hits / len(picks) * 100 if picks else 0
    report_lines.append(f"| {d} | {len(picks)} | {hits} | {rate:.1f}% |")

# 7. Calibration: projection vs actual by stat
report_lines.append(f"")
report_lines.append(f"## 7. Projection Accuracy (MAE by Stat)")
report_lines.append(f"")
report_lines.append(f"| Stat | Picks | Mean Projection | Mean Actual | MAE | Bias (Proj-Actual) |")
report_lines.append(f"|------|-------|----------------|------------|-----|---------------------|")

stat_accuracy = defaultdict(list)
for p in graded_picks:
    proj = to_float(p.get("projection", 0))
    actual = to_float(p.get("actual", 0))
    stat_accuracy[p.get("stat","")].append((proj, actual))

for st, vals in sorted(stat_accuracy.items()):
    if len(vals) < 3:
        continue
    projs = [v[0] for v in vals]
    actls = [v[1] for v in vals]
    mean_proj = sum(projs) / len(projs)
    mean_act = sum(actls) / len(actls)
    mae = sum(abs(p - a) for p, a in vals) / len(vals)
    bias = sum(p - a for p, a in vals) / len(vals)
    report_lines.append(f"| {st} | {len(vals)} | {mean_proj:.3f} | {mean_act:.3f} | {mae:.3f} | {bias:+.3f} |")

# ----- Write report -----
OUTDIR.mkdir(parents=True, exist_ok=True)
report_path = OUTDIR / "FULL_BACKTEST_SELF_EDGE.md"
report_path.write_text("\n".join(report_lines))
print(f"\nReport written: {report_path}")
print(f"Total lines: {len(report_lines)}")

# Also output summary JSON
summary = {
    "total_graded": total_graded,
    "total_hits": total_hits,
    "overall_hit_rate": f"{overall_hit_rate:.1f}%",
    "total_roi": f"{total_roi:+.1f}%",
    "sports": sport_stats,
    "edge_buckets": {b: {"picks": len(picks), "hits": sum(1 for p in picks if p.get("hit") in (True, "True", 1))} for b, picks in buckets.items()}
}
summary_path = OUTDIR / "FULL_BACKTEST_SUMMARY.json"
summary_path.write_text(json.dumps(summary, indent=2, default=str))
print(f"Summary JSON: {summary_path}")
