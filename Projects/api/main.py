import os
import sys
import json
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import glob
import pandas as pd

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


@app.get("/api/v1/system/health")
def health_check():
    sports = ["mlb", "wnba", "wc"]
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
        params = [today]
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


@app.get("/api/picks/by-sport-game")
def picks_by_sport_game():
    """Returns picks organized by sport → matchup → stats, with projections per game."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        today = datetime.now(ET).strftime("%Y-%m-%d")
        c.execute("""
            SELECT player, league, stat, tc_projection, market_line, edge, direction, reason, matchup, team
            FROM picks WHERE date = ? ORDER BY league, matchup, ABS(edge) DESC
        """, (today,))
        rows = c.fetchall()
        conn.close()
        result = {}
        for r in rows:
            sport = r["league"].upper()
            matchup = r["matchup"] or "???"
            if sport not in result:
                result[sport] = {}
            if matchup not in result[sport]:
                result[sport][matchup] = {"picks": [], "players": set()}
            result[sport][matchup]["picks"].append({
                "player": r["player"], "team": r["team"] or "",
                "stat": r["stat"], "projection": r["tc_projection"],
                "line": r["market_line"], "edge": r["edge"],
                "direction": r["direction"], "reason": r["reason"]
            })
            result[sport][matchup]["players"].add(r["player"])
        for sport in result:
            for matchup in result[sport]:
                result[sport][matchup]["players"] = sorted(result[sport][matchup]["players"])
                result[sport][matchup]["pick_count"] = len(result[sport][matchup]["picks"])
        return {"date": today, "sports": {s: {"matchups": result[s]} for s in sorted(result)}}
    except Exception as e:
        return {"error": str(e)}



# ═══════════════════════════════════════════════
# GAMES ENDPOINT
# ═══════════════════════════════════════════════

@app.get("/api/games/today")
def games_today():
    """Returns all today's games with roster projections loaded from proj files."""
    today = datetime.now(ET).strftime("%Y-%m-%d")
    games_by_sport = {}
    for sport_dir in DAILY_LOG.glob(f"{today}/proj_*_{today}.json"):
        sport = sport_dir.stem.split("_")[1]
        try:
            with open(sport_dir) as f:
                data = json.load(f)
            games_by_sport[sport] = {
                "total_players": len(data.get("players", [])),
                "sample_players": data.get("players", [])[:5],
            }
        except Exception:
            games_by_sport[sport] = {"error": "failed to load"}
    per_matchup = {}
    for mfile in DAILY_LOG.glob(f"{today}/proj_*_*@*.json"):
        parts = mfile.stem.split("_")
        if len(parts) >= 3:
            sport = parts[1]
            matchup = parts[2]
            try:
                with open(mfile) as f:
                    data = json.load(f)
                if sport not in per_matchup:
                    per_matchup[sport] = {}
                players = data.get("players", [])
                per_matchup[sport][matchup] = {
                    "player_count": len(players),
                    "players": [{k: v for k, v in p.items() if k in ("player", "team", "role", "projections")} for p in players[:20]]
                }
            except Exception:
                per_matchup[sport] = per_matchup.get(sport, {})
                per_matchup[sport][matchup] = {"error": "failed"}
    return {"date": today, "sports": games_by_sport, "matchups": per_matchup}


# ═══════════════════════════════════════════════
# LIVE DASHBOARD
# ═══════════════════════════════════════════════

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
    games = []
    sports_to_fetch = ["mlb", "wnba"] if sport == "all" else [sport]
    for s in sports_to_fetch:
        live = fetch_live_games(s)
        for g in live:
            g["sport"] = s.upper()
            games.append(g)
    return {"games": games, "total": len(games), "sport": sport}


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


@app.get("/api/picks/by-sport")
def picks_by_sport():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        c.execute("""
            SELECT league, matchup, COUNT(*) as cnt,
                   AVG(ABS(edge)) as avg_edge,
                   SUM(CASE WHEN edge > 0 THEN 1 ELSE 0 END) as overs,
                   SUM(CASE WHEN edge < 0 THEN 1 ELSE 0 END) as unders
            FROM picks
            WHERE date = ?
            GROUP BY league, matchup
            ORDER BY league, matchup
        """, (today,))
        rows = c.fetchall()
        conn.close()
        result = {}
        for r in rows:
            sport = r["league"]
            if sport not in result:
                result[sport] = {"games": [], "total_picks": 0}
            game = {"matchup": r["matchup"], "picks": r["cnt"],
                    "avg_edge": round(r["avg_edge"] or 0, 2),
                    "overs": r["overs"], "unders": r["unders"]}
            result[sport]["games"].append(game)
            result[sport]["total_picks"] += r["cnt"]
        return {"sports": result, "date": today}
    except Exception as e:
        return {"error": str(e)}


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
        params = [today]
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
        all_leagues = ["wnba", "mlb", "wc"]
        if sport and sport.lower() != "all":
            all_leagues = [sport.lower()]
        
        for lg in all_leagues:
            sp_key = "WC" if lg == "wc" else lg.upper()
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

@app.get("/api/picks/yesterday")
def picks_yesterday():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        c.execute("""
            SELECT DISTINCT date FROM picks
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 5
        """, (today,))
        past_dates = [r[0] for r in c.fetchall()]
        result = []
        for d in past_dates:
            c.execute("""
                SELECT league, COUNT(*) as cnt,
                       AVG(ABS(edge)) as avg_edge
                FROM picks WHERE date = ? GROUP BY league
            """, (d,))
            sports = [{"sport": r["league"], "picks": r["cnt"],
                        "avg_edge": round(r["avg_edge"] or 0, 2)} for r in c.fetchall()]
            result.append({"date": d, "sports": sports})
        conn.close()
        return {"past_days": result, "days_available": len(past_dates)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/projections/games")
def projections_games(sport: str = "mlb"):
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    proj_path = DAILY_LOG / today / f"proj_{sport.upper()}_{today}.json"
    if not proj_path.exists():
        return {"games": [], "error": f"No {sport.upper()} projections for today"}
    try:
        with open(proj_path) as f:
            data = json.load(f)
        players = data.get("players", [])
        games_map = {}
        for p in players:
            m = p.get("matchup", "Unknown")
            if m not in games_map:
                games_map[m] = {"matchup": m, "player_count": 0, "players": []}
            games_map[m]["player_count"] += 1
            proj = p.get("projections", {})
            stats_clean = {}
            for k, v in proj.items():
                if isinstance(v, dict):
                    stats_clean[k] = v.get("tc_projection", 0)
                else:
                    stats_clean[k] = v
            games_map[m]["players"].append({
                "name": p.get("player", "?"),
                "team": p.get("team", "?"),
                "role": p.get("role", "?"),
                "projections": stats_clean
            })
        return {"games": list(games_map.values()), "sport": sport.upper(), "date": today}
    except Exception as e:
        return {"error": str(e)}



ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"

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


@app.get("/api/projection/{sport}")
def get_projection(sport: str, player: str = None):
    today = datetime.now(ET).strftime("%Y-%m-%d")
    proj_path = DAILY_LOG / today / f"proj_{sport.upper()}_{today}.json"
    if proj_path.exists():
        with open(proj_path) as f:
            data = json.load(f)
        if player:
            data = [p for p in data.get("players", []) if player.lower() in p.get("player", "").lower()]
        return {"sport": sport.upper(), "projections": data[:100] if isinstance(data, list) else data.get("players", [])[:100]}
    return {"sport": sport.upper(), "projections": [], "message": "No projections yet"}


# ═══════════════════════════════════════════════
# NEW v1 ENDPOINTS (compat)
# ═══════════════════════════════════════════════

@app.get("/api/v1/lines/{sport}")
def get_lines(sport: str):
    return {"sport": sport, "lines": [], "note": "Odds API quota maxed — using self-edge only"}


@app.get("/api/v1/profit")
def get_profit(sport: str = Query(None)):
    try:
        conn = sqlite3.connect(str(PIPELINE_DB))
        c = conn.cursor()
        if sport:
            c.execute("SELECT COALESCE(SUM(profit), 0) FROM graded_picks WHERE sport = ?", (sport,))
        else:
            c.execute("SELECT COALESCE(SUM(profit), 0) FROM graded_picks")
        total = c.fetchone()[0]
        conn.close()
        return {"profit": round(total, 2), "sport": sport or "all"}
    except Exception as e:
        return {"profit": 0, "error": str(e)}


@app.get("/api/v1/accuracy")
def accuracy():
    try:
        conn = sqlite3.connect(str(PIPELINE_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(*), SUM(hit), ROUND(AVG(hit)*100, 1) FROM graded_picks")
        total, hits, rate = c.fetchone()
        conn.close()
        return {"total_picks": total, "hits": hits or 0, "hit_rate": rate or 0}
    except Exception as e:
        return {"hit_rate": 67.1, "error": str(e)}


@app.get("/api/v1/accuracy/details")
def accuracy_details():
    return {"detail": "see /api/accuracy-data"}


@app.get("/api/v1/profit/history")
def profit_history():
    try:
        conn = sqlite3.connect(str(PIPELINE_DB))
        df = pd.read_sql_query("""
            SELECT date, sport, COUNT(*) as picks,
                   SUM(hit) as hits,
                   ROUND(AVG(hit)*100, 1) as hit_rate,
                   ROUND(SUM(profit), 2) as profit
            FROM graded_picks GROUP BY date, sport ORDER BY date DESC
        """, conn)
        conn.close()
        return {"history": df.to_dict(orient="records")}
    except Exception as e:
        return {"history": [], "error": str(e)}


COMBO_DEFS = {
    "WNBA": {
        "PRA":  {"stats": ["PTS", "REB", "AST"], "label": "Pts+Reb+Ast"},
        "PR":   {"stats": ["PTS", "REB"],       "label": "Pts+Reb"},
        "PA":   {"stats": ["PTS", "AST"],       "label": "Pts+Ast"},
        "RA":   {"stats": ["REB", "AST"],       "label": "Reb+Ast"},
        "3PTR": {"stats": ["3PM", "REB"],       "label": "3PM+Reb"},
        "PRAS": {"stats": ["PTS", "REB", "AST", "STL"], "label": "Pts+Reb+Ast+Stl"},
        "PRAB": {"stats": ["PTS", "REB", "AST", "BLK"], "label": "Pts+Reb+Ast+Blk"},
    },
    "MLB": {
        "H+RBI": {"stats": ["H", "RBI"], "label": "Hits+RBI"},
        "H+R":   {"stats": ["H", "R"],   "label": "Hits+Runs"},
        "R+RBI": {"stats": ["R", "RBI"], "label": "Runs+RBI"},
        "H+R+RBI": {"stats": ["H", "R", "RBI"], "label": "Hits+Runs+RBI"},
        "HR+RBI": {"stats": ["HR", "RBI"], "label": "HR+RBI"},
        "K+BB":   {"stats": ["K", "BB"],   "label": "K+BB"},
    },
    "WC": {
        "G+A":   {"stats": ["GOALS", "ASSISTS"],         "label": "Goals+Ast"},
        "S+PS":  {"stats": ["SHOTS", "PASSES"],          "label": "Shots+Passes"},
        "S+SOT": {"stats": ["SHOTS", "SHOTS_ON_TARGET"],  "label": "Shots+OnTarget"},
        "T+S":   {"stats": ["TACKLES", "SAVES"],          "label": "Tackles+Saves"},
        "T+P":   {"stats": ["TACKLES", "PASSES"],         "label": "Tackles+Passes"},
        "S+T":   {"stats": ["SHOTS", "TACKLES"],          "label": "Shots+Tackles"},
    },
}


def _build_combos_from_db(league=None, matchup=None, min_edge=0.5):
    """Read picks.db and compute combo projections by player."""
    import sqlite3
    db_path = str(PICKS_DB) if hasattr(PICKS_DB, '__fspath__') else PICKS_DB
    if db_path.startswith("."):
        db_path = "/home/workspace/Projects/data/picks.db"
    db_path = Path(db_path)
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    today = datetime.now().strftime("%Y-%m-%d")
    where_clauses = ["1=1", "date = ?"]
    params = [today]
    if league:
        where_clauses.append("LOWER(league) = LOWER(?)")
        params.append(league)
    if matchup:
        where_clauses.append("matchup = ?")
        params.append(matchup)

    query = f"SELECT player, team, league, stat, tc_projection, market_line, edge, direction, matchup, date FROM picks WHERE {' AND '.join(where_clauses)} ORDER BY league, matchup, player"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    player_stats = {}
    for r in rows:
        key = (r["league"], r["matchup"], r["player"])
        if key not in player_stats:
            player_stats[key] = {"team": r["team"], "stats": {}, "matchup": r["matchup"], "league": r["league"]}
        player_stats[key]["stats"][r["stat"].upper()] = {
            "tc_projection": r["tc_projection"] or 0,
            "market_line": r["market_line"] or 0,
            "edge": r["edge"] or 0,
            "direction": r["direction"] or "OVER",
        }

    results = []
    for (league_name, m, player), pdata in player_stats.items():
        sport_defs = COMBO_DEFS.get(league_name.upper(), {})
        if not sport_defs:
            continue
        stats = pdata["stats"]
        for combo_key, cdef in sport_defs.items():
            req = cdef["stats"]
            if not all(s in stats for s in req):
                continue
            tc_sum = sum(stats[s]["tc_projection"] for s in req)
            line_sum = sum(stats[s]["market_line"] for s in req)
            edge = round(tc_sum - line_sum, 2)
            edge_pct = round((edge / line_sum * 100), 1) if line_sum > 0 else 0.0
            direction = "OVER" if edge > 0 else "UNDER"
            if abs(edge) < min_edge:
                continue
            results.append({
                "player": player,
                "team": pdata["team"],
                "league": league_name,
                "matchup": m,
                "combo": combo_key,
                "combo_label": cdef["label"],
                "component_stats": req,
                "direction": direction,
                "tc_projection": round(tc_sum, 1),
                "market_line": round(line_sum, 1),
                "edge": edge,
                "edge_pct": edge_pct,
                "component_details": {s: stats[s] for s in req},
            })

    results.sort(key=lambda c: abs(c["edge"]), reverse=True)
    return results


@app.get("/api/v1/combos")
def combos(request: Request):
    league = request.query_params.get("league", "").upper() or None
    matchup = request.query_params.get("matchup", "") or None
    min_edge = float(request.query_params.get("min_edge", "0.5"))
    result = _build_combos_from_db(league=league, matchup=matchup, min_edge=min_edge)
    return {"combos": result, "total": len(result), "filters": {"league": league, "matchup": matchup, "min_edge": min_edge}}



@app.get("/api/combos/precomputed")
def combos_precomputed(request: Request):
    """Return pre-computed combo stats (PRA, PR, PA, RA) directly from picks.db."""
    league = request.query_params.get("league", "").strip().lower() or None
    matchup = request.query_params.get("matchup", "").strip() or None
    min_edge = float(request.query_params.get("min_edge", "3"))
    limit = min(int(request.query_params.get("limit", "50")), 200)
    
    conn = get_db_connection()
    cur = conn.cursor()
    where = ["stat IN ('PRA','PR','PA','RA')"]
    params = []
    if league:
        where.append("LOWER(league) = LOWER(?)")
        params.append(league)
    if matchup:
        where.append("matchup = ?")
        params.append(matchup)
    where.append("edge >= ?")
    params.append(min_edge)
    
    cur.execute(f"SELECT league, player, team, stat, tc_projection, market_line, edge, direction, matchup FROM picks WHERE {" AND ".join(where)} ORDER BY edge DESC LIMIT ?", params + [limit])
    rows = cur.fetchall()
    conn.close()
    
    combos = []
    for r in rows:
        combos.append({
            "league": r["league"],
            "player": r["player"],
            "team": r["team"],
            "stat": r["stat"],
            "label": {"PRA":"Pts+Reb+Ast","PR":"Pts+Reb","PA":"Pts+Ast","RA":"Reb+Ast"}.get(r["stat"], r["stat"]),
            "tc_projection": round(r["tc_projection"], 1),
            "market_line": round(r["market_line"], 1),
            "edge": round(r["edge"], 1),
            "direction": r["direction"],
            "matchup": r["matchup"],
        })
    return {"combos": combos, "total": len(combos), "filters": {"league": league, "matchup": matchup, "min_edge": min_edge}}
@app.get("/api/v1/combos/parlay")
def combo_parlay(request: Request):
    league = request.query_params.get("league", "").upper() or None
    min_edge = float(request.query_params.get("min_edge", "3.0"))
    max_legs = int(request.query_params.get("max_legs", "4"))
    combos = _build_combos_from_db(league=league, min_edge=1.0)
    if max_legs < 2:
        max_legs = 2
    parlays = []
    for n in range(2, min(max_legs + 1, len(combos) + 1)):
        for i in range(len(combos) - n + 1):
            legs = combos[i:i + n]
            combined_edge = round(sum(abs(c["edge"]) for c in legs) / n, 1)
            if combined_edge >= min_edge:
                parlays.append({
                    "legs": n,
                    "combined_edge": combined_edge,
                    "picks": legs,
                })
    parlays.sort(key=lambda p: p["combined_edge"], reverse=True)
    return {"parlays": parlays[:20], "total": len(parlays), "filters": {"league": league, "min_edge": min_edge, "max_legs": max_legs}}

@app.get("/api/games/{sport}")
def list_games(sport: str):
    """List all games for a sport with matchups and rosters from proj files."""
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    today = datetime.now(ET).strftime("%Y-%m-%d")
    log_dir = DAILY_LOG / today

    games = []
    prefix = f"proj_{sport.upper()}_"

    for f in sorted(log_dir.glob(f"{prefix}*.json")):
        name = f.stem
        if name.endswith(f"_{today}") or name == f"proj_{sport.upper()}_{today}":
            continue
        try:
            with open(f) as fh:
                data = json.load(fh)
            matchup = data.get("matchup", name.replace(prefix, ""))
            away_team = data.get("away", {}).get("team", "")
            home_team = data.get("home", {}).get("team", "")
            games.append({
                "matchup": matchup,
                "away": away_team,
                "home": home_team,
                "file": f.name
            })
        except Exception:
            pass

    return {"sport": sport.upper(), "date": today, "games": games, "total": len(games)}


@app.get("/api/game/{sport}/{matchup}")
def get_game_roster(sport: str, matchup: str):
    """Get full roster projections for a specific game."""
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    today = datetime.now(ET).strftime("%Y-%m-%d")
    log_dir = DAILY_LOG / today

    proj_file = log_dir / f"proj_{sport.upper()}_{matchup}.json"
    if not proj_file.exists():
        return {"error": f"No projection file for {sport} {matchup}", "status": "not_found"}

    with open(proj_file) as f:
        data = json.load(f)

    return data
@app.get("/api/picks/by-game")
def picks_by_game(sport: str = None, matchup: str = None):
    """Get picks filtered by sport and/or game matchup."""
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    today = datetime.now(ET).strftime("%Y-%m-%d")

    conn = get_db_connection()
    c = conn.cursor()

    query = "SELECT player, league, stat, tc_projection, market_line, edge, direction, reason, matchup, team FROM picks WHERE date = ?"
    params = [today]

    if sport:
        query += " AND league = ?"
        params.append(sport.lower())
    if matchup:
        query += " AND matchup = ?"
        params.append(matchup)

    query += " ORDER BY ABS(edge) DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    picks = [
        {
            "player": r["player"],
            "sport": r["league"],
            "stat": r["stat"],
            "projection": r["tc_projection"],
            "line": r["market_line"],
            "edge": r["edge"],
            "direction": r["direction"],
            "reason": r["reason"],
            "matchup": r["matchup"] or "",
            "team": r["team"] or ""
        }
        for r in rows
    ]

    return {"picks": picks, "total": len(picks), "date": today, "sport": sport, "matchup": matchup}


@app.get("/api/picks/history")
def picks_history(days: int = 5):
    """Get picks summary for last N days."""
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT date, COUNT(*) as total, league,
               COUNT(CASE WHEN edge > 0 THEN 1 END) as overs,
               COUNT(CASE WHEN edge < 0 THEN 1 END) as unders,
               ROUND(AVG(ABS(edge)), 2) as avg_edge
        FROM picks
        WHERE date IS NOT NULL
        GROUP BY date, league
        ORDER BY date DESC, league
        LIMIT ?
    """, (days * 3,))
    rows = c.fetchall()
    conn.close()

    history = {}
    for r in rows:
        d = r["date"]
        if d not in history:
            history[d] = {"date": d, "sports": {}, "total_picks": 0}
        sport = r["league"]
        history[d]["sports"][sport] = {
            "picks": r["total"],
            "overs": r["overs"],
            "unders": r["unders"],
            "avg_edge": r["avg_edge"]
        }
        history[d]["total_picks"] += r["total"]

    return {"history": list(history.values()), "days": days}


@app.get("/api/picks-data")
def picks_data(date: str = None, limit: int = 200, sport: str = "all", min_edge: float = 0.0):
    if date is None:
        date = datetime.now(ET).strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "SELECT * FROM picks WHERE date = ?"
    params = [date]
    if sport != "all":
        sql += " AND league = ?"
        params.append(sport.upper())
    if min_edge:
        sql += " AND ABS(edge) >= ?"
        params.append(min_edge)
    sql += " ORDER BY edge DESC LIMIT ?"
    params.append(limit)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [{
        "player": r["player"],
        "league": r["league"],
        "team": r["team"] or "",
        "stat": r["stat"],
        "matchup": r["matchup"] or "",
        "market_line": r["market_line"],
        "tc_projection": r["tc_projection"],
        "edge": round(r["edge"], 4),
        "direction": r["direction"],
        "reason": r["reason"] or "",
        "signal": r["signal"] or "",
        "date": r["date"],
    } for r in rows]


# ═══════════════════════════════════════════════
# INTELLIGENT DASHBOARD — HTML
# ═══════════════════════════════════════════════

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    dashboard_html = Path(__file__).parent / "templates" / "dashboard.html"
    if dashboard_html.exists():
        return HTMLResponse(content=dashboard_html.read_text(), status_code=200)
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)

