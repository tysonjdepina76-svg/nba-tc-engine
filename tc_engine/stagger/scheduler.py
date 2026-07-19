"""Scheduler — Cron wrapper with health checks for daily TC pipeline runs.

Runs daily_picks.py for each sport on schedule, logs results,
and checks pipeline health afterward. Can be run as a standalone process
or imported by the API.
"""
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

ENGINE_DIR = Path(__file__).parent.parent / "engine"
DAILY_LOG = Path("/home/workspace/Daily_Log")
HEALTH_FILE = Path("/home/workspace/health_status.json")

SPORTS = ["wnba", "mlb", "wc"]
SCHEDULE_HOUR = 1
SCHEDULE_MINUTE = 20

scheduler = BlockingScheduler()


def run_pipeline():
    timestamp = datetime.now().isoformat()
    results = {"mlb": 0, "wnba": 0, "wc": 0, "timestamp": timestamp, "status": "started"}

    for sport in SPORTS:
        try:
            result = subprocess.run(
                ["python3", str(ENGINE_DIR / "daily_picks.py"), "--sport", sport],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                results[sport] = _count_picks(sport)
            else:
                results[f"{sport}_error"] = result.stderr[:500]
        except subprocess.TimeoutExpired:
            results[f"{sport}_error"] = "timeout after 10 min"
        except Exception as e:
            results[f"{sport}_error"] = str(e)

    results["status"] = "completed"
    _save_run_results(results)
    _run_health_check()
    return results


def _count_picks(sport: str) -> int:
    import sqlite3
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    today = datetime.now(ET).strftime("%Y-%m-%d")
    picks_db = Path("/home/workspace/Projects/data/picks.db")

    if not picks_db.exists():
        return 0

    conn = sqlite3.connect(str(picks_db))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM picks WHERE date = ? AND league = ?", (today, sport.upper() if sport == "wc" else sport))
    count = c.fetchone()[0]
    conn.close()
    return count


def _save_run_results(results: dict):
    DAILY_LOG.mkdir(parents=True, exist_ok=True)
    last_run_path = DAILY_LOG / "last_run.json"

    last_run = {
        "last_run": results["timestamp"],
        "picks_count": sum(v for k, v in results.items() if k in SPORTS and isinstance(v, int)),
        "sports": {s: results.get(s, 0) for s in SPORTS if isinstance(results.get(s), int)},
        "status": results.get("status", "unknown"),
    }
    last_run_path.write_text(json.dumps(last_run, indent=2))


def _run_health_check():
    try:
        result = subprocess.run(
            ["python3", str(Path(__file__).parent.parent.parent / "sports_pipeline" / "health_check.py")],
            capture_output=True, text=True, timeout=30
        )
        HEALTH_FILE.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "output": result.stdout[:2000],
            "returncode": result.returncode,
        }, indent=2))
    except Exception:
        HEALTH_FILE.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "status": "health check failed"}))


def start():
    scheduler.add_job(run_pipeline, "cron", hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE,
                      id="tc_daily_pipeline", timezone="America/New_York")
    scheduler.start()


if __name__ == "__main__":
    start()
