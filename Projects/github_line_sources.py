#!/usr/bin/env python3
"""GitHub-sourced line enricher — oddsScraper + espn_scraper integration.

Sources:
  - espn_scraper (andr3w321): ESPN boxscores, rosters, game data
  - oddsScraper (actNetScrape/fdScrape/unabatScrape): Action Network, FanDuel, Unabated

Status:
  - ESPN v2 API (game-level odds): WORKING — spread, OU, ML via espn_odds_scraper.py
  - ESPN Core API (player stats): WORKING — projections enrichment
  - oddsScraper modules: Selenium-dependent — desktop-only, NOT available on Zo server
  - Action Network API: 403 CloudFront — requires browser rendering
  - DraftKings API: Access Denied — WAF blocks non-browser requests
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger("github_sources")


def get_available_sources() -> Dict[str, Dict[str, str]]:
    """Return status of all available line sources."""
    return {
        "espn_v2_odds": {
            "status": "live",
            "sports": ["wnba", "mlb"],
            "data": "spread, over/under, moneyline (game-level only, no player props)",
            "module": "espn_odds_scraper.py",
        },
        "espn_core_stats": {
            "status": "live",
            "sports": ["wnba", "mlb"],
            "data": "player stats, rosters, boxscores",
            "module": "espn_scraper (github: andr3w321)",
        },
        "action_network_props": {
            "status": "offline",
            "reason": "CloudFront 403 — requires Selenium browser",
            "sports": ["wnba", "mlb"],
            "data": "player props (PTS/REB/AST/3PT for WNBA, K/H/HR/RBI for MLB)",
            "module": "oddsScraper/actNetScrape.py",
        },
        "fanduel_props": {
            "status": "offline",
            "reason": "Requires Selenium/Firefox — desktop-only",
            "sports": ["wnba"],
            "data": "player props",
            "module": "oddsScraper/fdScrape.py",
        },
        "unabated_props": {
            "status": "offline",
            "reason": "Requires Selenium/Firefox — desktop-only",
            "sports": ["wnba"],
            "data": "player props",
            "module": "oddsScraper/unabatScrape.py",
        },
        "serpapi_search": {
            "status": "live",
            "sports": ["wnba", "mlb"],
            "data": "player prop lines via Google search snippets",
            "module": "serp_odds_scraper.py",
            "quota": "253 calls/day (SerpAPI plan limit)",
        },
    }


def enrich_with_espn_v2(sport: str, projections: List[Dict]) -> List[Dict]:
    """Enrich projections with ESPN v2 game-level odds (spread/OU/ML).
    
    This gives context lines — what the game spread is, the over/under,
    and moneyline pricing. Useful for evaluating TC edge against market.
    """
    try:
        from espn_odds_scraper import fetch_espn_v2_odds
    except ImportError:
        logger.warning("espn_odds_scraper not available")
        return projections
    
    odds_map = fetch_espn_v2_odds(sport)
    if not odds_map:
        logger.info(f"No ESPN v2 game odds for {sport}")
        return projections
    
    enriched = 0
    for proj in projections:
        event_id = str(proj.get("event_id", ""))
        if event_id in odds_map:
            proj["game_odds"] = odds_map[event_id]
            enriched += 1
    
    logger.info(f"ESPN v2 enriched {enriched}/{len(projections)} with game odds for {sport}")
    return projections


def check_selenium_availability() -> bool:
    """Check if Selenium + browser are available for oddsScraper modules."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        return True
    except ImportError:
        return False


def source_report() -> str:
    """Generate a human-readable source availability report."""
    sources = get_available_sources()
    lines = []
    lines.append("=" * 60)
    lines.append("LINE SOURCE STATUS")
    lines.append("=" * 60)
    
    for name, info in sources.items():
        status_icon = "✓" if info["status"] == "live" else "✗"
        lines.append(f"\n{status_icon} {name}")
        lines.append(f"   Status:  {info['status'].upper()}")
        lines.append(f"   Sports:  {', '.join(info['sports'])}")
        lines.append(f"   Data:    {info['data']}")
        lines.append(f"   Module:  {info['module']}")
        if "reason" in info:
            lines.append(f"   Why:     {info['reason']}")
        if "quota" in info:
            lines.append(f"   Quota:   {info['quota']}")
    
    lines.append(f"\n{'=' * 60}")
    lines.append(f"ACTIVE: 3 sources (ESPN v2, ESPN Core, SerpAPI)")
    lines.append(f"BLOCKED: 3 sources (Action Network, FanDuel, Unabated)")
    lines.append(f"  — All require Selenium browser (not available on headless Zo server)")
    lines.append(f"  — Can be run from user's local machine with Python + Firefox/Chrome")
    lines.append(f"{'=' * 60}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    print(source_report())
    
    sel_available = check_selenium_availability()
    print(f"\nSelenium available on this machine: {sel_available}")
    
    if not sel_available:
        print("\nTo use oddsScraper modules locally:")
        print("  pip install selenium webdriver-manager")
        print("  cd Projects/oddsScraper")
        print("  python3 script/actNetScrape.py  # Action Network props")
        print("  python3 script/fdScrape.py       # FanDuel props")
        print("  python3 script/unabatScrape.py   # Unabated props")
