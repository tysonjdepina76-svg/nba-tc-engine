"""ESPN adapter — games, rosters, boxscores."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import urllib.request
import json
from typing import List

from entities import Game, Player, Boxscore, Team, GameStatus
import logging


SPORT_MAP = {
    "NBA": ("basketball/nba", "basketball/nba/scoreboard"),
    "WNBA": ("basketball/wnba", "basketball/wnba/scoreboard"),
    "MLB": ("baseball/mlb", "baseball/mlb/scoreboard"),
    "NHL": ("hockey/nhl", "hockey/nhl/scoreboard"),
}


class ESPNClient:
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"

    def __init__(self):
        self._session = None

    def _get(self, url):
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def fetch_games(self, sport: str) -> List[Game]:
        if sport not in SPORT_MAP:
            return []
        _, path = SPORT_MAP[sport]
        url = f"{self.BASE_URL}/{path}"
        try:
            payload = self._get(url)
        except Exception:
            return []
        games = []
        for event in payload.get("events", []):
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            home = ""
            away = ""
            status_name = comp.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
            status = GameStatus.SCHEDULED if "SCHEDULED" in status_name else GameStatus.FINAL if "FINAL" in status_name else GameStatus.LIVE
            for c in competitors:
                abbr = (c.get("team", {}).get("abbreviation") or "").upper()
                if c.get("homeAway") == "home":
                    home = abbr
                else:
                    away = abbr
            games.append(Game(
                id=str(event.get("id", "")),
                sport=sport,
                home=home,
                away=away,
                start_time=event.get("date"),
                home_team=Team(abbr=home, name=home),
                away_team=Team(abbr=away, name=away),
                status=status,
            ))
        return games

    def fetch_team_roster(self, team_id: str, sport: str = "NBA") -> List[Player]:
        if sport not in SPORT_MAP:
            return []
        path, _ = SPORT_MAP[sport]
        url = f"{self.BASE_URL}/{path}/teams/{team_id}/roster"
        try:
            payload = self._get(url)
        except Exception:
            return []
        players = []
        for athlete in payload.get("athletes", []):
            pos = athlete.get("position", {})
            position = pos.get("abbreviation") if isinstance(pos, dict) else str(pos)
            raw_stats = athlete.get("stats", {})
            if isinstance(raw_stats, dict):
                stats = {k.lower(): v for k, v in raw_stats.items()}
            elif isinstance(raw_stats, list):
                stats = {}
                for s in raw_stats:
                    if isinstance(s, dict):
                        key = s.get("name") or s.get("abbreviation", "").lower()
                        stats[key] = s.get("value") or s.get("displayValue")
            else:
                stats = {}
            players.append(Player(
                id=str(athlete.get("id", "")),
                name=athlete.get("displayName", ""),
                team=team_id,
                position=position or "",
                stats=stats,
            ))
        return players

    def fetch_boxscore(self, event_id: str, sport: str = "NBA") -> Boxscore:
        if sport not in SPORT_MAP:
            return Boxscore(game_id=event_id, sport=sport)
        path, _ = SPORT_MAP[sport]
        url = f"{self.BASE_URL}/{path}/summary?event={event_id}"
        try:
            payload = self._get(url)
        except Exception:
            return Boxscore(game_id=event_id, sport=sport)
        return Boxscore.from_dict(payload, sport=sport)
