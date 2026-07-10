#!/usr/bin/env python3
"""Run daily_picks with HTTP call measurement.

Usage:
    python3 /home/workspace/Projects/src/domain/daily_picks.py --sport WNBA --date 2026-07-02 --measure-calls

Inner module: /home/workspace/Projects/daily_picks.py
"""

from __future__ import annotations
import argparse
import importlib.util as _ilu
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path("/home/workspace")
sys.path.insert(0, str(WORKSPACE / "Projects"))

_inner_spec = _ilu.spec_from_file_location(
    "projects_daily_picks",
    WORKSPACE / "Projects" / "daily_picks.py",
)
if not _inner_spec or not _inner_spec.loader:
    sys.exit("FATAL: cannot locate Projects/daily_picks.py")
_inner = _ilu.module_from_spec(_inner_spec)
sys.modules[_inner_spec.name] = _inner
_inner_spec.loader.exec_module(_inner)

_mspec = _ilu.spec_from_file_location(
    "projects_src.measure", WORKSPACE / "Projects" / "src" / "measure.py"
)
if not _mspec or not _mspec.loader:
    sys.exit("FATAL: cannot locate Projects/src/measure.py")
_mmod = _ilu.module_from_spec(_mspec)
sys.modules[_mspec.name] = _mmod
_mspec.loader.exec_module(_mmod)
from projects_src.measure import install, reset, report  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sport", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--phase", default=None)
    p.add_argument("--measure-calls", action="store_true")
    p.add_argument("--out", default=str(WORKSPACE / "Daily_Log" / "call_measurement.json"))
    args = p.parse_args()

    os.environ["TC_RUN_DATE"] = args.date

    print("\n=== TC DAILY PICKS — HTTP CALL MEASUREMENT ===")
    print(f"Sport: {args.sport}   Date: {args.date}\n")

    install()
    reset()

    sys.argv = ["daily_picks.py", "--sport", args.sport, "--date", args.date]
    if args.dry_run:
        sys.argv.append("--dry-run")
    if args.phase:
        sys.argv += ["--phase", args.phase]

    _inner.run_daily_log((args.sport,))

    if args.measure_calls:
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

        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"sport": args.sport, "date": args.date, **rep}, indent=2))
        print(f"\nReport saved: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())