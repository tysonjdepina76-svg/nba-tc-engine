"""
ESPN Box Score Fetcher — pulls live/complete player stats for WNBA, MLB, NBA.
Used by the TC API to serve box score data to the dashboard.
"""
import requests
import time
from functools import lru_cache

ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"
WNBA_BASE = f"{ESPN_CORE}/basketball/leagues/wnba"
MLB_BASE = f"{ESPN_CORE}/baseball/leagues/mlb"
NBA_BASE = f"{ESPN_CORE}/basketball/leagues/nba"

@lru_cache(maxsize=32)
def _cached_get(url, ttl_key=None):
    resp = requests.get(url, params={"lang": "en", "region": "us"}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def _get_today_event_ids(sport_base):
    url = f"{sport_base}/events"
    # ESPN site API for scoreboard
    if "wnba" in sport_base:
        site_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
    elif "mlb" in sport_base:
        site_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    elif "nba" in sport_base:
        site_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    else:
        return []
    
    data = _cached_get(site_url)
    events = data.get("events", [])
    results = []
    for e in events:
        comps = e.get("competitions", [{}])[0]
        status = comps.get("status", {})
        eid = e.get("id")
        results.append({
            "id": eid,
            "shortName": e.get("shortName", ""),
            "status": status.get("type", {}).get("name", ""),
            "state": status.get("type", {}).get("state", ""),
            "period": status.get("period", 0),
            "clock": status.get("displayClock", ""),
            "home": {
                "team": comps.get("competitors", [{}])[0].get("team", {}).get("abbreviation", ""),
                "score": comps.get("competitors", [{}])[0].get("score", "0"),
            },
            "away": {
                "team": comps.get("competitors", [{}, {}])[1].get("team", {}).get("abbreviation", ""),
                "score": comps.get("competitors", [{}, {}])[1].get("score", "0"),
            },
        })
    return results

def _get_player_name(sport_base, athlete_id):
    url = f"{sport_base}/seasons/2026/athletes/{athlete_id}"
    try:
        data = _cached_get(url)
        return data.get("fullName", data.get("displayName", f"#{athlete_id}"))
    except:
        return f"#{athlete_id}"

def _get_position_name(sport_base, pos_id):
    url = f"{sport_base}/positions/{pos_id}"
    try:
        data = _cached_get(url)
        return data.get("abbreviation", data.get("name", ""))
    except:
        return ""

def _parse_basketball_stats(categories, player_id, sport_base):
    stats = {}
    for cat in categories:
        for s in cat.get("stats", []):
            name = s.get("name", "")
            val = s.get("value", 0)
            if name == "points": stats["PTS"] = int(val)
            elif name == "totalRebounds": stats["REB"] = int(val)
            elif name == "assists": stats["AST"] = int(val)
            elif name == "threePointFieldGoalsMade": stats["3PM"] = int(val)
            elif name == "steals": stats["STL"] = int(val)
            elif name == "blocks": stats["BLK"] = int(val)
            elif name == "turnovers": stats["TO"] = int(val)
            elif name == "personalFouls" or name == "fouls": stats["F"] = int(val)
            elif name == "minutes": stats["MIN"] = int(val)
            elif name == "fieldGoalsMade": stats["FGM"] = int(val)
            elif name == "fieldGoalsAttempted": stats["FGA"] = int(val)
            elif name == "threePointFieldGoalsAttempted": stats["3PA"] = int(val)
            elif name == "freeThrowsMade": stats["FTM"] = int(val)
            elif name == "freeThrowsAttempted": stats["FTA"] = int(val)
            elif name == "offensiveRebounds": stats["OREB"] = int(val)
            elif name == "defensiveRebounds": stats["DREB"] = int(val)
    return stats

def _parse_baseball_batting(categories, player_id, sport_base):
    stats = {}
    for cat in categories:
        cat_name = cat.get("name", "")
        for s in cat.get("stats", []):
            name = s.get("name", "")
            val = s.get("value", 0)
            if name == "atBats": stats["AB"] = int(val)
            elif name == "runs": stats["R"] = int(val)
            elif name == "hits": stats["H"] = int(val)
            elif name == "rbi": stats["RBI"] = int(val)
            elif name == "strikeOuts" or name == "strikeouts": stats["K"] = int(val)
            elif name == "baseOnBalls": stats["BB"] = int(val)
            elif name == "stolenBases": stats["SB"] = int(val)
            elif name == "homeRuns": stats["HR"] = int(val)
            elif name == "battingAverage": stats["AVG"] = round(val, 3) if val else 0
            elif name == "totalBases": stats["TB"] = int(val)
            elif name == "doubles": stats["2B"] = int(val)
            elif name == "triples": stats["3B"] = int(val)
            elif name == "sacrificeFlies": stats["SF"] = int(val)
    return stats

def _parse_baseball_pitching(categories, player_id, sport_base):
    stats = {}
    for cat in categories:
        for s in cat.get("stats", []):
            name = s.get("name", "")
            val = s.get("value", 0)
            if name == "inningsPitched": stats["IP"] = round(val, 1)
            elif name == "hitsAllowed": stats["HA"] = int(val)
            elif name == "runsAllowed": stats["RA"] = int(val)
            elif name == "earnedRuns": stats["ER"] = int(val)
            elif name == "strikeOuts" or name == "pitcherStrikeouts": stats["K"] = int(val)
            elif name == "baseOnBalls": stats["BB"] = int(val)
            elif name == "homeRunsAllowed": stats["HRA"] = int(val)
            elif name == "pitchesThrown": stats["PIT"] = int(val)
            elif name == "strikes": stats["STR"] = int(val)
            elif name == "battersFaced": stats["BF"] = int(val)
            elif name == "era": stats["ERA"] = round(val, 2) if val else 0
    return stats

def _get_player_boxscore(sport_base, event_id, team_id, player_id, is_pitcher=False):
    """Get individual player game stats from ESPN core API"""
    roster_stats_url = f"{sport_base}/events/{event_id}/competitions/{event_id}/competitors/{team_id}/roster/{player_id}/statistics/0"
    try:
        data = _cached_get(roster_stats_url)
        splits = data.get("splits", {})
        categories = splits.get("categories", [])
        if is_pitcher:
            return _parse_baseball_pitching(categories, player_id, sport_base)
        else:
            return _parse_baseball_batting(categories, player_id, sport_base) if "baseball" in sport_base else _parse_basketball_stats(categories, player_id, sport_base)
    except Exception:
        return {}


def get_wnba_boxscore(event_id):
    """Get full WNBA box score for an event"""
    sport_base = WNBA_BASE
    teams_comp_url = f"{sport_base}/events/{event_id}/competitions/{event_id}/competitors"
    competitors = _cached_get(teams_comp_url)
    items = competitors.get("items", [])
    
    teams_data = []
    for comp in items:
        team_id = comp.get("id")
        home_away = comp.get("homeAway")
        team_name = "???"
        try:
            team_ref = comp.get("team", {}).get("$ref", "")
            team_data = _cached_get(team_ref)
            team_name = team_data.get("abbreviation", team_data.get("displayName", ""))
        except:
            pass
        
        roster_url = f"{sport_base}/events/{event_id}/competitions/{event_id}/competitors/{team_id}/roster"
        roster_data = _cached_get(roster_url)
        entries = roster_data.get("entries", [])
        
        players = []
        for entry in entries:
            pid = entry.get("playerId")
            jersey = entry.get("jersey", "")
            starter = entry.get("starter", False)
            
            pos_name = ""
            try:
                pos_ref = entry.get("position", {}).get("$ref", "")
                pos_data = _cached_get(pos_ref)
                pos_name = pos_data.get("abbreviation", "")
            except:
                pass
            
            name = _get_player_name(sport_base, pid)
            stats = _get_player_boxscore(sport_base, event_id, team_id, pid)
            
            players.append({
                "id": pid,
                "name": name,
                "position": pos_name,
                "jersey": jersey,
                "starter": starter,
                "stats": stats,
            })
        
        teams_data.append({
            "team": team_name,
            "homeAway": home_away,
            "players": sorted(players, key=lambda p: (not p["starter"], p.get("position", ""))),
        })
    
    return {"event_id": event_id, "teams": teams_data}


def get_mlb_boxscore(event_id):
    """Get full MLB box score with batting order + pitching"""
    sport_base = MLB_BASE
    teams_comp_url = f"{sport_base}/events/{event_id}/competitions/{event_id}/competitors"
    competitors = _cached_get(teams_comp_url)
    items = competitors.get("items", [])
    
    teams_data = []
    for comp in items:
        team_id = comp.get("id")
        home_away = comp.get("homeAway")
        team_name = "???"
        try:
            team_ref = comp.get("team", {}).get("$ref", "")
            team_data = _cached_get(team_ref)
            team_name = team_data.get("abbreviation", team_data.get("displayName", ""))
        except:
            pass
        
        roster_url = f"{sport_base}/events/{event_id}/competitions/{event_id}/competitors/{team_id}/roster"
        roster_data = _cached_get(roster_url)
        entries = roster_data.get("entries", [])
        
        batters = []
        pitchers = []
        for entry in entries:
            pid = entry.get("playerId")
            jersey = entry.get("jersey", "")
            starter = entry.get("starter", False)
            
            pos_name = ""
            try:
                pos_ref = entry.get("position", {}).get("$ref", "")
                pos_data = _cached_get(pos_ref)
                pos_name = pos_data.get("abbreviation", pos_data.get("name", ""))
            except:
                pass
            
            name = _get_player_name(sport_base, pid)
            is_pitcher = pos_name in ("SP", "RP", "P")
            stats = _get_player_boxscore(sport_base, event_id, team_id, pid, is_pitcher=is_pitcher)
            
            if is_pitcher:
                pitchers.append({
                    "id": pid,
                    "name": name,
                    "position": pos_name,
                    "jersey": jersey,
                    "starter": starter,
                    "stats": stats,
                })
            else:
                batters.append({
                    "id": pid,
                    "name": name,
                    "position": pos_name,
                    "jersey": jersey,
                    "starter": starter,
                    "stats": stats,
                })
        
        teams_data.append({
            "team": team_name,
            "homeAway": home_away,
            "batters": batters,
            "pitchers": pitchers,
        })
    
    return {"event_id": event_id, "teams": teams_data}


def get_today_wnba_boxscores():
    events = _get_today_event_ids(WNBA_BASE)
    results = []
    for evt in events:
        bs = get_wnba_boxscore(evt["id"])
        bs["meta"] = evt
        results.append(bs)
    return results


def get_today_mlb_boxscores():
    events = _get_today_event_ids(MLB_BASE)
    results = []
    for evt in events:
        bs = get_mlb_boxscore(evt["id"])
        bs["meta"] = evt
        results.append(bs)
    return results
