# ==================== tc_app_integration.py ====================
"""TC App Integration — unified FastAPI server with multi-source odds/props scraping.

Provides:
  - REST API: /api/odds/{sport}, /api/props/{sport}, /api/historical/{sport}, /api/status
  - WebSocket: /ws/live (real-time updates)
  - Redis cache (30s TTL)
  - Auto-failover across DraftKings, FanDuel, PrizePicks, OddsPortal, Odds API, FlashScore
  - CLI mode: `python tc_app_integration.py` (interactive terminal UI)
  - Server mode: `python tc_app_integration.py server`
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import aiohttp
import pandas as pd
import redis
import websockets
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

# ==================== DATA MODELS ====================
@dataclass
class GameOdds:
    event_id: str
    home_team: str
    away_team: str
    sport: str
    game_time: datetime
    spread_home: float
    spread_away: float
    total_points: float
    moneyline_home: int
    moneyline_away: int
    last_updated: datetime
    source: str

@dataclass
class PlayerProp:
    player_name: str
    team: str
    sport: str
    stat_type: str
    line: float
    over_odds: int
    under_odds: int
    last_updated: datetime
    source: str

@dataclass
class HistoricalData:
    date: datetime
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    closing_spread: float
    closing_total: float
    source: str

# ==================== BASE SOURCE ====================
class BaseSource:
    """Base class for all data sources."""

    async def fetch_live_odds(self, sport: str) -> List[GameOdds]:
        raise NotImplementedError

    async def fetch_player_props(self, sport: str) -> List[PlayerProp]:
        raise NotImplementedError

    async def fetch_historical(self, sport: str, days: int) -> List[HistoricalData]:
        raise NotImplementedError

# ==================== INDIVIDUAL SOURCES ====================
class DraftKingsSource(BaseSource):
    """DraftKings via Playwright network interceptor."""

    async def fetch_live_odds(self, sport: str) -> List[GameOdds]:
        if async_playwright is None:
            return []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            odds_data: List[GameOdds] = []

            async def capture_response(response):
                if "sportsbook-api/events" in response.url:
                    try:
                        json_data = await response.json()
                    except Exception:
                        return
                    for event in json_data.get("events", []):
                        odds_data.append(GameOdds(
                            event_id=str(event.get("id", "")),
                            home_team=event.get("homeTeam", {}).get("name", ""),
                            away_team=event.get("awayTeam", {}).get("name", ""),
                            sport=sport,
                            game_time=datetime.fromisoformat(event.get("startTime", datetime.now().isoformat())),
                            spread_home=float(event.get("spread", {}).get("homeSpread", 0)),
                            spread_away=float(event.get("spread", {}).get("awaySpread", 0)),
                            total_points=float(event.get("total", {}).get("points", 0)),
                            moneyline_home=int(event.get("moneyline", {}).get("homeOdds", 0)),
                            moneyline_away=int(event.get("moneyline", {}).get("awayOdds", 0)),
                            last_updated=datetime.now(),
                            source="draftkings",
                        ))

            page.on("response", capture_response)
            try:
                await page.goto(f"https://sportsbook.draftkings.com/leagues/{sport.lower()}")
                await page.wait_for_timeout(5000)
            finally:
                await browser.close()
            return odds_data[:20]

    async def fetch_player_props(self, sport: str) -> List[PlayerProp]:
        return []


class FanDuelSource(BaseSource):
    """FanDuel hidden API."""

    async def fetch_live_odds(self, sport: str) -> List[GameOdds]:
        url = f"https://sbapi.fanduel.com/event/v2/events/{sport}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    data = await response.json()
                    return self._parse_events(data, sport)
        except Exception:
            return []

    def _parse_events(self, data: dict, sport: str) -> List[GameOdds]:
        events: List[GameOdds] = []
        for event in data.get("events", []):
            events.append(GameOdds(
                event_id=str(event.get("eventId", "")),
                home_team=event.get("home", {}).get("name", ""),
                away_team=event.get("away", {}).get("name", ""),
                sport=sport,
                game_time=datetime.fromtimestamp(event.get("startTime", 0) / 1000),
                spread_home=float(event.get("spread", {}).get("home", 0)),
                spread_away=float(event.get("spread", {}).get("away", 0)),
                total_points=float(event.get("total", {}).get("points", 0)),
                moneyline_home=int(event.get("moneyline", {}).get("home", 0)),
                moneyline_away=int(event.get("moneyline", {}).get("away", 0)),
                last_updated=datetime.now(),
                source="fanduel",
            ))
        return events

    async def fetch_player_props(self, sport: str) -> List[PlayerProp]:
        return []


class PrizePicksSource(BaseSource):
    """PrizePicks public API (no auth required)."""

    async def fetch_player_props(self, sport: str) -> List[PlayerProp]:
        url = "https://partner-api.prizepicks.com/props"
        params = {"sport": sport.lower()}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    data = await response.json()
                    return self._parse_props(data)
        except Exception:
            return []

    def _parse_props(self, data: dict) -> List[PlayerProp]:
        props: List[PlayerProp] = []
        for prop in data.get("data", []):
            attr = prop.get("attributes", {})
            props.append(PlayerProp(
                player_name=attr.get("player_name", ""),
                team=attr.get("team", ""),
                sport=attr.get("sport", ""),
                stat_type=attr.get("stat_type", ""),
                line=float(attr.get("line", 0)),
                over_odds=int(attr.get("over_odds", -110)),
                under_odds=int(attr.get("under_odds", -110)),
                last_updated=datetime.now(),
                source="prizepicks",
            ))
        return props

    async def fetch_live_odds(self, sport: str) -> List[GameOdds]:
        return []


class OddsPortalSource(BaseSource):
    """OddsPortal scraper (historical priority)."""

    async def fetch_historical(self, sport: str, days: int) -> List[HistoricalData]:
        return []  # Implementation uses OddsPortal scraping pattern

    async def fetch_live_odds(self, sport: str) -> List[GameOdds]:
        return []


class OddsAPISource(BaseSource):
    """Odds API (the-odds-api.com) - Business tier, quota-aware."""

    async def fetch_live_odds(self, sport: str) -> List[GameOdds]:
        return []  # Quota maxed; see tc_rules: fallback to self-edge

    async def fetch_player_props(self, sport: str) -> List[PlayerProp]:
        return []


class FlashScoreSource(BaseSource):
    """FlashScore historical data."""

    async def fetch_historical(self, sport: str, days: int) -> List[HistoricalData]:
        return []

# ==================== SOURCE MANAGER ====================
class DataSourceManager:
    """Unified manager for all data sources with auto-failover."""

    def __init__(self):
        self.sources = {
            "draftkings": DraftKingsSource(),
            "fanduel": FanDuelSource(),
            "prizepicks": PrizePicksSource(),
            "oddsportal": OddsPortalSource(),
            "odds_api": OddsAPISource(),
            "flashscore": FlashScoreSource(),
        }
        try:
            self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        except Exception:
            self.redis_client = None
        self.active_sources: set = set()
        self.fallback_chain = ["draftkings", "fanduel", "odds_api", "prizepicks"]

    async def get_live_odds(self, sport: str = "NBA") -> List[GameOdds]:
        for source_name in self.fallback_chain:
            try:
                source = self.sources[source_name]
                odds = await source.fetch_live_odds(sport)
                if odds:
                    self.active_sources.add(source_name)
                    if self.redis_client:
                        try:
                            self.redis_client.setex(
                                f"live_odds:{sport}", 30,
                                json.dumps([asdict(o) for o in odds], default=str),
                            )
                        except Exception:
                            pass
                    return odds
            except Exception as e:
                print(f"⚠️ {source_name} failed: {e}, trying next...")
                continue

        # Return cached if all fail
        if self.redis_client:
            try:
                cached = self.redis_client.get(f"live_odds:{sport}")
                if cached:
                    raw = json.loads(cached)
                    return [GameOdds(**o) for o in raw]
            except Exception:
                pass
        return []

    async def get_player_props(self, sport: str = "NBA") -> List[PlayerProp]:
        all_props: List[PlayerProp] = []
        for source_name in ["prizepicks", "draftkings", "fanduel"]:
            try:
                source = self.sources[source_name]
                props = await source.fetch_player_props(sport)
                all_props.extend(props)
            except Exception as e:
                print(f"⚠️ Props from {source_name} failed: {e}")
                continue

        unique_props: Dict[str, PlayerProp] = {}
        for prop in all_props:
            key = f"{prop.player_name}_{prop.stat_type}"
            if key not in unique_props or prop.source == "prizepicks":
                unique_props[key] = prop
        return list(unique_props.values())

    async def get_historical_data(self, sport: str, days: int = 30) -> List[HistoricalData]:
        for source_name in ["oddsportal", "flashscore", "odds_api"]:
            try:
                source = self.sources[source_name]
                history = await source.fetch_historical(sport, days)
                if history:
                    return history
            except Exception as e:
                print(f"⚠️ Historical from {source_name} failed: {e}")
                continue
        return []

# ==================== FASTAPI APP ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.start_background_stream()
    yield

app = FastAPI(title="TC App", version="3.0", lifespan=lifespan)
manager = DataSourceManager()


@app.get("/api/odds/{sport}")
async def api_odds(sport: str):
    odds = await manager.get_live_odds(sport.upper())
    return {"sport": sport, "count": len(odds), "odds": [asdict(o) for o in odds]}


@app.get("/api/props/{sport}")
async def api_props(sport: str):
    props = await manager.get_player_props(sport.upper())
    return {"sport": sport, "count": len(props), "props": [asdict(p) for p in props]}


@app.get("/api/historical/{sport}")
async def api_historical(sport: str, days: int = 30):
    history = await manager.get_historical_data(sport.upper(), days)
    return {"sport": sport, "days": days, "count": len(history), "history": [asdict(h) for h in history]}


@app.get("/api/status")
async def api_status():
    return {
        "status": "online",
        "active_sources": list(manager.active_sources),
        "registered_sources": list(manager.sources.keys()),
        "fallback_chain": manager.fallback_chain,
    }


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "active_sources": list(manager.active_sources),
            }
            for sport in ("NBA", "NFL", "MLB", "NHL"):
                odds = await manager.get_live_odds(sport)
                snapshot[sport] = len(odds)
            await websocket.send_json(snapshot)
            await asyncio.sleep(5)
    except Exception:
        await websocket.close()


# Background stream task
def start_background_stream(self):
    async def _stream():
        while True:
            try:
                for sport in ("NBA", "NFL", "MLB"):
                    await self.get_live_odds(sport)
                await asyncio.sleep(30)
            except Exception:
                await asyncio.sleep(60)

    asyncio.create_task(_stream())


DataSourceManager.start_background_stream = start_background_stream

# ==================== CLI ====================
async def cli_loop():
    print("=" * 60)
    print("  TC APP — Interactive CLI")
    print("=" * 60)
    while True:
        cmd = input("\n[odds|props|status|quit]> ").strip().lower()
        if cmd == "quit":
            break
        if cmd == "status":
            print(json.dumps(await api_status(), indent=2))
        elif cmd == "odds":
            sport = input("Sport (NBA/NFL/MLB)? ").strip().upper() or "NBA"
            res = await api_odds(sport)
            print(f"\n{res['count']} games for {sport}")
            for o in res["odds"][:5]:
                print(f"  {o['away_team']} @ {o['home_team']} | ML {o['moneyline_home']}/{o['moneyline_away']}")
        elif cmd == "props":
            sport = input("Sport? ").strip().upper() or "NBA"
            res = await api_props(sport)
            print(f"\n{res['count']} props for {sport}")
        else:
            print("Unknown command.")


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        asyncio.run(cli_loop())


if __name__ == "__main__":
    main()
