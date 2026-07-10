"""Baseball-Reference scraper for MLB batting/pitching leaderboards.

Used as a tier-3 fallback for player stats when paid APIs are down.

BR's leaderboard structure: each stat has its own div (e.g. #leaderboard_batting_WAR)
containing ranked rows with .rank / .who / .value spans. We scrape multiple
stat divs and join them by player name to reconstruct a season profile.

Note: BR's HTML is wrapped inside comments and uses divs, not standard <table><tr><td>.
We follow redirects and parse the div grid structure.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
from bs4 import BeautifulSoup
import re
import unicodedata
from typing import List, Dict, Optional


def clean_name(name: str) -> str:
    """Normalize and fix common mojibake (e.g. 'SÃ¡nchez' -> 'Sánchez').

    BR serves UTF-8 but the default BS4 html.parser sometimes double-encodes
    accented characters. NFKC normalization + latin1->utf-8 round-trip
    recovers the original glyphs.
    """
    if not name:
        return name
    try:
        return unicodedata.normalize("NFKC", name).encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Already clean or unfixable — return as-is
        return name


class BaseballReferenceScraper:
    BASE_URL = "https://www.baseball-reference.com"

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
            resp.encoding = "utf-8"  # force UTF-8 to prevent mojibake on accented names
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"BR fetch failed ({path}): {e}")
            return None

    def _parse_leaderboard_div(self, div_id: str, stat_key: str) -> Dict[str, float]:
        """Parse a single BR leaderboard div. Returns {player_name: value}."""
        soup = self._fetch(f"/leagues/majors/{self.season}-batting-leaders.shtml")
        if not soup:
            return {}
        div = soup.find("div", {"id": div_id})
        if not div:
            return {}
        out: Dict[str, float] = {}
        for row in div.find_all("div", class_="first_place"):
            who = row.find("span", class_="who")
            val = row.find("span", class_="value")
            if who and val:
                name = who.get_text(strip=True).split(" • ")[0]
                try:
                    out[name] = float(val.get_text(strip=True))
                except (ValueError, TypeError):
                    pass
        # Also dig into further rank rows (BR limits first-place visible by default)
        for row in div.find_all("div", class_=re.compile(r"rank|player")):
            pass
        return out

    def fetch_batting(self) -> List[Dict]:
        """Scrape batting WAR leaderboard and join with rate stats."""
        # BR's batting leaders page is at /leagues/majors/YYYY-batting-leaders.shtml
        # Pull WAR, AVG, HR, RBI, R, SB, OPS in one pass
        soup = self._fetch(f"/leagues/majors/{self.season}-batting-leaders.shtml")
        if not soup:
            return []
        # Each stat is a div with id like 'leaderboard_batting_WAR'
        stat_divs = soup.find_all("div", id=re.compile(r"^leaderboard_batting_[A-Z]"))
        players: Dict[str, Dict] = {}
        for div in stat_divs:
            stat_name = div.get("id", "").replace("leaderboard_batting_", "")
            for row in div.find_all("div"):
                classes = row.get("class", [])
                if "first_place" not in classes and "other" not in classes:
                    continue
                who = row.find("span", class_="who")
                val = row.find("span", class_="value")
                if not (who and val):
                    continue
                raw = who.get_text(" ", strip=True)
                # Format: "LastName • TEAM"
                parts = raw.split("•")
                if len(parts) < 2:
                    continue
                name = parts[0].strip()
                team = parts[1].strip()
                try:
                    v = float(val.get_text(strip=True))
                except (ValueError, TypeError):
                    continue
                p = players.setdefault(name, {"name": name, "team": team})
                p[stat_name.lower()] = v
        return list(players.values())

    def fetch_pitching(self) -> List[Dict]:
        """Scrape pitching leaderboard."""
        soup = self._fetch(f"/leagues/majors/{self.season}-pitching-leaders.shtml")
        if not soup:
            return []
        stat_divs = soup.find_all("div", id=re.compile(r"^leaderboard_pitching_[A-Z]"))
        players: Dict[str, Dict] = {}
        for div in stat_divs:
            stat_name = div.get("id", "").replace("leaderboard_pitching_", "")
            for row in div.find_all("div"):
                classes = row.get("class", [])
                if "first_place" not in classes and "other" not in classes:
                    continue
                who = row.find("span", class_="who")
                val = row.find("span", class_="value")
                if not (who and val):
                    continue
                raw = who.get_text(" ", strip=True)
                parts = raw.split("•")
                if len(parts) < 2:
                    continue
                name = clean_name(parts[0].strip())
                team = parts[1].strip()
                try:
                    v = float(val.get_text(strip=True))
                except (ValueError, TypeError):
                    continue
                p = players.setdefault(name, {"name": name, "team": team})
                p[stat_name.lower()] = v
        return list(players.values())

    @staticmethod
    def _safe_float(val) -> float:
        try:
            return float(str(val).strip())
        except (ValueError, AttributeError, TypeError):
            return 0.0

    @staticmethod
    def _safe_int(val) -> int:
        try:
            return int(str(val).strip())
        except (ValueError, AttributeError, TypeError):
            return 0


if __name__ == "__main__":
    scraper = BaseballReferenceScraper(2026)
    print("Batting leaders (top 5):")
    for p in scraper.fetch_batting()[:5]:
        print(f"  {p.get('name')} ({p.get('team')}): {p}")
    print("Pitching leaders (top 5):")
    for p in scraper.fetch_pitching()[:5]:
        print(f"  {p.get('name')} ({p.get('team')}): {p}")
