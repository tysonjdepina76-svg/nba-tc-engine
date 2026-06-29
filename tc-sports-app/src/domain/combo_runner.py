# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""Combo runner — loads projections from daily_picks reports and qualifies combos.

Usage:
  python -m src.domain.combo_runner --sport WNBA --date 2026-06-29
  python -m src.domain.combo_runner --sport WNBA --min-edge 2.0 --min-conf 0.7
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.entities import Projection
from src.domain.combo_qualifier import (
    ComboQualifier,
    aggregate_lines,
    median_line,
)


REPORTS_DIR = PROJECT_ROOT / "reports" / "daily"
COMBOS_DIR = PROJECT_ROOT / "reports" / "combos"


def load_projections(sport: str, date: str) -> List[Projection]:
    """Load all valid projections from a daily_picks report."""
    path = REPORTS_DIR / f"{sport.lower()}_{date}.json"
    if not path.exists():
        print(f"  ⚠  No report found: {path}")
        return []
    with open(path) as f:
        report = json.load(f)

    projections: List[Projection] = []
    for matchup in report.get("matchups", []):
        matchup_id = matchup.get("matchup", "unknown")
        for prop in matchup.get("valid_props", []):
            p = Projection(
                player=prop.get("player", ""),
                team=prop.get("team", ""),
                role=prop.get("role", "BENCH"),
                status=prop.get("status", "ACTIVE"),
                stat=prop.get("stat", ""),
                tc_projection=float(prop.get("tc_projection", 0)),
                line=float(prop.get("line", 0)),
                edge=float(prop.get("edge", 0)),
                direction=prop.get("direction", "OVER"),
                valid=bool(prop.get("valid", True)),
            )
            # attach game_id dynamically
            p.__dict__["game_id"] = matchup_id
            projections.append(p)
    return projections


def main():
    parser = argparse.ArgumentParser(description="TC Combo Qualifier — self-edge based")
    parser.add_argument("--sport", required=True, help="NFL, NBA, WNBA, MLB, SOCCER, NHL, BOXING, MMA")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="YYYY-MM-DD (default: today)")
    parser.add_argument("--min-edge", type=float, default=None, help="Override min edge")
    parser.add_argument("--min-conf", type=float, default=None, help="Override min confidence (0-1)")
    parser.add_argument("--min-corr", type=float, default=None, help="Override min correlation (0-1)")
    parser.add_argument("--min-hit-prob", type=float, default=None, help="Override min hit probability (0-1)")
    parser.add_argument("--max-legs", type=int, default=None, help="Override max legs")
    parser.add_argument("--min-legs", type=int, default=None, help="Override min legs")
    args = parser.parse_args()

    override = {}
    if args.min_edge is not None:
        override["min_edge"] = args.min_edge
    if args.min_conf is not None:
        override["min_confidence"] = args.min_conf
    if args.min_corr is not None:
        override["min_correlation"] = args.min_corr
    if args.min_hit_prob is not None:
        override["min_hit_prob"] = args.min_hit_prob
    if args.max_legs is not None:
        override["max_legs"] = args.max_legs
    if args.min_legs is not None:
        override["min_legs"] = args.min_legs

    print(f"\n=== Combo Qualifier :: {args.sport.upper()} :: {args.date} ===\n")

    projections = load_projections(args.sport, args.date)
    print(f"  Loaded {len(projections)} projections")

    if not projections:
        print("  ⚠  No projections to qualify — run daily_picks first.")
        sys.exit(0)

    qualifier = ComboQualifier(sport=args.sport, criteria_override=override or None)
    print(f"  Criteria: {qualifier.criteria}")

    combos, report = qualifier.qualify(projections)
    print(f"\n  Filter: {report.to_dict()['passed_count']} passed / {report.to_dict()['filtered_count']} filtered")
    print(f"  Combos: {len(combos)} qualified")

    # Save
    COMBOS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = COMBOS_DIR / f"{args.sport.lower()}_{args.date}.json"
    out = {
        "sport": args.sport.upper(),
        "date": args.date,
        "generated_at": datetime.now().isoformat(),
        "criteria": qualifier.criteria,
        "filter_report": report.to_dict(),
        "combos": [c.to_dict() for c in combos],
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  ✅ Saved: {out_path}")

    # Top 5 preview
    if combos:
        print(f"\n  Top 5 combos (by hit probability):\n")
        for i, c in enumerate(combos[:5], 1):
            print(f"    {i}. {c.game_id} ({c.total_legs} legs) | "
                  f"edge={c.avg_edge:.2f} | conf={c.avg_confidence:.2f} | "
                  f"corr={c.correlation:.2f} | hit_prob={c.hit_probability:.2f}")
            for leg in c.legs:
                print(f"       - {leg.player} ({leg.team}) {leg.stat} {leg.direction} {leg.tc_projection:.1f}")


if __name__ == "__main__":
    main()
