#!/usr/bin/env python3
"""Run the MLB pipeline + alerts on a schedule."""
import logging
import schedule
import time

from src.adapters.mlb_pipeline import MLBPipeline
from alert_system import AlertSystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("mlb_pipeline.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("mlb_scheduler")


def run_pipeline() -> None:
    log.info("Starting MLB pipeline run")
    pipe = MLBPipeline("picks.csv")
    try:
        out = pipe.export_best_bets("best_bets_live.json")
        log.info("Found %d opportunities", out["total_games"])
        if out["total_games"] > 0:
            AlertSystem(threshold=-22.0).check_and_alert()
    except Exception as e:
        log.error("Pipeline failed: %s", e)
    finally:
        pipe.close()
    log.info("Pipeline run complete")


if __name__ == "__main__":
    log.info("MLB pipeline scheduler started")
    run_pipeline()
    schedule.every(30).minutes.do(run_pipeline)
    while True:
        schedule.run_pending()
        time.sleep(60)
