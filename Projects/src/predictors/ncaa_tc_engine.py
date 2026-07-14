"""NCAA Triple-Conservative engine. Stub for college football/basketball projection."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple

MIN_EDGE_PCT = 0.5
SHRINKAGE_FACTOR = 0.30
MODERATE_EDGE = 0.06
STRONG_EDGE = 0.12

# NCAA-relevant props vary by sport
NCAA_PROPS = {
    "CFB": ["pass_yds", "rush_yds", "rec_yds", "receptions", "pass_td", "rush_td"],
    "CBB": ["pts", "reb", "ast", "stl", "blk", "3pm"],
}


def project_player(player_stats: Dict, recent_n: int = 8) -> float:
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
    e = edge_pct(projection, market_line)
    if e < MIN_EDGE_PCT:
        return None, e, "NONE"
    direction = "OVER" if projection > market_line else "UNDER"
    if e >= STRONG_EDGE:
        return direction, e, "STRONG"
    if e >= MODERATE_EDGE:
        return direction, e, "MODERATE"
    return direction, e, "WEAK"


def project_sport(sport: str, players: List[Dict]) -> List[Dict]:
    """sport: 'CFB' or 'CBB'."""
    props = NCAA_PROPS.get((sport or "").upper(), [])
    out = []
    for p in players:
        proj = project_player(p)
        for prop in props:
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


if __name__ == "__main__":
    print("NCAA TC engine ready (CFB + CBB).")
