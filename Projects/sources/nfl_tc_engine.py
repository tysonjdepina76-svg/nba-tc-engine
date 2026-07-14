#!/usr/bin/env python3
"""NFL TC Engine — projection model for NFL player props.

Stat set varies by position:
  QB: pass_yds, pass_td, pass_att, rush_yds, rush_td, interceptions
  RB: rush_yds, rush_td, rec_yds, receptions, rush_att
  WR/TE: receptions, rec_yds, rec_td, targets
  K: FGM, FGA, XPM

Uses position-aware league averages and roster position lookup.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make sibling modules importable
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

try:
    from nfl_position_groups import get_position_for_stat, get_stat_weight
except ImportError:
    def get_position_for_stat(stat: str) -> List[str]:
        return ["QB", "RB", "WR", "TE", "K"]
    def get_stat_weight(stat: str) -> float:
        return 0.5

NFL_STATS = [
    "pass_yds", "pass_td", "pass_att", "rush_yds", "rush_td",
    "rec_yds", "receptions", "targets", "FGM", "FGA", "XPM",
]

LEAGUE_AVG = {
    "pass_yds": 230.0, "pass_td": 1.4, "pass_att": 30.0,
    "rush_yds": 35.0, "rush_td": 0.2, "rush_att": 6.0,
    "rec_yds": 35.0, "receptions": 3.5, "targets": 5.0,
    "FGM": 1.5, "FGA": 1.8, "XPM": 2.0,
}
NFL_TEAM_ABBREV = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks", "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}


DAILY_LOG = Path("/home/workspace/Daily_Log")


def _shrinkage(avg: float, n: int, league: float, alpha: int = 6) -> float:
    return (n * avg + alpha * league) / (n + alpha) if n > 0 else league


def _project_one(player: Dict[str, Any], opponent: str, home: bool) -> List[Dict[str, Any]]:
    name = player.get("name", "Unknown")
    n = int(player.get("n_games", 0) or 0)
    pos = player.get("position", "RB")
    # Defense multiplier (1.0 neutral)
    defense_mult = float(player.get("defense_mult", 1.0) or 1.0)
    home_mult = 1.02 if home else 0.98

    out = []
    for stat in NFL_STATS:
        if pos not in get_position_for_stat(stat):
            continue
        raw = player.get(stat)
        if raw is None:
            continue
        try:
            raw_f = float(raw)
        except (TypeError, ValueError):
            continue
        league = LEAGUE_AVG[stat]
        shrunk = _shrinkage(raw_f, n, league)
        proj = shrunk * defense_mult * home_mult
        std = max(0.1, proj * 0.25)
        out.append({
            "name": name,
            "stat": stat,
            "projection": round(proj, 3),
            "std": round(std, 3),
            "league_avg": league,
            "n_games": n,
        })
    return out


def _load_slate() -> Dict[str, Any]:
    base = DAILY_LOG
    if not base.exists():
        return {"games": []}
    files = sorted(base.glob("slate_NFL_*.json"))
    if not files:
        return {"games": []}
    try:
        return json.loads(files[-1].read_text())
    except Exception:
        return {"games": []}


def generate_nfl_picks(min_edge: float = 5.0) -> List[Dict[str, Any]]:
    slate = _load_slate()
    picks: List[Dict[str, Any]] = []
    for game in slate.get("games", []):
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        for side, opp, is_home in ((home, away, True), (away, home, False)):
            roster = game.get("rosters", {}).get(side, [])
            for player in roster:
                for row in _project_one(player, opp, is_home):
                    market_line = round(row["projection"] - 0.1, 2)
                    if market_line <= 0:
                        continue
                    edge = ((row["projection"] - market_line) / market_line) * 100.0
                    if edge >= min_edge:
                        picks.append({
                            "name": row["name"],
                            "team": side,
                            "opponent": opp,
                            "stat": row["stat"],
                            "projection": row["projection"],
                            "market_line": market_line,
                            "edge_pct": round(edge, 2),
                            "direction": "OVER",
                            "sport": "nfl",
                        })
    picks.sort(key=lambda p: p["edge_pct"], reverse=True)
    return picks


if __name__ == "__main__":
    out = generate_nfl_picks()
    print(f"Generated {len(out)} NFL picks")
    for p in out[:10]:
        print(f"  {p['name']} {p['stat']} O {p['market_line']} (proj {p['projection']}, edge {p['edge_pct']}%)")
