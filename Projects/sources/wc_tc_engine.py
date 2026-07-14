#!/usr/bin/env python3
"""WC TC Engine — projection model for World Cup soccer player props.

Mirrors sources/nba_tc_engine.py but uses soccer stats (goals, assists, shots,
SOT, passes) and FIFA-style opponent rank adjustments (FIFArank 1-211).
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

WC_STATS = ["GOALS", "ASSISTS", "SHOTS", "SOT", "PASSES", "TACKLES", "MIN"]

LEAGUE_AVG = {
    "GOALS": 0.28, "ASSISTS": 0.18, "SHOTS": 2.1, "SOT": 0.9,
    "PASSES": 42.0, "TACKLES": 1.8, "MIN": 65.0,
}

# FIFA-style opponent strength (lower rank = tougher defense, multiplier < 1.0)
OPPONENT_RANK = {
    "ARG": 1, "FRA": 2, "BRA": 3, "BOL": 50, "JAM": 55, "SAU": 60, "VEN": 58, "ENG": 4, "BEL": 5, "NED": 6,
    "POR": 7, "ESP": 8, "ITA": 9, "GER": 10, "MEX": 11, "URU": 12,
    "COL": 13, "CRO": 14, "MAR": 15, "SUI": 16, "USA": 17, "JPN": 18,
    "KOR": 19, "SEN": 20, "AUS": 22, "POL": 23, "DEN": 24, "CAN": 25,
    "TUR": 26, "ECU": 27, "IRN": 28, "QAT": 29, "KSA": 30, "GHA": 32,
    "TUN": 34, "CMR": 35, "NGA": 38, "EGY": 40, "CRC": 45, "CIV": 50,
    "PAN": 55, "WAL": 60, "SRB": 65, "PAR": 70, "JPN": 75, "BIH": 80,
    "CZE": 85, "SCO": 90, "AUT": 95, "NOR": 100, "PER": 110,
    "HON": 120, "ALG": 130, "CHI": 140, "RSA": 150, "ISL": 155,
    "NZL": 160, "IRQ": 165, "CRC": 170, "UAE": 175, "CHN": 180,
    "PHI": 185, "SYR": 190, "KEN": 195, "MAD": 200, }


def _opponent_mult(opponent: str) -> float:
    """Convert opponent FIFA rank to a multiplier 0.85-1.15."""
    rank = OPPONENT_RANK.get(opponent, 100)
    norm = (rank - 1) / 210.0
    return 0.85 + (0.30 * (1.0 - norm))


def project_player(player: Dict[str, Any], stat: str, opponent: str) -> Optional[float]:
    """Project a single player stat vs a given opponent."""
    if stat not in WC_STATS:
        return None
    history = player.get("history", {}).get(stat, [])
    if not history:
        season_avg = player.get("season_avg", {}).get(stat, LEAGUE_AVG[stat])
        base = float(season_avg)
    else:
        base = statistics.mean(history[-10:]) if len(history) >= 3 else float(history[-1])
    league = LEAGUE_AVG[stat]
    base = (base * 0.7) + (league * 0.3)
    mult = _opponent_mult(opponent)
    proj = base * mult
    if stat == "MIN":
        proj = min(90.0, max(15.0, proj))
    return round(proj, 2)


def _project_one(player: Dict[str, Any], opponent: str) -> Dict[str, Any]:
    """Project all WC stats for one player."""
    out = {"player": player.get("name", "?"), "team": player.get("team", "?"), "opponent": opponent, "projections": {}}
    for stat in WC_STATS:
        proj = project_player(player, stat, opponent)
        if proj is not None:
            out["projections"][stat] = proj
    return out


def generate_wc_picks(roster_path: str = None, date: str = None) -> List[Dict[str, Any]]:
    """Generate WC picks for a matchup. Reads roster from proj_*.json in Daily_Log."""
    from pathlib import Path
    import glob
    base = Path("/home/workspace/Daily_Log")
    if not base.exists():
        return []
    files = sorted(glob.glob(str(base / "**/proj_WC_*.json"), recursive=True))
    if not files:
        return []
    picks: List[Dict[str, Any]] = []
    for f in files[-3:]:
        try:
            data = json.loads(Path(f).read_text())
        except Exception:
            continue
        matchup = data.get("matchup", "")
        for team_key in ("home", "away"):
            team = data.get(team_key, {})
            opp_abbr = data.get("away" if team_key == "home" else "home", {}).get("abbr", "USA")
            for player in team.get("roster", []):
                proj = _project_one(player, opp_abbr)
                picks.append({"matchup": matchup, **proj})
    return picks


if __name__ == "__main__":
    print(f"WC TC Engine loaded. {len(WC_STATS)} stats. {len(OPPONENT_RANK)} opponent ranks.")
    sample = {"name": "Mbappe", "team": "FRA", "season_avg": {"GOALS": 0.7, "SHOTS": 3.5, "MIN": 80}}
    for s in ("GOALS", "SHOTS", "MIN"):
        print(f"  {s} vs ARG: {project_player(sample, s, 'ARG')}")
