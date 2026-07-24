"""
real_time_streamer.py – Full production real-time engine.
Redis Streams (persistence + replay) + Pub/Sub scaling.
Full type hints. No stubs.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Callable, Awaitable, Optional
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
import uvicorn

from utils.odds_fetcher import get_odds, get_player_props, format_pick, calculate_edge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

type PickDict = Dict[str, Any]
type LiveUpdate = Dict[str, Any]


class LiveEngine:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.subscribers: List[Callable[[LiveUpdate], Awaitable[None]]] = []
        self.latest: LiveUpdate = {"odds": [], "props": [], "picks": [], "timestamp": 0.0}
        self.stream_key: str = "tc_sports:live_stream"
        self._ws_clients: List[WebSocket] = []

    async def connect(self):
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info(f"Connected to Redis at {self.redis_url}")

    async def publish(self, data: LiveUpdate):
        if not self.redis_client:
            return
        data["timestamp"] = time.time()
        data_json = json.dumps(data)

        await self.redis_client.publish("tc_sports_live", data_json)
        await self.redis_client.xadd(
            self.stream_key,
            {"data": data_json},
            maxlen=10000,
            approximate=True,
        )

        self.latest = data
        await self.broadcast(data)
        await self._broadcast_ws(data_json)

    async def subscribe_redis_pubsub(self):
        if not self.redis_client:
            return
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("tc_sports_live")
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                try:
                    data: LiveUpdate = json.loads(msg["data"])
                    await self.broadcast(data)
                    await self._broadcast_ws(msg["data"])
                except Exception as e:
                    logger.error(f"PubSub error: {e}")

    async def replay_from_stream(self, last_id: str = "0"):
        if not self.redis_client:
            return
        entries = await self.redis_client.xrange(self.stream_key, last_id, "+", count=50)
        for _, entry in entries:
            try:
                data = json.loads(entry["data"])
                await self.broadcast(data)
            except Exception:
                pass
        logger.info(f"Replayed {len(entries)} historical updates")

    async def broadcast(self, data: LiveUpdate):
        for cb in self.subscribers:
            try:
                await cb(data)
            except Exception as e:
                logger.warning(f"Subscriber failed: {e}")

    async def _broadcast_ws(self, data_json: str):
        dead = []
        for ws in self._ws_clients:
            try:
                await ws.send_text(data_json)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_clients.remove(ws)

    def calculate_picks(self, props: List[PickDict]) -> List[PickDict]:
        picks: List[PickDict] = []
        for p in props:
            proj: float = float(p.get("projected_value", 0))
            line: float = float(p.get("line", 0))
            direction: str = p.get("direction", "over")
            odds: float = float(p.get("american_odds", -110))
            edge: float = calculate_edge(proj, line, direction, odds)
            if edge > 4.0:
                pick = p.copy()
                pick["edge"] = edge
                pick["clear_pick"] = format_pick(pick)
                pick["timestamp"] = datetime.now(timezone.utc).isoformat()
                picks.append(pick)
        return picks

    def register_subscriber(self, callback: Callable[[LiveUpdate], Awaitable[None]]):
        self.subscribers.append(callback)

    def register_ws(self, ws: WebSocket):
        self._ws_clients.append(ws)

    def unregister_ws(self, ws: WebSocket):
        if ws in self._ws_clients:
            self._ws_clients.remove(ws)


engine = LiveEngine()

app = FastAPI(title="TC Sports Live Engine")


@app.on_event("startup")
async def startup():
    await engine.connect()
    asyncio.create_task(engine.subscribe_redis_pubsub())
    asyncio.create_task(background_update_mlb())
    asyncio.create_task(background_update_wnba())


async def background_update_mlb():
    while True:
        try:
            odds = get_odds("MLB", force_refresh=True)
            props = get_player_props("MLB")
            update: LiveUpdate = {
                "sport": "MLB",
                "odds": odds,
                "props": props,
                "picks": engine.calculate_picks(props),
                "timestamp": time.time(),
            }
            await engine.publish(update)
        except Exception as e:
            logger.error(f"MLB update error: {e}")
        await asyncio.sleep(45)


async def background_update_wnba():
    while True:
        try:
            odds = get_odds("WNBA", force_refresh=True)
            props = get_player_props("WNBA")
            update: LiveUpdate = {
                "sport": "WNBA",
                "odds": odds,
                "props": props,
                "picks": engine.calculate_picks(props),
                "timestamp": time.time(),
            }
            await engine.publish(update)
        except Exception as e:
            logger.error(f"WNBA update error: {e}")
        await asyncio.sleep(60)


@app.get("/api/live/odds/{sport}")
async def get_live_odds(sport: str):
    odds = get_odds(sport.upper(), force_refresh=True)
    return {"sport": sport.upper(), "odds": odds, "count": len(odds)}


@app.get("/api/live/picks/{sport}")
async def get_live_picks(sport: str):
    return {
        "sport": sport.upper(),
        "picks": engine.latest.get("picks", []),
        "timestamp": engine.latest.get("timestamp", 0),
    }


@app.get("/api/live/status")
async def get_status():
    return {
        "redis": "connected" if engine.redis_client else "disconnected",
        "latest_update": engine.latest.get("timestamp", 0),
        "ws_clients": len(engine._ws_clients),
        "subscribers": len(engine.subscribers),
    }


@app.get("/sse/odds/{sport}")
async def sse_odds(sport: str):
    async def event_stream():
        last_ts = 0
        while True:
            if engine.latest.get("timestamp", 0) > last_ts:
                last_ts = engine.latest["timestamp"]
                yield f"data: {json.dumps(engine.latest)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    engine.register_ws(ws)
    try:
        await ws.send_text(json.dumps(engine.latest))
        while True:
            data = await ws.receive_text()
            if data == "replay":
                await engine.replay_from_stream()
                await ws.send_text(json.dumps({"replay": "complete"}))
    except WebSocketDisconnect:
        engine.unregister_ws(ws)
    except Exception:
        engine.unregister_ws(ws)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
