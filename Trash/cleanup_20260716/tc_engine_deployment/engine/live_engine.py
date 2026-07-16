#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/workspace/Projects")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://tc_engine:tc_engine_dev@postgres:5432/tc_picks")

STAGGER_SECONDS = int(os.environ.get("STAGGER_SECONDS", "600"))
SPORTS = ["wnba", "mlb"]


def run_pipeline(sport: str) -> dict:
    result = {"sport": sport, "status": "ok", "picks": 0, "error": None}
    try:
        proc = subprocess.run(
            ["python3", "/app/daily_picks.py", "--sport", sport, "--date", datetime.now(timezone.utc).strftime("%Y-%m-%d")],
            capture_output=True, text=True, timeout=300, cwd="/home/workspace/Projects"
        )
        result["stdout"] = proc.stdout[-500:]
        if proc.returncode != 0:
            result["status"] = "failed"
            result["error"] = proc.stderr[-500:]
        else:
            for line in proc.stdout.split("\n"):
                if "picks" in line.lower() and "total" in line.lower():
                    result["output_line"] = line.strip()
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def grade_recent():
    try:
        proc = subprocess.run(
            ["python3", "/app/grade_picks.py"],
            capture_output=True, text=True, timeout=120, cwd="/home/workspace/Projects"
        )
        return {"status": "ok" if proc.returncode == 0 else "failed", "output": proc.stdout[-300:]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] TC Live Engine started")
    print(f"  SPORTS: {SPORTS}")
    print(f"  STAGGER: {STAGGER_SECONDS}s between sports")

    while True:
        print(f"\n--- CYCLE START: {datetime.now(timezone.utc).isoformat()} ---")

        for i, sport in enumerate(SPORTS):
            result = run_pipeline(sport)
            status_icon = "OK" if result["status"] == "ok" else "FAIL"
            print(f"  [{status_icon}] {sport.upper()}: {result.get('output_line', result.get('error', ''))}")

            grade_result = grade_recent()
            print(f"  [GRADE] {grade_result['status']}")

            time.sleep(STAGGER_SECONDS)

        print(f"--- CYCLE END: {datetime.now(timezone.utc).isoformat()} ---")
        time.sleep(STAGGER_SECONDS * 2)


if __name__ == "__main__":
    main()
