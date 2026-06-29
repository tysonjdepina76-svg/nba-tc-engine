"""Pipeline - ONE entry point. Replaces the 8 broken engines.

Run: python3 pipeline.py --mode daily
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from data_validator import gate_picks, gate_game_data
from circuit_breaker import CircuitBreakerRegistry
from health_check import get_health_check
from alert_deduper import get_deduper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("/home/workspace/tc-sports-app/logs/pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pipeline")


def load_picks_from_file(path: str) -> list:
    p = Path(path)
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def run_health_check() -> dict:
    logger.info("Running health check")
    health = get_health_check()
    report = health.run_full_check()
    logger.info(f"Health: {health.get_status_summary()}")
    if not health.should_alert(report):
        logger.info("No alert needed")
        return report
    deduper = get_deduper()
    for issue in report["issues"]:
        if issue["severity"] == "high":
            key = f"{issue['type']}:{','.join(issue.get('sources', []))}"
            suppressed = deduper.get_suppressed_count("health", key)
            logger.warning(f"ALERT: {issue} (suppressed duplicates: {suppressed})")
    return report


def run_daily(sport: str = None) -> dict:
    """Main daily entry point. Validates, gates, and reports."""
    logger.info(f"=== DAILY RUN START: {datetime.now().isoformat()} ===")
    health_report = run_health_check()
    breakers = CircuitBreakerRegistry.get_all_status()
    open_sources = [n for n, s in breakers.items() if s["state"] == "open"]
    if open_sources:
        logger.error(f"Aborting: open circuits = {open_sources}")
        return {"status": "aborted", "reason": "open_circuits", "open": open_sources}
    return {"status": "ready", "health": health_report, "timestamp": datetime.now().isoformat()}


def main():
    parser = argparse.ArgumentParser(description="TC Pipeline - single entry point")
    parser.add_argument("--mode", choices=["health", "daily", "validate"], default="health", help="Run mode")
    parser.add_argument("--sport", help="Sport filter (mlb, wnba, nba, etc.)")
    parser.add_argument("--input", help="Input file (JSON picks) for validate mode")
    args = parser.parse_args()
    if args.mode == "health":
        report = run_health_check()
        print(json.dumps(report, indent=2))
    elif args.mode == "daily":
        result = run_daily(args.sport)
        print(json.dumps(result, indent=2))
    elif args.mode == "validate":
        if not args.input:
            print("ERROR: --input required for validate mode")
            sys.exit(1)
        picks = load_picks_from_file(args.input)
        result = gate_picks(picks)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
