"""WNBA live data adapter — free, no-key, swar/nba_api (WNBA LeagueID)."""
from __future__ import annotations
import logging
from typing import Dict, List, Any
from nba_api.stats.endpoints import (
    scoreboardv2, boxscoretraditionalv2,
    playergamelogs, commonteamroster
)
from nba_api.stats.library.parameters import LeagueID
from nba_api.stats.static import teams

logger = logging.getLogger(__name__)

WNBA_LEAGUE = LeagueID.wnba


def get_todays_games() -> List[Dict]:
    try:
        board = scoreboardv2.ScoreboardV2(league_id=WNBA_LEAGUE)
        games = board.game_header.get_data_frame()
        if games.empty:
            return []
        results = []
        for _, g in games.iterrows():
            results.append({
                "game_id": g.get("GAME_ID"),
                "home_team": _team_name(g.get("HOME_TEAM_ID")),
                "away_team": _team_name(g.get("VISITOR_TEAM_ID")),
                "home_score": int(g.get("HOME_TEAM_SCORE") or 0),
                "away_score": int(g.get("VISITOR_TEAM_SCORE") or 0),
                "status": g.get("GAME_STATUS_TEXT", ""),
                "period": int(g.get("LIVE_PERIOD") or 0),
                "clock": g.get("LIVE_PC_TIME", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"WNBA scoreboard: {e}")
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
            "starters": _format_players(starters),
            "bench": _format_players(bench),
            "team_stats": team.to_dict("records"),
        }
    except Exception as e:
        logger.warning(f"WNBA boxscore {game_id}: {e}")
        return {"game_id": game_id, "starters": [], "bench": [], "team_stats": [], "error": str(e)}


def get_player_season_stats(season: str = "2026", last_n: int = 20) -> List[Dict]:
    try:
        logs = playergamelogs.PlayerGameLogs(
            season_nullable=season,
            last_n_games_nullable=last_n,
            league_id_nullable=WNBA_LEAGUE
        )
        return logs.player_game_logs.get_data_frame().to_dict("records")
    except Exception as e:
        logger.warning(f"WNBA player stats: {e}")
        return []


def get_roster(team_id: int) -> List[Dict]:
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id, league_id_nullable=WNBA_LEAGUE)
        return roster.common_team_roster.get_data_frame().to_dict("records")
    except Exception as e:
        logger.warning(f"WNBA roster {team_id}: {e}")
        return []


def _format_players(df) -> List[Dict]:
    records = df.to_dict("records")
    for r in records:
        for k in list(r):
            try:
                if r[k] is not None and not isinstance(r[k], (str, bool, int, float)):
                    r[str(k)] = str(r[k])
            except Exception:
                pass
    return records


_team_cache: Dict[int, str] = {}


def _team_name(team_id: int) -> str:
    if team_id not in _team_cache:
        try:
            t = teams.find_team_name_by_id(team_id)
            _team_cache[team_id] = t.get("full_name", str(team_id)) if t else str(team_id)
        except Exception:
            _team_cache[team_id] = str(team_id)
    return _team_cache[team_id]
