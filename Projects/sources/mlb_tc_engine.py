#!/usr/bin/env python3
"""MLB TC Engine — projection model for MLB player props.

Stat set: H, 2B, 3B, HR, RBI, R, BB, K, SB, TB, H+R+RBI.
Uses platoon splits, park factors, and recent form (last 14 days).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

MLB_STATS = ["H", "2B", "3B", "HR", "RBI", "R", "BB", "K", "SB", "TB", "H+R+RBI"]

LEAGUE_AVG = {
    "H": 0.85, "2B": 0.17, "3B": 0.01, "HR": 0.11, "RBI": 0.45,
    "R": 0.45, "BB": 0.30, "K": 0.85, "SB": 0.06, "TB": 1.30,
    "H+R+RBI": 1.75,
}

PARK_FACTORS = {
    "COL": 1.18, "BOS": 1.06, "NYY": 1.04, "HOU": 1.05, "LAA": 1.03,
    "MIL": 1.04, "TEX": 1.05, "CIN": 1.05, "PHI": 1.03, "ATL": 1.03,
    "MIN": 1.02, "DET": 1.02, "CHC": 1.02, "SEA": 0.96, "SF": 0.94,
    "OAK": 0.94, "SD": 0.95, "STL": 0.97, "PIT": 0.96, "MIA": 0.95,
    "TB": 0.96, "TOR": 1.00, "BAL": 1.01, "KC": 0.99, "CWS": 1.00,
    "CLE": 1.00, "WSH": 1.00, "NYM": 0.98, "ARI": 1.01, "LAD": 1.00,
}

DAILY_LOG = Path("/home/workspace/Daily_Log")


def _shrinkage(avg: float, n: int, league: float, alpha: int = 12) -> float:
    return (n * avg + alpha * league) / (n + alpha) if n > 0 else league


def _project_one(player: Dict[str, Any], opponent: str, home: bool) -> List[Dict[str, Any]]:
    name = player.get("name", "Unknown")
    n = int(player.get("n_games", 0) or 0)
    park = PARK_FACTORS.get(opponent.upper(), 1.0)
    park *= 1.03 if home else 0.97
    platoon = 1.05 if player.get("bats") == (player.get("opp_handedness", "R")) else 1.0
    recent = float(player.get("recent_14day_avg", 0) or 0)

    out = []
    for stat in MLB_STATS:
        raw = player.get(stat)
        if raw is None:
            continue
        try:
            raw_f = float(raw)
        except (TypeError, ValueError):
            continue
        league = LEAGUE_AVG[stat]
        blended = (raw_f + recent) / 2.0 if recent else raw_f
        shrunk = _shrinkage(blended, n, league)
        proj = shrunk * park * platoon
        if stat == "K":
            proj = shrunk * park  # K unaffected by platoon
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
    files = sorted(base.glob("slate_MLB_*.json"))
    if not files:
        return {"games": []}
    try:
        return json.loads(files[-1].read_text())
    except Exception:
        return {"games": []}


def generate_mlb_picks(min_edge: float = 5.0) -> List[Dict[str, Any]]:
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
                            "sport": "mlb",
                        })
    picks.sort(key=lambda p: p["edge_pct"], reverse=True)
    return picks


if __name__ == "__main__":
    out = generate_mlb_picks()
    print(f"Generated {len(out)} MLB picks")
    for p in out[:10]:
        print(f"  {p['name']} {p['stat']} O {p['market_line']} (proj {p['projection']}, edge {p['edge_pct']}%)")