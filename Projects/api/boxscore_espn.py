#!/usr/bin/env python3
"""
ESPN Box Score Aggregator — fetches live player stats for WNBA/NBA and MLB.
Returns structured JSON with TC picks merged in.
"""
import json, urllib.request, urllib.error, time, sqlite3, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports"
ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"

SPORT_LEAGUES = {
    "WNBA": ("basketball", "wnba"),
    "MLB":  ("baseball", "mlb"),
}

DB_PATH = "/home/workspace/Projects/data/picks.db"

def fetch_json(url: str, timeout: int = 10) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ⚠ fetch failed {url[-80:]}: {e}")
        return None

def fetch_espn_scoreboard(sport: str) -> list[dict]:
    path = SPORT_LEAGUES.get(sport.upper())
    if not path:
        return []
    url = f"{ESPN_SITE}/{path[0]}/{path[1]}/scoreboard"
    data = fetch_json(url)
    return data.get("events", []) if data else []

def fetch_wnba_boxscore(event_id: str) -> dict:
    """
    Fetch full WNBA box score: roster, starters, per-player stats.
    Uses ESPN core API with parallel athlete+stats calls.
    """
    base = f"{ESPN_CORE}/basketball/leagues/wnba/events/{event_id}/competitions/{event_id}"
    
    competitors_data = fetch_json(f"{base}/competitors?lang=en&region=us")
    if not competitors_data:
        return {"error": "no competitors data", "event_id": event_id}
    
    result = {"event_id": event_id, "home": {}, "away": {}, "status": "unknown"}
    
    for comp in competitors_data.get("items", []):
        home_away = comp.get("homeAway", "home")  # home or away
        team_id = comp.get("id")
        team_data = {"team_id": team_id, "winner": comp.get("winner", False)}
        
        # Get team name
        team_ref = comp.get("team", {}).get("$ref", "")
        if team_ref:
            team_info = fetch_json(team_ref)
            if team_info:
                team_data["team_name"] = team_info.get("displayName", team_info.get("shortName", "?"))
                team_data["team_abbr"] = team_info.get("abbreviation", "?")
                team_data["team_logo"] = team_info.get("logos", [{}])[-1].get("href", "") if team_info.get("logos") else ""
        
        # Get team total stats
        stats_ref = comp.get("statistics", {}).get("$ref", "")
        if stats_ref:
            team_stats = fetch_json(stats_ref)
            if team_stats:
                totals = {}
                for cat in team_stats.get("splits", {}).get("categories", []):
                    for s in cat.get("stats", []):
                        totals[s.get("name", "")] = s.get("value", 0)
                team_data["team_totals"] = {
                    "points": totals.get("points", 0),
                    "fg_pct": totals.get("fieldGoalPct", 0),
                    "fg3_pct": totals.get("threePointFieldGoalPct", 0),
                    "ft_pct": totals.get("freeThrowPct", 0),
                    "rebounds": totals.get("totalRebounds", 0),
                    "assists": totals.get("assists", 0),
                    "steals": totals.get("steals", 0),
                    "blocks": totals.get("blocks", 0),
                    "turnovers": totals.get("turnovers", 0),
                    "fouls": totals.get("fouls", 0),
                }
        
        # Get linescores
        linescore_ref = comp.get("linescores", {}).get("$ref", "")
        if linescore_ref:
            ls_data = fetch_json(linescore_ref)
            if ls_data:
                team_data["linescores"] = [
                    {"period": i.get("period", p+1), "value": i.get("value", 0)}
                    for p, i in enumerate(ls_data.get("items", []))
                ]
        
        # Get roster with player stats — parallel fetch
        roster_ref = comp.get("roster", {}).get("$ref", "")
        players = []
        if roster_ref:
            roster_data = fetch_json(roster_ref)
            entries = roster_data.get("entries", []) if roster_data else []
            
            def fetch_player(entry):
                pid = entry.get("playerId")
                jersey = entry.get("jersey", "?")
                starter = entry.get("starter", False)
                
                # Get athlete name + position
                athlete_ref = entry.get("athlete", {}).get("$ref", "")
                name = f"#{jersey}"
                pos_name = "?"
                pos_abbr = "?"
                
                if athlete_ref:
                    athlete_data = fetch_json(athlete_ref)
                    if athlete_data:
                        name = athlete_data.get("shortName") or athlete_data.get("fullName") or name
                        pos = athlete_data.get("position", {})
                        pos_name = pos.get("name", "?")
                        pos_abbr = pos.get("abbreviation", "?")
                
                # Get player stats
                stats_ref = entry.get("statistics", {}).get("$ref", "")
                stats = {}
                if stats_ref:
                    stats_data = fetch_json(stats_ref)
                    if stats_data:
                        for cat in stats_data.get("splits", {}).get("categories", []):
                            for s in cat.get("stats", []):
                                stats[s.get("name", "")] = s.get("value", 0)
                
                return {
                    "player_id": pid,
                    "name": name,
                    "jersey": jersey,
                    "position": pos_abbr,
                    "position_name": pos_name,
                    "starter": starter,
                    "stats": {
                        "min": stats.get("minutes", 0),
                        "pts": stats.get("points", 0),
                        "reb": stats.get("totalRebounds", 0),
                        "ast": stats.get("assists", 0),
                        "fg3m": stats.get("threePointFieldGoalsMade", 0),
                        "stl": stats.get("steals", 0),
                        "blk": stats.get("blocks", 0),
                        "pf": stats.get("fouls", 0),
                        "fgm": stats.get("fieldGoalsMade", 0),
                        "fga": stats.get("fieldGoalsAttempted", 0),
                        "ftm": stats.get("freeThrowsMade", 0),
                        "fta": stats.get("freeThrowsAttempted", 0),
                        "to": stats.get("turnovers", 0),
                        "plus_minus": stats.get("plusMinus", 0),
                    },
                }
            
            with ThreadPoolExecutor(max_workers=12) as ex:
                futures = {ex.submit(fetch_player, e): e for e in entries}
                for f in as_completed(futures):
                    players.append(f.result())
            
            # Sort: starters first, then by minutes desc
            players.sort(key=lambda p: (not p["starter"], -(p["stats"].get("min", 0) or 0)))
        
        team_data["players"] = players
        result[home_away] = team_data
    
    return result


def fetch_mlb_boxscore(event_id: str) -> dict:
    """
    Fetch full MLB box score: lineup, batting stats, pitching stats.
    Uses ESPN core API with parallel player stats calls.
    """
    base = f"{ESPN_CORE}/baseball/leagues/mlb/events/{event_id}/competitions/{event_id}"
    
    competitors_data = fetch_json(f"{base}/competitors?lang=en&region=us")
    if not competitors_data:
        return {"error": "no competitors data", "event_id": event_id}
    
    result = {"event_id": event_id, "home": {}, "away": {}, "status": "unknown"}
    
    for comp in competitors_data.get("items", []):
        home_away = comp.get("homeAway", "home")
        team_id = comp.get("id")
        team_data = {"team_id": team_id, "winner": comp.get("winner", False)}
        
        # Get team name
        team_ref = comp.get("team", {}).get("$ref", "")
        if team_ref:
            team_info = fetch_json(team_ref)
            if team_info:
                team_data["team_name"] = team_info.get("displayName", team_info.get("shortName", "?"))
                team_data["team_abbr"] = team_info.get("abbreviation", "?")
        
        # Get linescores  
        linescore_ref = comp.get("linescores", {}).get("$ref", "")
        if linescore_ref:
            ls_data = fetch_json(linescore_ref)
            if ls_data:
                team_data["linescores"] = [
                    {"inning": i.get("period", idx+1), "runs": i.get("value", 0)}
                    for idx, i in enumerate(ls_data.get("items", []))
                ]
        
        # Get team stats (H, E, etc.)
        team_data["hits"] = comp.get("hits", "0")
        team_data["errors"] = comp.get("errors", "0")
        
        # Get roster with player stats
        roster_ref = comp.get("roster", {}).get("$ref", "")
        players = []
        if roster_ref:
            roster_data = fetch_json(roster_ref)
            entries = roster_data.get("entries", []) if roster_data else []
            
            def fetch_mlb_player(entry):
                pid = entry.get("playerId")
                jersey = entry.get("jersey", "?")
                starter = entry.get("starter", False)
                batting_order = entry.get("battingOrder", -1)
                
                athlete_ref = entry.get("athlete", {}).get("$ref", "")
                name = f"#{jersey}"
                pos_abbr = "?"
                
                if athlete_ref:
                    athlete_data = fetch_json(athlete_ref)
                    if athlete_data:
                        name = athlete_data.get("shortName") or athlete_data.get("fullName") or name
                        pos = athlete_data.get("position", {})
                        pos_abbr = pos.get("abbreviation", "?")
                
                # Get player stats
                stats_ref = entry.get("statistics", {}).get("$ref", "")
                batting = {}
                pitching = {}
                if stats_ref:
                    stats_data = fetch_json(stats_ref)
                    if stats_data:
                        for cat in stats_data.get("splits", {}).get("categories", []):
                            cat_name = cat.get("name", "")
                            for s in cat.get("stats", []):
                                if cat_name in ("batting", "offensive"):
                                    batting[s.get("name", "")] = s.get("value", 0)
                                elif cat_name == "pitching":
                                    pitching[s.get("name", "")] = s.get("value", 0)
                
                player = {
                    "player_id": pid,
                    "name": name,
                    "jersey": jersey,
                    "position": pos_abbr,
                    "starter": starter,
                    "batting_order": batting_order,
                    "batting": {
                        "ab": _get_stat("atBats", "AB", batting),
                        "r": _get_stat("runs", "R", batting),
                        "h": _get_stat("hits", "H", batting),
                        "rbi": _get_stat("RBI", "RBI", batting),
                        "bb": _get_stat("baseOnBalls", "BB", batting),
                        "k": _get_stat("strikeOuts", "SO", batting),
                        "avg": _get_stat("battingAvg", "AVG", batting),
                        "hr": _get_stat("homeRuns", "HR", batting),
                        "sb": _get_stat("stolenBases", "SB", batting),
                        "tb": _get_stat("totalBases", "TB", batting),
                        "obp": _get_stat("onBasePct", "OBP", batting),
                        "slg": _get_stat("slugPct", "SLG", batting),
                        "ops": _get_stat("OPS", "OPS", batting),
                    },
                    "pitching": {
                        "ip": pitching.get("inningsPitched", "0.0"),
                        "h": pitching.get("hits", 0),
                        "r": pitching.get("runs", 0),
                        "er": pitching.get("earnedRuns", 0),
                        "bb": pitching.get("baseOnBalls", 0),
                        "k": pitching.get("strikeOuts", 0),
                        "hr": pitching.get("homeRuns", 0),
                        "era": pitching.get("ERA", 0),
                        "pitches": pitching.get("pitchesThrown", 0),
                        "strikes": pitching.get("strikes", 0),
                    } if pitching else None,
                }
                return player
            
            with ThreadPoolExecutor(max_workers=12) as ex:
                futures = {ex.submit(fetch_mlb_player, e): e for e in entries}
                for f in as_completed(futures):
                    players.append(f.result())
            
            # Sort by batting order
            players.sort(key=lambda p: p.get("batting_order", 99) if p["batting_order"] > 0 else 99)
        
        team_data["players"] = players
        result[home_away] = team_data
    
    return result


def _get_stat(*keys, stats_dict):
    for k in keys:
        if k in stats_dict:
            return stats_dict[k]
    return 0


def get_tc_picks_for_game(matchup: str, sport: str) -> list[dict]:
    """Get TC picks for a specific game from the database."""
    picks = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT player, team, stat, tc_projection, market_line, edge, direction, reason
            FROM picks 
            WHERE date = date('now') 
              AND league = ? 
              AND matchup LIKE ?
        """, (sport.upper(), f"%{matchup}%"))
        for row in cur.fetchall():
            picks.append({
                "player": row["player"],
                "team": row["team"],
                "stat": row["stat"],
                "projection": row["tc_projection"],
                "line": row["market_line"],
                "edge": row["edge"],
                "direction": row["direction"],
                "reason": row["reason"],
            })
        conn.close()
        
        # Try alternate matchup format (HOME @ AWAY vs AWAY @ HOME)
        parts = matchup.split(" @ ")
        if len(parts) == 2:
            alt = f"{parts[1]} @ {parts[0]}"
            conn2 = sqlite3.connect(DB_PATH)
            conn2.row_factory = sqlite3.Row
            cur2 = conn2.cursor()
            cur2.execute("""
                SELECT player, team, stat, tc_projection, market_line, edge, direction, reason
                FROM picks 
                WHERE date = date('now') 
                  AND league = ? 
                  AND matchup LIKE ?
            """, (sport.upper(), f"%{alt}%"))
            for row in cur2.fetchall():
                picks.append({
                    "player": row["player"],
                    "team": row["team"],
                    "stat": row["stat"],
                    "projection": row["tc_projection"],
                    "line": row["market_line"],
                    "edge": row["edge"],
                    "direction": row["direction"],
                    "reason": row["reason"],
                })
            conn2.close()
    except Exception as e:
        print(f"  DB error for {matchup}: {e}")
    return picks


def get_all_boxscores() -> dict:
    """Fetch live box scores for all active WNBA and MLB games with TC picks."""
    result = {"timestamp": time.time(), "sports": {}}
    
    for sport in ["WNBA", "MLB"]:
        print(f"Fetching {sport} scoreboard...")
        events = fetch_espn_scoreboard(sport)
        sport_data = {"games": [], "game_count": 0}
        
        for event in events:
            comps = event.get("competitions", [])[0] if event.get("competitions") else {}
            status = comps.get("status", {}).get("type", {}).get("name", "UNKNOWN")
            clock = comps.get("status", {}).get("displayClock", "")
            period = comps.get("status", {}).get("period", 0)
            
            teams = comps.get("competitors", [])
            home_team = ""
            away_team = ""
            home_score = "0"
            away_score = "0"
            for t in teams:
                if t.get("homeAway") == "home":
                    home_team = t.get("team", {}).get("abbreviation", "?")
                    home_score = t.get("score", "0")
                else:
                    away_team = t.get("team", {}).get("abbreviation", "?")
                    away_score = t.get("score", "0")
            
            matchup = f"{away_team} @ {home_team}"
            event_id = event.get("id")
            
            print(f"  {matchup} ({status}) — fetching box score...")
            
            # Fetch full box score
            if sport == "WNBA":
                box = fetch_wnba_boxscore(event_id)
            else:
                box = fetch_mlb_boxscore(event_id)
            
            if "error" not in box:
                box["matchup"] = matchup
                box["status"] = status
                box["clock"] = clock
                box["period"] = period
                box["home_score"] = home_score
                box["away_score"] = away_score
                box["sport"] = sport
                
                # Merge TC picks
                picks = get_tc_picks_for_game(matchup, sport)
                box["tc_picks"] = picks
                box["pick_count"] = len(picks)
                
                sport_data["games"].append(box)
        
        sport_data["game_count"] = len(sport_data["games"])
        result["sports"][sport] = sport_data
    
    return result


if __name__ == "__main__":
    data = get_all_boxscores()
    print(json.dumps(data, indent=2))
