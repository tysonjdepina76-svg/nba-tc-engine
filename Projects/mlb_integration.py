#!/usr/bin/env python3
# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
MLB Integration Wrapper
=======================
Orchestrates the MLB pipeline pieces:
  - mlb_tc_engine.py   (projections, edges, signals)
  - daily_picks.py     (formatted daily pick log + combos)
  - mlb_dashboard.py   (streamlit)

Flags:
  --sport mlb            Run MLB projections (default)
  --show-positions       Overlay lineup slot / role flags (C/1B/2B/SS/3B/OF/SP/RP)
                         onto projections using existing rosters module
  --ml                   Pass through to daily_picks log
  --date YYYY-MM-DD      Run for a specific date (ET)
  --slate                Full slate (alias for mlb_tc_engine --slate)
  --game "MIA@PHI"       Single matchup
  --report               Generate markdown report alongside JSON
  --output PATH          JSON output path

Examples:
  python3 mlb_integration.py --sport mlb --show-positions
  python3 mlb_integration.py --sport mlb --ml
  python3 mlb_integration.py --sport mlb --game "PHI@DET" --show-positions
  python3 mlb_integration.py --sport mlb --slate --report
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS = Path(__file__).resolve().parent
DAILY_LOG = PROJECTS.parent / "Daily_Log"


def now_et() -> datetime.date:
    """ET date for default --date."""
    try:
        import zoneinfo  # py3.9+
        et = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York")).date()
    except Exception:
        et = datetime.date.today()
    return et


def run_cmd(cmd: List[str]) -> int:
    """Run a subprocess and stream output."""
    print(f"[mlb_integration] $ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(PROJECTS))


def load_mlb_engine_output(date_str: str, slate: bool, game: Optional[str]) -> Dict[str, Any]:
    """
    Call mlb_tc_engine.py and parse the JSON it writes.
    Falls back to {} if the engine didn't emit JSON for this run.
    """
    engine_out = PROJECTS / f"mlb_engine_{date_str}.json"
    args = [sys.executable, str(PROJECTS / "mlb_tc_engine.py")]
    if slate:
        args.append("--slate")
    if game:
        args.extend(["--game", game])
    args.extend(["--output", str(engine_out)])

    rc = run_cmd(args)
    if rc != 0:
        print(f"[mlb_integration] mlb_tc_engine exited with rc={rc}", file=sys.stderr)
        return {}
    if not engine_out.exists():
        print("[mlb_integration] no engine JSON produced (silent run?)", file=sys.stderr)
        return {}
    try:
        return json.loads(engine_out.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[mlb_integration] failed to parse engine JSON: {exc}", file=sys.stderr)
        return {}


def attach_positions(engine_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Walk engine projections and attach a `position` field per player where
    the existing rosters module can resolve it. Best-effort — never raises.
    """
    try:
        from nba_tc.rosters import lookup_position  # type: ignore
    except Exception:
        try:
            from rosters import lookup_position  # type: ignore
        except Exception:
            return engine_data  # silently skip if not available

    for game_block in engine_data.get("games", []) or [engine_data]:
        for side in ("home", "away"):
            for player in game_block.get(side, []) or []:
                name = player.get("name") or player.get("player")
                if not name:
                    continue
                try:
                    pos = lookup_position("MLB", name)
                except Exception:
                    pos = None
                if pos:
                    player["position"] = pos
                    if pos in {"SP", "RP"}:
                        player["role"] = "pitcher"
                    elif pos in {"C", "1B", "2B", "3B", "SS", "OF", "DH"}:
                        player["role"] = "batter"
    return engine_data


def write_positions_report(engine_data: Dict[str, Any], date_str: str) -> Optional[Path]:
    """Emit a compact positions overlay report."""
    if not engine_data or "games" not in engine_data:
        return None
    out = DAILY_LOG / date_str / f"MLB_POSITIONS_{date_str}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# MLB Position Overlay — {date_str}", ""]
    for game in engine_data.get("games", []):
        matchup = game.get("matchup") or f"{game.get('away',{}).get('abbr','AWAY')}@{game.get('home',{}).get('abbr','HOME')}"
        lines.append(f"## {matchup}")
        for side in ("away", "home"):
            team = game.get(side, {})
            abbr = team.get("abbr") or side.upper()
            lines.append(f"### {abbr}")
            rows = ["| Player | Pos | Role | Stat | TC | Line | Edge | Signal |",
                    "|---|---|---|---|---|---|---|---|"]
            for p in team.get("players", []):
                rows.append(
                    f"| {p.get('name','?')} | {p.get('position','—')} | "
                    f"{p.get('role','—')} | {p.get('stat','—')} | "
                    f"{p.get('tc','—')} | {p.get('line','—')} | "
                    f"{p.get('edge','—')} | {p.get('signal','—')} |"
                )
            lines.extend(rows)
            lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def run_daily_picks(sport: str, date_str: str, ml: bool, dry: bool) -> int:
    args = [sys.executable, str(PROJECTS / "daily_picks.py"),
            "--sport", sport, "--date", date_str]
    if ml:
        os.environ["TC_ML_MODE"] = "1"
    if dry:
        args.append("--dry-run")
    return run_cmd(args)


def main() -> int:
    p = argparse.ArgumentParser(description="MLB TC Integration Wrapper")
    p.add_argument("--sport", default="mlb", help="Sport key (mlb default)")
    p.add_argument("--show-positions", action="store_true",
                   help="Overlay position/role flags on projections")
    p.add_argument("--ml", action="store_true",
                   help="Tag daily_picks run as ML-mode")
    p.add_argument("--date", default=now_et().isoformat(),
                   help="ET date YYYY-MM-DD (default: today)")
    p.add_argument("--slate", action="store_true", help="Full MLB slate")
    p.add_argument("--game", type=str, default=None, help="Single matchup, e.g. PHI@DET")
    p.add_argument("--report", action="store_true", help="Also generate markdown report")
    p.add_argument("--output", type=str, default=None, help="Custom JSON output path")
    p.add_argument("--dry-run", action="store_true", help="Print only, don't persist")
    args = p.parse_args()

    date_str = args.date
    sport_key = args.sport.upper()
    print(f"[mlb_integration] sport={sport_key} date={date_str} "
          f"positions={args.show_positions} ml={args.ml} slate={args.slate} "
          f"game={args.game}")

    if sport_key not in {"MLB", "MILB"}:
        print(f"[mlb_integration] sport={sport_key} — this wrapper is MLB-focused; "
              f"daily_picks handles other sports directly.", file=sys.stderr)

    # 1) Engine pass
    engine_data = load_mlb_engine_output(date_str, slate=args.slate, game=args.game)
    if not engine_data:
        print("[mlb_integration] engine returned no data; aborting.", file=sys.stderr)
        return 2

    # 2) Optional position overlay
    if args.show_positions:
        engine_data = attach_positions(engine_data)
        out = write_positions_report(engine_data, date_str)
        if out:
            print(f"[mlb_integration] positions report: {out}")
        if args.output:
            Path(args.output).write_text(json.dumps(engine_data, indent=2), encoding="utf-8")
            print(f"[mlb_integration] engine+positions JSON: {args.output}")

    # 3) daily_picks pass (formatted log + combos)
    rc = run_daily_picks(sport_key, date_str, ml=args.ml, dry=args.dry_run)
    if rc != 0:
        print(f"[mlb_integration] daily_picks exited rc={rc}", file=sys.stderr)
        return rc

    # 4) Optional report
    if args.report:
        run_cmd([sys.executable, str(PROJECTS / "mlb_tc_engine.py"),
                 "--slate", "--report"])

    print("[mlb_integration] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
