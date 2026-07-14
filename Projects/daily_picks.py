"""Daily picks generator — hybrid TC math pipeline.
WNBA + MLB + WC (World Cup / Soccer). Generates plain-English 'why' snippets and signal strength.
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
    "wc": "proj_WC_*.json",
}

SPORT_KEY = {"wnba": "WNBA", "mlb": "MLB", "wc": "WC"}

STAT_NAMES = {
    "PTS": "points", "REB": "rebounds", "AST": "assists",
    "STL": "steals", "BLK": "blocks", "3PM": "three-pointers",
    "hits": "hits", "hr": "home runs", "rbi": "RBI",
    "runs": "runs", "sb": "stolen bases", "avg": "batting average",
    "goals": "goals", "assists_soccer": "assists", "shots": "shots",
    "shots_on_target": "shots on target", "saves": "saves",
    "passes": "passes", "tackles": "tackles", "yellow_cards": "yellow cards",
}


def classify_signal(edge: float, sport: str) -> str:
    """Classify pick strength based on edge magnitude (v2 ratio edge)."""
    config = SPORT_CONFIGS.get(sport)
    abs_edge = abs(edge)
    strong = getattr(config, "signal_strong", 0.10) if config else 0.10
    moderate = getattr(config, "signal_moderate", 0.05) if config else 0.05
    if abs_edge >= strong:
        return "STRONG"
    elif abs_edge >= moderate:
        return "MODERATE"
    return "WEAK"


def generate_why(player: str, team: str, stat: str, direction: str,
                 tc_proj: float, market_line: float, edge: float,
                 matchup: str) -> str:
    """Plain English explanation of why this pick exists."""
    stat_name = STAT_NAMES.get(stat, stat.replace("_", " "))
    edge_pct = abs(edge) * 100

    if direction == "OVER":
        return (
            f"{player} projected {tc_proj:.1f} {stat_name} vs. line of {market_line:.1f} "
            f"— {edge_pct:.0f}% edge to the OVER"
        )
    else:
        return (
            f"{player} projected {tc_proj:.1f} {stat_name} vs. line of {market_line:.1f} "
            f"— {edge_pct:.0f}% edge to the UNDER"
        )


def _read_wnba_players(proj: dict) -> List[dict]:
    rows = []
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


def _read_wc_players(proj: dict) -> List[dict]:
    """Read WC projection format: top-level list of {name, team, opponent, projections: {stat: {mean, over_line, ...}}}."""
    rows = []
    for p in (proj.get("picks") or []):
        team = p.get("team", "?")
        opponent = p.get("opponent", "?")
        match_round = p.get("match_round", "group_stage")
        for stat, val in (p.get("projections") or {}).items():
            over = val.get("over_line")
            under = val.get("under_line")
            market = over if over is not None else (under if under is not None else val.get("line", 0))
            rows.append({
                "player": p.get("name", "?"),
                "team": team,
                "role": f"{match_round}",
                "status": "",
                "stat": stat,
                "tc_projection": val.get("mean", 0),
                "market_line": market or 0,
                "dk_line": market,
                "edge_raw": val.get("edge", 0),
            })
    return rows


_READERS = {
    "wnba": _read_wnba_players,
    "mlb": _read_mlb_players,
    "wc": _read_wc_players,
}


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

    import glob as gmod
    files = gmod.glob(os.path.join(date_dir, glob_pat))

    if not files:
        print(f"  SKIP: no {glob_pat} files in {date_dir}")
        return []

    all_picks = []
    reader = _READERS.get(sport, _read_wnba_players)
    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        with open(fpath, "r") as f:
            data = json.load(f)

        raw = reader(data)
        game_matchup = data.get("matchup", "?")
        game_time = data.get("start_time") or data.get("game_time") or data.get("commence_time", "")
        if sport == "wc":
            teams = data.get("teams", [])
            game_matchup = data.get("matchup", " vs ".join(teams) if teams else "?")
            game_time = game_time or data.get("date", "")

        for r in raw:
            proj = r["tc_projection"]
            market = r.get("market_line") or r.get("dk_line") or None
            stat = r["stat"]

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
            else:
                result = determine_pick(
                    projection=float(proj),
                    real_line=None,
                    sport=sport_key,
                    stat=stat,
                    self_edge_threshold=3.5,
                    use_v2=True,
                    source="MOCK",
                )
                edge_val = result["edge"]
                direction = result["direction"]
                source = "SELF_EDGE"

            if direction in ("INVALID", "FLAT"):
                continue

            corrected = result.get("corrected_projection", proj)
            market_line = result.get("market_line", market or 0)

            why = generate_why(
                player=r["player"],
                team=r["team"],
                stat=stat,
                direction=direction,
                tc_proj=float(proj),
                market_line=float(market_line),
                edge=edge_val,
                matchup=game_matchup,
            )

            signal = classify_signal(edge_val, sport_key)

            all_picks.append({
                "date": log_date,
                "league": sport_key,
                "matchup": game_matchup,
                "game_time": game_time,
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
                "signal": signal,
                "why": why,
                "raw_average": round(r.get("edge_raw", 0), 2),
                "source": source,
                "actual": "",
                "result": "PENDING",
            })

    return all_picks


def main():
    ap = argparse.ArgumentParser(description="Daily picks — hybrid TC math (WNBA + MLB + WC)")
    ap.add_argument("--sport", choices=["mlb", "wnba", "wc", "all"], default="all")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--output", default="/home/workspace/Daily_Log")
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
