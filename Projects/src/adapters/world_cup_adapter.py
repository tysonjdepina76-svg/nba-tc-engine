import requests
from datetime import datetime
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class WorldCupAdapter:
    def __init__(self):
        self.session = requests.Session()

    def get_events(self, date: str = None) -> List[Dict]:
        """Fetch World Cup / soccer events via ESPN public API."""
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
        try:
            resp = self.session.get(url, params={"dates": date}, timeout=10)
            data = resp.json()
            events = []
            for ev in data.get("events", []):
                comps = ev.get("competitions", [{}])[0].get("competitors", [{}, {}])
                if len(comps) < 2:
                    continue
                events.append({
                    "game_id": ev.get("id"),
                    "home_team": comps[0].get("team", {}).get("abbreviation"),
                    "away_team": comps[1].get("team", {}).get("abbreviation"),
                    "start_time": ev.get("date"),
                    "sport": "world_cup"
                })
            logger.info(f"World Cup adapter fetched {len(events)} events")
            return events
        except Exception as e:
            logger.error(f"World Cup fetch error: {e}")
            return []
