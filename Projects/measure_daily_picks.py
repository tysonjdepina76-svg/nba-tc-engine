"""Measure daily picks & odds movements across sports."""
import json
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.adapters.odds_api_adapter import OddsAPIAdapter  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def measure_daily_picks() -> None:
    adapter = OddsAPIAdapter()
    markets = [
        ("basketball", "usa-nba"),
        ("football", "usa-nfl"),
        ("baseball", "usa-mlb"),
    ]
    results: dict = {}
    for sport, league in markets:
        logger.info(f"Fetching {sport}/{league}")
        events = adapter.get_events(sport=sport, league=league, use_cache=False)
        bucket = {
            "total_events": len(events),
            "sample_odds": [],
            "quota_exhausted": adapter.quota_exhausted,
        }
        for event in events[:5]:
            odds = adapter.get_event_odds(event.get("id"), use_cache=False)
            bucket["sample_odds"].append(
                {
                    "event": f"{event.get('home_team')} vs {event.get('away_team')}",
                    "odds": odds,
                }
            )
        results[f"{sport}_{league}"] = bucket

    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"logs/measurement_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Measurement complete: {out_path}")
    adapter.close()


if __name__ == "__main__":
    measure_daily_picks()
