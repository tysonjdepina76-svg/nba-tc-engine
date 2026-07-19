"""MLB live data adapter — free, no-key, statsapi (MLB-StatsAPI) + pybaseball. IN-SEASON."""
from __future__ import annotations
import logging
from typing import Dict, List, Any, Optional
import statsapi
import pybaseball

logger = logging.getLogger(__name__)


def get_todays_games() -> List[Dict]:
    try:
        sched = statsapi.schedule(date=None)
        results = []
        for g in (sched or []):
            results.append({
                "game_id": g.get("game_id"),
                "home_team": g.get("home_name", ""),
                "away_team": g.get("away_name", ""),
                "home_score": int(g.get("home_score") or 0),
                "away_score": int(g.get("away_score") or 0),
                "status": g.get("status", ""),
                "inning": g.get("inning", 0),
                "inning_state": g.get("inning_state", ""),
                "current_inning": g.get("current_inning", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"MLB schedule: {e}")
        return []


def get_live_boxscore(game_id: int) -> Dict[str, Any]:
    try:
        bs = statsapi.boxscore_data(game_id)
        box = statsapi.boxscore(game_id)
        linescore = statsapi.linescore(game_id)
        return {
            "game_id": game_id,
            "boxscore": bs,
            "linescore": linescore,
            "raw": box,
        }
    except Exception as e:
        logger.warning(f"MLB boxscore {game_id}: {e}")
        return {"game_id": game_id, "error": str(e)}


def get_batter_vs_pitcher(batter_id: int, pitcher_id: int) -> Dict[str, Any]:
    try:
        bvp = statsapi.batter_vs_pitcher(batter_id, pitcher_id)
        return bvp or {}
    except Exception as e:
        logger.warning(f"MLB BvP {batter_id}v{pitcher_id}: {e}")
        return {}


def get_roster(team_id: int) -> List[Dict]:
    try:
        roster = statsapi.roster(team_id)
        return roster if isinstance(roster, list) else [roster]
    except Exception as e:
        logger.warning(f"MLB roster {team_id}: {e}")
        return []


def get_player_stats(player_id: int, season: str = "2026") -> Dict[str, Any]:
    try:
        stats = statsapi.player_stat_data(player_id, group="hitting", type="season")
        return stats or {}
    except Exception as e:
        logger.warning(f"MLB player stats {player_id}: {e}")
        return {}


def lookup_player(name: str) -> Dict[str, Any]:
    try:
        return statsapi.lookup_player(name) or {}
    except Exception as e:
        logger.warning(f"MLB lookup '{name}': {e}")
        return {}


def get_league_leaders(stat: str = "homeRuns", season: int = 2026) -> List[Dict]:
    try:
        leaders = statsapi.league_leaders(stat, season=season, limit=50)
        return leaders if isinstance(leaders, list) else [leaders]
    except Exception as e:
        logger.warning(f"MLB league leaders '{stat}': {e}")
        return []


def get_team_leaders(team_id: int, stat: str = "homeRuns", season: int = 2026) -> Dict:
    try:
        return statsapi.team_leaders(team_id, stat, season=season) or {}
    except Exception as e:
        logger.warning(f"MLB team leaders {team_id}/{stat}: {e}")
        return {}
