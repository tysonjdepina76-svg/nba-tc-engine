#!/usr/bin/env python3
"""
Daily picks runner for TC Sports App.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.daily_picks import generate_daily_picks
from sources.utils.logging import setup_logging

logger = setup_logging()

def main():
    sports = ["mlb", "wnba", "wc", "nfl", "nhl", "ncaa"]
    for sport in sports:
        try:
            logger.info(f"Generating picks for {sport}...")
            result = generate_daily_picks(sport)
            logger.info(f"{sport}: {result.get('count', 0)} picks")
        except Exception as e:
            logger.error(f"{sport} failed: {e}")

if __name__ == "__main__":
    main()
