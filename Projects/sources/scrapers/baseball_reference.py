"""
Baseball-Reference scraper for MLB stats fallback.
"""

import requests
from bs4 import BeautifulSoup
import unicodedata
from typing import List, Dict

class BaseballReferenceScraper:
    BASE_URL = "https://www.baseball-reference.com"
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
    def _safe_int(self, val: str) -> int:
        try:
            return int(val.strip()) if val and val.strip() else 0
        except (ValueError, AttributeError):
            return 0
    def fetch_batting(self) -> List[Dict]:
        url = f"{self.BASE_URL}/leagues/MLB/{self.season}-batting.shtml"
        resp = requests.get(url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "batting"})
        if not table:
            return []
        rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")
        players = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue
            player = {
                "name": self._clean_name(cells[0].text),
                "team": cells[1].text.strip() if len(cells) > 1 else "",
                "avg": self._safe_float(cells[2].text),
                "hr": self._safe_int(cells[4].text) if len(cells) > 4 else 0,
                "rbi": self._safe_int(cells[5].text) if len(cells) > 5 else 0,
                "r": self._safe_int(cells[6].text) if len(cells) > 6 else 0,
                "sb": self._safe_int(cells[7].text) if len(cells) > 7 else 0,
                "ops": self._safe_float(cells[8].text) if len(cells) > 8 else 0.0,
            }
            players.append(player)
        return players
    def fetch_pitching(self) -> List[Dict]:
        url = f"{self.BASE_URL}/leagues/MLB/{self.season}-pitching.shtml"
        resp = requests.get(url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "pitching"})
        if not table:
            return []
        rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")
        pitchers = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            pitcher = {
                "name": self._clean_name(cells[0].text),
                "team": cells[1].text.strip() if len(cells) > 1 else "",
                "era": self._safe_float(cells[3].text) if len(cells) > 3 else 0.0,
                "whip": self._safe_float(cells[4].text) if len(cells) > 4 else 0.0,
                "so": self._safe_int(cells[5].text) if len(cells) > 5 else 0,
            }
            pitchers.append(pitcher)
        return pitchers
