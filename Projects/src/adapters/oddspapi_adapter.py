#!/usr/bin/env python3
"""
OddsPapi Adapter — wrapper around OddsPapi API (https://oddspapi.io).
Uses ODDSPAPI_API_KEY from environment. Auth via query param. Call monitor + budget.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from crash_guard import consume_budget, get_remaining_budget

logger = logging.getLogger("oddspapi")

ODDS_API_KEY = os.environ.get("ODDSPAPI_API_KEY", "")
BASE_URL = "https://api.oddspapi.io/v4"

SPORT_IDS = {"MLB": 13, "NBA": 11, "NFL": 14, "NHL": 15, "WNBA": 11}

TOURNAMENT_IDS = {"MLB": 109, "NBA": None, "NFL": None, "NHL": None, "WNBA": None}

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "oddspapi"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class OddsCallMonitor:
    def __init__(self, log_file: Path = None):
        self.log_file = log_file or Path("/home/workspace/data/odds_call_log.json")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.calls_today = 0
        self.date = datetime.now().strftime("%Y-%m-%d")
        self._load()

    def _load(self):
        if self.log_file.exists():
            try:
                with open(self.log_file) as f:
                    data = json.load(f)
                if data.get("date") == self.date:
                    self.calls_today = data.get("calls", 0)
                else:
                    self.calls_today = 0
            except Exception:
                self.calls_today = 0
        self._save()

    def _save(self):
        with open(self.log_file, "w") as f:
            json.dump({"date": self.date, "calls": self.calls_today}, f, indent=2)

    def increment(self, amount: int = 1) -> bool:
        if not consume_budget("oddspapi", amount):
            logger.warning("OddsPapi budget exhausted — skipping")
            return False
        self.calls_today += amount
        self._save()
        return True

    def get_remaining(self) -> int:
        return max(0, 999999 - self.calls_today)


class OddsPapiAdapter:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ODDS_API_KEY
        self.monitor = OddsCallMonitor()
        self._participants_cache = {}
        self._tournament_cache = {}
        self._market_cache = None

    def _get(self, path: str, params: Dict = None, cache_ttl: int = 0,
             cache_key: str = "") -> Optional[Dict]:
        if not self.api_key:
            logger.error("No API key")
            return None
        if not self.monitor.increment():
            return None

        if cache_ttl > 0 and cache_key:
            cf = CACHE_DIR / f"{cache_key}.json"
            if cf.exists() and (time.time() - cf.stat().st_mtime) < cache_ttl:
                with open(cf) as f:
                    return json.load(f)

        qs_params = {"apiKey": self.api_key}
        if params:
            qs_params.update(params)
        qs = "&".join(f"{k}={v}" for k, v in qs_params.items())
        url = f"{BASE_URL}{path}?{qs}"

        try:
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", "TC-Pipeline/1.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            if cache_ttl > 0 and cache_key:
                with open(CACHE_DIR / f"{cache_key}.json", "w") as f:
                    json.dump(data, f)
            return data
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300] if e.fp else ""
            logger.error(f"HTTP {e.code}: {body}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def get_participant_name(self, participant_id: int, sport_id: int = 13) -> str:
        if participant_id in self._participants_cache:
            return self._participants_cache[participant_id]
        data = self._get("/participants", {"sportId": sport_id},
                         cache_ttl=86400, cache_key=f"participants_{sport_id}")
        if data and isinstance(data, dict):
            self._participants_cache.update(data)
            return data.get(str(participant_id), str(participant_id))
        return str(participant_id)

    def get_fixtures(self, tournament_id: int, date: str) -> List[Dict]:
        data = self._get("/fixtures", {
            "tournamentId": tournament_id,
            "from": date,
            "to": date,
            "language": "en"
        }, cache_ttl=300, cache_key=f"fixtures_{tournament_id}_{date}")
        if isinstance(data, list):
            return data
        return []

    def get_odds(self, fixture_id: str) -> Optional[Dict]:
        return self._get("/odds", {
            "fixtureId": fixture_id,
            "oddsFormat": "american",
            "language": "en"
        })

    def get_mlb_player_props(self, date: str) -> Dict[str, Dict]:
        result = {}
        fixtures = self.get_fixtures(109, date)
        logger.info(f"OddsPapi: {len(fixtures)} MLB fixtures for {date}")

        for f in fixtures[:15]:
            fid = f.get("fixtureId", "")
            if not f.get("hasOdds"):
                continue
            home = self.get_participant_name(f.get("participant1Id", 0), 13)
            away = self.get_participant_name(f.get("participant2Id", 0), 13)
            matchup = f"{away}_at_{home}"

            odds_data = self.get_odds(fid)
            if not odds_data:
                continue

            bm_odds = odds_data.get("bookmakerOdds", {})
            for bm_name, bm_data in bm_odds.items():
                markets = bm_data.get("markets", {})
                for market_id, mdata in markets.items():
                    outcomes = mdata.get("outcomes", {})
                    for oid, odata in outcomes.items():
                        players = odata.get("players", {})
                        for pidx, pdata in players.items():
                            pname = pdata.get("playerName", "")
                            price_am = pdata.get("priceAmerican")
                            if pname and price_am:
                                key = f"{matchup}|{pname}"
                                if key not in result:
                                    result[key] = {
                                        "matchup": matchup,
                                        "player": pname,
                                        "markets": {}
                                    }
                                result[key]["markets"][market_id] = {
                                    "priceAmerican": price_am,
                                    "bookmaker": bm_name,
                                    "changedAt": pdata.get("changedAt", ""),
                                    "limit": pdata.get("limit"),
                                }
        return result


def get_line(sport: str, event_id: str, player: str, stat: str) -> Optional[float]:
    if not hasattr(get_line, "_adapter"):
        get_line._adapter = OddsPapiAdapter()
    return None


def get_odds_usage() -> Dict:
    monitor = OddsCallMonitor()
    return {
        "date": monitor.date,
        "calls_today": monitor.calls_today,
        "remaining": monitor.get_remaining(),
        "global_remaining": get_remaining_budget("oddspapi"),
    }
