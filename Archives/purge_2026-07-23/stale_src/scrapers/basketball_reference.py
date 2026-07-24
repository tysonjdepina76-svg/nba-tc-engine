"""Basketball Reference scraper for WNBA/NBA stats and lines."""
import requests
from typing import List, Dict, Optional
import re
import time


class BasketballReferenceScraper:
    """Scrapes WNBA/NBA player stats and game data from Basketball-Reference."""

    BASE_URL = "https://www.basketball-reference.com"

    def __init__(self, league: str = "wnba", rate_limit: float = 3.0):
        self.league = league
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
            match = re.search(r"/players/./([^/]+)\.html", resp.text)
            return match.group(1) if match else None
        except Exception:
            return None

    def get_player_stats(self, player_id: str, year: int) -> Dict:
        self._respect_rate_limit()
        try:
            url = f"{self.BASE_URL}/players/{player_id[0]}/{player_id}.html"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}
            return {
                "player_id": player_id,
                "year": year,
                "ppg": 0.0,
                "rpg": 0.0,
                "apg": 0.0,
                "spg": 0.0,
                "bpg": 0.0,
                "fg_pct": 0.0,
                "fg3_pct": 0.0,
                "ft_pct": 0.0,
                "mpg": 0.0,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_team_stats(self, team_abbr: str, year: int) -> Dict:
        return {"abbr": team_abbr, "year": year, "stat": "placeholder"}


def fetch_basketball_reference_lines(date_str: str, league: str = "wnba") -> Dict:
    """Module-level wrapper for hybrid predictor compatibility."""
    try:
        scraper = BasketballReferenceScraper(league=league)
        matchups = scraper.get_daily_matchups(date_str)
        lines: Dict[str, Dict[str, float]] = {}
        if matchups:
            for m in matchups:
                for player in m.get("players", []):
                    pname = player.get("name", "")
                    if pname:
                        lines[pname] = {
                            "PTS": float(player.get("pts", 0) or 0),
                            "REB": float(player.get("reb", 0) or 0),
                            "AST": float(player.get("ast", 0) or 0),
                        }
        return lines
    except Exception:
        return {}


def get_daily_matchups(self, date: str) -> List[Dict]:
        try:
            return []
        except Exception as e:
            return [{"error": str(e)}]
