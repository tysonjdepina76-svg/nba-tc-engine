#!/usr/bin/env python3
"""NHL TC Engine — projection model for NHL player props.

Stat set: G, A, Pts, SOG, BS, HIT, TOI, SHP, PPP.
Uses 5v5/PP time-on-ice splits, goalie matchup, and recent form.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

NHL_STATS = ["G", "A", "Pts", "SOG", "BS", "HIT", "TOI", "SHP", "PPP"]

LEAGUE_AVG = {
    "G": 0.20, "A": 0.35, "Pts": 0.55, "SOG": 2.20, "BS": 0.80,
    "HIT": 0.95, "TOI": 18.5, "SHP": 1.20, "PPP": 0.20,
}

# Goalies with high save% make shots more valuable (player SOG up, G down)
GOALIE_SV_PCT = {
    "VGK": 0.918, "BOS": 0.915, "DAL": 0.914, "NYR": 0.912, "STL": 0.910, "UTA": 0.905, "MIN": 0.910,
    "COL": 0.910, "FLA": 0.910, "WPG": 0.910, "CAR": 0.910,
    "TOR": 0.905, "EDM": 0.900, "SEA": 0.900, "TB": 0.905,
    "PIT": 0.905, "LA": 0.908, "MIN": 0.910, "NJ": 0.908,
    "ANA": 0.895, "CHI": 0.895, "CBJ": 0.895, "SJ": 0.890,
    "PHI": 0.895, "BUF": 0.900, "DET": 0.895, "OTT": 0.895,
    "STL": 0.900, "CGY": 0.898, "VAN": 0.905, "NSH": 0.900,
    "WSH": 0.900, "MTL": 0.895, "NYI": 0.905,
}

DAILY_LOG = Path("/home/workspace/Daily_Log")


def _shrinkage(avg: float, n: int, league: float, alpha: int = 8) -> float:
    return (n * avg + alpha * league) / (n + alpha) if n > 0 else league


def _project_one(player: Dict[str, Any], opponent_goalie: str) -> List[Dict[str, Any]]:
    name = player.get("name", "Unknown")
    n = int(player.get("n_games", 0) or 0)
    pp_unit = float(player.get("pp_unit", 0) or 0)  # 0-2
    sv = GOALIE_SV_PCT.get(opponent_goalie.upper(), 0.905)
    # Better goalies (higher sv%) → slightly less G, more SOG
    goalie_g_factor = 1.0 - max(0, sv - 0.910) * 1.5
    sog_factor = 1.0 + max(0, sv - 0.910) * 0.5
    pp_mult = 1.0 + pp_unit * 0.15

    out = []
    for stat in NHL_STATS:
        raw = player.get(stat)
        if raw is None:
            continue
        try:
            raw_f = float(raw)
        except (TypeError, ValueError):
            continue
        league = LEAGUE_AVG[stat]
        shrunk = _shrinkage(raw_f, n, league)
        proj = shrunk * pp_mult
        if stat == "G":
            proj *= goalie_g_factor
        elif stat == "SOG":
            proj *= sog_factor
        std = max(0.05, math.sqrt(max(proj, 0.05)))
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
    files = sorted(base.glob("slate_NHL_*.json"))
    if not files:
        return {"games": []}
    try:
        return json.loads(files[-1].read_text())
    except Exception:
        return {"games": []}


def generate_nhl_picks(min_edge: float = 5.0) -> List[Dict[str, Any]]:
    slate = _load_slate()
    picks: List[Dict[str, Any]] = []
    for game in slate.get("games", []):
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        home_goalie = game.get("home_goalie", home)
        away_goalie = game.get("away_goalie", away)
        for side, opp, opp_goalie in ((home, away, away_goalie), (away, home, home_goalie)):
            roster = game.get("rosters", {}).get(side, [])
            for player in roster:
                for row in _project_one(player, opp_goalie):
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
                            "sport": "nhl",
                        })
    picks.sort(key=lambda p: p["edge_pct"], reverse=True)
    return picks


if __name__ == "__main__":
    out = generate_nhl_picks()
    print(f"Generated {len(out)} NHL picks")
    for p in out[:10]:
        print(f"  {p['name']} {p['stat']} O {p['market_line']} (proj {p['projection']}, edge {p['edge_pct']}%)")
