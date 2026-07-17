from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sqlite3
import os
import sys
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.entities import REGISTRY
from src.adapters.line_fetcher import fetch_lines

app = FastAPI(title="TC Sports API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection(db_path="data/picks.db"):
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def root():
    return {"message": "TC Sports API", "version": "1.0.0", "status": "operational"}

@app.get("/api/v1/system/health")
def health_check():
    try:
        enabled = len(REGISTRY.list_enabled())
        return {"status": "healthy", "sports_enabled": enabled, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/v1/lines/{sport}")
def get_lines(sport: str):
    if sport not in ["mlb", "wnba", "wc"]:
        raise HTTPException(status_code=404, detail="Sport not found")
    data = fetch_lines(sport)
    return {"sport": sport, "data": data, "timestamp": datetime.now().isoformat()}

@app.get("/api/picks/top")
def get_top_picks(limit: int = 20):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT player, league, stat, tc_projection, market_line, edge, direction, reason
            FROM picks
            ORDER BY edge DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return []
        return [
            {
                "player": r["player"],
                "sport": r["league"],
                "stat": r["stat"],
                "projection": r["tc_projection"],
                "line": r["market_line"],
                "edge": r["edge"],
                "direction": r["direction"],
                "reason": r["reason"]
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.get("/api/projection/{sport}")
def get_projection(sport: str, player: str = None):
    try:
        if sport not in ["wnba", "wc", "mlb"]:
            return {"error": f"Sport '{sport}' is not active.", "status": "failed"}
        projection = {
            "player": player or "Sample Player",
            "team": "TBD",
            "projection": 10.0,
            "line": 9.0,
            "edge": 1.0,
            "direction": "OVER",
            "confidence": 0.75
        }
        return {"sport": sport, "projection": projection, "status": "success", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc(), "status": "failed"}

try:
    from api.routes import accuracy, combos
    app.include_router(accuracy.router, prefix="/api/v1")
    app.include_router(combos.router, prefix="/api/v1")
except ImportError:
    pass
