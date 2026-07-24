"""NBA live data adapter — free, no-key, swar/nba_api package (OFF-SEASON)."""
from __future__ import annotations
import logging
from datetime import date
from typing import Dict, List, Any, Optional
from nba_api.stats.endpoints import (
    leaguegamefinder, boxscoretraditionalv2, scoreboardv2,
    playergamelogs, commonallplayers, commonteamroster
)
from nba_api.stats.library.parameters import LeagueID
from nba_api.stats.static import teams

logger = logging.getLogger(__name__)
CACHE = {}


def get_todays_games() -> List[Dict]:
    try:
        board = scoreboardv2.ScoreboardV2(league_id=LeagueID.nba)
        games = board.game_header.get_data_frame()
        if games.empty:
            return []
        results = []
        for _, g in games.iterrows():
            results.append({
                "game_id": g.get("GAME_ID"),
                "home_team": _team_name(g.get("HOME_TEAM_ID")),
                "away_team": _team_name(g.get("VISITOR_TEAM_ID")),
                "home_score": g.get("HOME_TEAM_SCORE", 0),
                "away_score": g.get("VISITOR_TEAM_SCORE", 0),
                "status": g.get("GAME_STATUS_TEXT", ""),
                "period": g.get("LIVE_PERIOD", 0),
                "clock": g.get("LIVE_PC_TIME", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"NBA scoreboard: {e}")
        return []


def get_boxscore(game_id: str) -> Dict[str, Any]:
    try:
        box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
        players = box.player_stats.get_data_frame()
        team = box.team_stats.get_data_frame()
        starters = players[players["STARTING_POSITION"].notna() & (players["STARTING_POSITION"] != "")]
        bench = players[~players.index.isin(starters.index)]
        return {
            "game_id": game_id,
            "starters": starters.to_dict("records"),
            "bench": bench.to_dict("records"),
            "team_stats": team.to_dict("records"),
        }
    except Exception as e:
        logger.warning(f"NBA boxscore {game_id}: {e}")
        return {"game_id": game_id, "starters": [], "bench": [], "team_stats": [], "error": str(e)}


def get_player_season_stats(season: str = "2025-26", last_n: int = 20) -> List[Dict]:
    try:
        logs = playergamelogs.PlayerGameLogs(
            season_nullable=season,
            last_n_games_nullable=last_n,
            league_id_nullable=LeagueID.nba
        )
        return logs.player_game_logs.get_data_frame().to_dict("records")
    except Exception as e:
        logger.warning(f"NBA player stats: {e}")
        return []


def get_roster(team_id: int) -> List[Dict]:
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        return roster.common_team_roster.get_data_frame().to_dict("records")
    except Exception as e:
        logger.warning(f"NBA roster {team_id}: {e}")
        return []


def get_offseason_status() -> Dict[str, Any]:
    return {
        "status": "OFF-SEASON",
        "note": "NBA is off-season. Draft completed, free agency ongoing.",
        "next_event": "Summer League — July 2026",
        "regular_season_start": "October 2026",
    }


_team_cache: Dict[int, str] = {}


def _team_name(team_id: int) -> str:
    if team_id not in _team_cache:
        try:
            t = teams.find_team_name_by_id(team_id)
            _team_cache[team_id] = t.get("full_name", str(team_id)) if t else str(team_id)
        except Exception:
            _team_cache[team_id] = str(team_id)
    return _team_cache[team_id]
