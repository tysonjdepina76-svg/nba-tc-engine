"""Shared roster loader for all pipeline scripts.
Loads team rosters from /home/workspace/data/rosters/{mlb,wnba}_rosters.json
and provides name lists and player-team lookup maps.
"""

import json
from pathlib import Path
from typing import Optional

ROSTER_DIR = Path("/home/workspace/data/rosters")

_mlb_cache: Optional[dict] = None
_wnba_cache: Optional[dict] = None

POSITION_PLAYERS = {"1B", "2B", "3B", "SS", "C", "LF", "CF", "RF", "DH", "OF", "IF", "UTIL", "UT"}
PITCHERS = {"SP", "RP", "P", "CL"}


def load_mlb_rosters() -> dict:
    """Return {team_abbr: [player_dict, ...]} from MLB roster file."""
    global _mlb_cache
    if _mlb_cache is not None:
        return _mlb_cache
    p = ROSTER_DIR / "mlb_rosters.json"
    with open(p) as f:
        raw = json.load(f)
    rosters = raw.get("rosters", raw) if isinstance(raw, dict) else {}
    out: dict[str, list] = {}
    for key, val in rosters.items():
        players = val.get("players", []) if isinstance(val, dict) else (val if isinstance(val, list) else [])
        out[key] = players
    _mlb_cache = out
    return out


def load_wnba_rosters() -> dict:
    """Return {team_abbr: [player_dict, ...]} from WNBA roster file."""
    global _wnba_cache
    if _wnba_cache is not None:
        return _wnba_cache
    p = ROSTER_DIR / "wnba_rosters.json"
    with open(p) as f:
        raw = json.load(f)
    out: dict[str, list] = {}
    for key, val in raw.items():
        players = val.get("players", []) if isinstance(val, dict) else (val if isinstance(val, list) else [])
        out[key] = players
    _wnba_cache = out
    return out


def _is_batter(pos: str) -> bool:
    return pos.upper() in POSITION_PLAYERS


def get_mlb_player_names(team: str, limit: int = 0, batters_only: bool = True) -> list[str]:
    """Get player names for an MLB team. batters_only=True filters out pitchers."""
    rosters = load_mlb_rosters()
    players = rosters.get(team, [])
    if batters_only:
        players = [p for p in players if _is_batter(p.get("position", ""))]
    names = [p["name"] for p in players]
    return names[:limit] if limit else names


def get_wnba_player_names(team: str, limit: int = 0) -> list[str]:
    """Get player names for a WNBA team."""
    rosters = load_wnba_rosters()
    players = rosters.get(team, [])
    names = [p["name"] for p in players]
    return names[:limit] if limit else names


def get_mlb_player(name: str, team: str = "") -> Optional[dict]:
    """Find an MLB player by name, optionally filtered by team."""
    rosters = load_mlb_rosters()
    if team and team in rosters:
        for p in rosters[team]:
            if p["name"].lower() == name.lower():
                return p
    for t_players in rosters.values():
        for p in t_players:
            if p["name"].lower() == name.lower():
                return p
    return None


def get_wnba_player(name: str, team: str = "") -> Optional[dict]:
    """Find a WNBA player by name, optionally filtered by team."""
    rosters = load_wnba_rosters()
    if team and team in rosters:
        for p in rosters[team]:
            if p["name"].lower() == name.lower():
                return p
    for t_players in rosters.values():
        for p in t_players:
            if p["name"].lower() == name.lower():
                return p
    return None


def build_mlb_player_team_map() -> dict:
    """Build {player_name_lower: team_abbr} lookup for team correction."""
    rosters = load_mlb_rosters()
    result = {}
    for team, players in rosters.items():
        for p in players:
            result[p["name"].lower()] = team
    return result


def build_wnba_player_team_map() -> dict:
    """Build {player_name_lower: team_abbr} lookup for team correction."""
    rosters = load_wnba_rosters()
    result = {}
    for team, players in rosters.items():
        for p in players:
            result[p["name"].lower()] = team
    return result
