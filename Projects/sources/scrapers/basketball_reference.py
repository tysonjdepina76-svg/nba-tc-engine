"""
Basketball-Reference scraper for WNBA stats fallback.
"""

import requests
from bs4 import BeautifulSoup
import unicodedata
from typing import List, Dict

class BasketballReferenceScraper:
    BASE_URL = "https://www.basketball-reference.com/wnba"
    def __init__(self, season: int = 2026):
        self.season = season
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    def _clean_name(self, name: str) -> str:
        if not name:
            return name
        return unicodedata.normalize('NFKC', name).strip()
    def _safe_float(self, val: str) -> float:
        try:
            return float(val.strip()) if val and val.strip() else 0.0
        except (ValueError, AttributeError):
            return 0.0
    def fetch_player_stats(self) -> List[Dict]:
        url = f"{self.BASE_URL}/players/{self.season}/per_game.html"
        resp = requests.get(url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "players"})
        if not table:
            return []
        rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")
        players = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 10:
                continue
            player = {
                "name": self._clean_name(cells[0].text),
                "team": cells[1].text.strip() if len(cells) > 1 else "",
                "pts": self._safe_float(cells[2].text) if len(cells) > 2 else 0.0,
                "reb": self._safe_float(cells[3].text) if len(cells) > 3 else 0.0,
                "ast": self._safe_float(cells[4].text) if len(cells) > 4 else 0.0,
                "fg_pct": self._safe_float(cells[5].text) if len(cells) > 5 else 0.0,
                "fg3": self._safe_float(cells[6].text) if len(cells) > 6 else 0.0,
                "stl": self._safe_float(cells[7].text) if len(cells) > 7 else 0.0,
                "blk": self._safe_float(cells[8].text) if len(cells) > 8 else 0.0,
            }
            players.append(player)
        return players
