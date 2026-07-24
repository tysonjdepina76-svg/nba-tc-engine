import os
import sys
import json
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.api_cap_tracker import cap_check

sys.path.insert(0, "/home/workspace/Projects")
sys.path.insert(0, "/home/workspace/Projects/src")

app = FastAPI(title="TC Sports API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DAILY_LOG = Path("/home/workspace/Daily_Log")
PICKS_DB = Path("/home/workspace/Projects/data/picks.db")
PIPELINE_DB = Path("/home/workspace/Projects/data/tc_pipeline.db")
LOG_FILE = DAILY_LOG / "last_run.json"
ET = ZoneInfo("America/New_York")


def get_db_connection(db_path=None):
    conn = sqlite3.connect(str(db_path or PICKS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_live_games(sport):
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    if sport == "wnba":
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        games = []
        for event in data.get("events", []):
            comps = event.get("competitions", [])
            if not comps:
                continue
            c = comps[0]
            teams_list = []
            for competitor in c.get("competitors", []):
                team_name = competitor.get("team", {}).get("abbreviation", "?")
                side = "home" if competitor.get("homeAway") == "home" else "away"
                score = int(competitor.get("score", 0) or 0)
                players = []
                for plr in competitor.get("roster", [])[:8]:
                    players.append({
                        "name": plr.get("athlete", {}).get("displayName", "?"),
                        "team": team_name,
                        "role": plr.get("position", {}).get("abbreviation", "BAT"),
                    })
                teams_list.append({"name": team_name, "side": side, "players": players, "score": score})
            games.append({
                "shortName": event.get("shortName", "?"),
                "sport": sport.upper(),
                "state": c.get("status", {}).get("type", {}).get("state", "pre"),
                "period": c.get("status", {}).get("period", 0),
                "clock": c.get("status", {}).get("displayClock", ""),
                "away_score": c.get("competitors", [{}])[1].get("score", 0) if len(c.get("competitors", [])) > 1 else 0,
                "home_score": c.get("competitors", [{}])[0].get("score", 0) if c.get("competitors", []) else 0,
                "teams": teams_list,
            })
        return games
    except Exception:
        return []


# ═══════════════════════════════════════════════
# HEALTH & SYSTEM
# ═══════════════════════════════════════════════

@app.get("/")
def root():
    return {"app": "TC Sports API", "version": "2.0", "docs": "/docs"}
@app.get("/health")
def health_check():
    """Comprehensive health check — database, daily log, picks summary."""
    health = {
        "status": "healthy",
        "timestamp": datetime.now(ET).strftime("%Y-%m-%d %I:%M:%S %p") + " ET",
        "version": "2.0",
        "components": {
            "database": {"status": "unknown", "path": str(PICKS_DB)},
            "daily_log": {"status": "unknown", "path": str(DAILY_LOG)}
        },
        "picks_summary": {"total": 0, "by_league": {}, "today": 0}
    }

    try:
        if PICKS_DB.exists():
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM picks")
            health["picks_summary"]["total"] = cur.fetchone()[0]
            cur.execute("SELECT league, COUNT(*) FROM picks GROUP BY league")
            for row in cur.fetchall():
                health["picks_summary"]["by_league"][row[0]] = row[1]
            today_str = datetime.now(ET).strftime("%Y-%m-%d")
            cur.execute("SELECT COUNT(*) FROM picks WHERE date = ?", (today_str,))
            health["picks_summary"]["today"] = cur.fetchone()[0]
            conn.close()
            health["components"]["database"]["status"] = "up"
    except Exception as e:
        health["components"]["database"]["status"] = f"error: {e}"
        health["status"] = "degraded"

    try:
        if DAILY_LOG.exists():
            today_dir = DAILY_LOG / datetime.now(ET).strftime("%Y-%m-%d")
            proj_files = list(today_dir.glob("proj_*.json")) if today_dir.exists() else []
            health["components"]["daily_log"] = {"status": "up", "projections_today": len(proj_files)}
    except Exception as e:
        health["components"]["daily_log"]["status"] = f"error: {e}"

    return health



@app.get("/api/v1/system/health")
def system_health_check():
    sports = ["mlb", "wnba"]
    enabled = sum(1 for s in sports if (DAILY_LOG / datetime.now(ET).strftime("%Y-%m-%d") / f"proj_{s.upper()}_{datetime.now(ET).strftime('%Y-%m-%d')}.json").exists())
    return {"status": "healthy", "sports_enabled": enabled, "timestamp": datetime.now().isoformat()}


# ═══════════════════════════════════════════════
# PICKS ENDPOINTS
# ═══════════════════════════════════════════════

@app.get("/api/picks/top")
def get_top_picks(limit: int = 50, sport: str = None, min_edge: float = -100.0):
    """Get top picks. Pass sport=mlb/wnba/wc to filter. min_edge filter removed by default."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        today = datetime.now(ET).strftime("%Y-%m-%d")
        query = "SELECT player, league, stat, tc_projection, market_line, edge, direction, reason, matchup, team FROM picks WHERE date = ?"
        params = []
        if sport:
            query += " AND LOWER(league) = ?"
            params.append(sport.lower())
        if min_edge > -100.0:
            query += " AND ABS(edge) >= ?"
            params.append(min_edge)
        query += " ORDER BY ABS(edge) DESC LIMIT ?"
        params.append(limit)
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [{
            "player": r["player"], "sport": r["league"], "stat": r["stat"],
            "projection": r["tc_projection"], "line": r["market_line"],
            "edge": r["edge"], "direction": r["direction"],
            "reason": r["reason"], "matchup": r["matchup"] or "", "team": r["team"] or ""
        } for r in rows]
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/live-dashboard")
def live_dashboard(sport: str = "all"):
    today = datetime.now(ET).strftime("%Y-%m-%d")
    dash_path = DAILY_LOG / today / "live_dashboard.json"
    if dash_path.exists():
        with open(dash_path) as f:
            data = json.load(f)
        games = data.get("games", [])
        if sport != "all":
            sport_upper = sport.upper()
            games = [g for g in games if g.get("sport", "").upper() == sport_upper]
        for g in games:
            if "home_team" not in g:
                teams = g.get("teams", [])
                g["home_team"] = teams[1]["name"] if len(teams) > 1 else "?"
                g["away_team"] = teams[0]["name"] if len(teams) > 0 else "?"
        return {"games": games, "total": len(games), "sport": sport}
    from api.live_boxscore import fetch_all_boxscores
    bs = fetch_all_boxscores(sport)
    all_games = []
    for sport_key, sd in bs.get("sports", {}).items():
        for g in sd.get("games", []):
            g["sport"] = sport_key
            all_games.append(g)
    return {"games": all_games, "total": len(all_games), "sport": sport}


# ═══════════════════════════════════════════════
# ACCURACY & SYSTEM
# ═══════════════════════════════════════════════

@app.get("/api/accuracy-data")
def accuracy_data():
    try:
        conn = sqlite3.connect(str(PIPELINE_DB))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT sport, COUNT(*) as total,
                   SUM(hit) as hits,
                   ROUND(AVG(hit) * 100, 1) as hit_rate,
                   ROUND(AVG(ABS(projection - actual)), 2) as mae,
                   ROUND(SUM(profit), 2) as profit
            FROM graded_picks GROUP BY sport
        """)
        rows = c.fetchall()
        conn.close()
        sports = [dict(r) for r in rows]
        total_picks = sum(r["total"] for r in rows)
        total_hits = sum(r["hits"] for r in rows)
        total_profit = sum(r["profit"] for r in rows)
        overall_hit_rate = round(total_hits / total_picks * 100, 1) if total_picks > 0 else 0
        return {
            "sports": sports,
            "by_sport": sports,
            "total": total_picks,
            "hit_rate": overall_hit_rate,
            "graded": total_picks,
            "total_picks": total_picks,
            "profit": round(total_profit, 2),
            "avg_edge": "N/A (lines unavailable)",
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/system-data")
def system_data():
    result = {}
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            result["last_run"] = json.load(f)
    today = datetime.now(ET).strftime("%Y-%m-%d")
    today_dir = DAILY_LOG / today
    result["today_files"] = sorted([f.name for f in today_dir.iterdir()]) if today_dir.exists() else []

    # Add picks counts from picks.db
    try:
        conn = sqlite3.connect(str(PICKS_DB))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM picks")
        row = c.fetchone()
        result["total_picks"] = row["cnt"] if row else 0
        conn.close()
    except:
        result["total_picks"] = 0

    result["status"] = "operational"
    result["alerts_count"] = 0
    try:
        alerts_file = today_dir / "alerts.json"
        if alerts_file.exists():
            with open(alerts_file) as f:
                alerts_data = json.load(f)
            result["alerts_count"] = len(alerts_data.get("alerts", []))
    except:
        pass

    return result


@app.get("/api/picks/by-game-structured")
def picks_by_game_structured(sport: str = None):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        ET = ZoneInfo("America/New_York")
        today = datetime.now(ET).strftime("%Y-%m-%d")

        query = """
            SELECT player, league, team, stat, tc_projection, market_line,
                   edge, direction, reason, matchup
            FROM picks WHERE date = ?
        """
        params = []
        if sport and sport.lower() != "all":
            query += " AND LOWER(league) = ?"
            params.append(sport.lower())
        query += " ORDER BY league, matchup, ABS(edge) DESC"

        c.execute(query, params)
        rows = c.fetchall()

        sports_map = {}
        for r in rows:
            sp = r["league"].upper()
            m = r["matchup"] or "TBD"
            if sp not in sports_map:
                sports_map[sp] = {}
            if m not in sports_map[sp]:
                sports_map[sp][m] = {"matchup": m, "picks": [], "total_picks": 0, "max_edge": 0}

            pick = {
                "player": r["player"],
                "team": r["team"] or "",
                "stat": r["stat"],
                "projection": r["tc_projection"],
                "line": r["market_line"],
                "edge": r["edge"],
                "direction": r["direction"],
                "reason": r["reason"]
            }
            sports_map[sp][m]["picks"].append(pick)
            sports_map[sp][m]["total_picks"] += 1
            if abs(r["edge"]) > abs(sports_map[sp][m]["max_edge"]):
                sports_map[sp][m]["max_edge"] = r["edge"]

        # AFTER building sports_map from today, fill gaps per-sport
        # Find the latest date that has picks for a sport if today has none
        all_leagues = ["wnba", "mlb"]
        if sport and sport.lower() != "all":
            all_leagues = [sport.lower()]
        
        for lg in all_leagues:
            sp_key = lg.upper()
            if sp_key in sports_map and sports_map[sp_key]:
                continue  # Today already has picks for this sport
            
            # This sport has no picks today — find latest date for this sport
            c.execute(
                "SELECT date FROM picks WHERE LOWER(league) = ? ORDER BY date DESC LIMIT 1",
                [lg]
            )
            row = c.fetchone()
            if not row:
                continue
            fallback_date = row[0]
            
            c.execute(
                """SELECT player, league, team, stat, tc_projection, market_line,
                          edge, direction, reason, matchup
                   FROM picks WHERE date = ? AND LOWER(league) = ?
                   ORDER BY matchup, ABS(edge) DESC""",
                [fallback_date, lg]
            )
            fb_rows = c.fetchall()
            for r in fb_rows:
                sp = r["league"].upper()
                m = r["matchup"] or "TBD"
                if sp not in sports_map:
                    sports_map[sp] = {}
                if m not in sports_map[sp]:
                    sports_map[sp][m] = {"matchup": m, "picks": [], "total_picks": 0, "max_edge": 0}
                pick = {
                    "player": r["player"],
                    "team": r["team"] or "",
                    "stat": r["stat"],
                    "projection": r["tc_projection"] or 0,
                    "line": r["market_line"] or 0,
                    "edge": r["edge"] or 0,
                    "direction": r["direction"] or "OVER",
                    "reason": r["reason"] or "",
                }
                sports_map[sp][m]["picks"].append(pick)
                sports_map[sp][m]["total_picks"] += 1
                if abs(pick["edge"]) > abs(sports_map[sp][m]["max_edge"]):
                    sports_map[sp][m]["max_edge"] = pick["edge"]

        conn.close()

        result = {"date": today, "sports": {}}
        for sp_name, matchups in sports_map.items():
            games_list = sorted(matchups.values(), key=lambda g: -abs(g["max_edge"]))
            for g in games_list:
                g["picks"].sort(key=lambda p: -abs(p["edge"]))
            result["sports"][sp_name] = {
                "games": games_list,
                "game_count": len(games_list),
                "total_picks": sum(g["total_picks"] for g in games_list),
            }

        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/box-scores")
def box_scores(sport: str = "all", refresh: str = "false"):
    """Returns live box scores for WNBA/MLB with full player stats and TC pick overlay.
    
    Data is cached for 5 minutes. Use refresh=true to force a fresh fetch.
    """
    try:
        from api.live_boxscore import fetch_all_boxscores, BOXSCORE_DIR
    except ImportError:
        return {"error": "live_boxscore module not found", "games": []}
    
    if refresh.lower() == "true":
        data = fetch_all_boxscores(sport.lower())
    else:
        # Serve from cache if fresh
        import time
        cache_key = f"boxscore_{sport.lower()}_{datetime.now().strftime('%Y%m%d')}.json"
        cache_path = BOXSCORE_DIR / cache_key
        CACHE_TTL = 300
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < CACHE_TTL:
                with open(cache_path) as f:
                    return json.load(f)
        data = fetch_all_boxscores(sport.lower())
    
    return data
@app.get("/api/tc-alerts")
def tc_alerts(limit: int = 50, min_edge: float = 0.02, sport: str = "all"):
    today = datetime.now(ET).strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM picks WHERE date = ? AND edge >= ?"
        + (" AND league = ?" if sport != "all" else "")
        + " ORDER BY edge DESC LIMIT ?",
        [today, min_edge] + ([sport.upper()] if sport != "all" else []) + [limit]
    )
    rows = cursor.fetchall()
    conn.close()
    alerts = []
    for r in rows:
        edge = r["edge"]
        abs_edge = abs(edge)
        if abs_edge >= 0.06:
            level = "STRONG"
        elif abs_edge >= 0.04:
            level = "MODERATE"
        else:
            level = "LIGHT"
        alerts.append({
            "player": r["player"],
            "league": r["league"],
            "stat": r["stat"],
            "direction": r["direction"],
            "matchup": r["matchup"] or "",
            "market_line": r["market_line"],
            "tc_projection": r["tc_projection"],
            "edge": round(edge, 4),
            "why": r["reason"] or "",
            "alert_level": level,
            "signal": r["signal"] or level,
            "team": r["team"] or "",
        })
    return {"generated": today, "total": len(alerts), "alerts": alerts}


@app.get("/api/injuries")
def injuries(sport: str = "all"):
    today = datetime.now(ET).strftime("%Y-%m-%d")
    inj_path = DAILY_LOG / today / "injuries.json"
    if inj_path.exists():
        with open(inj_path) as f:
            data = json.load(f)
        if sport != "all":
            data = [i for i in (data if isinstance(data, list) else data.get("injuries", [])) if i.get("sport", "").upper() == sport.upper()]
        return {"injuries": data}
    return {"injuries": [], "message": "No injury data yet today"}


# Combo definitions
COMBO_DEFS = {
    "WNBA": {
        "PRA":  {"label": "Pts+Reb+Ast", "stats": ["PTS", "REB", "AST"]},
        "PR":   {"label": "Pts+Reb",     "stats": ["PTS", "REB"]},
        "PA":   {"label": "Pts+Ast",     "stats": ["PTS", "AST"]},
        "RA":   {"label": "Reb+Ast",     "stats": ["REB", "AST"]},
        "3S":   {"label": "3PM+STL",     "stats": ["3PM", "STL"]},
        "SB":   {"label": "STL+BLK",     "stats": ["STL", "BLK"]},
    },
    "MLB": {
        "HR":   {"label": "H+R",         "stats": ["H", "R"]},
        "HRBI": {"label": "H+RBI",       "stats": ["H", "RBI"]},
        "RRBI": {"label": "R+RBI",       "stats": ["R", "RBI"]},
        "HRR":  {"label": "H+R+RBI",     "stats": ["H", "R", "RBI"]},
        "HRRBI2": {"label": "HR+RBI",    "stats": ["HR", "RBI"]},
        "KB":   {"label": "K+BB",         "stats": ["K", "BB"]},
    }
}


def _fetch_combos_from_table(league=None, min_edge=0.5, limit=50):
    """Read pre-computed combos from combos table — fast, no on-the-fly math."""
    db_path = PICKS_DB
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    where_clauses = []
    params = []
    if league:
        where_clauses.append("LOWER(league) = LOWER(?)")
        params.append(league)
    if where_clauses:
        query = f"SELECT * FROM combos WHERE {' AND '.join(where_clauses)} ORDER BY ABS(edge) DESC LIMIT ?"
    else:
        query = f"SELECT * FROM combos ORDER BY ABS(edge) DESC LIMIT ?"
    params.append(limit)
    try:
        rows = conn.execute(query, params).fetchall()
    except:
        conn.close()
        return []
    results = []
    for r in rows:
        results.append({
            "combo_type": r["combo_type"],
            "players": r["players"],
            "league": r["league"],
            "date": r["date"],
            "combined_projection": r["combined_projection"],
            "combined_line": r["combined_line"],
            "edge": r["edge"],
            "projections": r["projections"] if "projections" in r.keys() else "",
        })
    conn.close()
    return results

def _build_combos_from_db(league=None, matchup=None, min_edge=0.5):
    """Read combos table directly — no recomputation from picks."""
    db_path = PICKS_DB
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    where_clauses = ["1=1"]
    params = []
    if league:
        where_clauses.append("LOWER(league) = LOWER(?)")
        params.append(league)
    if matchup:
        where_clauses.append("matchup = ?")
        params.append(matchup)
    query = f"""SELECT id, date, league, combo_type, players, projections,
                       combined_projection, combined_line, edge, direction, matchup, created_at
                FROM combos WHERE {' AND '.join(where_clauses)}
                ORDER BY ABS(edge) DESC LIMIT 50"""
    rows = conn.execute(query, params).fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "date": r["date"],
            "league": r["league"],
            "combo": r["combo_type"],
            "combo_label": r["combo_type"],
            "players": r["players"],
            "projections": r["projections"],
            "tc_projection": round(r["combined_projection"], 1),
            "market_line": round(r["combined_line"], 1),
            "edge": r["edge"] or 0,
            "edge_pct": round((r["edge"] / r["combined_line"] * 100), 1) if r["combined_line"] and r["combined_line"] > 0 else 0,
            "direction": r["direction"] or "OVER",
            "matchup": r["matchup"] or "",
            "created_at": r["created_at"],
        })
    return results

@app.get("/api/v1/combos")
def combos(request: Request):
    league = request.query_params.get("league", "").upper() or None
    matchup = request.query_params.get("matchup", "") or None
    min_edge = float(request.query_params.get("min_edge", "0.5"))
    result = _fetch_combos_from_table(league=league, min_edge=min_edge)
    return {"combos": result, "total": len(result), "filters": {"league": league, "matchup": matchup, "min_edge": min_edge}}

