"""FastAPI Application — Stagger API for the TC Engine.

Serves picks, odds, live data, backtest results, combos, and system health.
Connects to the TC engine modules for real computation.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pathlib import Path
import json
import sqlite3

from stagger.models import PicksResponse, AccuracyResponse, SystemHealth, LiveDashboardResponse

app = FastAPI(title="TC Stagger API", version="2.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PICKS_DB = Path("/home/workspace/Projects/data/picks.db")
PIPELINE_DB = Path("/home/workspace/Projects/data/tc_pipeline.db")
DAILY_LOG = Path("/home/workspace/Daily_Log")


def _db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def root():
    return {"service": "TC Stagger API", "version": "2.0.0", "status": "operational", "docs": "/docs"}


@app.get("/health", response_model=SystemHealth)
def health():
    try:
        sports_enabled = len(["mlb", "wnba", "wc"])
        return SystemHealth(
            status="healthy",
            sports_enabled=sports_enabled,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        return SystemHealth(status="unhealthy", sports_enabled=0, timestamp=datetime.now().isoformat())


@app.get("/api/v1/lines/{sport}")
def get_lines(sport: str):
    if sport not in ["mlb", "wnba", "wc"]:
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not available")
    return {"sport": sport, "data": [], "timestamp": datetime.now().isoformat(), "note": "TC self-edge lines"}


@app.get("/api/picks/top", response_model=PicksResponse)
def top_picks(limit: int = Query(20, ge=1, le=200), sport: str = Query("all")):
    conn = _db(PICKS_DB)
    c = conn.cursor()

    if sport == "all":
        c.execute("""SELECT player, league, stat, tc_projection, market_line, edge, direction, reason, matchup
                     FROM picks ORDER BY ABS(edge) DESC LIMIT ?""", (limit,))
    else:
        c.execute("""SELECT player, league, stat, tc_projection, market_line, edge, direction, reason, matchup
                     FROM picks WHERE league = ? ORDER BY ABS(edge) DESC LIMIT ?""", (sport.upper(), limit))

    rows = c.fetchall()
    conn.close()

    picks = [dict(r) for r in rows]
    return PicksResponse(picks=picks, count=len(picks))


@app.get("/api/accuracy", response_model=AccuracyResponse)
def accuracy():
    conn = _db(PIPELINE_DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) as total FROM graded_picks")
    total = c.fetchone()["total"]
    c.execute("SELECT COUNT(*) as hits FROM graded_picks WHERE hit = 1")
    hits = c.fetchone()["hits"]
    hit_rate = round(hits / total * 100, 1) if total else 0

    c.execute("SELECT sport, COUNT(*) as cnt, SUM(CASE WHEN hit=1 THEN 1 ELSE 0 END) as hits FROM graded_picks GROUP BY sport")
    by_sport = [{"sport": r["sport"], "count": r["cnt"], "hits": r["hits"], "hit_rate": round(r["hits"] / r["cnt"] * 100, 1) if r["cnt"] else 0} for r in c.fetchall()]

    c.execute("SELECT SUM(profit) as profit FROM bet_tracking")
    profit_row = c.fetchone()
    profit = profit_row["profit"] or 0 if profit_row else 0

    conn.close()
    return AccuracyResponse(total_graded=total, hits=hits, hit_rate=hit_rate, profit=round(profit, 2), by_sport=by_sport)


@app.get("/api/live-dashboard", response_model=LiveDashboardResponse)
def live_dashboard(sport: str = Query("all")):
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    today = datetime.now(ET).strftime("%Y-%m-%d")
    dash_path = DAILY_LOG / today / "live_dashboard.json"

    games = []
    if dash_path.exists():
        with open(dash_path) as f:
            data = json.load(f)
        games = data.get("games", [])
        if sport != "all":
            games = [g for g in games if g.get("sport", "").upper() == sport.upper()]

    return LiveDashboardResponse(games=games, total=len(games), sport=sport)


@app.get("/api/system-data")
def system_data():
    conn = _db(PICKS_DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM picks")
    pick_count = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(DISTINCT player) as cnt FROM picks")
    player_count = c.fetchone()["cnt"]
    c.execute("SELECT league as sport, COUNT(*) as cnt FROM picks GROUP BY league")
    by_sport = [{"sport": r["sport"], "count": r["cnt"]} for r in c.fetchall()]
    conn.close()

    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    today = datetime.now(ET).strftime("%Y-%m-%d")
    dash_path = DAILY_LOG / today / "live_dashboard.json"
    live_games = 0
    if dash_path.exists():
        with open(dash_path) as f:
            data = json.load(f)
        live_games = len([g for g in data.get("games", []) if g.get("state") == "in"])

    return {
        "picks_today": pick_count,
        "players_projected": player_count,
        "live_games": live_games,
        "by_sport": by_sport,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/backtest")
def backtest_summary():
    from engine.backtest import BacktestRunner
    runner = BacktestRunner()
    results = runner.run()
    return results


@app.get("/api/combo-trigger")
def combo_trigger(sport: str = Query("mlb"), min_edge: float = Query(5.0)):
    conn = _db(PICKS_DB)
    df_query = "SELECT player, league, stat, tc_projection, market_line, edge, direction FROM picks WHERE ABS(edge) >= ?"
    import pandas as pd
    df = pd.read_sql_query(df_query, conn, params=(min_edge,))
    conn.close()

    if df.empty:
        return {"combos": [], "message": f"No picks with edge >= {min_edge}%"}

    if sport != "all":
        df = df[df["league"] == sport.upper()]

    high_edge = df.sort_values("edge", key=abs, ascending=False)
    combos = []
    for i in range(0, len(high_edge) - 1, 2):
        if i + 1 < len(high_edge):
            leg1 = high_edge.iloc[i]
            leg2 = high_edge.iloc[i + 1]
            combos.append({
                "legs": [
                    {"player": leg1["player"], "stat": leg1["stat"], "edge": leg1["edge"], "direction": leg1["direction"]},
                    {"player": leg2["player"], "stat": leg2["stat"], "edge": leg2["edge"], "direction": leg2["direction"]},
                ],
                "combined_edge": round((abs(leg1["edge"]) + abs(leg2["edge"])) / 2, 1),
            })

    return {"combos": combos, "count": len(combos)}
