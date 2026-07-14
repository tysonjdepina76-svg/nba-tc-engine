"""NFL Raptor engine — FiveThirtyEight-style rating-based projection (off-season aware)."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple

# NFL off-season: mid-February to early September
NFL_OFF_SEASON_MONTHS = {2, 3, 4, 5, 6, 7, 8}

MIN_EDGE_PCT = 0.5
SHRINKAGE_FACTOR = 0.30
MODERATE_EDGE = 0.06
STRONG_EDGE = 0.12

# Position-specific props
NFL_PROPS = {
    "QB": ["pass_yds", "pass_td", "rush_yds", "interceptions"],
    "RB": ["rush_yds", "rush_td", "rec_yds", "receptions"],
    "WR": ["rec_yds", "receptions", "rec_td"],
    "TE": ["rec_yds", "receptions", "rec_td"],
}


def is_off_season(date_str: str) -> bool:
    try:
        m = int(date_str.split("-")[1])
        return m in NFL_OFF_SEASON_MONTHS
    except Exception:
        return False


def project_player(player_stats: Dict, recent_n: int = 10) -> float:
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


def project_team(team_rating: Dict, opponent_rating: Dict) -> Dict:
    """Raptor-style: expected points added based on team ratings."""
    off = float(team_rating.get("off", 0.0))
    deff = float(opponent_rating.get("def", 0.0))
    pace = float(team_rating.get("pace", 1.0))
    return {
        "off_raptor": off - deff,
        "expected_pace_adj": pace,
    }


def project_player_props(players: List[Dict]) -> List[Dict]:
    out = []
    for p in players:
        pos = (p.get("position") or "").upper()
        props = NFL_PROPS.get(pos, [])
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
                    "position": pos,
                    "prop": prop,
                    "projection": round(proj, 2),
                    "line": line,
                    "direction": direction,
                    "edge": round(edge, 2),
                    "signal": signal,
                })
    return out


if __name__ == "__main__":
    print("NFL Raptor engine ready (off-season aware).")
