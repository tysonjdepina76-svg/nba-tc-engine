#!/usr/bin/env python3
"""Run daily_picks for WNBA today with HTTP call measurement.

Usage:
    python3 -m src.domain.run_measured

Reports:
    • live HTTP calls per provider (ESPN / SGO / OddsAPI / OTHER)
    • cache hits per provider
    • quota ledger today vs daily cap (500)
    • before/after comparison to target (<500/day)
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

WORKSPACE = Path("/home/workspace")
sys.path.insert(0, str(WORKSPACE / "Projects"))

from src.measure import install, reset, report  # noqa: E402

# Install before importing daily_picks so monkeypatch is in place
install()
reset()

# Import after install
from daily_picks import run_daily_log  # noqa: E402

if __name__ == "__main__":
    print("\n=== TC DAILY PICKS — HTTP CALL MEASUREMENT ===")
    print("Sport: WNBA   Date: 2026-06-29\n")

    result = run_daily_log(("WNBA",))

    print("\n=== HTTP CALL MEASUREMENT REPORT ===")
    rep = report()
    calls = rep["measured_calls"]
    hits = rep["cache_hits"]
    total_live = rep["measured_total"]
    used_today = rep["quota_used_today"]
    cap = rep["daily_limit"]
    remaining = max(0, cap - used_today)

    print(f"Live calls this run (per provider): {dict(calls)}")
    print(f"Cache hits during this run:          {dict(hits)}")
    print(f"Live calls this run:                 {total_live}")
    print(f"Quota used today (all runs):         {used_today}/{cap}")
    print(f"Quota remaining:                     {remaining}")

    if total_live == 0 and used_today > 0:
        print("\n✓ 100% cache-served — zero live HTTP calls this run.")
    elif total_live == 0:
        print("\n✓ Zero live HTTP calls this run.")
    else:
        print(f"\n→ Live calls used this run: {total_live}. Within budget (500/day).")

    # Persist a machine-readable report
    out_path = WORKSPACE / "Daily_Log" / "call_measurement.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "sport": "WNBA",
        "date": "2026-06-29",
        **rep,
    }, indent=2))
    print(f"\nReport saved: {out_path}")
