import json
import time
import sys
import logging
from datetime import datetime

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from daily_picks import generate_picks
DB_PATH = None  # handled by daily_picks
from pipeline.health_check import main as health_main
from pipeline.repair import run_repairs, REPAIR_MAP
from pipeline.alert import send_alert
from pipeline.config import MAX_RETRIES, BACKOFF_FACTOR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("runner")


def run_pipeline_with_retries(sports: list) -> tuple:
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Attempt {attempt + 1}/{MAX_RETRIES}")
            results = {}
            for sport in sports:
                picks = generate_picks(sport)
                results[sport] = len(picks)
            return True, results
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                wait = BACKOFF_FACTOR ** attempt
                logger.info(f"Retrying in {wait}s")
                time.sleep(wait)
    return False, None


def main():
    logger.info("=" * 50)
    logger.info(f"Runner started at {datetime.now().isoformat()}")

    health_exit = health_main()
    if health_exit == 2:
        logger.warning("CRITICAL health. Attempting self-repair.")
        from pipeline.health_check import run_health_checks
        checks = run_health_checks()
        repair_report = run_repairs({
            "checks": {
                name: {"status": "PASS" if ok else "FAIL", "message": msg}
                for name, (ok, msg) in checks.items()
            }
        })
        health_exit = health_main()
        if health_exit == 2:
            send_alert("Self-repair failed. Aborting pipeline.", "CRITICAL")
            sys.exit(1)
        else:
            send_alert("Self-repair succeeded. Proceeding.", "WARNING")

    sports = ["mlb", "wnba", "wc"]
    success, results = run_pipeline_with_retries(sports)

    if success and results:
        total = sum(results.values())
        logger.info(f"Pipeline complete: {total} picks ({results})")
        send_alert(f"Pipeline ran: {total} picks. {results}", "INFO")

        post_exit = health_main()
        if post_exit != 0:
            send_alert(f"Post-run health: {post_exit}", "WARNING")
    else:
        send_alert("Pipeline failed after all retries.", "CRITICAL")
        sys.exit(2)


if __name__ == "__main__":
    main()
