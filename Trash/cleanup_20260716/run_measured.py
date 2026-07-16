#!/usr/bin/env python3
"""Run measured: timed pipeline execution with per-stage metrics."""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime

DAILY = Path("/home/workspace/Daily_Log")
PROJECTS = Path("/home/workspace/Projects")


def stage(name, fn):
    t0 = time.time()
    print(f"[{name}] starting...")
    try:
        result = fn()
        dt = time.time() - t0
        print(f"[{name}] OK in {dt:.2f}s")
        return {"name": name, "ok": True, "secs": round(dt, 2), "result": result}
    except Exception as e:
        dt = time.time() - t0
        print(f"[{name}] FAILED in {dt:.2f}s: {e}")
        return {"name": name, "ok": False, "secs": round(dt, 2), "error": str(e)}


def run_daily_picks(sport):
    import subprocess
    out = subprocess.run(
        [sys.executable, "daily_picks.py", "--sport", sport, "--date", datetime.now().strftime("%Y-%m-%d")],
        cwd=str(PROJECTS), capture_output=True, text=True, timeout=300
    )
    return {"returncode": out.returncode, "lines": out.stdout.count("\n")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sport", default="all")
    args = p.parse_args()

    sports = ["WNBA", "MLB", "WORLD_CUP"] if args.sport == "all" else [args.sport.upper()]
    print("=" * 60)
    print("MEASURED PIPELINE RUN")
    print(f"  sports: {sports}")
    print(f"  {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 60)

    metrics = []
    for sport in sports:
        m = stage(f"daily_picks[{sport}]", lambda s=sport: run_daily_picks(s))
        metrics.append(m)

    total_secs = sum(m["secs"] for m in metrics)
    ok = sum(1 for m in metrics if m["ok"])
    print("=" * 60)
    print(f"SUMMARY: {ok}/{len(metrics)} ok in {total_secs:.2f}s")
    out = DAILY / datetime.now().strftime("%Y-%m-%d") / "run_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "metrics": metrics}, indent=2))
    print(f"  metrics: {out}")


if __name__ == "__main__":
    main()
