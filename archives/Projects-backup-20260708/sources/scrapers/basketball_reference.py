"""Basketball-Reference WNBA scraper.

Tier-3 fallback for WNBA player stats when ESPN/SportsData.io fail.
Returns per-game stats for the season.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
from bs4 import BeautifulSoup
import unicodedata
import re
from typing import List, Dict, Optional


def clean_name(name: str) -> str:
    if not name:
        return name
    return unicodedata.normalize("NFKC", name).strip()


class BasketballReferenceScraper:
    BASE_URL = "https://www.basketball-reference.com/wnba"

    def __init__(self, season: int = 2026):
        self.season = season
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def _fetch(self, path: str) -> Optional[BeautifulSoup]:
        url = f"{self.BASE_URL}{path}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"BR-WNBA fetch failed ({path}): {e}")
            return None

    def fetch_player_stats(self) -> List[Dict]:
        """Scrape WNBA player per-game stats for the season."""
        soup = self._fetch(f"/years/{self.season}_per_game.html")
        if not soup:
            return []
        table = soup.find("table", {"id": "per_game"})
        if not table or not table.find("tbody"):
            return []
        players: List[Dict] = []
        for row in table.find("tbody").find_all("tr"):
            # BR uses partial-table rows (league avg) with class="thead"
            classes = row.get("class", [])
            if "thead" in classes or "partial_table" in classes:
                continue
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            stat: Dict = {}
            for c in cells:
                ds = c.get("data-stat", "")
                val = c.get_text(strip=True)
                if not ds or not val:
                    continue
                stat[ds] = val
            if "player" not in stat:
                continue
            stat["name"] = clean_name(stat.pop("player", ""))
            # Convert numeric stat fields
            for k, v in list(stat.items()):
                if k in ("name", "team_name", "pos", "team_id"):
                    continue
                try:
                    stat[k] = float(v)
                except (ValueError, TypeError):
                    pass
            players.append(stat)
        return players


if __name__ == "__main__":
    import sys
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    s = BasketballReferenceScraper(season=season)
    stats = s.fetch_player_stats()
    print(f"Players: {len(stats)}")
    if stats:
        print(f"Sample: {stats[0]}")
        print(f"Top PTS: {sorted(stats, key=lambda p: p.get('pts_per_g', 0), reverse=True)[:3]}")
