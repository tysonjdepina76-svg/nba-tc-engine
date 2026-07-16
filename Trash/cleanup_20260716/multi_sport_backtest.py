#!/usr/bin/env python3
"""Multi-sport backtest — consolidates real graded pick data into reports/backtest_report.json.

Inputs:
  - Daily_Log/2026-06-13/boxscore_graded.csv (WNBA, 45 graded)
  - Reports/wc_picks_graded_20260615.csv (World Cup, 180 graded)
  - Daily_Log/backtests/30day/30day_hitrates.csv (mixed)

Outputs:
  - reports/backtest_report.json (per-sport hit rate, avg edge, ROI)
  - reports/backtest_report.md (consolidated)

ROI assumes -110 odds ($100 risk wins $91.91). Override per-sport if known.
"""
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean

WORKSPACE = Path("/home/workspace")
REPORTS = WORKSPACE / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)


def grade_wnba_6_13():
    """WNBA 2026-06-13 graded picks (45 rows incl 6 NOT_FOUND)."""
    out = []
    p = WORKSPACE / "Daily_Log/2026-06-13/boxscore_graded.csv"
    if not p.exists():
        return out
    for row in csv.DictReader(open(p)):
        result = row["result"]
        edge = float(row["edge"]) if row.get("edge") else None
        ml = float(row["market_line"]) if row.get("market_line") else None
        out.append({
            "date": row["date"],
            "sport": "WNBA",
            "matchup": row["matchup"],
            "player": row["player"],
            "stat": row["stat"],
            "direction": row["direction"],
            "market_line": ml,
            "edge": edge,
            "actual": row.get("actual"),
            "result": result,
        })
    return out


def grade_wc_6_15():
    """World Cup 2026-06-15 graded picks (180 rows)."""
    out = []
    p = WORKSPACE / "Reports/wc_picks_graded_20260615.csv"
    if not p.exists():
        return out
    for row in csv.DictReader(open(p)):
        try:
            line = float(row["line"]) if row.get("line") else None
        except ValueError:
            line = None
        try:
            odds = float(row["odds"]) if row.get("odds") else None
        except ValueError:
            odds = None
        out.append({
            "date": str(row["date"])[:10],
            "sport": "SOCCER",
            "matchup": row["matchup"],
            "player": row["player"],
            "stat": row["stat"],
            "direction": row["stat_key"],  # not exact, used as proxy
            "market_line": line,
            "odds": odds,
            "actual": row.get("actual"),
            "result": row["result"],
        })
    return out


def grade_30day():
    """30-day rollup — only summary stats available, no per-pick rows."""
    # Source CSV has category-level aggregates, not individual picks
    # so we can't put them in by_sport rollup; just count as detail.
    return []


def grade_mlb_sf_atl():
    """MLB SF@ATL 2026-06-18 — picks have lines but no boxscore captured (PENDING)."""
    out = []
    p = WORKSPACE / "data/historical/mlb/2025/2026-06-18/picks.csv"
    if not p.exists():
        return out
    for row in csv.DictReader(open(p)):
        try:
            ml = float(row["market_line"]) if row.get("market_line") else None
        except ValueError:
            ml = None
        try:
            edge = float(row["edge"]) if row.get("edge") else None
        except ValueError:
            edge = None
        out.append({
            "date": row["date"],
            "sport": "MLB",
            "matchup": row["matchup"],
            "player": row["player"],
            "stat": row["stat"],
            "direction": row["direction"],
            "market_line": ml,
            "edge": edge,
            "actual": row.get("actual"),
            "result": row.get("result", "PENDING"),
        })
    return out


def summarize(rows, sport):
    """Compute aggregate stats for a list of pick rows."""
    completed = [r for r in rows if r.get("result") in ("HIT", "H", "MISS", "M")]
    hits = sum(1 for r in completed if r["result"] in ("HIT", "H"))
    misses = sum(1 for r in completed if r["result"] in ("MISS", "M"))
    pushes = sum(1 for r in rows if r.get("result") == "PUSH")
    total = len(rows)
    graded = len(completed)

    if graded == 0:
        hit_rate = None
    else:
        hit_rate = round(hits / graded * 100, 1)

    edges = [r["edge"] for r in rows if r.get("edge") is not None]
    avg_edge = round(mean(edges), 2) if edges else None

    # ROI at -110: hit pays +91.91, miss loses 100, push returns stake
    wagered = graded * 100
    payout = hits * 91.91
    roi_pct = round((payout - wagered) / wagered * 100, 1) if wagered > 0 else None

    return {
        "picks": total,
        "graded": graded,
        "hits": hits,
        "misses": misses,
        "pushes": pushes,
        "hit_rate_pct": hit_rate,
        "avg_edge": avg_edge,
        "roi_pct": roi_pct,
        "wagered_usd": wagered,
        "payout_usd": round(payout, 2),
        "profit_usd": round(payout - wagered, 2),
    }


def main():
    sections = []
    sections.append(("WNBA — 2026-06-13 (39 graded)", grade_wnba_6_13(), "WNBA"))
    sections.append(("World Cup — 2026-06-15 (180 graded)", grade_wc_6_15(), "SOCCER"))
    sections.append(("MLB SF@ATL — 2026-06-18 (39 picks, all PENDING)", grade_mlb_sf_atl(), "MLB"))

    out = {
        "generated_at": "2026-06-30",
        "total_picks": 0,
        "by_sport": {},
        "details": {},
    }

    all_rows = []
    for label, rows, _ in sections:
        all_rows.extend(rows)
        out["details"][label] = summarize(rows, label)

    out["total_picks"] = len(all_rows)

    # By-sport rollup
    by_sport = defaultdict(list)
    for r in all_rows:
        by_sport[r["sport"]].append(r)

    all_sports = list(by_sport.keys()) + ["ALL"]
    for sport in all_sports:
        rows = by_sport.get(sport, [])
        if sport == "ALL":
            rows = all_rows
        if not rows:
            continue
        out["by_sport"][sport] = summarize(rows, sport)

    json_path = REPORTS / "backtest_report.json"
    json_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {json_path}", flush=True)


if __name__ == "__main__":
    main()
