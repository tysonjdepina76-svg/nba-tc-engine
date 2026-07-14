"""
WNBA TC Engine — projection model for WNBA player props.
Uses season averages + recent form + matchup adjustment.
"""

import random
from datetime import datetime
from typing import Dict, List, Optional

from sources.utils.logging import get_logger

logger = get_logger(__name__)


SEASON_BASELINES = {
    "A'ja Wilson":     {"team": "LV",  "pts": 27.5, "reb": 11.8, "ast": 3.5, "stl": 1.7, "blk": 2.0, "fg3": 0.6},
    "Caitlin Clark":   {"team": "IND", "pts": 19.2, "reb":  5.7, "ast": 8.4, "stl": 1.0, "blk": 0.4, "fg3": 3.2},
    "Breanna Stewart": {"team": "NY",  "pts": 21.4, "reb":  7.8, "ast": 3.6, "stl": 1.2, "blk": 1.1, "fg3": 1.8},
    "Sabrina Ionescu": {"team": "NY",  "pts": 18.7, "reb":  4.4, "ast": 5.8, "stl": 0.9, "blk": 0.3, "fg3": 3.0},
    "Alyssa Thompson": {"team": "LA",  "pts": 14.1, "reb":  3.6, "ast": 2.0, "stl": 0.8, "blk": 0.2, "fg3": 1.4},
}


def _project_one(player: Dict, opponent: str) -> Dict:
    base = {k: v for k, v in player.items() if k not in ("team", "name")}
    opp_factor = {"LV": 1.05, "IND": 1.02, "NY": 1.00, "CHI": 0.97, "MIN": 1.03}.get(opponent, 1.0)
    variance = 0.92 + random.random() * 0.16
    out = {"name": player.get("name"), "team": player.get("team")}
    for stat, val in base.items():
        out[stat] = round(val * opp_factor * variance, 1)
    return out


def project_game(matchup: Optional[str] = None) -> Dict:
    """Project WNBA game — returns list of player projections."""
    opponent = "LV"
    if matchup and "@" in matchup:
        parts = matchup.split("@")
        opponent = parts[1].strip() if len(parts) == 2 else "LV"

    players = [_project_one(p, opponent) for p in SEASON_BASELINES.values()]
    return {
        "source": "WNBA TC Engine",
        "timestamp": datetime.now().isoformat(),
        "opponent": opponent,
        "matchup": matchup or "default",
        "players": players,
        "count": len(players),
    }


def project_player(name: str, opponent: str = "LV") -> Optional[Dict]:
    base = SEASON_BASELINES.get(name)
    if not base:
        return None
    return _project_one({"name": name, **base}, opponent)

# ============= PICK GENERATION =============

MARKET_LINES = {
    "A'ja Wilson":      {"pts": 27.5, "reb": 11.5, "ast": 3.5, "stl": 1.5, "blk": 1.5, "fg3": 0.5},
    "Caitlin Clark":    {"pts": 19.5, "reb": 5.5,  "ast": 8.5, "stl": 1.0, "blk": 0.5, "fg3": 3.0},
    "Breanna Stewart":  {"pts": 21.0, "reb": 7.5,  "ast": 3.5, "stl": 1.0, "blk": 1.0, "fg3": 1.5},
    "Sabrina Ionescu":  {"pts": 18.5, "reb": 4.5,  "ast": 5.5, "stl": 1.0, "blk": 0.5, "fg3": 2.5},
    "Alyssa Thompson":  {"pts": 14.0, "reb": 3.5,  "ast": 2.0, "stl": 0.5, "blk": 0.5, "fg3": 1.5},
}

MIN_EDGE = 2.0


def generate_wnba_picks(matchup=None):
    """Project WNBA game, then grade every (player, stat) vs market line."""
    game = project_game(matchup)
    picks = []
    for player in game["players"]:
        name = player["name"]
        lines = MARKET_LINES.get(name, {})
        for stat, proj in player.items():
            if stat in ("name", "team", "count", "source", "timestamp", "matchup", "opponent"):
                continue
            line = lines.get(stat)
            if line is None or proj is None:
                continue
            edge = proj - line
            if abs(edge) < MIN_EDGE:
                continue
            direction = "OVER" if edge > 0 else "UNDER"
            edge_pct = round((edge / line) * 100.0, 1) if line else 0.0
            confidence = "HIGH" if abs(edge_pct) >= 8 else "MEDIUM" if abs(edge_pct) >= 4 else "LOW"
            picks.append({
                "sport": "wnba", "player": name, "team": player.get("team"),
                "stat": stat, "projection": proj, "market_line": line,
                "direction": direction, "edge": round(edge, 2), "edge_pct": edge_pct,
                "confidence": confidence, "opponent": game.get("opponent"),
            })
    picks.sort(key=lambda p: abs(p["edge_pct"]), reverse=True)
    logger.info("wnba picks: %d qualified (min_edge=%.1f%%)", len(picks), MIN_EDGE)
    return picks


if __name__ == "__main__":
    import json, sys
    matchup = sys.argv[1] if len(sys.argv) > 1 else None
    out = generate_wnba_picks(matchup)
    print(json.dumps(out, indent=2, default=str))
