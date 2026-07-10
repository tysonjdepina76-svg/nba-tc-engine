"""SportsDataIO Base Adapter — Shared client for all sports."""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class SportsDataIOBase:
    """Base client for SportsDataIO API."""

    BASE_URL = "https://api.sportsdata.io/v3"

    def __init__(self, sport: str, api_key: Optional[str] = None):
        self.sport = sport
        self.api_key = api_key or os.environ.get("SPORTSDATAIO_API_KEY") or os.environ.get("SportsDataIo")
        if not self.api_key:
            raise ValueError("SPORTSDATAIO_API_KEY (or SportsDataIo) not set")

        self.sport_paths = {
            "wnba": "/wnba",
            "nfl": "/nfl",
            "mlb": "/mlb",
        }
        self.sport_path = self.sport_paths.get(self.sport, f"/{self.sport}")

        self.cache_dir = Path("/tmp/sportsdataio_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = 300  # 5 minutes

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        import hashlib
        key_str = f"{endpoint}_{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Any]:
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text())
            cached_time = datetime.fromisoformat(data["timestamp"])
            if (datetime.now() - cached_time).seconds > self.cache_ttl:
                return None
            return data["value"]
        except Exception:
            return None

    def _set_cached(self, key: str, value: Any):
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "value": value
        }))

    def _request(self, category: str, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.BASE_URL}{self.sport_path}/{category}/json/{endpoint}"
        params = params or {}

        cache_key = self._get_cache_key(f"{category}/{endpoint}", params)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        response = requests.get(url, params=params, headers={"Ocp-Apim-Subscription-Key": self.api_key}, timeout=30)
        response.raise_for_status()
        data = response.json()
        self._set_cached(cache_key, data)
        return data

    def fetch_teams(self) -> List[Dict]:
        return self._request("scores", "Teams")

    def fetch_players(self, team_id: Optional[int] = None) -> List[Dict]:
        endpoint = "Players" if not team_id else f"PlayersByTeam/{team_id}"
        return self._request("scores", endpoint)

    def fetch_games(self, date: str) -> List[Dict]:
        return self._request("scores", f"GamesByDate/{date}")

    def fetch_boxscore(self, game_id: int) -> Dict:
        return self._request("stats", f"BoxScore/{game_id}")

    def fetch_player_game_stats(self, player_id: int, game_id: int) -> Dict:
        return self._request("stats", f"PlayerGameStatsByPlayerID/{game_id}/{player_id}")

    def fetch_team_game_stats(self, team_id: int, game_id: int) -> Dict:
        return self._request("stats", f"TeamGameStats/{game_id}/{team_id}")

    def fetch_injuries(self) -> List[Dict]:
        return self._request("scores", "Injuries")

    def fetch_betting_events(self, season: int = None) -> List[Dict]:
        ep = f"BettingEvents/{season}" if season else "BettingEvents"
        return self._request("odds", ep)

    def fetch_betting_markets(self, event_id: int) -> List[Dict]:
        return self._request("odds", f"BettingMarkets/{event_id}")

    def fetch_betting_outcomes(self, market_id: int) -> List[Dict]:
        return self._request("odds", f"BettingMarket/{market_id}")

    def fetch_player_props(self, score_id: int) -> List[Dict]:
        return self._request("odds", f"BettingPlayerPropsByScoreID/{score_id}")

    # --- Headshots ---

    def fetch_headshot(self, player_id: int) -> Optional[str]:
        """Return SportsDataIO-hosted headshot URL for a player.

        SportsDataIO serves headshots from images.sportsdata.io, keyed by PlayerID.
        Returns None if the player cannot be looked up.
        """
        try:
            # Try to find the player in the roster to get sport-specific image key
            players = self.fetch_players()
            match = next((p for p in players if p.get("PlayerID") == player_id), None)
            if not match:
                return None
            first = (match.get("FirstName") or "").strip()
            last = (match.get("LastName") or "").strip()
            if not first and not last:
                return None
            from urllib.parse import quote
            return (
                f"https://images.sportsdata.io/{self.sport}/headshots/{quote(first + ' ' + last)}.png"
            )
        except Exception:
            return None

    # --- News ---

    def fetch_news_by_team(self, team_id: int) -> List[Dict]:
        return self._request("scores", f"NewsByTeam/{team_id}")

    def fetch_news_by_player(self, player_id: int) -> List[Dict]:
        # SDIO uses NewsByPlayerID for player news
        return self._request("scores", f"NewsByPlayerID/{player_id}")

    def fetch_news_by_date(self, date: str) -> List[Dict]:
        return self._request("scores", f"NewsByDate/{date}")

    def fetch_player_news_notes(self, player_id: int) -> List[Dict]:
        """Brief injury/status notes for a player."""
        return self._request("scores", f"NewsByPlayerID/{player_id}")

    # --- DFS Slates ---

    def fetch_dfs_slates_by_week(self, week: int, season: int = 2026) -> List[Dict]:
        """DFS slates for a given NFL week (e.g. week=1, season=2026)."""
        return self._request("fantasy", f"DfsSlatesByWeek/{season}/{week}")

    def fetch_dfs_slates_by_date(self, date: str) -> List[Dict]:
        """DFS slates for a given date (YYYY-MM-DD)."""
        return self._request("fantasy", f"DfsSlatesByDate/{date}")

    # --- Fantasy / ADP ---

    def fetch_idp_adp(self, season: int = 2026) -> List[Dict]:
        """IDP (Individual Defensive Player) ADP for fantasy drafts."""
        return self._request("fantasy", f"IdpAdp/{season}")

    def fetch_fantasy_points_by_week(self, week: int, season: int = 2026) -> List[Dict]:
        """Weekly fantasy scoring for a given NFL week."""
        return self._request("fantasy", f"FantasyPointsByWeek/{season}/{week}")

    def fetch_fantasy_adp(self, season: int = 2026) -> List[Dict]:
        """Overall fantasy player ADP for a season."""
        return self._request("fantasy", f"Adp/{season}")