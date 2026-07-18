#!/usr/bin/env python3
"""
Real-time sports data pipeline - fetches MLB (StatsAPI) and WNBA (ESPN).
Extracts player props and returns structured JSON.
"""
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

try:
    from sports_skills import wnba, mlb
except ImportError:
    wnba = mlb = None

from config import CACHE_DIR, CACHE_TTL_SECONDS, ODDS_API_KEY

logger = logging.getLogger("pipeline")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
    logger.addHandler(ch)

class Cache:
    def __init__(self, cache_dir: str = CACHE_DIR, ttl: int = CACHE_TTL_SECONDS):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        import hashlib
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def get(self, key: str) -> Optional[Dict]:
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
            if (datetime.now() - cached_at).total_seconds() > self.ttl:
                return None
            return data.get("data")
        except Exception:
            return None

    def set(self, key: str, data: Dict) -> None:
        path = self._key_path(key)
        with open(path, "w") as f:
            json.dump({"_cached_at": datetime.now().isoformat(), "data": data}, f, indent=2)


class MLBFetcher:
    BASE_URL = "http://statsapi.mlb.com/api/v1"

    def __init__(self, cache: Cache):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SportsPipeline/1.0"})

    def get_schedule(self, date: Optional[str] = None) -> Dict:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        key = f"mlb_schedule_{date}"
        cached = self.cache.get(key)
        if cached:
            return cached
        url = f"{self.BASE_URL}/schedule"
        params = {"date": date, "sportId": 1}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.cache.set(key, data)
            return data
        except Exception as e:
            logger.error(f"MLB schedule failed: {e}")
            return {"error": str(e), "dates": []}

    def get_boxscore(self, game_pk: int) -> Dict:
        key = f"mlb_boxscore_{game_pk}"
        cached = self.cache.get(key)
        if cached:
            return cached
        url = f"{self.BASE_URL}/game/{game_pk}/boxscore"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.cache.set(key, data)
            return data
        except Exception as e:
            logger.error(f"MLB boxscore failed for {game_pk}: {e}")
            return {"error": str(e)}

    def get_live_games(self) -> List[Dict]:
        schedule = self.get_schedule()
        games = []
        for date in schedule.get("dates", []):
            for game in date.get("games", []):
                status = game.get("status", {}).get("detailedState", "")
                if status in ["In Progress", "Live"]:
                    games.append({
                        "game_pk": game.get("gamePk"),
                        "away_team": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                        "home_team": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                        "away_score": game.get("teams", {}).get("away", {}).get("score"),
                        "home_score": game.get("teams", {}).get("home", {}).get("score"),
                        "inning": game.get("linescore", {}).get("inning"),
                        "inning_state": game.get("linescore", {}).get("inningState"),
                        "status": status
                    })
        return games


class WNBAFetcher:
    ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"

    def __init__(self, cache: Cache):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SportsPipeline/1.0"})
        self._use_sdk = wnba is not None

    def get_scoreboard(self, date: Optional[str] = None) -> Dict:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        key = f"wnba_scoreboard_{date}"
        cached = self.cache.get(key)
        if cached:
            return cached
        if self._use_sdk:
            try:
                result = wnba.get_scoreboard(date=date)
                data = result.get("data", {})
                self.cache.set(key, data)
                return data
            except Exception:
                pass
        url = f"{self.ESPN_BASE}/scoreboard"
        params = {"dates": date}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.cache.set(key, data)
            return data
        except Exception as e:
            logger.error(f"WNBA scoreboard failed: {e}")
            return {"error": str(e), "events": []}

    def get_boxscore(self, event_id: str) -> Dict:
        key = f"wnba_boxscore_{event_id}"
        cached = self.cache.get(key)
        if cached:
            return cached
        if self._use_sdk:
            try:
                result = wnba.get_game_summary(event_id=event_id)
                data = result.get("data", {})
                self.cache.set(key, data)
                return data
            except Exception:
                pass
        url = f"{self.ESPN_BASE}/game/{event_id}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.cache.set(key, data)
            return data
        except Exception as e:
            logger.error(f"WNBA boxscore failed for {event_id}: {e}")
            return {"error": str(e)}

    def get_live_games(self) -> List[Dict]:
        scoreboard = self.get_scoreboard()
        games = []
        for event in scoreboard.get("events", []):
            status = event.get("status", {}).get("type", {}).get("state", "")
            if status in ["in", "live"]:
                comps = event.get("competitions", [{}])[0]
                games.append({
                    "event_id": event.get("id"),
                    "away_team": comps.get("competitors", [{}])[0].get("team", {}).get("displayName"),
                    "home_team": comps.get("competitors", [{}])[1].get("team", {}).get("displayName"),
                    "away_score": comps.get("competitors", [{}])[0].get("score"),
                    "home_score": comps.get("competitors", [{}])[1].get("score"),
                    "period": comps.get("status", {}).get("period"),
                    "clock": comps.get("status", {}).get("displayClock"),
                    "status": status
                })
        return games


class OddsFetcher:
    ODDS_API_BASE = "https://api.the-odds-api.com/v4"

    def __init__(self, cache: Cache, api_key: str = ODDS_API_KEY):
        self.cache = cache
        self.api_key = api_key
        self.session = requests.Session()

    def get_odds(self, sport: str = "baseball_mlb", regions: str = "us", markets: str = "spreads,totals") -> List[Dict]:
        if not self.api_key:
            return []
        key = f"odds_{sport}_{regions}_{markets}"
        cached = self.cache.get(key)
        if cached:
            return cached.get("data", [])
        url = f"{self.ODDS_API_BASE}/sports/{sport}/odds"
        params = {"apiKey": self.api_key, "regions": regions, "markets": markets, "oddsFormat": "american"}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.cache.set(key, {"data": data})
            return data
        except Exception as e:
            logger.error(f"Odds fetch failed: {e}")
            return []


@dataclass
class GameData:
    league: str
    matchup: str
    away_team: str
    home_team: str
    away_score: Optional[int] = None
    home_score: Optional[int] = None
    status: str = "scheduled"
    period: Optional[str] = None
    clock: Optional[str] = None
    game_id: Optional[str] = None
    boxscore: Optional[Dict] = None
    odds: Optional[List[Dict]] = None
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class PlayerProp:
    player: str
    team: str
    stat: str
    line: float
    projection: float
    edge: float
    source: str
    game_id: str
    league: str
    matchup: str
    confidence: int = 70
    adjusted_projection: Optional[float] = None
    game_context: Optional[str] = None
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SportsPipeline:
    def __init__(self):
        self.cache = Cache()
        self.mlb = MLBFetcher(self.cache)
        self.wnba = WNBAFetcher(self.cache)
        self.odds = OddsFetcher(self.cache)

    def fetch_all_live_games(self) -> Dict[str, List[GameData]]:
        result = {"mlb": [], "wnba": []}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._fetch_mlb_live): "mlb",
                executor.submit(self._fetch_wnba_live): "wnba",
            }
            for future in as_completed(futures):
                league = futures[future]
                try:
                    result[league] = future.result(timeout=30)
                except Exception as e:
                    logger.error(f"Failed {league}: {e}")
                    result[league] = []
        return result

    def _fetch_mlb_live(self) -> List[GameData]:
        games = []
        for g in self.mlb.get_live_games():
            pk = g.get("game_pk")
            if not pk:
                continue
            box = self.mlb.get_boxscore(pk)
            odds = self.odds.get_odds(sport="baseball_mlb") if self.odds.api_key else []
            games.append(GameData(
                league="MLB",
                matchup=f"{g.get('away_team','')}@{g.get('home_team','')}",
                away_team=g.get("away_team",""),
                home_team=g.get("home_team",""),
                away_score=g.get("away_score"),
                home_score=g.get("home_score"),
                status=g.get("status","unknown"),
                period=g.get("inning"),
                clock=g.get("inning_state"),
                game_id=str(pk),
                boxscore=box,
                odds=odds
            ))
        return games

    def _fetch_wnba_live(self) -> List[GameData]:
        games = []
        for g in self.wnba.get_live_games():
            eid = g.get("event_id")
            if not eid:
                continue
            box = self.wnba.get_boxscore(eid)
            odds = self.odds.get_odds(sport="basketball_wnba") if self.odds.api_key else []
            games.append(GameData(
                league="WNBA",
                matchup=f"{g.get('away_team','')}@{g.get('home_team','')}",
                away_team=g.get("away_team",""),
                home_team=g.get("home_team",""),
                away_score=g.get("away_score"),
                home_score=g.get("home_score"),
                status=g.get("status","unknown"),
                period=g.get("period"),
                clock=g.get("clock"),
                game_id=str(eid),
                boxscore=box,
                odds=odds
            ))
        return games

    def extract_player_props(self, games: Dict[str, List[GameData]]) -> List[PlayerProp]:
        props = []
        for game in games.get("mlb", []):
            if not game.boxscore:
                continue
            box = game.boxscore
            for side in ["away", "home"]:
                team_data = box.get(side, {})
                players = team_data.get("players", {})
                team_name = team_data.get("team", {}).get("name", "")
                for pid, pdata in players.items():
                    name = pdata.get("person", {}).get("fullName", "")
                    stats = pdata.get("stats", {}).get("batting", {})
                    for s, v in [("H", stats.get("hits", 0)),
                                 ("HR", stats.get("homeRuns", 0)),
                                 ("RBI", stats.get("rbi", 0)),
                                 ("R", stats.get("runs", 0))]:
                        if v > 0:
                            line = self._get_line(game, name, s)
                            proj = float(v)
                            edge = (proj - line) / line if line > 0 else 0
                            props.append(PlayerProp(
                                player=name, team=team_name, stat=s,
                                line=line, projection=proj, edge=edge,
                                source="mlb_statsapi", game_id=game.game_id,
                                league="MLB", matchup=game.matchup,
                                confidence=85 if s in ["H","R"] else 70
                            ))
        for game in games.get("wnba", []):
            if not game.boxscore:
                continue
            box = game.boxscore
            for competitor in box.get("competitors", []):
                team_name = competitor.get("team", {}).get("displayName", "")
                for athlete in competitor.get("athletes", []):
                    name = athlete.get("athlete", {}).get("displayName", "")
                    stats = athlete.get("stats", {})
                    for s, v in [("PTS", stats.get("points", 0)),
                                 ("REB", stats.get("rebounds", 0)),
                                 ("AST", stats.get("assists", 0))]:
                        if v > 0:
                            line = self._get_line(game, name, s)
                            proj = float(v)
                            edge = (proj - line) / line if line > 0 else 0
                            props.append(PlayerProp(
                                player=name, team=team_name, stat=s,
                                line=line, projection=proj, edge=edge,
                                source="wnba_espn", game_id=game.game_id,
                                league="WNBA", matchup=game.matchup,
                                confidence=90 if s == "REB" else 75
                            ))
        return props

    def _get_line(self, game: GameData, player: str, stat: str) -> float:
        defaults = {
            "MLB": {"H": 0.9, "HR": 0.3, "RBI": 0.5, "R": 0.5},
            "WNBA": {"PTS": 10.0, "REB": 5.0, "AST": 3.0}
        }
        return defaults.get(game.league, {}).get(stat, 1.0)

    def run(self) -> Dict:
        start = time.time()
        games = self.fetch_all_live_games()
        props = self.extract_player_props(games)
        return {
            "timestamp": datetime.now().isoformat(),
            "runtime_seconds": time.time() - start,
            "games": {
                "mlb": [asdict(g) for g in games.get("mlb", [])],
                "wnba": [asdict(g) for g in games.get("wnba", [])]
            },
            "player_props": [asdict(p) for p in props],
            "summary": {
                "total_games": len(games.get("mlb",[])) + len(games.get("wnba",[])),
                "total_props": len(props),
                "mlb_games": len(games.get("mlb",[])),
                "wnba_games": len(games.get("wnba",[]))
            }
        }
