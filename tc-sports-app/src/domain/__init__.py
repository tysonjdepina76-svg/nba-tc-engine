"""Domain layer — pure data + pure math, zero I/O."""
from .entities import Game, Player, Projection, Sport, BADGE_COLORS
from .engine import TCEngine, compute_line_and_edge, compute_tc_projection, project_game, project_player
from .sport_config import SPORT_CONFIG, get_config, get_sport_config, stat_keys

__all__ = [
    "Game",
    "Player",
    "Projection",
    "Sport",
    "BADGE_COLORS",
    "TCEngine",
    "compute_tc_projection",
    "compute_line_and_edge",
    "project_game",
    "project_player",
    "SPORT_CONFIG",
    "get_config",
    "get_sport_config",
    "stat_keys",
]