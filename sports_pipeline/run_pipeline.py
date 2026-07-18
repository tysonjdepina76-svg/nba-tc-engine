#!/usr/bin/env python3
"""
Robust runner – calls pipeline with retries, health checks, auto-repair, alerts.
"""
import json
import time
import sys
import logging
from datetime import datetime

from pipeline import SportsPipeline
from storage import append_historical_record
from alert import send_alert
from health_check import run_all_checks, evaluate_status
from repair import run_repairs
from config import OUTPUT_FILE, MAX_RETRIES, BACKOFF_FACTOR

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("runner")


def run_with_retries():
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Attempt {attempt+1}/{MAX_RETRIES}")
            pipeline = SportsPipeline()
            result = pipeline.run()
            return True, result
        except Exception as e:
            logger.error(f"Attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                wait = BACKOFF_FACTOR ** attempt
                logger.info(f"Retry in {wait}s")
                time.sleep(wait)
    return False, None


def run_health_and_repair() -> str:
    """Run health check; if CRITICAL, attempt repair and re-check. Returns final status."""
    checks = run_all_checks()
    status = evaluate_status(checks)

    if status == "CRITICAL":
        logger.warning("CRITICAL health – attempting self-repair...")
        repair_report = run_repairs({
            "checks": {name: {"status": "PASS" if ok else "FAIL", "message": msg}
                       for name, (ok, msg) in checks.items()}
        })

        checks = run_all_checks()
        status = evaluate_status(checks)

        if status == "CRITICAL":
            send_alert("Self-repair failed – aborting pipeline.", "CRITICAL")
            return "CRITICAL"
        else:
            send_alert("Self-repair succeeded. Proceeding with pipeline.", "WARNING")
            return status

    return status


def main():
    logger.info("=" * 50)
    logger.info("Runner started")

    # Pre-run health check with auto-repair
    pre_status = run_health_and_repair()
    if pre_status == "CRITICAL":
        sys.exit(1)

    success, result = run_with_retries()

    if success and result:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(result, f, indent=2)

        try:
            run_id = append_historical_record(result)
            logger.info(f"Recorded to DB (run_id={run_id})")
        except Exception as e:
            logger.error(f"DB append failed: {e}")
            send_alert(f"DB append failed: {e}", "WARNING")

        # Post-run health
        post_checks = run_all_checks()
        post_status = evaluate_status(post_checks)
        if post_status != "OK":
            send_alert(f"Post-run health status {post_status}", "WARNING")

        logger.info("Pipeline run successful")
    else:
        send_alert("Pipeline failed after all retries", "CRITICAL")
        sys.exit(2)


if __name__ == "__main__":
    main()
