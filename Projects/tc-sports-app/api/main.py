from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PICKS_DB = os.path.join(DATA_DIR, "picks.db")
PIPELINE_DB = os.path.join(DATA_DIR, "tc_pipeline.db")

app = FastAPI(title="TC Sports API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_picks_conn():
    return sqlite3.connect(PICKS_DB)


def get_pipeline_conn():
    return sqlite3.connect(PIPELINE_DB)


@app.get("/api/v1/system/health")
def health():
    checks = {"api": "ok", "timestamp": datetime.now().isoformat()}
    checks["picks_db"] = os.path.exists(PICKS_DB)
    checks["pipeline_db"] = os.path.exists(PIPELINE_DB)

    if os.path.exists(PIPELINE_DB):
        try:
            conn = sqlite3.connect(PIPELINE_DB)
            cur = conn.execute("SELECT COUNT(*) FROM graded_picks")
            checks["graded_picks_count"] = cur.fetchone()[0]
            cur = conn.execute("SELECT COUNT(*) FROM bet_tracking")
            checks["bet_tracking_count"] = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            checks["db_error"] = str(e)
            return {"status": "degraded", "checks": checks}

    if os.path.exists(PICKS_DB):
        try:
            conn = sqlite3.connect(PICKS_DB)
            cur = conn.execute("SELECT COUNT(*) FROM picks")
            checks["picks_count"] = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            checks["db_error"] = str(e)
            return {"status": "degraded", "checks": checks}

    all_ok = checks.get("picks_db", False) and checks.get("pipeline_db", False)
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}


@app.get("/api/picks/top")
def picks_top(sport: str = None, limit: int = 50):
    if not os.path.exists(PICKS_DB):
        return {"error": "Database not initialized", "picks": []}
    conn = get_picks_conn()
    query = "SELECT id, player, team, sport, stat, projection, line, edge, signal, reason, outcome, date FROM picks WHERE 1=1"
    params = []
    if sport:
        query += " AND sport = ?"
        params.append(sport.lower())
    query += " ORDER BY ABS(edge) DESC LIMIT ?"
    params.append(limit)
    try:
        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return {"picks": rows, "count": len(rows)}
    except Exception as e:
        conn.close()
        return {"error": str(e), "picks": []}


@app.get("/api/picks/{date}")
def picks_by_date(date: str, sport: str = None):
    if not os.path.exists(PICKS_DB):
        return {"error": "Database not initialized", "picks": []}
    conn = get_picks_conn()
    query = "SELECT id, player, team, sport, stat, projection, line, edge, signal, reason, outcome, date FROM picks WHERE date = ?"
    params = [date]
    if sport:
        query += " AND sport = ?"
        params.append(sport.lower())
    query += " ORDER BY ABS(edge) DESC"
    try:
        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return {"date": date, "picks": rows, "count": len(rows)}
    except Exception as e:
        conn.close()
        return {"error": str(e), "picks": []}


@app.get("/api/v1/accuracy")
def accuracy(sport: str = None):
    if not os.path.exists(PIPELINE_DB):
        return {"error": "Pipeline database not initialized"}
    conn = get_pipeline_conn()
    query = """
        SELECT sport,
               ROUND(AVG(ABS(projection - actual)), 2) AS mae,
               ROUND(AVG(projection - actual), 2) AS bias,
               ROUND(AVG(hit) * 100, 1) AS hit_rate,
               COUNT(*) AS n
        FROM graded_picks
        WHERE actual IS NOT NULL
    """
    if sport:
        query += " AND sport = ?"
    query += " GROUP BY sport"
    try:
        cur = conn.execute(query, (sport,) if sport else ())
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return rows if rows else []
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.get("/api/v1/combos")
def combos(sport: str, date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(PICKS_DB):
        return {"combos": [], "error": "Database not initialized"}
    conn = get_picks_conn()
    try:
        cur = conn.execute(
            "SELECT player, team, sport, stat, projection, line, edge, signal, reason FROM picks WHERE sport = ? AND date = ? AND edge >= 0.5 ORDER BY edge DESC LIMIT 30",
            (sport.lower(), date),
        )
        cols = [d[0] for d in cur.description]
        players = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()

        combos = []
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                combo_edge = round((players[i]["edge"] + players[j]["edge"]) / 2, 2)
                combos.append(
                    {
                        "legs": [
                            {"player": players[i]["player"], "stat": players[i]["stat"],
                             "edge": players[i]["edge"]},
                            {"player": players[j]["player"], "stat": players[j]["stat"],
                             "edge": players[j]["edge"]},
                        ],
                        "combo_edge": combo_edge,
                        "sport": sport.upper(),
                    }
                )
        combos.sort(key=lambda x: x["combo_edge"], reverse=True)
        return combos[:20] if combos else []
    except Exception as e:
        conn.close()
        return {"combos": [], "error": str(e)}


@app.get("/api/stats/dashboard")
def stats_dashboard():
    if not os.path.exists(PIPELINE_DB):
        return {"error": "Pipeline database not initialized"}
    conn = get_pipeline_conn()
    try:
        cur = conn.execute("SELECT COUNT(*) AS total, ROUND(AVG(hit) * 100, 1) AS win_rate, ROUND(AVG(edge), 2) AS avg_edge FROM graded_picks WHERE actual IS NOT NULL")
        row = cur.fetchone()
        total = row[0] or 0
        win_rate = row[1] or 0.0
        avg_edge = row[2] or 0.0

        cur = conn.execute("SELECT date, SUM(hit) AS wins, COUNT(*)-SUM(hit) AS losses FROM graded_picks WHERE actual IS NOT NULL GROUP BY date ORDER BY date DESC LIMIT 30")
        trend = [{"day": r[0], "wins": r[1], "losses": r[2]} for r in cur.fetchall()]

        conn.close()
        return {"total_bets": total, "win_rate": win_rate, "avg_edge": avg_edge, "trend": trend}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.get("/api/stats/recap")
def stats_recap(date: str = None):
    if not date:
        date = (datetime.now().strftime("%Y-%m-%d"))
    if not os.path.exists(PIPELINE_DB):
        return []
    conn = get_pipeline_conn()
    try:
        cur = conn.execute(
            "SELECT player, team, sport, stat, projection, line, actual, hit, edge FROM graded_picks WHERE date = ? AND actual IS NOT NULL ORDER BY hit DESC",
            (date,),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        conn.close()
        return []


@app.get("/api/v1/lines/mlb")
def lines_mlb():
    return {"data": {"games": [], "note": "Live odds via SportsDataIO — configure SPORTSDATA_KEY_MLB"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
