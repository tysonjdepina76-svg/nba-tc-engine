#!/usr/bin/env python3
"""TC pipeline health scan.

Checks the 13 manifest files, validates Python syntax, and inspects
key data dirs. Exits non-zero if anything is broken so cron/cron-equivalent
tasks fail fast.

Usage:
  python3 scan.py              # full scan, exit code reflects issues
  python3 scan.py --report     # write scan_report.md next to log
"""

import argparse
import ast
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("/home/workspace/Projects")
DAILY_LOG_ROOT = Path("/home/workspace/Daily_Log")
DATA_ROOT = PROJECT_ROOT / "data"

# The 13 files that must exist + parse for the pipeline to be considered alive
REQUIRED_FILES = [
    "orchestrator.py",
    "scan.py",
    "fix_pipeline.py",
    "streamlit_app.py",
    "daily_picks.py",
    "build_pregame_combos.py",
    "run_settlement.py",
    "setup_cron.py",
    "verify_picks.py",
    "generate_todays_picks.py",
    "sources/nba_tc_engine.py",
    "sources/wnba_tc_engine.py",
    "sources/mlb_tc_engine.py",
    "sources/nhl_tc_engine.py",
    "sources/soccer_tc_engine.py",
    "sources/nfl_tc_engine.py",
    "sources/nfl_position_groups.py",
    "sources/player_stats_scraper.py",
    "config/algorithm_weights.json",
    "tc_math_hybrid.py",
    "data/historical.csv",
    "WIRE.md",
]


def _check_file(path: Path) -> tuple[str, str]:
    """Return (status, detail). status in {OK, MISSING, SYNTAX_ERROR}."""
    if not path.exists():
        return "MISSING", "file not found"
    if path.suffix == ".py":
        try:
            ast.parse(path.read_text())
        except SyntaxError as e:
            return "SYNTAX_ERROR", f"line {e.lineno}: {e.msg}"
    if path.suffix == ".json":
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as e:
            return "JSON_ERROR", f"line {e.lineno}: {e.msg}"
    if path.suffix == ".csv":
        lines = path.read_text().splitlines()
        if len(lines) < 2:
            return "EMPTY_CSV", "only header row"
    return "OK", f"{path.stat().st_size} bytes"


def _check_imports() -> list[str]:
    """Import every sport engine to confirm no broken imports."""
    issues = []
    sys.path.insert(0, str(PROJECT_ROOT))
    for mod in ("nba_tc_engine", "wnba_tc_engine", "mlb_tc_engine",
                "nhl_tc_engine", "soccer_tc_engine", "nfl_tc_engine"):
        try:
            __import__(f"sources.{mod}")
        except Exception as e:
            issues.append(f"sources.{mod}: {e.__class__.__name__}: {e}")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    print(f"=== TC scan @ {datetime.now().isoformat()} ===")
    fail = 0
    rows = []
    for rel in REQUIRED_FILES:
        status, detail = _check_file(PROJECT_ROOT / rel)
        if status != "OK":
            fail += 1
        rows.append((rel, status, detail))
        marker = "✅" if status == "OK" else "❌"
        print(f"  {marker} {rel:45s} {status:14s} {detail}")

    import_issues = _check_imports()
    if import_issues:
        fail += len(import_issues)
        print(f"\n  ❌ {len(import_issues)} import error(s):")
        for i in import_issues:
            print(f"     - {i}")
    else:
        print("\n  ✅ all 6 sport engines import clean")

    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = DAILY_LOG_ROOT / today
    if log_dir.exists():
        proj_files = list(log_dir.glob("proj_*.json"))
        print(f"  ℹ️  {len(proj_files)} projection file(s) for {today}")
    else:
        print(f"  ⚠️  no log dir for {today} ({log_dir})")

    if args.report:
        report_path = PROJECT_ROOT / "scan_report.md"
        lines = [f"# TC scan report — {datetime.now().isoformat()}\n"]
        for rel, status, detail in rows:
            lines.append(f"- **{rel}** — {status} — {detail}")
        if import_issues:
            lines.append("\n## Import errors\n" + "\n".join(f"- {i}" for i in import_issues))
        report_path.write_text("\n".join(lines))
        print(f"\n  report: {report_path}")

    print(f"\n=== summary: {len(REQUIRED_FILES) - fail}/{len(REQUIRED_FILES)} files OK, "
          f"{len(import_issues)} import issue(s) ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
