"""Daily picks generator — hybrid TC math pipeline.
Uses tc_math_hybrid.determine_pick() as the single truth for all sports.
"""

import sys
import os
import argparse
import json
import csv
from datetime import date, datetime
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tc_math_hybrid import determine_pick, SPORT_CONFIGS

SPORT_PROJ_GLOB = {
    "wnba": "proj_WNBA_*.json",
    "mlb": "proj_MLB_*.json",
    "wc": "soccer_player_projs.json",
}

SPORT_KEY = {"wnba": "WNBA", "mlb": "MLB", "wc": "WC"}


def _read_wnba_players(proj: dict) -> List[dict]:
    rows = []
    matchup = proj.get("matchup", "?")
    for side in ("away", "home"):
        side_data = proj.get(side, {})
        for group_key in ("all", "starters"):
            group = side_data.get(group_key, {})
            for p in group.get("players", []):
                for stat, val in (p.get("projections") or {}).items():
                    if not val.get("valid", True):
                        continue
                    rows.append({
                        "player": p.get("player", "?"),
                        "team": p.get("team", "?"),
                        "role": p.get("role", "?"),
                        "status": p.get("status", ""),
                        "stat": stat,
                        "tc_projection": val.get("tc_projection", 0),
                        "market_line": val.get("line", 0),
                        "dk_line": val.get("dk_line"),
                        "edge_raw": val.get("edge", 0),
                    })
    return rows


def _read_mlb_players(proj: dict) -> List[dict]:
    rows = []
    matchup = proj.get("matchup", "?")
    for side in ("away", "home"):
        side_data = proj.get(side, {})
        for p in (side_data.get("players") or side_data.get("batters") or []):
            for stat, val in (p.get("projections") or {}).items():
                if not val.get("valid", True):
                    continue
                rows.append({
                    "player": p.get("player", "?"),
                    "team": p.get("team", "?"),
                    "role": p.get("role", "?"),
                    "status": p.get("status", ""),
                    "stat": stat,
                    "tc_projection": val.get("tc_projection", 0),
                    "market_line": val.get("line", 0),
                    "dk_line": val.get("dk_line"),
                    "edge_raw": val.get("edge", 0),
                })
    return rows


def _read_wc_players(proj_list: list, log_date: str) -> List[dict]:
    rows = []
    for p in proj_list:
        tc_proj = float(p.get("tc_projection", 0))
        raw_avg = float(p.get("tc_raw", tc_proj))
        rows.append({
            "player": p.get("player", "?"),
            "team": p.get("team", "?"),
            "role": "starter" if p.get("is_starter") else "bench",
            "status": "",
            "stat": p.get("stat", "?"),
            "tc_projection": tc_proj,
            "market_line": 0,
            "dk_line": None,
            "edge_raw": float(p.get("edge", 0)),
        })
    return rows


def generate_picks(sport: str, log_date: Optional[str] = None) -> List[Dict[str, Any]]:
    sport_key = SPORT_KEY[sport]
    log_date = log_date or date.today().isoformat()
    glob_pat = SPORT_PROJ_GLOB[sport]
    log_dir = "/home/workspace/Daily_Log"
    date_dir = os.path.join(log_dir, log_date)

    if not os.path.isdir(date_dir):
        print(f"  SKIP: {date_dir} not found")
        return []

    config = SPORT_CONFIGS.get(sport_key)
    use_pct = config.use_pct if config else False

    import glob as gmod
    files = gmod.glob(os.path.join(date_dir, glob_pat))

    if not files:
        print(f"  SKIP: no {glob_pat} files in {date_dir}")
        return []

    all_picks = []
    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        with open(fpath, "r") as f:
            data = json.load(f)

        if sport == "wc":
            if isinstance(data, list):
                raw = _read_wc_players(data, log_date)
            elif isinstance(data, dict) and "starter_projections" in data:
                sp = data.get("starter_projections", [])
                raw = _read_wc_players(sp if isinstance(sp, list) else [], log_date)
            else:
                raw = _read_wc_players(data if isinstance(data, list) else [], log_date)
            game_matchup = "?"
        else:
            raw = _read_wnba_players(data) if sport == "wnba" else _read_mlb_players(data)
            game_matchup = data.get("matchup", "?")

        for r in raw:
            proj = r["tc_projection"]
            market = r.get("market_line") or r.get("dk_line") or None
            stat = r["stat"]

            if today_date := log_date:
                pass

            if market is not None and float(market) > 0:
                result = determine_pick(
                    projection=float(proj),
                    real_line=float(market),
                    sport=sport_key,
                    stat=stat,
                    use_v2=True,
                )
                edge_val = result["edge"]
                direction = result["direction"]
                source = result["source"]
                is_self_edge = False
            else:
                result = determine_pick(
                    projection=float(proj),
                    real_line=None,
                    sport=sport_key,
                    stat=stat,
                    self_edge_threshold=10.0 if sport == "wc" else 3.5,
                    use_v2=True,
                    source="MOCK",
                )
                edge_val = result["edge"]
                direction = result["direction"]
                source = "SELF_EDGE"
                is_self_edge = True

            if direction in ("INVALID", "FLAT"):
                continue

            corrected = result.get("corrected_projection", proj)
            market_line = result.get("market_line", market or 0)

            all_picks.append({
                "date": log_date,
                "league": sport_key.replace("_", " "),
                "matchup": game_matchup,
                "team": r["team"],
                "player": r["player"],
                "role": r["role"],
                "status": r["status"],
                "stat": stat,
                "direction": direction,
                "market_line": market_line,
                "tc_projection": round(proj, 2),
                "tc_target": round(corrected, 2),
                "edge": round(edge_val, 4),
                "threshold": round(getattr(config, "min_edge", 0.5) if config else 0.5, 2),
                "raw_average": round(r.get("edge_raw", 0), 2),
                "source": source,
                "actual": "",
                "result": "PENDING",
            })

    return all_picks


def generate_combo_picks(sport: str, log_date: Optional[str] = None) -> List[Dict]:
    return []


def main():
    ap = argparse.ArgumentParser(description="Daily picks — hybrid TC math")
    ap.add_argument("--sport", choices=["mlb", "wnba", "wc", "all"], default="all")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--output", default="/home/workspace/Daily_Log")
    ap.add_argument("--combos", action="store_true")
    args = ap.parse_args()

    sports = ["mlb", "wnba", "wc"] if args.sport == "all" else [args.sport]
    log_date = args.date
    log_dir = os.path.join(args.output, log_date)
    os.makedirs(log_dir, exist_ok=True)

    all_picks = []
    for sport in sports:
        picks = generate_picks(sport, log_date)
        print(f"Generated {len(picks)} picks for {sport}")
        all_picks.extend(picks)

    if all_picks:
        csv_file = os.path.join(log_dir, "picks.csv")
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_picks[0].keys()))
            writer.writeheader()
            writer.writerows(all_picks)
        print(f"Saved {len(all_picks)} picks to {csv_file}")

        import shutil
        dashboard_csv = "/home/workspace/sports_betting_dashboard/data/picks.csv"
        os.makedirs(os.path.dirname(dashboard_csv), exist_ok=True)
        shutil.copy2(csv_file, dashboard_csv)
        print(f"Synced to {dashboard_csv}")
    else:
        print("No picks generated across all sports")


if __name__ == "__main__":
    main()
