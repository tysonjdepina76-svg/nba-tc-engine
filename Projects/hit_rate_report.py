#!/usr/bin/env python3
"""Hit-Rate Report from Saved graded_picks.csv"""
import csv
from pathlib import Path
from collections import defaultdict

def generate_hit_rate_report(date="2026-07-11"):
    graded_file = Path(f"/home/workspace/Daily_Log/{date}/graded_picks.csv")

    if not graded_file.exists():
        print(f"No graded file at {graded_file}")
        return

    results = defaultdict(lambda: {"hits": 0, "misses": 0, "pending": 0})
    by_stat = defaultdict(lambda: {"hits": 0, "misses": 0, "pending": 0})
    by_dir = defaultdict(lambda: {"hits": 0, "misses": 0, "pending": 0})

    with open(graded_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            league = row.get("league", "UNKNOWN")
            result = row.get("result", "PENDING")
            stat = row.get("stat", "?")
            direction = row.get("direction", "?")

            if result == "H":
                results[league]["hits"] += 1
                by_stat[stat]["hits"] += 1
                by_dir[direction]["hits"] += 1
            elif result == "M":
                results[league]["misses"] += 1
                by_stat[stat]["misses"] += 1
                by_dir[direction]["misses"] += 1
            else:
                results[league]["pending"] += 1
                by_stat[stat]["pending"] += 1
                by_dir[direction]["pending"] += 1

    def show(label, store):
        print(f"\n--- BY {label} ---")
        print(f"{label:12} {'Hits':>6} {'Miss':>6} {'Pend':>6} {'Graded':>7} {'Acc':>7}")
        for k, v in sorted(store.items()):
            graded = v["hits"] + v["misses"]
            acc = (v["hits"] / graded * 100) if graded else 0
            print(f"{k:12} {v['hits']:>6} {v['misses']:>6} {v['pending']:>6} {graded:>7} {acc:>6.1f}%")

    print(f"=== HIT-RATE REPORT — {date} ===")
    show("LEAGUE", results)
    show("STAT", by_stat)
    show("DIRECTION", by_dir)

    total_h = sum(v["hits"] for v in results.values())
    total_m = sum(v["misses"] for v in results.values())
    total_p = sum(v["pending"] for v in results.values())
    graded = total_h + total_m
    print(f"\nOVERALL: {total_h}H / {total_m}M / {total_p} pending  |  {total_h} hits, accuracy {total_h/graded*100:.1f}%" if graded else f"\nOVERALL: {total_p} pending")

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-07-11"
    generate_hit_rate_report(d)
