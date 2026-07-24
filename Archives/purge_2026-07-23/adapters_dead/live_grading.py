#!/usr/bin/env python3
"""Live auto-grading engine — statsapi for MLB (free, no auth). 
Grades picks against final box scores. Runs inside daily_picks.py after generation."""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("tc_pipeline")

PROJECTS = Path("/home/workspace/Projects")
DATA_DIR = Path("/home/workspace/data/picks")
DAILY_LOG = Path("/home/workspace/Daily_Log")

def get_mlb_final_scores(date_str: str = None) -> Dict[str, dict]:
    """Pull final scores and player stats for completed MLB games via statsapi."""
    import statsapi
    
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    results = {}
    try:
        schedule = statsapi.schedule(date=date_str)
        for game in (schedule or []):
            game_id = game.get("game_id")
            status = game.get("status", "")
            
            if status not in ("Final", "Game Over", "Completed Early"):
                continue
            
            matchup_key = f"{game.get('away_name', '')}@{game.get('home_name', '')}"
            
            try:
                box = statsapi.boxscore_data(game_id)
                linescore = statsapi.linescore(game_id)
                
                player_stats = {}
                
                for team_side in ("away", "home"):
                    team_data = box.get(team_side, {})
                    team_name = team_data.get("team", {}).get("name", "") if isinstance(team_data.get("team"), dict) else ""
                    
                    batters = team_data.get("batters", []) or []
                    for batter_id in batters:
                        batter = team_data.get("players", {}).get(f"ID{batter_id}", {})
                        if batter:
                            stats = batter.get("stats", {}).get("batting", {})
                            name = batter.get("person", {}).get("fullName", "")
                            player_stats[name] = {
                                "team": team_name,
                                "hits": int(stats.get("hits", 0) or 0),
                                "homeRuns": int(stats.get("homeRuns", 0) or 0),
                                "rbi": int(stats.get("rbi", 0) or 0),
                                "stolenBases": int(stats.get("stolenBases", 0) or 0),
                                "runs": int(stats.get("runs", 0) or 0),
                                "strikeOuts": int(stats.get("strikeOuts", 0) or 0),
                                "atBats": int(stats.get("atBats", 0) or 0),
                                "ops": float(stats.get("ops", 0) or 0),
                            }
                    
                    pitchers = team_data.get("pitchers", []) or []
                    for pitcher_id in pitchers:
                        pitcher = team_data.get("players", {}).get(f"ID{pitcher_id}", {})
                        if pitcher:
                            stats = pitcher.get("stats", {}).get("pitching", {})
                            name = pitcher.get("person", {}).get("fullName", "")
                            player_stats[name] = {
                                "team": team_name,
                                "era": float(stats.get("era", 0) or 0),
                                "strikeOuts": int(stats.get("strikeOuts", 0) or 0),
                                "inningsPitched": stats.get("inningsPitched", "0"),
                                "hits": int(stats.get("hits", 0) or 0),
                                "runs": int(stats.get("runs", 0) or 0),
                            }
                
                results[matchup_key] = {
                    "game_id": game_id,
                    "status": status,
                    "home_score": game.get("home_score", 0),
                    "away_score": game.get("away_score", 0),
                    "players": player_stats,
                }
                logger.info(f"[GRADING] {matchup_key}: Final — {len(player_stats)} players")
                
            except Exception as e:
                logger.warning(f"[GRADING] Boxscore {matchup_key}: {e}")
                
    except Exception as e:
        logger.warning(f"[GRADING] Schedule fetch: {e}")
    
    return results


def grade_picks_against_live(date_str: str = None) -> Dict:
    """Grade today's picks against live final scores from statsapi."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    picks_csv = DATA_DIR / f"mlb_{date_str}.csv"
    graded_csv = DAILY_LOG / date_str / "graded_picks.csv"
    
    if not picks_csv.exists():
        logger.info(f"[GRADING] No picks CSV for {date_str}")
        return {"date": date_str, "total": 0, "graded": 0, "hits": 0, "hit_rate": 0}
    
    boxscores = get_mlb_final_scores(date_str)
    logger.info(f"[GRADING] {len(boxscores)} completed games found for {date_str}")
    
    if not boxscores:
        return {"date": date_str, "total": 0, "graded": 0, "hits": 0, "hit_rate": 0, "note": "No completed games yet"}
    
    picks = []
    with open(picks_csv) as f:
        reader = csv.DictReader(f)
        picks = list(reader)
    
    stat_map = {
        "H": "hits",
        "HR": "homeRuns",
        "RBI": "rbi",
        "SB": "stolenBases",
        "R": "runs",
        "SO": "strikeOuts",
        "ERA": "era",
    }
    
    graded = []
    hits = 0
    total = 0
    
    for pick in picks:
        name = pick.get("name", "")
        stat = pick.get("stat", "")
        matchup = pick.get("matchup", "")
        projection = float(pick.get("projection", 0) or 0)
        direction = pick.get("direction", "OVER")
        sport = pick.get("sport", "mlb")
        
        if sport != "mlb":
            continue
        
        total += 1
        stats_key = stat_map.get(stat, stat.lower())
        actual = 0
        hit = None
        
        game_data = boxscores.get(matchup, {})
        players = game_data.get("players", {})
        
        if name in players:
            actual = players[name].get(stats_key, 0) or 0
            if direction == "OVER":
                hit = actual > projection
            else:
                hit = actual < projection
            if hit:
                hits += 1
        else:
            for pname, pdata in players.items():
                if name.lower() in pname.lower():
                    actual = pdata.get(stats_key, 0) or 0
                    if direction == "OVER":
                        hit = actual > projection
                    else:
                        hit = actual < projection
                    if hit:
                        hits += 1
                    break
        
        graded.append({
            **pick,
            "actual": str(actual),
            "hit": str(hit).lower() if hit is not None else "pending",
            "graded_at": datetime.now().isoformat(),
        })
    
    DAILY_LOG.mkdir(parents=True, exist_ok=True)
    (DAILY_LOG / date_str).mkdir(parents=True, exist_ok=True)
    
    fieldnames = list(graded[0].keys()) if graded else []
    with open(graded_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(graded)
    
    hit_rate = hits / total * 100 if total > 0 else 0
    result = {
        "date": date_str,
        "total": total,
        "graded": len([g for g in graded if g.get("hit") != "pending"]),
        "hits": hits,
        "hit_rate": round(hit_rate, 1),
        "completed_games": len(boxscores),
    }
    
    logger.info(f"[GRADING] {date_str}: {hits}/{total} ({hit_rate:.1f}%) — {len(boxscores)} games")
    return result


def grading_summary(date_str: str = None) -> str:
    """Return a human-readable grading summary."""
    result = grade_picks_against_live(date_str)
    if result.get("note"):
        return f"No completed games yet — {result['note']}"
    return (
        f"Grading {result['date']}: {result['graded']}/{result['total']} picks graded, "
        f"{result['hits']} hits ({result['hit_rate']}%) — {result['completed_games']} completed games"
    )
