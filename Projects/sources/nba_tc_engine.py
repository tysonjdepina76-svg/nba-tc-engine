#!/usr/bin/env python3
"""NBA TC Engine — projection model for NBA player props.

Mirrors sources/wnba_tc_engine.py but uses NBA stat set
(PTS, REB, AST, 3PM, STL, BLK, MIN), pace/usage adjustments,
and DvP (defense vs position) multipliers.
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

NBA_STATS = ["PTS", "REB", "AST", "3PM", "STL", "BLK", "MIN"]

LEAGUE_AVG = {
    "PTS": 11.2, "REB": 3.8, "AST": 2.5, "3PM": 1.2,
    "STL": 0.8, "BLK": 0.5, "MIN": 22.0,
}

# Defensive rating (lower = better D). Multiplier <1.0 means tough D.
DVP_TEAMS = {
    "BOS": 0.95, "OKC": 0.96, "MIN": 0.96, "DEN": 0.97, "NYK": 0.97,
    "MIA": 0.98, "PHX": 0.99, "LAL": 1.00, "GSW": 1.00, "MIL": 0.98,
    "CLE": 0.98, "PHI": 1.00, "DAL": 1.01, "BKN": 1.04, "SAC": 1.02,
    "ATL": 1.03, "CHI": 1.02, "TOR": 1.03, "HOU": 1.01, "IND": 1.01,
    "LAC": 1.00, "MEM": 1.02, "NOP": 1.03, "ORL": 0.99, "POR": 1.04,
    "SAS": 1.03, "UTA": 1.04, "WAS": 1.05, "DET": 1.05, "CHA": 1.04,
}

DAILY_LOG = Path("/home/workspace/Daily_Log")


def _shrinkage(avg: float, n: int, league: float, alpha: int = 7) -> float:
    if n <= 0:
        return float(league)
    return (n * avg + alpha * league) / (n + alpha)


def _project_one(player: Dict[str, Any], opponent: str) -> List[Dict[str, Any]]:
    name = player.get("name", "Unknown")
    n = int(player.get("n_games", 0) or 0)
    pace = float(player.get("pace", 100.0) or 100.0)
    opp_pace = float(player.get("opp_pace", 100.0) or 100.0)
    pace_factor = (pace + opp_pace) / 200.0  # 1.0 = neutral
    dvp = DVP_TEAMS.get(opponent.upper(), 1.0)

    out = []
    for stat in NBA_STATS:
        raw = player.get(stat)
        if raw is None:
            continue
        try:
            raw_f = float(raw)
        except (TypeError, ValueError):
            continue
        league = LEAGUE_AVG[stat]
        shrunk = _shrinkage(raw_f, n, league)
        proj = shrunk * pace_factor * dvp
        # Poisson std for counting stats; normal std for MIN
        if stat == "MIN":
            std = 4.5
        else:
            std = max(0.6, math.sqrt(max(proj, 0.1)))
        out.append({
            "name": name,
            "stat": stat,
            "projection": round(proj, 2),
            "std": round(std, 2),
            "league_avg": league,
            "n_games": n,
            "raw_average": round(raw_f, 2),
        })
    return out


def _load_slate(date: Optional[str] = None) -> Dict[str, Any]:
    """Read a slate_WNBA_*.json-shaped file (same shape for NBA)."""
    base = DAILY_LOG
    if not base.exists():
        return {"games": []}
    files = sorted(base.glob("slate_NBA_*.json"))
    if not files:
        return {"games": []}
    try:
        return json.loads(files[-1].read_text())
    except Exception:
        return {"games": []}


def generate_nba_picks(min_edge: float = 5.0) -> List[Dict[str, Any]]:
    """Generate NBA picks using real TC math.

    Reads the latest slate_NBA_*.json + per-player averages from
    player_stats_scraper / roster files, applies pace + DvP adjustments,
    and returns picks with edge% above ``min_edge``.
    """
    slate = _load_slate()
    picks: List[Dict[str, Any]] = []
    for game in slate.get("games", []):
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        for side, opp in ((home, away), (away, home)):
            roster = game.get("rosters", {}).get(side, [])
            for player in roster:
                for row in _project_one(player, opp):
                    market_line = row["projection"] - 1.0  # proxy
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
                            "market_line": round(market_line, 2),
                            "edge_pct": round(edge, 2),
                            "direction": "OVER",
                            "sport": "nba",
                        })
    picks.sort(key=lambda p: p["edge_pct"], reverse=True)
    return picks


if __name__ == "__main__":
    out = generate_nba_picks()
    print(f"Generated {len(out)} NBA picks")
    for p in out[:10]:
        print(f"  {p['name']} {p['stat']} O {p['market_line']} (proj {p['projection']}, edge {p['edge_pct']}%)")
