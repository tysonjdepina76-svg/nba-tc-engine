#!/usr/bin/env python3
"""World Cup Odds Scraper — reuses the generic WNBA odds scraper plumbing.

We import the WNBAOddsScraper class directly (not its `main()` entrypoint)
to avoid recursive re-entry from this module's own `__main__` block. The
scraper already accepts a sport key via the Odds API, so we just pass
`soccer_world_cup` (or `soccer_fifa_world_cup`).
"""

import sys
import argparse
from wnba_odds_scraper import WNBAOddsScraper
from pathlib import Path

OUTPUT_DIR = Path("/home/workspace/Daily_Log")

def fetch_wc_odds(date=None, sport_key: str = "soccer_world_cup"):
    scraper = WNBAOddsScraper()
    odds = scraper.get_odds(sport_key=sport_key, date=date)
    if not odds:
        print(f"No odds for {sport_key} on {date or 'today'}")
        return []
    df = scraper.parse_odds(odds)
    if df is None or df.empty:
        print(f"No parseable WC odds rows for {date or 'today'}")
        return []
    out_dir = OUTPUT_DIR / (date or scraper._today_iso())
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wc_odds_live.json"
    df.to_json(out_path, orient="records", indent=2)
    print(f"Saved {len(df)} WC odds rows → {out_path}")
    return df.to_dict(orient="records")

def main():
    p = argparse.ArgumentParser(description="World Cup odds scraper")
    p.add_argument("date", nargs="?", default=None)
    p.add_argument("--sport", default="soccer_world_cup",
                   help="Odds API sport key (default: soccer_world_cup)")
    args = p.parse_args()
    fetch_wc_odds(date=args.date, sport_key=args.sport)

if __name__ == "__main__":
    main()
