import requests
import os
from src.adapters.cache_adapter import CacheAdapter

cache = CacheAdapter()

class FantasyImages:
    BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("SPORTSDB_API_KEY", "3")

    def search_team(self, team_name):
        cache_key = f"team_{team_name}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        try:
            data = requests.get(
                f"{self.BASE_URL}/searchteams.php?t={team_name}", timeout=10
            ).json()
            cache.set(cache_key, data, ttl_seconds=86400)
            return data
        except Exception:
            return {}

    def get_team_logo(self, team_name):
        data = self.search_team(team_name)
        teams = data.get("teams", [])
        return teams[0].get("strTeamBadge") if teams else None

    def get_team_icon_url(self, team_name):
        return self.get_team_logo(team_name)
