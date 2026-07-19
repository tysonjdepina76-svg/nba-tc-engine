#!/usr/bin/env python3
"""Add new dashboard API endpoints to main.py"""
import sys
sys.path.insert(0, "/home/workspace/Projects")

# Read current main.py
with open("/home/workspace/Projects/api/main.py") as f:
    content = f.read()

# New endpoints to add before the final if __name__ block
new_endpoints = '''
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
'''

# Insert new endpoints before the "if __name__" line
if 'if __name__ == "__main__":' in content:
    parts = content.split('if __name__ == "__main__":')
    new_content = parts[0] + new_endpoints + '\nif __name__ == "__main__":' + parts[1]
else:
    new_content = content + new_endpoints

with open("/home/workspace/Projects/api/main.py", "w") as f:
    f.write(new_content)

print("API endpoints added successfully")
print("New endpoints: /api/games/{sport}, /api/game/{sport}/{matchup}, /api/picks/by-game, /api/picks/history")
