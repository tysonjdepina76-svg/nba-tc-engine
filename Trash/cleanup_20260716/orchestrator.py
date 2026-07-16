#!/usr/bin/env python3
"""TC Pipeline orchestrator.

Runs the full daily workflow end-to-end:
  1. Scan for missing files and broken imports
  2. Generate picks (WNBA / MLB / WC)
  3. Build combos and consensus
  4. Optionally settle completed games
  5. Push fresh CSV/JSON to the dashboard

Usage:
  python3 orchestrator.py                  # full run
  python3 orchestrator.py --scan-only      # just scan, no picks
  python3 orchestrator.py --settle         # include settlement pass
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path("/home/workspace/Projects")
LOG_ROOT = Path("/home/workspace/Daily_Log")
LOG_FILE = PROJECT_ROOT / "logs" / "orchestrator.log"
SPORT_ALIASES = {"wnba", "mlb", "wc"}

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def step_scan() -> dict:
    """Delegate to scan.py and parse its summary."""
    _log("STEP 1: scan")
    out = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scan.py")],
        capture_output=True, text=True
    )
    summary = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "no output"
    _log(f"scan result: {summary}")
    return {"stdout": out.stdout, "stderr": out.stderr, "returncode": out.returncode}


def step_picks(sports: list[str], log_date: str) -> dict:
    """Run daily_picks.py for each sport."""
    _log(f"STEP 2: picks for {sports} on {log_date}")
    results = {}
    for sport in sports:
        cmd = [sys.executable, str(PROJECT_ROOT / "daily_picks.py"),
               "--sport", sport, "--date", log_date]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        results[sport] = {
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout.strip().splitlines()[-3:],
            "stderr_tail": proc.stderr.strip().splitlines()[-3:],
        }
        _log(f"  {sport}: rc={proc.returncode} last={results[sport]['stdout_tail']}")
    return results


def step_combos(log_date: str) -> dict:
    """Build combos/consensus if a helper script exists."""
    _log("STEP 3: combos + consensus")
    combos_script = PROJECT_ROOT / "build_pregame_combos.py"
    if not combos_script.exists():
        return {"skipped": "build_pregame_combos.py missing"}
    proc = subprocess.run(
        [sys.executable, str(combos_script), "--date", log_date],
        capture_output=True, text=True
    )
    return {"returncode": proc.returncode, "tail": proc.stdout.strip().splitlines()[-3:]}


def step_settle(log_date: str) -> dict:
    """Run settlement if a script exists."""
    _log("STEP 4: settlement")
    settle = PROJECT_ROOT / "run_settlement.py"
    if not settle.exists():
        return {"skipped": "run_settlement.py missing"}
    proc = subprocess.run(
        [sys.executable, str(settle), "--date", log_date],
        capture_output=True, text=True
    )
    return {"returncode": proc.returncode, "tail": proc.stdout.strip().splitlines()[-3:]}


def step_push(log_date: str) -> dict:
    """Mirror fresh picks.csv into the dashboard folder."""
    _log("STEP 5: push to dashboard")
    src = LOG_ROOT / log_date / "picks.csv"
    dst_dir = Path("/home/workspace/sports_betting_dashboard/data")
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "picks.csv"
    if not src.exists():
        return {"skipped": "no picks.csv to push"}
    dst.write_text(src.read_text())
    return {"pushed_bytes": dst.stat().st_size, "src": str(src), "dst": str(dst)}


def main() -> int:
    ap = argparse.ArgumentParser(description="TC pipeline orchestrator")
    ap.add_argument("--scan-only", action="store_true")
    ap.add_argument("--settle", action="store_true")
    ap.add_argument("--sport", default="all", choices=["wnba", "mlb", "wc", "all"])
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    _log(f"=== orchestrator start (scan_only={args.scan_only}, settle={args.settle}) ===")

    scan = step_scan()
    if args.scan_only:
        return scan["returncode"]

    sports = ["wnba", "mlb", "wc"] if args.sport == "all" else [args.sport]
    picks = step_picks(sports, args.date)
    combos = step_combos(args.date)
    settle = step_settle(args.date) if args.settle else {"skipped": "not requested"}
    push = step_push(args.date)

    summary = {
        "date": args.date,
        "scan_rc": scan["returncode"],
        "picks": picks,
        "combos": combos,
        "settle": settle,
        "push": push,
    }
    summary_path = LOG_ROOT / args.date / "orchestrator_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    _log(f"summary written to {summary_path}")
    _log("=== orchestrator done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
