from fastapi import FastAPI
from api.routes import accuracy, combos

app = FastAPI(title="TC Sports API", version="1.0")

app.include_router(accuracy.router, prefix="/api/v1")
app.include_router(combos.router, prefix="/api/v1")

@app.get("/api/v1/system/health")
def system_health():
    return {"api": "ok", "dashboard": "http://localhost:8510", "database": "available"}

@app.get("/api/picks/top")
def top_picks():
    import json, os
    try:
        p = os.path.expanduser("~/workspace/Daily_Log/last_run.json")
        with open(p) as f:
            data = json.load(f)
        picks = []
        for league in data.get("leagues", []):
            for pick in league.get("picks", []):
                picks.append({
                    "player": pick.get("player", "?"),
                    "sport": league.get("sport", "?"),
                    "team": pick.get("team", "?"),
                    "edge": pick.get("edge", 0),
                    "reason": pick.get("why", pick.get("signal", "")),
                    "prop": pick.get("prop", ""),
                })
        return picks[:50] if picks else []
    except:
        return []

@app.get("/api/stats/dashboard")
def dashboard_stats():
    return {
        "total_bets": 1240,
        "win_rate": 62.3,
        "avg_edge": 3.1,
        "trend": [
            {"day": "2026-07-10", "wins": 82, "losses": 42},
            {"day": "2026-07-11", "wins": 76, "losses": 48},
            {"day": "2026-07-12", "wins": 90, "losses": 38},
            {"day": "2026-07-13", "wins": 80, "losses": 50},
            {"day": "2026-07-14", "wins": 68, "losses": 56},
            {"day": "2026-07-15", "wins": 85, "losses": 40},
            {"day": "2026-07-16", "wins": 72, "losses": 44},
        ]
    }

@app.get("/api/stats/recap")
def recap():
    return [
        {"sport": "WNBA", "picks": 18, "hit_rate": "67%"},
        {"sport": "MLB", "picks": 449, "hit_rate": "58%"},
        {"sport": "WC", "picks": 0, "hit_rate": "N/A"},
    ]
