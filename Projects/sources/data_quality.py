"""
Data quality monitoring (from legacy nba_tc_pipeline_v2).
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sources.utils.logging import get_logger

logger = get_logger(__name__)


class DataQualityMonitor:
    """Monitor data quality for all sports."""

    def __init__(self):
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.passed: int = 0
        self.failed: int = 0

    def reset(self) -> None:
        self.issues = []
        self.warnings = []
        self.passed = 0
        self.failed = 0

    def check_null_values(self, data: Dict, fields: List[str], context: str = "") -> List[str]:
        null_fields = []
        for field in fields:
            if field not in data or data[field] is None:
                null_fields.append(field)

        if null_fields:
            issue = {
                "type": "null_values",
                "context": context,
                "fields": null_fields,
                "count": len(null_fields),
                "timestamp": datetime.now().isoformat()
            }
            self.issues.append(issue)
            self.failed += 1
        else:
            self.passed += 1

        return null_fields

    def check_outliers(self, data: List[Dict], field: str, lower: float, upper: float, context: str = "") -> List[Dict]:
        outliers = []
        for item in data:
            val = item.get(field, 0)
            if isinstance(val, (int, float)):
                if val < lower or val > upper:
                    outliers.append(item)

        if outliers:
            issue = {
                "type": "outliers",
                "context": context,
                "field": field,
                "count": len(outliers),
                "lower_bound": lower,
                "upper_bound": upper,
                "sample": outliers[:5],
                "timestamp": datetime.now().isoformat()
            }
            self.issues.append(issue)
            self.failed += 1
        else:
            self.passed += 1

        return outliers

    def check_missing_teams(self, players: List[Dict]) -> List[Dict]:
        missing = [p for p in players if not p.get("team")]
        if missing:
            issue = {
                "type": "missing_teams",
                "count": len(missing),
                "players": [p.get("name", "Unknown") for p in missing[:10]],
                "timestamp": datetime.now().isoformat()
            }
            self.issues.append(issue)
            self.failed += 1
        else:
            self.passed += 1
        return missing

    def check_negative_stats(self, players: List[Dict], stat_fields: List[str]) -> List[Dict]:
        negatives = []
        for p in players:
            for field in stat_fields:
                val = p.get(field, 0)
                if isinstance(val, (int, float)) and val < 0:
                    negatives.append({"player": p.get("name", "Unknown"), "field": field, "value": val})

        if negatives:
            issue = {
                "type": "negative_stats",
                "count": len(negatives),
                "sample": negatives[:10],
                "timestamp": datetime.now().isoformat()
            }
            self.issues.append(issue)
            self.failed += 1
        else:
            self.passed += 1

        return negatives

    def check_player_data(self, players: List[Dict], sport: str) -> Dict[str, Any]:
        self.reset()

        stat_fields = {
            "mlb": ["avg", "hr", "rbi", "r", "sb", "ops", "era", "whip", "so"],
            "wnba": ["pts", "reb", "ast", "fg_pct", "fg3", "stl", "blk"],
            "wc": ["goals", "assists", "shots", "shots_on_target", "pass_pct", "tackles", "fouls"],
            "nfl": ["pass_yds", "rush_yds", "rec_yds", "td", "int", "sacks"],
            "nhl": ["goals", "assists", "points", "sog", "pim"],
        }.get(sport, ["pts", "reb", "ast"])

        null_names = [p for p in players if not p.get("name")]
        if null_names:
            self.issues.append({
                "type": "null_names",
                "count": len(null_names),
                "timestamp": datetime.now().isoformat()
            })
            self.failed += 1
        else:
            self.passed += 1

        self.check_missing_teams(players)
        self.check_negative_stats(players, stat_fields)

        for field in stat_fields[:3]:
            values = [p.get(field, 0) for p in players if isinstance(p.get(field), (int, float))]
            if values:
                mean = sum(values) / len(values)
                std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
                lower = max(0, mean - 3 * std)
                upper = mean + 3 * std
                self.check_outliers(players, field, lower, upper, f"{sport} {field}")

        return {
            "status": "pass" if self.failed == 0 else "fail",
            "passed": self.passed,
            "failed": self.failed,
            "issues": self.issues,
            "warnings": self.warnings,
            "player_count": len(players),
            "timestamp": datetime.now().isoformat()
        }

    def check_game_data(self, games: List[Dict], sport: str) -> Dict[str, Any]:
        self.reset()

        missing_away = [g for g in games if not g.get("away")]
        missing_home = [g for g in games if not g.get("home")]

        if missing_away:
            self.issues.append({"type": "missing_away_teams", "count": len(missing_away)})
            self.failed += 1
        else:
            self.passed += 1

        if missing_home:
            self.issues.append({"type": "missing_home_teams", "count": len(missing_home)})
            self.failed += 1
        else:
            self.passed += 1

        seen = set()
        duplicates = []
        for g in games:
            key = f"{g.get('away', '')}@{g.get('home', '')}"
            if key in seen:
                duplicates.append(key)
            seen.add(key)

        if duplicates:
            self.issues.append({"type": "duplicate_games", "count": len(duplicates), "sample": duplicates[:5]})
            self.failed += 1
        else:
            self.passed += 1

        return {
            "status": "pass" if self.failed == 0 else "fail",
            "passed": self.passed,
            "failed": self.failed,
            "issues": self.issues,
            "game_count": len(games),
            "timestamp": datetime.now().isoformat()
        }


def validate_data(sport: str, data: Dict) -> Dict:
    monitor = DataQualityMonitor()

    if "players" in data and data["players"]:
        result = monitor.check_player_data(data["players"], sport)
        return result
    elif "games" in data and data["games"]:
        result = monitor.check_game_data(data["games"], sport)
        return result
    else:
        return {
            "status": "warning",
            "passed": 0,
            "failed": 0,
            "issues": [{"type": "no_data", "message": "No players or games found"}],
            "timestamp": datetime.now().isoformat()
        }


def validate_players(players: List[Dict], sport: str) -> Dict:
    return validate_data(sport, {"players": players})


def validate_games(games: List[Dict], sport: str) -> Dict:
    return validate_data(sport, {"games": games})


if __name__ == "__main__":
    sample_players = [
        {"name": "A'ja Wilson", "team": "LV", "pts": 25.7, "reb": 11.2},
        {"name": "Test Player", "team": "", "pts": -5.0},
    ]
    result = validate_players(sample_players, "wnba")
    print(f"Data quality: {result['status']}")
    print(f"Passed: {result['passed']}, Failed: {result['failed']}")
    print(f"Issues: {len(result['issues'])}")
