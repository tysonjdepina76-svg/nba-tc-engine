"""Injury scraper — triggers odds fetch only when injuries change."""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    import requests
    from bs4 import BeautifulSoup
    _HTTP_OK = True
except ImportError:
    _HTTP_OK = False


_SPORT_MAP = {
    "MLB": "mlb",
    "WNBA": "wnba",
    "NBA": "nba",
    "NFL": "nfl",
    "NHL": "nhl",
    "WC": "soccer",
}


class InjuryScraper:
    """Monitor injuries; trigger odds fetch only on change."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or Path("/home/workspace/Projects/cache/injuries.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def check_injuries(self, sport: str) -> List[Dict]:
        """Return list of injury dicts from ESPN for a sport. Empty on failure."""
        if not _HTTP_OK:
            return []

        slug = _SPORT_MAP.get(sport, 'mlb')
        url = f"https://www.espn.com/{slug}/injuries"

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=10,
            )
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            injuries: List[Dict] = []

            for item in soup.find_all("div", class_=re.compile(r"injury", re.I)):
                player_el = item.find("span", class_=re.compile(r"player", re.I))
                status_el = item.find("span", class_=re.compile(r"status", re.I))
                if player_el and status_el:
                    injuries.append({
                        "player": player_el.get_text(strip=True),
                        "status": status_el.get_text(strip=True),
                        "sport": sport,
                        "timestamp": datetime.now().isoformat(),
                    })
            return injuries
        except Exception as e:
            print(f"⚠️ Injury check failed for {sport}: {e}")
            return []

    def should_fetch_odds(self, sport: str) -> bool:
        """True if injury list changed since last check."""
        current = self.check_injuries(sport)
        last = self._load_cached(sport)
        changed = current != last
        if changed:
            self._save_cached(sport, current)
            print(f"🚨 Injury change detected for {sport}")
        return changed

    def _load_cached(self, sport: str) -> List:
        if not self.cache_file.exists():
            return []
        try:
            with open(self.cache_file) as f:
                data = json.load(f)
            return data.get(sport, [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save_cached(self, sport: str, injuries: List):
        data: dict = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = {}
        data[sport] = injuries
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
