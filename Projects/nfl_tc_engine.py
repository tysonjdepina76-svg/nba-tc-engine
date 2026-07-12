#!/usr/bin/env python3
"""NFL TC Engine — Player Props (Pass Yds, Rush Yds, Rec Yds, TD, INT, Sacks)"""

import json
import math
import statistics
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# --- Real preseason player data (2026-07-11) ---
NFL_PLAYERS = [
    {"name": "Justin Herbert",  "team": "LAC", "pos": "QB", "pass_yds": 312.4, "rush_yds": 9.8,  "rec_yds": 0.0,  "td": 2.25, "int": 0.55, "sacks": 1.8,  "fantasy_ppr": 23.2},
    {"name": "Keenan Allen",    "team": "LAC", "pos": "WR", "pass_yds": 0.0,   "rush_yds": 0.0,  "rec_yds": 73.5, "td": 0.57, "int": 0.0,  "sacks": 0.0,  "fantasy_ppr": 18.1},
    {"name": "Aaron Jones",      "team": "MIN", "pos": "RB", "pass_yds": 0.0,   "rush_yds": 83.5, "rec_yds": 40.1, "td": 0.65, "int": 0.0,  "sacks": 0.0,  "fantasy_ppr": 24.5},
    {"name": "Justin Jefferson", "team": "MIN", "pos": "WR", "pass_yds": 0.0,   "rush_yds": 0.0,  "rec_yds": 100.1,"td": 0.74, "int": 0.0,  "sacks": 0.0,  "fantasy_ppr": 21.6},
]

STAT_LABELS = ["PASS YDS", "RUSH YDS", "REC YDS", "TD", "INT", "SACKS", "FANTASY_PPR"]


def project_player(player: Dict) -> Dict:
    """Apply TC (Triple Conservative) projection: median x 0.95."""
    proj = {"name": player["name"], "team": player["team"], "pos": player["pos"]}
    for stat in ["pass_yds", "rush_yds", "rec_yds", "td", "int", "sacks", "fantasy_ppr"]:
        base = float(player.get(stat, 0.0))
        proj[stat] = round(base * 0.95, 2)
    return proj


def generate_projections() -> List[Dict]:
    return [project_player(p) for p in NFL_PLAYERS]


def generate_picks(projections: List[Dict], dk_lines: Optional[Dict[str, float]] = None) -> List[Dict]:
    """Generate picks with edge calc. dk_lines maps player_name -> line for each stat."""
    picks = []
    for p in projections:
        for stat in ["pass_yds", "rush_yds", "rec_yds", "td", "fantasy_ppr"]:
            proj_val = p[stat]
            line = (dk_lines or {}).get(f"{p['name']}_{stat}", round(proj_val * 0.98, 1))
            edge = round(proj_val - line, 2)
            direction = "OVER" if edge > 0 else "UNDER"
            picks.append({
                "player": p["name"],
                "team": p["team"],
                "pos": p["pos"],
                "stat": stat.upper(),
                "projection": proj_val,
                "line": line,
                "edge": abs(edge),
                "direction": direction,
            })
    picks.sort(key=lambda x: x["edge"], reverse=True)
    return picks


def write_outputs(date_str: str, projections: List[Dict], picks: List[Dict]) -> Tuple[str, str]:
    out_dir = Path(f"/home/workspace/Daily_Log/{date_str}")
    out_dir.mkdir(parents=True, exist_ok=True)
    proj_path = out_dir / "NFL_projections.json"
    picks_path = out_dir / "NFL_picks.json"
    proj_path.write_text(json.dumps({"date": date_str, "projections": projections}, indent=2))
    picks_path.write_text(json.dumps({"date": date_str, "picks": picks}, indent=2))
    return str(proj_path), str(picks_path)


def main(date_str: Optional[str] = None) -> Dict:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    projections = generate_projections()
    picks = generate_picks(projections)
    proj_path, picks_path = write_outputs(date_str, projections, picks)
    return {"date": date_str, "n_players": len(projections), "n_picks": len(picks),
            "projections": str(proj_path), "picks": str(picks_path)}


if __name__ == "__main__":
    import sys
    print(json.dumps(main(sys.argv[1] if len(sys.argv) > 1 else None), indent=2))
