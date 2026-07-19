"""ESPN Site API Boxscore Engine — single-call WNBA/MLB player stats with TC pick overlay.

Uses the ESPN site API summary endpoint (one HTTP call per game) instead of the
slow ESPN core API (one call per player). Returns full rosters, individual stats,
and overlays TC picks from picks.db.
"""
import json
import requests
import sqlite3
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports"
PICKS_DB = Path("/home/workspace/Projects/data/picks.db")

WNBA_BOX_URL = f"{ESPN_SITE}/basketball/wnba/summary?event=%s"
MLB_BOX_URL = f"{ESPN_SITE}/baseball/mlb/summary?event=%s"
WNBA_SCOREBOARD_URL = f"{ESPN_SITE}/basketball/wnba/scoreboard"
MLB_SCOREBOARD_URL = f"{ESPN_SITE}/baseball/mlb/scoreboard"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"

WSTAT_MAP = {
    "minutes": "MIN", "points": "PTS", "rebounds": "REB", "assists": "AST",
    "threePointFieldGoalsMade": "3PM", "steals": "STL", "blocks": "BLK",
    "fieldGoalsMade": "FGM", "fieldGoalsAttempted": "FGA",
    "threePointFieldGoalsAttempted": "3PA", "freeThrowsMade": "FTM",
    "freeThrowsAttempted": "FTA", "personalFouls": "PF", "turnovers": "TO",
    "offensiveRebounds": "OREB", "defensiveRebounds": "DREB", "plusMinusPoints": "+/-",
}

MBAT_MAP = {
    "atBats": "AB", "runs": "R", "hits": "H", "rbi": "RBI",
    "baseOnBalls": "BB", "strikeOuts": "K", "homeRuns": "HR",
    "stolenBases": "SB", "totalBases": "TB",
}

STAT_LABELS = {
    "batting": "avg", "obp": "OBP", "slg": "SLG", "ops": "OPS",
    "onBasePct": "OBP", "slugPct": "SLG",
    "AVG": "AVG",
    "AB": "AB", "R": "R", "H": "H", "RBI": "RBI",
}


def _get(url):
    try:
        r = SESSION.get(url, timeout=12)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _get_scoreboard(sport):
    url = WNBA_SCOREBOARD_URL if sport == "wnba" else MLB_SCOREBOARD_URL
    data = _get(url)
    if not data:
        return []
    return data.get("events", [])


def _tc_picks_for_matchup(sport, short_name):
    try:
        conn = sqlite3.connect(str(PICKS_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        parts = short_name.split(" @ ")
        if len(parts) == 2:
            cur.execute("""
                SELECT DISTINCT player, team, stat, tc_projection, market_line, edge, direction, reason
                FROM picks WHERE date = ? AND league = ?
                AND (matchup LIKE ? OR matchup LIKE ?)
                ORDER BY ABS(edge) DESC
            """, (today, sport.upper(), f"%{parts[0]}%{parts[1]}%", f"%{parts[1]}%{parts[0]}%"))
        else:
            cur.execute("""
                SELECT DISTINCT player, team, stat, tc_projection, market_line, edge, direction, reason
                FROM picks WHERE date = ? AND league = ?
                ORDER BY ABS(edge) DESC
            """, (today, sport.upper()))
        rows = cur.fetchall()
        conn.close()
        return [{
            "player": r["player"], "team": r["team"], "stat": r["stat"],
            "projection": round(r["tc_projection"], 2) if r["tc_projection"] else 0,
            "line": round(r["market_line"], 2) if r["market_line"] else 0,
            "edge": round(r["edge"], 4) if r["edge"] else 0,
            "direction": r["direction"], "reason": r.get("reason") or "",
        } for r in rows]
    except Exception:
        return []


def _parse_wnba_player(pl):
    athlete = pl.get("athlete", {})
    stats_list = pl.get("statistics", [])
    stats = {}
    for cat in stats_list:
        keys_arr = cat.get("keys", []) or []
        vals_arr = cat.get("values", []) or []
        for i, k in enumerate(keys_arr):
            if i < len(vals_arr):
                raw = WSTAT_MAP.get(k) or k[:6].upper()
                val = vals_arr[i]
                stats[raw] = int(val) if isinstance(val, (int, float)) and val == int(val) else val

    pts = stats.get("PTS", 0) or 0
    reb = stats.get("REB", 0) or 0
    ast = stats.get("AST", 0) or 0

    return {
        "name": athlete.get("displayName") or athlete.get("shortName") or "?",
        "position": pl.get("position", {}).get("abbreviation") or "",
        "jersey": pl.get("jersey", ""),
        "starter": bool(pl.get("starter", False)),
        "stats": stats,
        "combos": {"PRA": pts + reb + ast, "PTS": pts, "REB": reb, "AST": ast},
    }


def _parse_mlb_player(pl):
    athlete = pl.get("athlete", {})
    stats_list = pl.get("statistics", [])
    batting = {}
    for cat in stats_list:
        if cat.get("name") == "batting":
            keys_arr = cat.get("keys", []) or []
            vals_arr = cat.get("values", []) or []
            for i, k in enumerate(keys_arr):
                if k == "stats":
                    continue
                short = MBAT_MAP.get(k) or k[:6].upper()
                if i < len(vals_arr):
                    val = vals_arr[i]
                    batting[short] = int(val) if isinstance(val, (int, float)) and val == int(val) else round(float(val), 3)

    return {
        "name": athlete.get("displayName") or athlete.get("shortName") or "?",
        "position": pl.get("position", {}).get("abbreviation") or pl.get("position", {}).get("name") or "",
        "jersey": pl.get("jersey", ""),
        "battingOrder": pl.get("battingOrder", 99),
        "starter": bool(pl.get("starter", False)),
        "batting": batting,
    }


def _get_wnba_boxscore(event_id, short_name):
    data = _get(WNBA_BOX_URL % event_id)
    if not data:
        return None

    box = data.get("boxscore", {}) or {}
    raw_players = box.get("players", [])

    home = []
    away = []
    for pl in raw_players:
        team_info = pl.get("team", {})
        abbr = team_info.get("abbreviation", "").upper() if team_info else ""
        player = _parse_wnba_player(pl)

        # Determine starter from order
        if len(home) < 5 and abbr:
            home.append(player)
        elif len(away) < 5 and abbr:
            away.append(player)
        else:
            # Fall back to team matching
            pass

    # Use the teams list from boxscore for proper separation
    teams_list = box.get("teams", [])
    home_players = []
    away_players = []
    home_abbr = ""
    away_abbr = ""
    home_score = 0
    away_score = 0
    home_name = ""
    away_name = ""

    for t in teams_list:
        t_info = t.get("team", {})
        abbr = t_info.get("abbreviation", "")
        full = t_info.get("displayName", abbr)
        stats = t.get("statistics", [])
        t_score = 0
        for s in stats:
            if s.get("name") == "teamStats":
                t_score = sum(s.get("values", []) or [])
                break

        if t.get("homeAway") == "home":
            home_abbr = abbr
            home_name = full
            home_score = t_score or t.get("score", 0)
        else:
            away_abbr = abbr
            away_name = full
            away_score = t_score or t.get("score", 0)

    for pl in raw_players:
        t_info = pl.get("team", {})
        t_abbr = t_info.get("abbreviation", "").upper() if t_info else ""
        player = _parse_wnba_player(pl)

        # Sort: separate boxes
        stats_list = pl.get("statistics", [])
        for cat in stats_list:
            pass  # already parsed

        if t_abbr == home_abbr:
            home_players.append(player)
        elif t_abbr == away_abbr:
            away_players.append(player)

    home_players.sort(key=lambda p: (not p["starter"], p.get("name", "")))
    away_players.sort(key=lambda p: (not p["starter"], p.get("name", "")))

    picks = _tc_picks_for_matchup("wnba", short_name)
    status_data = data.get("boxscore", {}).get("players", []) and data.get("header", {})

    return {
        "event_id": event_id,
        "shortName": short_name,
        "sport": "WNBA",
        "home": {
            "name": home_name, "abbrev": home_abbr, "score": home_score,
            "players": home_players,
        },
        "away": {
            "name": away_name, "abbrev": away_abbr, "score": away_score,
            "players": away_players,
        },
        "picks": picks,
    }


def _get_mlb_boxscore(event_id, short_name):
    data = _get(MLB_BOX_URL % event_id)
    if not data:
        return None

    box = data.get("boxscore", {}) or {}
    raw_players = box.get("players", [])
    teams_list = box.get("teams", [])

    home_players = []
    away_players = []
    home_abbr = ""
    away_abbr = ""
    home_score = 0
    away_score = 0
    home_name = ""
    away_name = ""
    home_starters = []
    away_starters = []
    home_bullpen = []
    away_bullpen = []

    for t in teams_list:
        t_info = t.get("team", {})
        abbr = t_info.get("abbreviation", "")
        full = t_info.get("displayName", abbr)
        stats = t.get("statistics", [])
        t_score = 0
        for s in stats:
            if s.get("name") == "teamStats":
                t_score = sum(s.get("values", []) or [])
                break

        if t.get("homeAway") == "home":
            home_abbr = abbr
            home_name = full
            home_score = t_score or t.get("score", 0)
        else:
            away_abbr = abbr
            away_name = full
            away_score = t_score or t.get("score", 0)

    for pl in raw_players:
        t_info = pl.get("team", {})
        t_abbr = t_info.get("abbreviation", "").upper() if t_info else ""
        player = _parse_mlb_player(pl)

        if t_abbr == home_abbr:
            home_players.append(player)
        elif t_abbr == away_abbr:
            away_players.append(player)

    home_players.sort(key=lambda p: (p.get("battingOrder", 99)))
    away_players.sort(key=lambda p: (p.get("battingOrder", 99)))

    # Find pitchers separately from non-batting players
    home_batters = [p for p in home_players if p.get("battingOrder", 99) < 99]
    away_batters = [p for p in away_players if p.get("battingOrder", 99) < 99]
    home_pitchers = [p for p in home_players if p.get("battingOrder", 99) >= 99]
    away_pitchers = [p for p in away_players if p.get("battingOrder", 99) >= 99]

    picks = _tc_picks_for_matchup("mlb", short_name)

    return {
        "event_id": event_id,
        "shortName": short_name,
        "sport": "MLB",
        "home": {
            "name": home_name, "abbrev": home_abbr, "score": home_score,
            "batters": home_batters, "pitchers": home_pitchers, "players": home_players,
        },
        "away": {
            "name": away_name, "abbrev": away_abbr, "score": away_score,
            "batters": away_batters, "pitchers": away_pitchers, "players": away_players,
        },
        "picks": picks,
    }


def get_all_boxscores(sport="all"):
    result = {}
    sports = ["wnba", "mlb"] if sport == "all" else [sport.lower()]

    for s in sports:
        events = _get_scoreboard(s)
        boxes = []
        for ev in events[:8]:
            eid = ev.get("id", "")
            sn = ev.get("shortName", "")
            if not eid:
                continue
            try:
                if s == "wnba":
                    box = _get_wnba_boxscore(eid, sn)
                else:
                    box = _get_mlb_boxscore(eid, sn)
                if box:
                    boxes.append(box)
            except Exception:
                pass
        result[s.upper()] = {
            "game_count": len(boxes),
            "games": boxes,
        }

    return result


if __name__ == "__main__":
    import sys
    sp = sys.argv[1] if len(sys.argv) > 1 else "all"
    start = time.time()
    data = get_all_boxscores(sp)
    elapsed = time.time() - start
    print(json.dumps(data, indent=2, default=str)[:4000])
    print(f"... ({elapsed:.1f}s)")

