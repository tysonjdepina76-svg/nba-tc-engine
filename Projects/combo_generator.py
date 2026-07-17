#!/usr/bin/env python3
"""
Combo Generator — computes PRA, PR, PA, and other combo stats from single-stat
TC projections. Reads valid_props from projection files and produces combo picks
with proper TC targets, market lines (summed), and edges.

Usage:
  python3 combo_generator.py [--date 2026-07-16] [--sport wnba]
"""

import json, os, sys, argparse
from datetime import datetime
from glob import glob
from typing import Dict, List, Optional, Any

ET_TZ = __import__("zoneinfo").ZoneInfo("America/New_York")

COMBO_DEFS = {
    "PRA":  {"stats": ["PTS", "REB", "AST"], "label": "Pts+Reb+Ast"},
    "PR":   {"stats": ["PTS", "REB"],       "label": "Pts+Reb"},
    "PA":   {"stats": ["PTS", "AST"],       "label": "Pts+Ast"},
    "RA":   {"stats": ["REB", "AST"],       "label": "Reb+Ast"},
    "PRAS": {"stats": ["PTS", "REB", "AST", "STL"], "label": "Pts+Reb+Ast+Stl"},
    "PRAB": {"stats": ["PTS", "REB", "AST", "BLK"], "label": "Pts+Reb+Ast+Blk"},
    "3PTR": {"stats": ["3PM", "REB"],       "label": "3PM+Reb"},
}

def load_valid_props(fpath: str) -> List[Dict]:
    """Load valid_props from a projection file."""
    with open(fpath) as f:
        data = json.load(f)
    props = data.get("valid_props") or data.get("props") or data.get("players") or []
    return [p for p in props if isinstance(p, dict)]

def build_player_stat_map(props: List[Dict]) -> Dict[str, Dict[str, dict]]:
    """Build player -> stat -> projection dict from valid_props."""
    pmap: Dict[str, Dict[str, dict]] = {}
    for p in props:
        name = p.get("player", "?")
        stat = str(p.get("stat", "")).upper().strip()
        if not stat:
            continue
        if name not in pmap:
            pmap[name] = {}
        pmap[name][stat] = p
    return pmap

def compute_combos(player_map: Dict[str, Dict[str, dict]],
                   combo_defs: Dict = None) -> List[Dict[str, Any]]:
    """Compute combo projections for all players who have all required stats."""
    if combo_defs is None:
        combo_defs = COMBO_DEFS
    results = []
    for player, stats in player_map.items():
        team = ""
        role = ""
        status = ""
        period = "GAME"
        for s in stats.values():
            team = team or s.get("team", "")
            role = role or s.get("role", "")
            status = status or s.get("status", "")
            period = period or s.get("period", "GAME")

        for combo_key, combo_def in combo_defs.items():
            req_stats = combo_def["stats"]
            if not all(s in stats for s in req_stats):
                continue

            tc_sum = sum(float(stats[s].get("tc_projection", stats[s].get("projection", 0))) for s in req_stats)
            line_sum = sum(float(stats[s].get("market_line", 0)) for s in req_stats)
            tc_target_sum = sum(float(stats[s].get("tc_target", stats[s].get("tc_projection", 0))) for s in req_stats)

            edge = tc_sum - line_sum
            edge_pct = (edge / line_sum * 100) if line_sum > 0 else 0.0
            direction = "OVER" if edge > 0 else "UNDER"

            raw_edge = sum(float(stats[s].get("raw_average", stats[s].get("edge", 0))) for s in req_stats)

            results.append({
                "player": player,
                "team": team,
                "role": role,
                "status": status,
                "combo": combo_key,
                "combo_label": combo_def["label"],
                "stats": req_stats,
                "direction": direction,
                "period": period,
                "tc_projection": round(tc_sum, 1),
                "market_line": round(line_sum, 1),
                "tc_target": round(tc_target_sum, 1),
                "edge": round(edge, 2),
                "edge_pct": round(edge_pct, 1),
                "raw_average": round(raw_edge, 2),
                "source": stats.get(req_stats[0], {}).get("source", "SELF_EDGE"),
            })
    return results

def generate_combos(sport: str = "WNBA", log_date: str = None) -> List[Dict]:
    """Main entry: generate combos for a sport on a given date."""
    log_date = log_date or datetime.now(ET_TZ).date().isoformat()
    log_dir = "/home/workspace/Daily_Log"
    date_dir = os.path.join(log_dir, log_date)

    glob_pat = f"proj_{sport}_*.json" if sport in ("WNBA", "MLB") else f"proj_{sport}_*.json"

    files = sorted(glob(os.path.join(date_dir, glob_pat)))
    files = [f for f in files if not f.endswith("_.json") and "_at_" in f or "@" in f]

    if not files:
        files = sorted(glob(os.path.join(date_dir, f"proj_{sport}_*.json")))

    all_combos = []
    for fpath in files:
        fname = os.path.basename(fpath)
        if len(fname.split("_")) < 3:
            continue

        props = load_valid_props(fpath)
        if not props:
            continue

        player_map = build_player_stat_map(props)
        combos = compute_combos(player_map)

        matchup = ""
        with open(fpath) as f:
            data = json.load(f)
            matchup = data.get("matchup", "")
        for c in combos:
            c["matchup"] = matchup
            c["date"] = log_date

        all_combos.extend(combos)

    all_combos.sort(key=lambda c: abs(c["edge"]), reverse=True)
    return all_combos

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="WNBA")
    ap.add_argument("--date", default=None)
    ap.add_argument("--min-edge", type=float, default=1.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    combos = generate_combos(args.sport.upper(), args.date)
    filtered = [c for c in combos if abs(c["edge"]) >= args.min_edge]

    if args.json:
        print(json.dumps(filtered, indent=2))
    else:
        print(f"\n{'='*70}")
        print(f"TC COMBO GENERATOR — {args.sport.upper()} — {args.date or 'today'}")
        print(f"{'='*70}")
        print(f"Found {len(filtered)} combos with edge >= {args.min_edge}\n")
        for i, c in enumerate(filtered[:25], 1):
            print(f"  {i:2d}. {c['player']:<20s} {c['combo_label']:<25s} "
                  f"TC {c['tc_projection']:>5.1f}  Line {c['market_line']:>5.1f}  "
                  f"Edge {c['edge']:>+6.1f} ({c['edge_pct']:>+5.1f}%)  [{c['direction']}]")

if __name__ == "__main__":
    main()
