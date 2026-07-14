#!/usr/bin/env python3
"""scheduler.py — In-process scheduler for daily tasks (no cron).

Runs daily pipeline at 8:00 AM and health check at 9:00 AM local time.
Each run is one-shot per day (tracked by date). Loops every 30s.
"""

import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/home/workspace/Projects/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "scheduler.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

PROJECTS = Path("/home/workspace/Projects")


def run_pipeline():
    logger.info("Running daily pipeline...")
    try:
        r = subprocess.run(
            ["python3", "run.py", "--all-sports", "--show-positions", "--settle"],
            cwd=str(PROJECTS),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if r.returncode == 0:
            logger.info("Pipeline complete")
        else:
            logger.error(f"Pipeline returned {r.returncode}: {r.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        logger.error("Pipeline timed out after 300s")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")


def run_health_check():
    logger.info("Running health check...")
    try:
        r = subprocess.run(
            ["python3", "health_check.py"],
            cwd=str(PROJECTS),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            logger.info("Health check complete")
        else:
            logger.error(f"Health check returned {r.returncode}: {r.stderr[-500:]}")
    except Exception as e:
        logger.error(f"Health check failed: {e}")


def scheduler_loop():
    logger.info("Scheduler started. Pipeline at 8:00 AM, Health check at 9:00 AM.")
    last_pipeline = None
    last_health = None

    while True:
        now = datetime.now()
        today = now.date()

        if now.hour == 8 and now.minute == 0 and last_pipeline != today:
            run_pipeline()
            last_pipeline = today

        if now.hour == 9 and now.minute == 0 and last_health != today:
            run_health_check()
            last_health = today

        time.sleep(30)


if __name__ == "__main__":
    scheduler_loop()
