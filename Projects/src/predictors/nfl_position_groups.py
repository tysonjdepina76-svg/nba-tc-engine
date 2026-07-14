"""NFL position groups: aggregates for skill positions (QB/RB/WR/TE) projections."""
from __future__ import annotations
from typing import Dict, List, Optional

POSITION_GROUPS = {
    "QB": ["QB"],
    "RB": ["RB", "FB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "OL": ["OT", "OG", "C", "OL"],
    "DL": ["DE", "DT", "NT", "DL"],
    "LB": ["OLB", "ILB", "MLB", "LB"],
    "DB": ["CB", "S", "FS", "SS", "DB"],
    "K": ["K"],
    "P": ["P"],
}

PROP_TYPES = {
    "QB": ["pass_yds", "pass_td", "rush_yds", "interceptions"],
    "RB": ["rush_yds", "rush_td", "rec_yds", "receptions"],
    "WR": ["rec_yds", "receptions", "rec_td", "rush_yds"],
    "TE": ["rec_yds", "receptions", "rec_td"],
    "K": ["fg_made", "xp_made", "points"],
}


def get_position_group(pos: str) -> Optional[str]:
    """Map an NFL position abbreviation to its group (QB, RB, WR, TE, etc.)."""
    pos = (pos or "").upper().strip()
    for group, members in POSITION_GROUPS.items():
        if pos in members:
            return group
    return None


def get_relevant_props(pos: str) -> List[str]:
    """Return the list of prop types relevant to a given position group."""
    grp = get_position_group(pos)
    return PROP_TYPES.get(grp, [])


def aggregate_team_skill_stats(players: List[dict], group: str) -> Dict[str, float]:
    """Sum a stat across all players in a position group on a team.

    Each player dict: {"position": "WR", "stats": {"rec_yds": 80, ...}}.
    """
    out: Dict[str, float] = {}
    for p in players:
        if get_position_group(p.get("position", "")) != group:
            continue
        for stat, val in p.get("stats", {}).items():
            try:
                out[stat] = out.get(stat, 0.0) + float(val)
            except (TypeError, ValueError):
                continue
    return out


if __name__ == "__main__":
    for p in ["QB", "RB", "WR", "TE", "OLB", "CB", "K", "P"]:
        print(f"{p} -> {get_position_group(p)} | props: {get_relevant_props(p)}")
