#!/usr/bin/env python3
"""NBA Odds Scraper — TheOddsAPI integration"""

from wnba_odds_scraper import main as wnba_main
import sys

if __name__ == "__main__":
    sys.argv.append("--sport")
    sys.argv.append("basketball_nba")
    wnba_main()
