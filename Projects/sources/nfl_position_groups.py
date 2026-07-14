#!/usr/bin/env python3
"""
NFL Position Groups — v1.0.0

Maps every NFL stat to the position group that produces it. Used by
player_stats_scraper to know which StatMuse/ESPN endpoints to pull and
which weighting to apply per position when projecting props.

Position groups:
  QB  — passing yards, TDs, INTs, rush yards (mobile QBs)
  RB  — rush yards/TDs, receptions, receiving yards, targets
  WR  — receptions, targets, receiving yards/TDs
  TE  — receptions, targets, receiving yards/TDs
  OL  — not projected (no props)
  DL  — not projected (no props)
  LB  — tackles (rarely has props)
  DB  — INTs (rarely has props)
  K   — FG made/attempted, XP made
  P   — punting yards (rarely has props)
"""

from __future__ import annotations
from typing import Dict, List

POSITION_GROUPS: Dict[str, List[str]] = {
    "QB": [
        "pass_yds", "pass_td", "pass_int", "pass_att", "pass_cmp",
        "rush_yds", "rush_td", "rush_att",
    ],
    "RB": [
        "rush_yds", "rush_td", "rush_att",
        "rec", "rec_yds", "rec_td", "targets",
    ],
    "WR": [
        "rec", "rec_yds", "rec_td", "targets",
        "rush_yds", "rush_td",  # jet sweeps / end-arounds
    ],
    "TE": [
        "rec", "rec_yds", "rec_td", "targets",
    ],
    "K": [
        "fg_made", "fg_att", "xp_made",
    ],
    "LB": [
        "tackles", "sacks",  # defensive props, only on DraftKings
    ],
    "DB": [
        "ints",  # defensive props, only on DraftKings
    ],
    "DL": [
        "sacks",  # defensive props, only on DraftKings
    ],
}

# Reverse map: stat -> possible position groups
STAT_TO_POSITIONS: Dict[str, List[str]] = {}
for _pos, _stats in POSITION_GROUPS.items():
    for _stat in _stats:
        STAT_TO_POSITIONS.setdefault(_stat, []).append(_pos)

# Default projection weights per stat (used by ensemble when no model picks)
STAT_WEIGHTS: Dict[str, float] = {
    "pass_yds": 0.40,
    "pass_td": 0.25,
    "pass_int": 0.10,
    "rush_yds": 0.35,
    "rush_td": 0.20,
    "rec": 0.30,
    "rec_yds": 0.40,
    "rec_td": 0.25,
    "targets": 0.20,
    "fg_made": 0.50,
    "xp_made": 0.30,
    "tackles": 0.40,
    "sacks": 0.50,
    "ints": 0.60,
}


def get_position_for_stat(stat: str) -> List[str]:
    """Return the position groups that produce this stat."""
    return STAT_TO_POSITIONS.get(stat, [])


def get_stats_for_position(position: str) -> List[str]:
    """Return the stats that this position produces."""
    return POSITION_GROUPS.get(position.upper(), [])


def get_stat_weight(stat: str) -> float:
    """Return default ensemble weight for a stat. Falls back to 0.30."""
    return STAT_WEIGHTS.get(stat, 0.30)


if __name__ == "__main__":
    import json
    print(json.dumps({
        "position_groups": POSITION_GROUPS,
        "stat_to_positions": STAT_TO_POSITIONS,
    }, indent=2))
