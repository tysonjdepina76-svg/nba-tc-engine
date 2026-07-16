#!/usr/bin/env python3
"""Combo Builder — wraps build_pregame_combos.py with standardized output and CLI.

Produces:
  /home/workspace/Daily_Log/YYYY-MM-DD/combos_<away>_<home>.json
  /home/workspace/Daily_Log/YYYY-MM-DD/combos_<away>_<home>.md
  /home/workspace/Daily_Log/YYYY-MM-DD/combos_summary.json

Usage:
  python3 combo_builder.py                       # today (America/New_York)
  python3 combo_builder.py 2026-07-11            # specific date
  python3 combo_builder.py 2026-07-11 --sports WNBA,MLB
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Reuse the existing implementation
sys.path.insert(0, str(Path(__file__).parent))
from build_pregame_combos import (  # noqa: E402
    LOG_DIR as _DEFAULT_LOG_DIR,
    build_combos,
    write_report,
)


def _resolve_log_dir(date_str: str) -> Path:
    """Return the daily log dir for the given date (creating it if missing)."""
    log_dir = Path(f"/home/workspace/Daily_Log/{date_str}")
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _discover_matchups(log_dir: Path, sports: list[str] | None) -> dict:
    """Discover matchups from projection files in the daily log folder."""
    games_by_sport: dict = {}
    sport_token_map = {"WNBA": "WNBA", "MLB": "MLB", "WORLD CUP": "WORLD CUP"}

    for proj_file in log_dir.glob("proj_*_at_*.json"):
        stem = proj_file.stem
        if not stem.startswith("proj_"):
            continue
        rest = stem[len("proj_"):]
        if rest.startswith("WORLD CUP_"):
            sport_tok = "WORLD CUP"
            match_part = rest[len("WORLD CUP_"):]
        else:
            parts = rest.split("_", 2)
            if len(parts) < 3:
                continue
            sport_tok = parts[0]
            match_part = parts[1] + "_" + parts[2] if len(parts) >= 3 else ""
        if "_at_" not in match_part:
            continue
        away, home = match_part.split("_at_", 1)
        if sport_tok not in sport_token_map:
            continue
        if sports and sport_tok not in sports:
            continue
        games_by_sport.setdefault(sport_token_map[sport_tok], []).append((away, home))

    if not games_by_sport:
        games_by_sport = {
            "WNBA": [("LV", "NY")],
            "WORLD CUP": [("JPN", "BRA"), ("MAR", "NED"), ("PAR", "GER")],
            "MLB": [],
        }
    return games_by_sport


def build_combos_for_date(date_str: str, sports: list[str] | None = None) -> dict:
    """Build combos for a given date and return a summary dict."""
    log_dir = _resolve_log_dir(date_str)
    games_by_sport = _discover_matchups(log_dir, sports)

    summary = []
    for sport, games in games_by_sport.items():
        if not games:
            summary.append({
                "matchup": "",
                "sport": sport,
                "matched": 0,
                "qualified": 0,
                "note": "no proj file (off-day)",
            })
            continue
        for away, home in games:
            try:
                result = build_combos(sport, away, home)
                safe = f"{away}_{home}".lower()
                write_report(
                    result,
                    log_dir / f"combos_{safe}.md",
                    log_dir / f"combos_{safe}.json",
                )
                summary.append({
                    "matchup": f"{away}@{home}",
                    "sport": sport,
                    "matched": result.get("matched_legs", 0),
                    "qualified": result.get("qualified_legs", 0),
                    "note": result.get("note") or result.get("error", ""),
                })
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR ({away}@{home}): {e}")
                summary.append({
                    "matchup": f"{away}@{home}",
                    "sport": sport,
                    "matched": 0,
                    "qualified": 0,
                    "note": str(e),
                })

    summary_path = log_dir / "combos_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    return {"date": date_str, "log_dir": str(log_dir), "results": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build pregame combos for a date.")
    parser.add_argument("date", nargs="?", default=None,
                        help="Date in YYYY-MM-DD (default: today America/New_York)")
    parser.add_argument("--sports", default=None,
                        help="Comma-separated sport list (WNBA,MLB,WORLD CUP)")
    args = parser.parse_args()

    if args.date is None:
        args.date = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        print(f"ERROR: invalid date '{args.date}' — expected YYYY-MM-DD", file=sys.stderr)
        return 2

    sports = None
    if args.sports:
        sports = [s.strip().upper() for s in args.sports.split(",") if s.strip()]
        # Normalize "WORLD_CUP" → "WORLD CUP" for internal use
        sports = ["WORLD CUP" if s == "WORLD_CUP" else s for s in sports]

    out = build_combos_for_date(args.date, sports)
    print(f"=== COMBOS SUMMARY ({args.date}) ===")
    print(json.dumps(out["results"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
