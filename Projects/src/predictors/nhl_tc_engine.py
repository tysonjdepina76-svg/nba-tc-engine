"""NHL Triple-Conservative engine. Off-season aware — disables when no games today."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# NHL off-season: mid-April to early October
NHL_OFF_SEASON_MONTHS = {4, 5, 6, 7, 8, 9}

PROP_TYPES = ["goals", "assists", "points", "shots", "saves", "goals_against"]

# Conservative thresholds
MIN_EDGE_PCT = 0.5
SHRINKAGE_FACTOR = 0.30
MODERATE_EDGE = 0.06
STRONG_EDGE = 0.12


def is_off_season(date_str: str) -> bool:
    """Return True if the given date falls in NHL off-season."""
    try:
        m = int(date_str.split("-")[1])
        return m in NHL_OFF_SEASON_MONTHS
    except Exception:
        return False


def project_player(player_stats: Dict, recent_n: int = 10) -> float:
    """Project a stat by averaging recent games and shrinking toward season mean."""
    recent = player_stats.get("recent", [])[-recent_n:]
    if not recent:
        return float(player_stats.get("season_avg", 0.0))
    recent_avg = sum(recent) / len(recent)
    season_avg = float(player_stats.get("season_avg", recent_avg))
    return (1 - SHRINKAGE_FACTOR) * recent_avg + SHRINKAGE_FACTOR * season_avg


def edge_pct(projection: float, market_line: float) -> float:
    if not market_line or market_line <= 0:
        return 0.0
    return abs(projection - market_line) / market_line * 100


def determine_pick(projection: float, market_line: float) -> Tuple[Optional[str], float, str]:
    """Return (direction, edge_pct, signal) for a projected prop.

    signal: STRONG / MODERATE / WEAK / None
    """
    e = edge_pct(projection, market_line)
    if e < MIN_EDGE_PCT:
        return None, e, "NONE"
    direction = "OVER" if projection > market_line else "UNDER"
    if e >= STRONG_EDGE:
        return direction, e, "STRONG"
    if e >= MODERATE_EDGE:
        return direction, e, "MODERATE"
    return direction, e, "WEAK"


def project_game(game: Dict) -> List[Dict]:
    """Project props for a single NHL game.

    game: {"home": str, "away": str, "players": [player_dict, ...]}
    """
    out = []
    for p in game.get("players", []):
        proj = project_player(p)
        for prop in PROP_TYPES:
            line = p.get("market_lines", {}).get(prop)
            if line is None:
                continue
            direction, edge, signal = determine_pick(proj, float(line))
            if direction:
                out.append({
                    "player": p.get("name"),
                    "team": p.get("team"),
                    "prop": prop,
                    "projection": round(proj, 2),
                    "line": line,
                    "direction": direction,
                    "edge": round(edge, 2),
                    "signal": signal,
                })
    return out


def project_today(date_str: str, games: List[Dict]) -> Dict:
    """Top-level: project today's NHL slate. Returns disabled state if off-season."""
    if is_off_season(date_str):
        return {
            "date": date_str,
            "disabled": True,
            "reason": "NHL off-season",
            "picks": [],
        }
    all_picks = []
    for g in games:
        all_picks.extend(project_game(g))
    return {
        "date": date_str,
        "disabled": False,
        "picks": all_picks,
        "count": len(all_picks),
    }


if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    print(project_today(today, []))
