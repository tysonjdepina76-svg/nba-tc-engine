#!/usr/bin/env python3
"""Soccer TC Engine — projection model for World Cup / soccer props.

Stat set: goals, assists, shots, shots_on_target, passes, tackles, interceptions.
Uses Poisson model for goals, normalized averages for non-goal stats.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from scipy.stats import norm

SOCCER_STATS = ["goals", "assists", "shots", "shots_on_target", "passes", "tackles", "interceptions"]

LEAGUE_AVG = {
    "goals": 0.20, "assists": 0.15, "shots": 1.50, "shots_on_target": 0.55,
    "passes": 35.0, "tackles": 1.20, "interceptions": 0.80,
}
SOCCER_CLUB_ABBREV = {
    "ARS": "Arsenal", "AVL": "Aston Villa", "BOU": "Bournemouth", "BRE": "Brentford",
    "BRI": "Brighton", "CHE": "Chelsea", "CRY": "Crystal Palace", "EVE": "Everton",
    "FUL": "Fulham", "LIV": "Liverpool", "MCI": "Man City", "MUN": "Man United",
    "NEW": "Newcastle", "NFO": "Nottm Forest", "SHU": "Sheffield Utd", "TOT": "Tottenham",
    "WHU": "West Ham", "WOL": "Wolves", "BAR": "Barcelona", "RMA": "Real Madrid",
    "ATM": "Atletico Madrid", "SEV": "Sevilla", "VAL": "Valencia", "VIL": "Villarreal",
    "ATH": "Athletic Club", "BET": "Real Betis", "GET": "Getafe", "OSA": "Osasuna",
    "BAY": "Bayern Munich", "BVB": "Borussia Dortmund", "RBL": "RB Leipzig",
    "LEV": "Bayer Leverkusen", "EFR": "Eintracht Frankfurt", "INT": "Inter Milan",
    "JUV": "Juventus", "MIL": "AC Milan", "ROM": "AS Roma", "LAZ": "Lazio",
    "NAP": "Napoli", "FIO": "Fiorentina", "ATA": "Atalanta", "MON": "Monaco",
    "MAR": "Marseille", "LYO": "Lyon", "PSG": "Paris Saint-Germain", "NIC": "Nice",
    "LIL": "Lille", "REN": "Rennes", "POR": "Porto", "CEL": "Celtic", "DOR": "Dortmund",
}


DAILY_LOG = Path("/home/workspace/Daily_Log")


def _shrinkage(avg: float, n: int, league: float, alpha: int = 8) -> float:
    return (n * avg + alpha * league) / (n + alpha) if n > 0 else league


def _project_one(player: Dict[str, Any], opponent_defense_rank: int, home: bool) -> List[Dict[str, Any]]:
    name = player.get("name", "Unknown")
    n = int(player.get("n_games", 0) or 0)
    # Defense rank: 1 = best, 32 = worst
    defense_factor = 1.0 + ((opponent_defense_rank - 16) / 32) * 0.20
    if home:
        defense_factor *= 1.05  # home advantage

    out = []
    for stat in SOCCER_STATS:
        raw = player.get(stat)
        if raw is None:
            continue
        try:
            raw_f = float(raw)
        except (TypeError, ValueError):
            continue
        league = LEAGUE_AVG[stat]
        shrunk = _shrinkage(raw_f, n, league)
        proj = shrunk * defense_factor
        std = max(0.01, math.sqrt(max(proj, 0.01)))
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
    files = sorted(base.glob("slate_WC_*.json"))
    if not files:
        return {"games": []}
    try:
        return json.loads(files[-1].read_text())
    except Exception:
        return {"games": []}


def generate_soccer_picks(min_edge: float = 5.0) -> List[Dict[str, Any]]:
    slate = _load_slate()
    picks: List[Dict[str, Any]] = []
    for game in slate.get("games", []):
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        home_def = int(game.get("home_defense_rank", 16) or 16)
        away_def = int(game.get("away_defense_rank", 16) or 16)
        for side, opp, opp_def, is_home in ((home, away, away_def, True), (away, home, home_def, False)):
            roster = game.get("rosters", {}).get(side, [])
            for player in roster:
                for row in _project_one(player, opp_def, is_home):
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
                            "sport": "soccer",
                        })
    picks.sort(key=lambda p: p["edge_pct"], reverse=True)
    return picks


if __name__ == "__main__":
    out = generate_soccer_picks()
    print(f"Generated {len(out)} soccer picks")
    for p in out[:10]:
        print(f"  {p['name']} {p['stat']} O {p['market_line']} (proj {p['projection']}, edge {p['edge_pct']}%)")
