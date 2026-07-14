"""TC Math Calibration Analyzer.

Loads tc_math_hybrid.py + daily_picks outputs and backtests on 7/12 results
to produce a calibration report with suggested fixes.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/home/workspace/Projects")
from tc_math_hybrid import (
    SPORT_CONFIGS,
    over_under_signal_v1,
    over_under_signal_v2,
    apply_corrections,
    apply_ensemble,
    determine_pick,
)


def load_picks(date_str: str) -> list:
    p = Path(f"/home/workspace/Daily_Log/{date_str}/picks.csv")
    if not p.exists():
        return []
    with open(p) as f:
        return list(csv.DictReader(f))


def calibrate_threshold(date_str: str, thresholds: list) -> dict:
    picks = load_picks(date_str)
    out = {}
    for t in thresholds:
        graded = [p for p in picks if p.get("actual") and p.get("result") != "" and float(p.get("edge", 0)) >= t]
        hits = sum(1 for p in graded if p.get("result") == "HIT")
        out[t] = {
            "count": len(graded),
            "hits": hits,
            "hit_rate": (hits / len(graded) * 100) if graded else 0,
        }
    return out


def analyze_by_dim(date_str: str) -> dict:
    picks = load_picks(date_str)
    if not picks:
        return {}
    graded = [p for p in picks if p.get("actual") and p.get("result") in ("HIT", "MISS")]
    by_sport = defaultdict(lambda: {"total": 0, "hit": 0})
    by_signal = defaultdict(lambda: {"total": 0, "hit": 0})
    by_direction = defaultdict(lambda: {"total": 0, "hit": 0})
    by_stat = defaultdict(lambda: {"total": 0, "hit": 0})
    for p in graded:
        s = p.get("league", "?")
        sig = p.get("signal", "?")
        d = p.get("direction", "?")
        st = p.get("stat", "?")
        r = p.get("result")
        by_sport[s]["total"] += 1
        by_signal[sig]["total"] += 1
        by_direction[d]["total"] += 1
        by_stat[st]["total"] += 1
        if r == "HIT":
            by_sport[s]["hit"] += 1
            by_signal[sig]["hit"] += 1
            by_direction[d]["hit"] += 1
            by_stat[st]["hit"] += 1
    def fmt(d):
        return {k: {"total": v["total"], "hits": v["hit"], "rate_pct": round(v["hit"] / v["total"] * 100, 1) if v["total"] else 0} for k, v in d.items()}
    return {"by_sport": fmt(by_sport), "by_signal": fmt(by_signal), "by_direction": fmt(by_direction), "by_stat": fmt(by_stat)}


def compare_to_market(date_str: str) -> dict:
    picks = load_picks(date_str)
    out = {"over": {"total": 0, "hit": 0}, "under": {"total": 0, "hit": 0}, "avg_edge": []}
    for p in picks:
        if p.get("result") not in ("HIT", "MISS"):
            continue
        d = p.get("direction", "").lower()
        if d in out:
            out[d]["total"] += 1
            if p["result"] == "HIT":
                out[d]["hit"] += 1
        try:
            out["avg_edge"].append(float(p.get("edge", 0)))
        except Exception:
            pass
    out["avg_edge"] = round(sum(out["avg_edge"]) / len(out["avg_edge"]), 4) if out["avg_edge"] else 0
    for d in ("over", "under"):
        t = out[d]["total"]
        out[d]["rate_pct"] = round(out[d]["hit"] / t * 100, 1) if t else 0
    return out


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = "2026-07-12"
    print("=" * 70)
    print("TC MATH CALIBRATION REPORT")
    print("=" * 70)

    # 1. Threshold sweep
    print("\n[1] THRESHOLD SWEEP (graded picks only)")
    print("-" * 70)
    print(f"{'Min Edge':<12}{'Count':<8}{'Hits':<8}{'Hit Rate':<10}")
    ths = calibrate_threshold(yesterday, [0.005, 0.01, 0.02, 0.03, 0.05, 0.10])
    for t, v in ths.items():
        if v["count"] > 0:
            print(f"{t:<12}{v['count']:<8}{v['hits']:<8}{v['hit_rate']:.1f}%")

    # 2. Per-dimension breakdown
    print("\n[2] BREAKDOWN BY SPORT / SIGNAL / DIRECTION / STAT")
    print("-" * 70)
    breakdown = analyze_by_dim(yesterday)
    for k, v in breakdown.items():
        print(f"\n  {k}:")
        for label, stats in v.items():
            if stats["total"] > 0:
                print(f"    {label:<12} {stats['hits']}/{stats['total']}  {stats['rate_pct']}%")

    # 3. Over vs Under
    print("\n[3] OVER vs UNDER PERFORMANCE")
    print("-" * 70)
    ou = compare_to_market(yesterday)
    print(f"  OVER:  {ou['over']['hit']}/{ou['over']['total']}  {ou['over']['rate_pct']}%")
    print(f"  UNDER: {ou['under']['hit']}/{ou['under']['total']}  {ou['under']['rate_pct']}%")
    print(f"  Avg edge: {ou['avg_edge']*100:.2f}%")

    # 4. Suggested fixes
    print("\n[4] SUGGESTED FIXES")
    print("-" * 70)
    fixes = []
    if breakdown.get("by_signal", {}).get("WEAK", {}).get("total", 0) > 0:
        wk = breakdown["by_signal"]["WEAK"]
        if wk["rate_pct"] < 55:
            fixes.append(f"WEAK signal hit rate {wk['rate_pct']}% < 55% -> raise min_edge from 0.005 to 0.015")
    if ou["over"]["rate_pct"] and ou["under"]["rate_pct"]:
        if abs(ou["over"]["rate_pct"] - ou["under"]["rate_pct"]) > 10:
            side = "OVER" if ou["over"]["rate_pct"] > ou["under"]["rate_pct"] else "UNDER"
            fixes.append(f"Directional bias: {side} outperforms by >10% -> consider asymmetric shrinkage")
    for sport, stats in breakdown.get("by_sport", {}).items():
        if stats["total"] >= 5 and stats["rate_pct"] < 50:
            fixes.append(f"{sport} hit rate {stats['rate_pct']}% on {stats['total']} picks -> retune correction_factors")
    for stat, stats in breakdown.get("by_stat", {}).items():
        if stats["total"] >= 5 and stats["rate_pct"] < 45:
            fixes.append(f"Stat '{stat}' hit rate {stats['rate_pct']}% on {stats['total']} -> lower correction factor for {stat}")
    if not fixes:
        fixes.append("No major issues detected — system performing within tolerance")
    for i, f in enumerate(fixes, 1):
        print(f"  {i}. {f}")

    # 5. Save report
    out_dir = Path("/home/workspace/Projects/reports")
    out_dir.mkdir(exist_ok=True)
    out = {
        "generated_at": datetime.now().isoformat(),
        "date_analyzed": yesterday,
        "thresholds": ths,
        "breakdown": breakdown,
        "over_under": ou,
        "fixes": fixes,
    }
    out_file = out_dir / f"calibration_{today}.json"
    with open(out_file, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[SAVED] {out_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
