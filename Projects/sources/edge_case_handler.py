"""
Edge case handlers (from legacy nba_tc_engine) — injury, load management, trades, call-ups.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sources.utils.logging import get_logger

logger = get_logger(__name__)


class EdgeCaseHandler:
    """Handle NBA/WNBA edge cases: injuries, load management, trades, call-ups."""

    DEFAULT_ADJUSTMENTS = {
        "two_way": -0.15,
        "injury_return": -0.10,
        "load_management": -0.12,
        "mid_season_trade": -0.08,
        "g_league_callup": -0.20,
    }

    @staticmethod
    def handle_two_way_contract(player: Dict[str, Any]) -> Dict[str, Any]:
        if player.get("contract_type") == "two_way":
            player["minutes_limit"] = 45
            player["availability_risk"] = 0.3
            player["projection_adjustment"] = EdgeCaseHandler.DEFAULT_ADJUSTMENTS["two_way"]
            player["adjusted"] = True
            logger.debug(f"Two-way adjustment applied to {player.get('name', 'Unknown')}")
        return player

    @staticmethod
    def handle_injury_return(player: Dict[str, Any]) -> Dict[str, Any]:
        if player.get("injury_status") == "returning":
            player["minutes_restriction"] = player.get("season_avg_minutes", 0) * 0.7
            player["conditioning_risk"] = 0.2
            player["rust_factor"] = 0.15
            player["projection_adjustment"] = EdgeCaseHandler.DEFAULT_ADJUSTMENTS["injury_return"]
            player["adjusted"] = True
            logger.debug(f"Injury return adjustment applied to {player.get('name', 'Unknown')}")
        return player

    @staticmethod
    def handle_load_management(player: Dict[str, Any]) -> Dict[str, Any]:
        if player.get("load_management") or (
            player.get("back_to_back") and player.get("is_star", False)
        ):
            player["rest_risk"] = 0.25
            player["load_management_minutes"] = player.get("season_avg_minutes", 0) * 0.85
            player["projection_adjustment"] = EdgeCaseHandler.DEFAULT_ADJUSTMENTS["load_management"]
            player["adjusted"] = True
            logger.debug(f"Load management adjustment applied to {player.get('name', 'Unknown')}")
        return player

    @staticmethod
    def handle_mid_season_trade(player: Dict[str, Any]) -> Dict[str, Any]:
        if player.get("traded_mid_season"):
            player["system_uncertainty"] = 0.3
            player["role_uncertainty"] = 0.2
            player["chemistry_factor"] = 0.1
            player["projection_adjustment"] = EdgeCaseHandler.DEFAULT_ADJUSTMENTS["mid_season_trade"]
            player["adjusted"] = True
            logger.debug(f"Mid-season trade adjustment applied to {player.get('name', 'Unknown')}")
        return player

    @staticmethod
    def handle_g_league_callup(player: Dict[str, Any]) -> Dict[str, Any]:
        if player.get("callup") or player.get("is_callup"):
            player["experience_factor"] = 0.6
            player["sample_size"] = "small"
            player["projection_adjustment"] = EdgeCaseHandler.DEFAULT_ADJUSTMENTS["g_league_callup"]
            player["adjusted"] = True
            logger.debug(f"G-League call-up adjustment applied to {player.get('name', 'Unknown')}")
        return player

    @staticmethod
    def apply_all_adjustments(player: Dict[str, Any]) -> Dict[str, Any]:
        original = player.copy()
        adjusted = player.copy()

        adjusted = EdgeCaseHandler.handle_two_way_contract(adjusted)
        adjusted = EdgeCaseHandler.handle_injury_return(adjusted)
        adjusted = EdgeCaseHandler.handle_load_management(adjusted)
        adjusted = EdgeCaseHandler.handle_mid_season_trade(adjusted)
        adjusted = EdgeCaseHandler.handle_g_league_callup(adjusted)

        total_adjustment = sum(
            adjusted.get(k, 0)
            for k in ["projection_adjustment"]
            if k in adjusted and isinstance(adjusted[k], (int, float))
        )
        if total_adjustment != 0 and "pts" in adjusted:
            adjusted["pts"] = round(adjusted["pts"] * (1 + total_adjustment), 1)
            adjusted["projection"] = round(adjusted.get("projection", adjusted["pts"]) * (1 + total_adjustment), 1)

        if "adjusted" not in adjusted:
            adjusted["adjusted"] = False

        return adjusted

    @staticmethod
    def get_adjustment_summary(player: Dict[str, Any]) -> Dict[str, Any]:
        summary = {
            "name": player.get("name", "Unknown"),
            "adjusted": player.get("adjusted", False),
            "adjustments": []
        }
        if player.get("minutes_limit"):
            summary["adjustments"].append(f"Minutes limit: {player['minutes_limit']}")
        if player.get("minutes_restriction"):
            summary["adjustments"].append(f"Minutes restriction: {player['minutes_restriction']}")
        if player.get("conditioning_risk"):
            summary["adjustments"].append(f"Conditioning risk: {player['conditioning_risk']}")
        if player.get("rest_risk"):
            summary["adjustments"].append(f"Rest risk: {player['rest_risk']}")
        if player.get("system_uncertainty"):
            summary["adjustments"].append(f"System uncertainty: {player['system_uncertainty']}")
        if player.get("role_uncertainty"):
            summary["adjustments"].append(f"Role uncertainty: {player['role_uncertainty']}")
        if player.get("experience_factor"):
            summary["adjustments"].append(f"Experience factor: {player['experience_factor']}")
        if player.get("sample_size"):
            summary["adjustments"].append(f"Sample size: {player['sample_size']}")
        if player.get("projection_adjustment"):
            summary["adjustments"].append(f"Projection adjustment: {player['projection_adjustment']:.2f}")
        return summary


def apply_edge_cases(player: Dict[str, Any]) -> Dict[str, Any]:
    return EdgeCaseHandler.apply_all_adjustments(player)


def get_edge_case_summary(player: Dict[str, Any]) -> Dict[str, Any]:
    return EdgeCaseHandler.get_adjustment_summary(player)


if __name__ == "__main__":
    test_players = [
        {"name": "Two-Way Player", "contract_type": "two_way", "pts": 10.0},
        {"name": "Injury Return", "injury_status": "returning", "season_avg_minutes": 30, "pts": 15.0},
        {"name": "Load Management", "load_management": True, "is_star": True, "season_avg_minutes": 35, "pts": 20.0},
        {"name": "Traded Player", "traded_mid_season": True, "pts": 12.0},
        {"name": "Call-up", "callup": True, "pts": 8.0},
    ]
    for p in test_players:
        adjusted = apply_edge_cases(p)
        summary = get_edge_case_summary(adjusted)
        print(f"\n{summary['name']}:")
        print(f"  Adjusted: {summary['adjusted']}")
        print(f"  PTS: {adjusted.get('pts', 0)}")
        if summary['adjustments']:
            print(f"  Adjustments: {', '.join(summary['adjustments'])}")
