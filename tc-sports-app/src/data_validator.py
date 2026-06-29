"""Data validator - the GATE between API response and user output.

Rejects incomplete/bad data BEFORE any alert or pick is sent.
This is the #1 fix - your old system trusted HTTP 200 = good data.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


class ValidationError:
    def __init__(self, field: str, reason: str, severity: str = "error"):
        self.field = field
        self.reason = reason
        self.severity = severity  # "error" = block, "warning" = log

    def to_dict(self):
        return {"field": self.field, "reason": self.reason, "severity": self.severity}


class PickValidator:
    """Validates a pick has all required fields and reasonable values."""

    REQUIRED_FIELDS = ["player", "stat", "line", "direction", "odds", "sport", "game_time"]
    MIN_ODDS = -10000
    MAX_ODDS = 10000
    VALID_DIRECTIONS = {"over", "under", "higher", "lower"}
    VALID_STATS = {"pts", "reb", "ast", "stl", "blk", "3pm", "pra", "pr", "pa", "ra", "so", "hits", "runs", "rbis", "hr", "sb"}

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate_pick(self, pick: Dict[str, Any]) -> bool:
        self.errors = []
        self.warnings = []
        for field in self.REQUIRED_FIELDS:
            if field not in pick or pick[field] is None or pick[field] == "":
                self.errors.append(ValidationError(field, "missing required field"))
        if "odds" in pick and isinstance(pick["odds"], (int, float)):
            if pick["odds"] < self.MIN_ODDS or pick["odds"] > self.MAX_ODDS:
                self.errors.append(ValidationError("odds", f"out of range: {pick['odds']}"))
        if "direction" in pick and isinstance(pick["direction"], str):
            if pick["direction"].lower() not in self.VALID_DIRECTIONS:
                self.errors.append(ValidationError("direction", f"invalid: {pick['direction']}"))
        if "stat" in pick and isinstance(pick["stat"], str):
            if pick["stat"].lower() not in self.VALID_STATS:
                self.warnings.append(ValidationError("stat", f"unknown stat: {pick['stat']}"))
        if "line" in pick and isinstance(pick["line"], (int, float)):
            if pick["line"] < 0:
                self.warnings.append(ValidationError("line", f"negative line: {pick['line']}"))
        return len(self.errors) == 0

    def validate_batch(self, picks: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid = []
        invalid = []
        for i, pick in enumerate(picks):
            if self.validate_pick(pick):
                valid.append(pick)
            else:
                invalid.append({"index": i, "pick": pick, "errors": [e.to_dict() for e in self.errors]})
        return {"valid_picks": valid, "invalid_picks": invalid, "valid_count": len(valid), "invalid_count": len(invalid)}


class GameDataValidator:
    """Validates game data (schedules, lineups, injuries)."""

    def validate_game(self, game: Dict[str, Any]) -> bool:
        required = ["game_id", "home_team", "away_team", "start_time"]
        for field in required:
            if field not in game or not game[field]:
                return False
        if "status" in game and game["status"] not in ["scheduled", "live", "final", "postponed"]:
            return False
        return True

    def validate_lineup(self, lineup: Dict[str, Any]) -> bool:
        if "team" not in lineup or "players" not in lineup:
            return False
        if not isinstance(lineup["players"], list) or len(lineup["players"]) < 5:
            return False
        for p in lineup["players"]:
            if "name" not in p or "position" not in p:
                return False
        return True


class DataFreshnessChecker:
    """Validates data is recent enough to use."""

    MAX_AGE_MINUTES = {
        "live_odds": 5,
        "pregame_odds": 60,
        "lineups": 30,
        "injuries": 60,
        "weather": 120,
    }

    def is_fresh(self, data: Dict[str, Any], data_type: str) -> bool:
        if "fetched_at" not in data:
            return False
        try:
            fetched = datetime.fromisoformat(data["fetched_at"])
            age_min = (datetime.now() - fetched).total_seconds() / 60
            max_age = self.MAX_AGE_MINUTES.get(data_type, 60)
            return age_min <= max_age
        except (ValueError, TypeError):
            return False


def gate_picks(picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Main entry: validates picks before they can be sent/alerts triggered."""
    validator = PickValidator()
    return validator.validate_batch(picks)


def gate_game_data(games: List[Dict[str, Any]]) -> Dict[str, Any]:
    validator = GameDataValidator()
    valid = [g for g in games if validator.validate_game(g)]
    return {"valid_games": valid, "invalid_count": len(games) - len(valid), "total": len(games)}
