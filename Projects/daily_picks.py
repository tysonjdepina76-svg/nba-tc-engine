"""Daily picks generator — hybrid TC math pipeline.
WNBA + MLB + WC (World Cup / Soccer). Generates plain-English 'why' snippets and signal strength.
"""

import sys
import os
import argparse
import json
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tc_math_hybrid import determine_pick, SPORT_CONFIGS
from db_writer import write_picks_to_db
from market_catalog import normalize_period, truth_metadata, is_real_book_source, catalog_for

ET_TZ = __import__("zoneinfo").ZoneInfo("America/New_York")

SPORT_PROJ_GLOB = {
    "wnba": "proj_WNBA_*.json",
    "mlb": "proj_MLB_*.json",
    "wc": "proj_WC_*.json",
}

SPORT_KEY = {"wnba": "WNBA", "mlb": "MLB", "wc": "WC"}

STAT_NAMES = {
    "PTS": "points", "REB": "rebounds", "AST": "assists",
    "STL": "steals", "BLK": "blocks", "3PM": "three-pointers",
    "hits": "hits",     "H": "hits", "TB": "total bases", "HR": "home runs", "RBI": "RBI",
    "R": "runs", "BB": "walks", "K": "strikeouts", "OUTS": "outs",
    "PITCHES": "pitches", "hr": "home runs", "rbi": "RBI",
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


def _value_number(value: Any, *keys: str) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) is not None:
                return value[key]
    return value


def _projection_rows(player: dict, sport: str) -> List[dict]:
    rows = []
    projections = player.get("projections") or {}
    entries = []
    if projections:
        for key, val in projections.items():
            if isinstance(val, dict) and not any(k in val for k in ("tc_projection", "projection", "mean", "line", "over_line", "dk_line")):
                entries.extend((key, stat, stat_val) for stat, stat_val in val.items())
            else:
                entries.append(("GAME", key, val))
    else:
        stat_keys = ("PTS", "REB", "AST", "3PM", "STL", "BLK") if sport in ("NBA", "WNBA") else tuple()
        for stat in stat_keys:
            stat_lower = stat.lower()
            projection = player.get(f"tc_{stat_lower}")
            if projection is not None:
                entries.append(("GAME", stat, {
                    "tc_projection": projection,
                    "book_line": player.get(f"line_{stat_lower}"),
                    "source": player.get("line_source") or player.get("market_source") or "",
                    "edge": player.get(f"edge_{stat_lower}", 0),
                }))

    parent_source = player.get("line_source") or player.get("market_source") or ""
    for period, stat, val in entries:
        if val is None or not isinstance(val, (dict, int, float)):
            continue
        projection = _value_number(val, "tc_projection", "projection", "mean")
        if projection is None:
            continue
        book_line = _value_number(val, "dk_line", "line", "book_line", "sportsbook_line", "over_line")
        source = (val.get("line_source") if isinstance(val, dict) else None) or (val.get("market_source") if isinstance(val, dict) else None) or (val.get("source") if isinstance(val, dict) else None) or parent_source
        rows.append({
            "player": player.get("player", player.get("name", "?")),
            "team": player.get("team", "?"),
            "role": player.get("role", "?"),
            "status": player.get("status", ""),
            "stat": str(stat).upper(),
            "period": normalize_period(period),
            "tc_projection": projection,
            "market_line": book_line,
            "dk_line": book_line,
            "line_source": source,
            "edge_raw": val.get("edge", 0) if isinstance(val, dict) else 0,
        })
    return rows


def _read_valid_props(proj: dict) -> List[dict]:
    rows = []
    for prop in proj.get("valid_props") or proj.get("props") or []:
        if not isinstance(prop, dict):
            continue
        projection = prop.get("tc_projection", prop.get("projection", prop.get("mean")))
        if projection is None:
            continue
        line = prop.get("dk_line", prop.get("book_line", prop.get("sportsbook_line")))
        source = prop.get("line_source", prop.get("market_source", ""))
        rows.append({
            "player": prop.get("player", prop.get("name", "?")),
            "team": prop.get("team", "?"),
            "role": prop.get("role", "?"),
            "status": prop.get("status", ""),
            "stat": str(prop.get("stat", "default")).upper(),
            "period": normalize_period(prop.get("period", "GAME")),
            "tc_projection": projection,
            "market_line": line,
            "dk_line": line,
            "line_source": source,
            "edge_raw": prop.get("edge", 0),
        })
    return rows


def generate_why(player: str, team: str, stat: str, direction: str,
                 tc_proj: float, market_line: float, edge: float,
                 matchup: str, period: str = "GAME") -> str:
    stat_name = STAT_NAMES.get(stat, stat.replace("_", " "))
    edge_pct = abs(edge) * 100
    period_label = normalize_period(period)
    period_text = "full game" if period_label == "GAME" else period_label.replace("_", " ")

    if direction == "OVER":
        return (
            f"{player} projected {tc_proj:.1f} {stat_name} ({period_text}) vs. line of {market_line:.1f} "
            f"— {edge_pct:.0f}% edge to the OVER"
        )
    else:
        return (
            f"{player} projected {tc_proj:.1f} {stat_name} ({period_text}) vs. line of {market_line:.1f} "
            f"— {edge_pct:.0f}% edge to the UNDER"
        )


def _read_wnba_players(proj: dict) -> List[dict]:
    rows = []
    seen = set()
    for side in ("away", "home"):
        side_data = proj.get(side, {})
        for group_key in ("all", "starters"):
            group = side_data.get(group_key, {})
            for p in group.get("players", []):
                for row in _projection_rows(p, "WNBA"):
                    row["team"] = row.get("team") or side_data.get("team", side.upper())
                    if row.get("status", "").upper() in ("OUT", "DNP"):
                        continue
                    key = (row["player"], row["stat"], row["period"], row["team"])
                    if key not in seen:
                        seen.add(key)
                        rows.append(row)
    return rows


def _read_mlb_players(proj: dict) -> List[dict]:
    rows = []
    for side in ("away", "home"):
        side_data = proj.get(side, {})
        players = []
        for group_key in ("players", "batters", "pitchers"):
            players.extend(side_data.get(group_key) or [])
        seen = set()
        for p in players:
            for row in _projection_rows(p, "MLB"):
                row["team"] = row.get("team") or side_data.get("team", side.upper())
                key = (row["player"], row["stat"], row["period"], row["team"])
                if row.get("status", "").upper() not in ("OUT", "DNP") and key not in seen:
                    seen.add(key)
                    rows.append(row)
    return rows


def _read_wc_players(proj: dict) -> List[dict]:
    """Read WC player props while preserving line provenance."""
    rows = _read_valid_props(proj)
    if rows:
        return rows
    for p in (proj.get("picks") or []):
        for row in _projection_rows(p, "WC"):
            row["team"] = row.get("team") or p.get("team", "?")
            rows.append(row)
    return rows


_READERS = {
    "wnba": _read_wnba_players,
    "mlb": _read_mlb_players,
    "wc": _read_wc_players,
}


def generate_picks(sport: str, log_date: Optional[str] = None) -> List[Dict[str, Any]]:
    sport_key = SPORT_KEY[sport]
    log_date = log_date or datetime.now(ET_TZ).date().isoformat()
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
        if not raw:
            raw = _read_valid_props(data)
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
            period = normalize_period(r.get("period", "GAME"))
            source_token = r.get("line_source", "")
            has_real_line = market is not None and float(market) > 0 and is_real_book_source(source_token)

            if has_real_line:
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
                period=period,
            )

            truth = truth_metadata(market_line=market, source=source_token, period=period)
            signal = classify_signal(edge_val, sport_key) if truth["alert_eligible"] else "PROJECTION ONLY"

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
                "period": period,
                "market_type": "PLAYER_PROP",
                "market_family": f"{sport_key}_{period}_PLAYER_PROP",
                "line_source": source_token,
                "catalog_supported": period in catalog_for(sport_key).get("periods", []),
                "line_status": truth["line_status"],
                "alert_eligible": truth["alert_eligible"],
                "truth_note": truth["truth_note"],
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
    ap.add_argument("--date", default=None)
    ap.add_argument("--output", default="/home/workspace/Daily_Log")
    args = ap.parse_args()

    sports = ["mlb", "wnba", "wc"] if args.sport == "all" else [args.sport]
    log_date = args.date or datetime.now(ET_TZ).date().isoformat()
    log_dir = os.path.join(args.output, log_date)
    os.makedirs(log_dir, exist_ok=True)

    all_picks = []
    for sport in sports:
        picks = generate_picks(sport, log_date)
        print(f"Generated {len(picks)} picks for {sport}")
        all_picks.extend(picks)

    csv_file = os.path.join(log_dir, "picks.csv")
    existing = []
    if os.path.isfile(csv_file):
        with open(csv_file, "r", newline="") as f:
            existing = list(csv.DictReader(f))

    if all_picks:
        regenerated_league = SPORT_KEY[args.sport] if args.sport != "all" else None
        if regenerated_league:
            existing = [row for row in existing if row.get("league") != regenerated_league]
        merged = existing + all_picks
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in merged for k in row)))
            writer.writeheader()
            writer.writerows(merged)
        print(f"Saved {len(merged)} picks to {csv_file}")

        import shutil
        dashboard_csv = "/home/workspace/sports_betting_dashboard/data/picks.csv"
        os.makedirs(os.path.dirname(dashboard_csv), exist_ok=True)
        shutil.copy2(csv_file, dashboard_csv)
        print(f"Synced to {dashboard_csv}")
        write_picks_to_db(all_picks, log_date)
    elif existing:
        print(f"No new picks; preserved {len(existing)} existing picks in {csv_file}")
    else:
        print("No picks generated across all sports")


if __name__ == "__main__":
    main()
