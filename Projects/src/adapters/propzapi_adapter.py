#!/usr/bin/env python3
"""
Propzapi Adapter — FREE player props from DraftKings via propzapi.com.
750 credits/mo, no credit card. /v1/props endpoint with real player names + lines.

Auth: X-API-Key header (PROPZAPI_API_KEY env var)
"""
import os, json, time, logging
import urllib.request, urllib.error
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("propzapi")

API_KEY = os.environ.get("PROPZAPI_API_KEY", "")
BASE = "https://api.propzapi.com"

MARKET_MAP = {
    "player_strikeouts": "SO",
    "player_total_bases": "TB",
    "player_hits": "H",
    "player_runs": "R",
    "player_rbis": "RBI",
    "player_home_runs": "HR",
    "player_stolen_bases": "SB",
    "player_walks": "BB",
    "player_singles": "1B",
    "player_doubles": "2B",
    "player_triples": "3B",
    "player_hits_runs_rbis": "HRR",
    "player_runs_rbis": "RRBI",
}

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "propzapi"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CALL_LOG = Path("/home/workspace/data/propzapi_usage.json")


class PropzapiAdapter:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or API_KEY
        self._load_usage()

    def _load_usage(self):
        self.usage = {"date": time.strftime("%Y-%m-%d"), "calls": 0, "credits_used": 0}
        if CALL_LOG.exists():
            try:
                d = json.loads(CALL_LOG.read_text())
                if d.get("date") == self.usage["date"]:
                    self.usage = d
            except:
                pass

    def _save_usage(self):
        CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        CALL_LOG.write_text(json.dumps(self.usage, indent=2))

    def _get(self, path: str, params: Dict = None) -> Optional[Dict]:
        if not self.api_key:
            logger.error("No PROPZAPI_API_KEY")
            return None

        qs = ""
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v)
        url = f"{BASE}{path}"
        if qs:
            url += "?" + qs

        try:
            req = urllib.request.Request(url)
            req.add_header("X-API-Key", self.api_key)
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", "TC-Pipeline/2.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                cost = resp.headers.get("X-Credits-Cost", "?")
                remaining = resp.headers.get("X-Credits-Remaining", "?")
                body = resp.read().decode()
                data = json.loads(body)

            self.usage["calls"] += 1
            self.usage["credits_used"] += int(cost) if cost.isdigit() else 0
            self._save_usage()

            logger.info(f"Propzapi {path}: cost={cost} remaining={remaining}")
            return data
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300] if e.fp else ""
            logger.error(f"Propzapi HTTP {e.code}: {body}")
            return None
        except Exception as e:
            logger.error(f"Propzapi error: {e}")
            return None

    def get_player_props(self, league: str = "MLB", market: str = None) -> Dict[str, Dict]:
        params = {"league": league}
        if market:
            params["market"] = market

        data = self._get("/v1/props", params)
        if not data or not data.get("data"):
            return {}

        result = {}
        for ev in data["data"]:
            home = ev.get("home_team", "")
            away = ev.get("away_team", "")
            matchup = f"{away}_at_{home}"
            event_id = ev.get("event_id", "")

            for prop in ev.get("props", []):
                player = prop.get("player", "")
                market_name = prop.get("market", "")
                line = prop.get("line")
                stat = MARKET_MAP.get(market_name, market_name)

                if not player or line is None:
                    continue

                key = f"{player}|{stat}"
                result[key] = {
                    "player": player,
                    "stat": stat,
                    "market_name": market_name,
                    "line": line,
                    "matchup": matchup,
                    "event_id": event_id,
                    "home_team": home,
                    "away_team": away,
                    "league": league,
                    "books": prop.get("books", []),
                }
        return result

    def get_credits_used(self) -> int:
        return self.usage.get("credits_used", 0)

    def get_calls_today(self) -> int:
        return self.usage.get("calls", 0)


def fetch_player_props(league: str = "MLB", market: str = None) -> Dict[str, Dict]:
    adapter = PropzapiAdapter()
    return adapter.get_player_props(league, market)


def get_line(sport: str, event_id: str, player: str, stat: str) -> Optional[float]:
    if not hasattr(get_line, "_cache"):
        get_line._cache = {}
        get_line._fetched = False

    if not get_line._fetched:
        adapter = PropzapiAdapter()
        league_map = {"MLB": "MLB", "WNBA": "WNBA", "NBA": "NBA", "NFL": "NFL", "NHL": "NHL"}
        league = league_map.get(sport.upper(), "MLB")
        props = adapter.get_player_props(league)
        get_line._cache = props
        get_line._fetched = True

    key = f"{player}|{stat}"
    entry = get_line._cache.get(key)
    if entry:
        return entry["line"]
    return None


if __name__ == "__main__":
    a = PropzapiAdapter()
    props = a.get_player_props("MLB")
    print(f"MLB props: {len(props)} entries, {a.get_credits_used()} credits, {a.get_calls_today()} calls today")
    for k, v in list(props.items())[:5]:
        print(f"  {k}: line={v['line']} books={[b['book'] for b in v['books']]}")
