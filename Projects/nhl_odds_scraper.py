#!/usr/bin/env python3
"""NHL Odds Scraper — TheOddsAPI integration"""

from wnba_odds_scraper import main as wnba_main
import sys

if __name__ == "__main__":
    sys.argv.append("--sport")
    sys.argv.append("icehockey_nhl")
    wnba_main()
