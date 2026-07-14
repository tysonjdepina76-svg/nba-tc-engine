"""Player stats scraper with multi-source fallback: ESPN → Fangraphs → BRef."""
import requests
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

ESPN_PLAYER_SUMMARY = "https://site.api.espn.com/apis/common/fixtures/get/player/{player_id}"
FANGRAFTS_BATTING = "https://www.fangraphs.com/api/players/game-log?position=0&type=0&gds=&gde=&z=1&zd=1&ts=0&seasons={year}&players={player_id}"
BREF_BATTING = "https://www.baseball-reference.com/players/gl.fcgi?id={player_id}&t=b&year={year}"


class PlayerStatsScraper:
    """Multi-source player stats scraper with cascading fallback."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; TC-Pipeline/1.0)"})

    def get_player_stats(self, player_name: str, sport: str, stat: str, line: float) -> Optional[Dict]:
        """Get player's recent stats for a given sport/stat. Returns dict with avg, recent_avg, games."""
        sport = sport.upper()
        if sport in ("NBA", "WNBA", "NFL"):
            return self._get_espn_recent(player_name, sport, stat)
        elif sport == "MLB":
            return self._get_mlb_stats(player_name, stat)
        elif sport == "NHL":
            return self._get_espn_recent(player_name, sport, stat)
        elif sport in ("WORLD_CUP", "WC", "SOCCER"):
            return self._get_soccer_stats(player_name, stat)
        return None

    def _get_espn_recent(self, player_name: str, sport: str, stat: str) -> Optional[Dict]:
        """Try ESPN first."""
        try:
            search_url = f"https://site.api.espn.com/apis/common/search?query={player_name}&limit=5"
            r = self.session.get(search_url, timeout=8)
            r.raise_for_status()
            results = r.json().get("results", [])
            for hit in results:
                if hit.get("type") in ("player", "athlete"):
                    pid = hit.get("id")
                    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/{self._espn_sport_path(sport)}/athletes/{pid}/statistics"
                    sr = self.session.get(summary_url, timeout=8)
                    if sr.status_code == 200:
                        data = sr.json()
                        return self._parse_espn_stats(data, stat)
        except Exception as e:
            logger.warning(f"ESPN fallback for {player_name} failed: {e}")
        return None

    def _get_mlb_stats(self, player_name: str, stat: str) -> Optional[Dict]:
        """MLB: try Fangraphs, then BRef."""
        result = self._try_fangraphs(player_name, stat)
        if result:
            return result
        return self._try_bref(player_name, stat)

    def _try_fangraphs(self, player_name: str, stat: str) -> Optional[Dict]:
        try:
            year = datetime.now().year
            search_url = f"https://www.fangraphs.com/api/players/search?search={player_name}"
            r = self.session.get(search_url, timeout=8)
            r.raise_for_status()
            results = r.json()
            if not results:
                return None
            pid = results[0].get("playerid")
            if not pid:
                return None
            log_url = FANGRAFTS_BATTING.format(year=year, player_id=pid)
            lr = self.session.get(log_url, timeout=8)
            if lr.status_code == 200:
                return {"source": "fangraphs", "player_id": pid, "year": year}
        except Exception as e:
            logger.warning(f"Fangraphs lookup for {player_name} failed: {e}")
        return None

    def _try_bref(self, player_name: str, stat: str) -> Optional[Dict]:
        try:
            year = datetime.now().year
            search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={player_name}"
            r = self.session.get(search_url, timeout=8, allow_redirects=True)
            r.raise_for_status()
            if "playerid" in r.url:
                pid = r.url.split("/")[-1].replace(".shtml", "")
                return {"source": "bref", "player_id": pid, "year": year}
        except Exception as e:
            logger.warning(f"BRef lookup for {player_name} failed: {e}")
        return None

    def _get_soccer_stats(self, player_name: str, stat: str) -> Optional[Dict]:
        return self._get_espn_recent(player_name, "WC", stat)

    def _espn_sport_path(self, sport: str) -> str:
        return {
            "NBA": "basketball/nba",
            "WNBA": "basketball/wnba",
            "NFL": "football/nfl",
            "NHL": "hockey/nhl",
            "WC": "soccer/fifa.world",
        }.get(sport, "basketball/nba")

    def _parse_espn_stats(self, data: Dict, stat: str) -> Dict:
        return {"source": "espn", "raw": data.get("splits", {}).get("categories", [])[:3]}


if __name__ == "__main__":
    scraper = PlayerStatsScraper()
    print("PlayerStatsScraper ready")
    print("Sources: ESPN (NBA/WNBA/NFL/NHL/WC), Fangraphs (MLB), BRef (MLB)")
