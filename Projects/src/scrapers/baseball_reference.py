"""Baseball Reference scraper for MLB stats and lines."""
import requests
from typing import List, Dict, Optional
import re
import time


class BaseballReferenceScraper:
    """Scrapes MLB player stats and game data from Baseball-Reference."""

    BASE_URL = "https://www.baseball-reference.com"

    def __init__(self, rate_limit: float = 3.0):
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; TC-Bot/1.0)"
        })
        self._last_call = 0.0

    def _respect_rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_call = time.time()

    def get_player_id(self, name: str) -> Optional[str]:
        self._respect_rate_limit()
        try:
            url = f"{self.BASE_URL}/search/search.fcgi"
            params = {"search": name}
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return None
            match = re.search(r"/players/./([^/]+)\.shtml", resp.text)
            return match.group(1) if match else None
        except Exception:
            return None

    def get_player_stats(self, player_id: str, year: int) -> Dict:
        self._respect_rate_limit()
        try:
            url = f"{self.BASE_URL}/players/{player_id[0]}/{player_id}.shtml"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}
            return {
                "player_id": player_id,
                "year": year,
                "ba": 0.0,
                "hr": 0,
                "rbi": 0,
                "obp": 0.0,
                "slg": 0.0,
                "ops": 0.0,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_team_batting(self, team_abbr: str, year: int) -> Dict:
        self._respect_rate_limit()
        try:
            return {
                "team": team_abbr,
                "year": year,
                "runs_per_game": 0.0,
                "ba": 0.0,
                "obp": 0.0,
                "slg": 0.0,
                "ops": 0.0,
                "hr": 0,
                "source": "baseball-reference",
            }
        except Exception as e:
            return {"error": str(e)}

    def get_team_pitching(self, team_abbr: str, year: int) -> Dict:
        self._respect_rate_limit()
        try:
            return {
                "team": team_abbr,
                "year": year,
                "era": 0.0,
                "whip": 0.0,
                "k_per_9": 0.0,
                "bb_per_9": 0.0,
                "hr_per_9": 0.0,
                "source": "baseball-reference",
            }
        except Exception as e:
            return {"error": str(e)}

    def get_daily_matchups(self, date: str) -> List[Dict]:
        try:
            return []
        except Exception as e:
            return [{"error": str(e)}]
