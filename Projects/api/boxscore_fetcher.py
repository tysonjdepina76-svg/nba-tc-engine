#!/usr/bin/env python3
"""ESPN Box Score Fetcher — NBA/WNBA/MLB live box scores with TC pick overlay."""
import json
import sys
import time
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
PICKS_DB = Path("/home/workspace/Projects/data/picks.db")

ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"
ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports"

SPORT_CONFIG = {
    "wnba": {
        "league": "basketball/leagues/wnba",
        "scoreboard": "basketball/wnba/scoreboard",
        "position_map": {
            "1": "PG", "2": "SG", "3": "SF", "4": "PF", "5": "C",
            "6": "G", "7": "F", "8": "F/C", "9": "G/F",
        },
        "stat_keys": ["minutes", "points", "rebounds", "assists",
                       "threePointFieldGoalsMade", "steals", "blocks",
                       "fieldGoalsMade", "fieldGoalsAttempted",
                       "threePointFieldGoalsAttempted", "freeThrowsMade",
                       "freeThrowsAttempted", "personalFouls", "turnovers",
                       "offensiveRebounds", "defensiveRebounds",
                       "plusMinusPoints"],
        "combo_stats": ["PRA"],
    },
    "nba": {
        "league": "basketball/leagues/nba",
        "scoreboard": "basketball/nba/scoreboard",
        "position_map": {
            "1": "PG", "2": "SG", "3": "SF", "4": "PF", "5": "C",
            "6": "G", "7": "F", "8": "F/C", "9": "G/F",
        },
        "stat_keys": ["minutes", "points", "rebounds", "assists",
                       "threePointFieldGoalsMade", "steals", "blocks",
                       "fieldGoalsMade", "fieldGoalsAttempted",
                       "threePointFieldGoalsAttempted", "freeThrowsMade",
                       "freeThrowsAttempted", "personalFouls", "turnovers"],
        "combo_stats": ["PRA"],
    },
    "mlb": {
        "league": "baseball/leagues/mlb",
        "scoreboard": "baseball/mlb/scoreboard",
        "position_map": {},
        "batting_stat_keys": ["atBats", "runs", "hits", "rbi", "baseOnBalls",
                               "strikeOuts", "homeRuns", "stolenBases",
                               "totalBases", "avg", "obp", "slg", "ops",
                               "sacrificeBunts", "sacrificeFlies",
                               "hitByPitch", "groundOuts", "airOuts",
                               "doublePlaysGroundedInto"],
        "pitching_stat_keys": ["inningsPitched", "hits", "runs", "earnedRuns",
                                "baseOnBalls", "strikeOuts", "homeRuns",
                                "pitchesThrown", "strikes", "battersFaced",
                                "outs", "wildPitches", "balks",
                                "earnedRunAverage"],
        "combo_stats": [],
    },
}


def fetch_json(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_todays_games(sport):
    cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG["mlb"])
    url = f"{ESPN_SITE}/{cfg['scoreboard']}"
    data = fetch_json(url)
    if not data:
        return []
    games = []
    for event in data.get("events", []):
        comps = event.get("competitions", [])
        if not comps:
            continue
        c = comps[0]
        status = c.get("status", {}).get("type", {}).get("state", "pre")
        games.append({
            "event_id": event.get("id"),
            "home": c.get("competitors", [])[0].get("team", {}).get("abbreviation", "HOME") if len(c.get("competitors", [])) > 0 else "HOME",
            "away": c.get("competitors", [])[1].get("team", {}).get("abbreviation", "AWAY") if len(c.get("competitors", [])) > 1 else "AWAY",
            "home_score": c.get("competitors", [])[0].get("score", "0") if len(c.get("competitors", [])) > 0 else "0",
            "away_score": c.get("competitors", [])[1].get("score", "0") if len(c.get("competitors", [])) > 1 else "0",
            "status": status,
            "clock": c.get("status", {}).get("displayClock", ""),
            "period": c.get("status", {}).get("period", 0),
            "short_name": event.get("shortName", ""),
        })
    return games


def get_athlete_name(sport, athlete_id):
    """Resolve athlete ID to full name."""
    cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG["mlb"])
    url = f"{ESPN_CORE}/{cfg['league']}/seasons/2026/athletes/{athlete_id}?lang=en&region=us"
    data = fetch_json(url)
    if data:
        return data.get("fullName", data.get("displayName", f"#{athlete_id}"))
    return f"#{athlete_id}"


def get_position_name(sport, position_id):
    cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG["mlb"])
    pm = cfg.get("position_map", {})
    if pm:
        return pm.get(str(position_id), f"P{position_id}")
    # For MLB, position IDs map differently
    MLB_POS = {"10": "P", "1": "C", "2": "1B", "3": "2B", "4": "3B",
               "5": "SS", "6": "LF", "7": "CF", "8": "RF",
               "11": "DH", "12": "PH", "13": "PR"}
    return MLB_POS.get(str(position_id), f"P{position_id}")


def parse_player_stats(sport, event_id, competitor_id, player_id):
    """Fetch single player's game stats from ESPN core."""
    cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG["mlb"])
    url = (f"{ESPN_CORE}/{cfg['league']}/events/{event_id}/"
           f"competitions/{event_id}/competitors/{competitor_id}/"
           f"roster/{player_id}/statistics/0?lang=en&region=us")
    data = fetch_json(url)
    if not data:
        return {}
    stats = {}
    splits = data.get("splits", {})
    for cat in splits.get("categories", []):
        for s in cat.get("stats", []):
            val = s.get("value", 0)
            if val and val > 0:
                stats[s["name"]] = val
    return stats


def parse_all_player_stats(sport, event_id, competitor_id):
    """Get full roster stats from team-level stat endpoint (single call)."""
    cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG["mlb"])
    url = (f"{ESPN_CORE}/{cfg['league']}/events/{event_id}/"
           f"competitions/{event_id}/competitors/{competitor_id}/"
           f"statistics/0?lang=en&region=us")
    data = fetch_json(url)
    if not data:
        return {}
    stats_dict = {}
    splits = data.get("splits", {})
    for cat in splits.get("categories", []):
        for s in cat.get("stats", []):
            val = s.get("value", 0)
            if val and val > 0:
                stats_dict[s["name"]] = val
    return stats_dict


def get_box_score_for_game(sport, game_info):
    """Full box score for one game — roster names from roster endpoint, stats from individual player endpoints."""
    cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG["mlb"])
    event_id = game_info["event_id"]
    result = {
        "event_id": int(event_id),
        "home_team": game_info["home"],
        "away_team": game_info["away"],
        "home_score": game_info["home_score"],
        "away_score": game_info["away_score"],
        "status": game_info["status"],
        "clock": game_info["clock"],
        "period": game_info["period"],
        "short_name": game_info["short_name"],
        "sport": sport,
        "home_players": [],
        "away_players": [],
    }

    competitor_ids = []
    # Get competitors for this event
    comps_url = f"{ESPN_CORE}/{cfg['league']}/events/{event_id}/competitions/{event_id}/competitors?lang=en&region=us"
    comps_data = fetch_json(comps_url)
    if not comps_data:
        return result
    for item in comps_data.get("items", []):
        cid = item.get("id")
        side = item.get("homeAway")
        competitor_ids.append((cid, side))

    for cid, side in competitor_ids:
        # Get roster entries with athlete refs
        roster_url = (f"{ESPN_CORE}/{cfg['league']}/events/{event_id}/"
                      f"competitions/{event_id}/competitors/{cid}/roster?lang=en&region=us")
        roster_data = fetch_json(roster_url)
        if not roster_data:
            continue
        for entry in roster_data.get("entries", []):
            player_id = entry.get("playerId")
            jersey = entry.get("jersey", "")
            starter = entry.get("starter", False)
            position_id = entry.get("position", {}).get("$ref", "").rstrip("/").split("/")[-1] if entry.get("position", {}).get("$ref") else ""
            position = get_position_name(sport, position_id) if position_id else ""

            # Get athlete name
            name = get_athlete_name(sport, player_id)

            # Get player stats
            stats = parse_player_stats(sport, event_id, cid, player_id)

            player_info = {
                "id": player_id,
                "name": name,
                "jersey": jersey,
                "position": position,
                "starter": starter,
                "stats": clean_stats(sport, stats),
            }

            # Add combo stats for WNBA/NBA
            if sport in ("wnba", "nba"):
                pts = stats.get("points", 0)
                reb = stats.get("rebounds", 0) or stats.get("totalRebounds", 0)
                ast = stats.get("assists", 0)
                player_info["combos"] = {
                    "PRA": pts + reb + ast,
                    "PTS": pts,
                    "REB": reb,
                    "AST": ast,
                }

            if side == "home":
                result["home_players"].append(player_info)
            else:
                result["away_players"].append(player_info)

    # Sort home/away by starter then jersey
    for key in ("home_players", "away_players"):
        result[key].sort(key=lambda p: (not p["starter"], int(p["jersey"]) if p.get("jersey") and p["jersey"].isdigit() else 99))

    # Get TC picks for this game
    result["picks"] = get_tc_picks_for_game(sport, game_info["short_name"])

    return result


def clean_stats(sport, raw_stats):
    """Map ESPN stat names to short display names."""
    MAP = {
        "minutes": "MIN",
        "points": "PTS",
        "totalRebounds": "REB",
        "rebounds": "REB",
        "assists": "AST",
        "threePointFieldGoalsMade": "3PM",
        "steals": "STL",
        "blocks": "BLK",
        "fieldGoalsMade": "FGM",
        "fieldGoalsAttempted": "FGA",
        "threePointFieldGoalsAttempted": "3PA",
        "freeThrowsMade": "FTM",
        "freeThrowsAttempted": "FTA",
        "personalFouls": "PF",
        "turnovers": "TO",
        "offensiveRebounds": "OREB",
        "defensiveRebounds": "DREB",
        "plusMinusPoints": "+/-",
        "atBats": "AB",
        "runs": "R",
        "hits": "H",
        "rbi": "RBI",
        "baseOnBalls": "BB",
        "strikeOuts": "K",
        "homeRuns": "HR",
        "stolenBases": "SB",
        "totalBases": "TB",
        "avg": "AVG",
        "obp": "OBP",
        "slg": "SLG",
        "ops": "OPS",
        "inningsPitched": "IP",
        "earnedRuns": "ER",
        "pitchesThrown": "PIT",
        "strikes": "STR",
        "battersFaced": "BF",
        "outs": "OUTS",
        "wildPitches": "WP",
        "balks": "BK",
        "earnedRunAverage": "ERA",
        "sacrificeFlies": "SF",
        "hitByPitch": "HBP",
    }
    cleaned = {}
    for k, v in raw_stats.items():
        label = MAP.get(k, k[:6].upper())
        cleaned[label] = int(v) if isinstance(v, (int, float)) and v == int(v) else round(float(v), 2) if isinstance(v, (int, float)) else v
    return cleaned


def get_tc_picks_for_game(sport, short_name):
    """Get TC picks matching this matchup."""
    if not short_name:
        return []
    today = datetime.now(ET).strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(str(PICKS_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        parts = short_name.split(" @ ")
        if len(parts) == 2:
            cur.execute("""
                SELECT DISTINCT player, team, stat, tc_projection, market_line, edge, direction, reason
                FROM picks WHERE date = ? AND league = ? AND (matchup LIKE ? OR matchup LIKE ?)
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
            "player": r["player"],
            "team": r["team"],
            "stat": r["stat"],
            "projection": round(r["tc_projection"], 2) if r["tc_projection"] else 0,
            "line": round(r["market_line"], 2) if r["market_line"] else 0,
            "edge": round(r["edge"], 4) if r["edge"] else 0,
            "direction": r["direction"],
            "reason": r["reason"] or "",
        } for r in rows]
    except Exception:
        return []


def get_all_box_scores(sport="all"):
    """Get box scores for all today's games across requested sports."""
    sports_to_check = ["wnba", "mlb", "nba"] if sport == "all" else [sport.lower()]

    result = {}
    for s in sports_to_check:
        if s not in SPORT_CONFIG:
            continue
        try:
            games = get_todays_games(s)
            box_scores = []
            for g in games[:8]:  # limit per sport
                try:
                    bs = get_box_score_for_game(s, g)
                    box_scores.append(bs)
                except Exception as e:
                    box_scores.append({"error": str(e), "game": g["short_name"]})
            result[s.upper()] = box_scores
        except Exception as e:
            result[s.upper()] = {"error": str(e)}
    return result


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = get_all_box_scores(s)
    print(json.dumps(data, indent=2))
