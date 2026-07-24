#!/usr/bin/env python3
"""Live auto-grading via statsapi — grades picks against real boxscores."""
from __future__ import annotations
import logging
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("tc_pipeline")

PROJECT_ROOT = Path("/home/workspace")
PICKS_DIR = PROJECT_ROOT / "data" / "picks"
DAILY_LOG = PROJECT_ROOT / "Daily_Log"


def get_live_mlb_game_results(date_str: Optional[str] = None) -> Dict[str, Dict]:
    """Pull final/active MLB game results via statsapi. Returns {game_id: {home_score, away_score, status, player_stats}}."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    results = {}
    try:
        import statsapi
        sched = statsapi.schedule(date=date_str)
        if not sched:
            logger.info(f"[LIVE-GRADER] No MLB games on {date_str}")
            return results
        for g in sched:
            gid = g.get("game_id")
            status = g.get("status", "")
            home = g.get("home_name", "")
            away = g.get("away_name", "")
            home_score = int(g.get("home_score") or 0)
            away_score = int(g.get("away_score") or 0)
            results[str(gid)] = {
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
                "inning": g.get("inning", 0),
                "inning_state": g.get("inning_state", ""),
                "player_stats": {},
            }
            if "Final" in status or "Completed" in status:
                try:
                    box = statsapi.boxscore_data(gid)
                    _extract_player_stats(box, results[str(gid)]["player_stats"])
                except Exception as e:
                    logger.warning(f"[LIVE-GRADER] Boxscore {gid} ({away}@{home}): {e}")
        completed = sum(1 for v in results.values() if "Final" in v["status"])
        logger.info(f"[LIVE-GRADER] {len(results)} games, {completed} final on {date_str}")
    except Exception as e:
        logger.warning(f"[LIVE-GRADER] MLB schedule failed: {e}")
    return results


def _extract_player_stats(box_data: Dict, target: Dict) -> None:
    """Extract per-player stats from statsapi boxscore data."""
    for side_key in ("home", "away"):
        side = box_data.get(side_key, {})
        players = side.get("players", {}) if isinstance(side, dict) else {}
        for player_id, pinfo in players.items():
            if not isinstance(pinfo, dict):
                continue
            name = pinfo.get("person", {}).get("fullName", "") if isinstance(pinfo.get("person"), dict) else pinfo.get("name", "")
            if not name:
                continue
            stats_data = pinfo.get("stats", {})
            batting = stats_data.get("batting", {}) if isinstance(stats_data, dict) else {}
            target[name] = {
                "hits": int(batting.get("hits", 0) or 0),
                "runs": int(batting.get("runs", 0) or 0),
                "rbi": int(batting.get("rbi", 0) or 0),
                "homeRuns": int(batting.get("homeRuns", 0) or 0),
                "stolenBases": int(batting.get("stolenBases", 0) or 0),
                "strikeOuts": int(batting.get("strikeOuts", 0) or 0),
                "atBats": int(batting.get("atBats", 0) or 0),
                "doubles": int(batting.get("doubles", 0) or 0),
                "triples": int(batting.get("triples", 0) or 0),
                "baseOnBalls": int(batting.get("baseOnBalls", 0) or 0),
            }


def load_picks_for_date(sport: str, date_str: str) -> List[Dict]:
    """Load picks from CSV for grading."""
    csv_path = PICKS_DIR / f"{sport}_{date_str}.csv"
    if not csv_path.exists():
        logger.info(f"[LIVE-GRADER] No picks CSV: {csv_path}")
        return []
    picks = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            picks.append(row)
    logger.info(f"[LIVE-GRADER] Loaded {len(picks)} {sport} picks for {date_str}")
    return picks


def grade_mlb_picks(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Grade today's MLB picks against live boxscores. Returns summary dict."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    picks = load_picks_for_date("mlb", date_str)
    if not picks:
        return {"date": date_str, "total": 0, "graded": 0, "message": "No picks to grade"}

    game_results = get_live_mlb_game_results(date_str)
    final_games = {k: v for k, v in game_results.items() if "Final" in v.get("status", "")}

    if not final_games:
        logger.info(f"[LIVE-GRADER] No final MLB games yet on {date_str}")
        return {"date": date_str, "total": len(picks), "graded": 0, "message": "No completed games yet"}

    stat_map = {
        "H": "hits", "R": "runs", "RBI": "rbi", "HR": "homeRuns",
        "SB": "stolenBases", "SO": "strikeOuts", "2B": "doubles",
        "3B": "triples", "BB": "baseOnBalls",
    }

    graded = []
    for pick in picks:
        name = pick.get("name", "").strip()
        stat = pick.get("stat", "H")
        proj = float(pick.get("projection", 0) or 0)
        direction = pick.get("direction", "OVER")

        actual = 0
        best_match = None
        for gid, game in final_games.items():
            for pname, pstats in game.get("player_stats", {}).items():
                if name.lower() in pname.lower() or pname.lower() in name.lower():
                    mapped = stat_map.get(stat, stat.lower())
                    actual = pstats.get(mapped, 0)
                    best_match = pname
                    break
            if best_match:
                break

        if best_match:
            hit = (actual > proj) if direction == "OVER" else (actual < proj)
        else:
            hit = None

        graded.append({
            **pick,
            "actual": actual,
            "hit": hit,
            "matched_name": best_match,
            "graded_at": datetime.now().isoformat(),
        })

    hits = sum(1 for g in graded if g["hit"] is True)
    misses = sum(1 for g in graded if g["hit"] is False)
    ungraded = sum(1 for g in graded if g["hit"] is None)
    hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0

    _save_graded_csv(date_str, graded)
    _save_graded_json(date_str, {"summary": {"total": len(graded), "hits": hits, "misses": misses, "ungraded": ungraded, "hit_rate": round(hit_rate, 2), "games_completed": len(final_games)}, "picks": graded})

    logger.info(f"[LIVE-GRADER] {hits}/{hits+misses} ({hit_rate:.1f}%), {ungraded} unmatched, {len(final_games)} final games")
    return {"date": date_str, "total": len(picks), "graded": hits + misses, "hits": hits, "misses": misses, "ungraded": ungraded, "hit_rate": round(hit_rate, 2), "games_completed": len(final_games)}


def _save_graded_csv(date_str: str, graded: List[Dict]) -> None:
    out_dir = DAILY_LOG / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "graded_picks.csv"
    fieldnames = ["name", "team", "sport", "stat", "matchup", "projection", "line", "edge", "direction", "reason", "actual", "hit", "matched_name", "graded_at"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for g in graded:
            writer.writerow({k: g.get(k, "") for k in fieldnames})
    logger.info(f"[LIVE-GRADER] Saved {len(graded)} graded picks to {path}")


def _save_graded_json(date_str: str, data: Dict) -> None:
    out_dir = DAILY_LOG / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "graded_summary.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"[LIVE-GRADER] Summary saved to {path}")
