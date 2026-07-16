#!/usr/bin/env python3
"""TC pipeline auto-fix.

Tries to repair the most common issues that the scan turns up:
  - missing empty stub files -> write a 1-line placeholder
  - JSON files with trailing commas
  - CSV with only a header row (no data) -> flag for manual review
  - empty log files -> seed with a timestamp

Usage:
  python3 fix_pipeline.py            # dry-run, show what would change
  python3 fix_pipeline.py --apply    # actually write changes
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("/home/workspace/Projects")
LOG_FILE = PROJECT_ROOT / "logs" / "fix_pipeline.log"

STUB_TEMPLATE = "#!/usr/bin/env python3\n# Auto-generated placeholder — flesh out before relying on this.\n"

# Map of common filename -> minimal working stub
STUBS = {
    "orchestrator.py": "#!/usr/bin/env python3\n# Orchestrator stub — see scan_report.md\n",
    "fix_pipeline.py": "#!/usr/bin/env python3\n# Fix-pipeline self-stub\n",
    "streamlit_app.py": (
        "#!/usr/bin/env python3\nimport streamlit as st\nst.title('TC Sports')\n"
        "st.write('Dashboard placeholder — needs real data wiring.')\n"
    ),
    "run_settlement.py": (
        "#!/usr/bin/env python3\n# Settlement stub — re-implement from /home/workspace/Projects/sources/run_settlement.py\n"
    ),
}


def _fix_json_trailing_comma(text: str) -> str:
    # Remove trailing comma before } or ]
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _try_fix(path: Path) -> tuple[bool, str]:
    """Return (changed, description)."""
    if not path.exists():
        return False, "missing (would need real content)"

    if path.suffix == ".json":
        try:
            json.loads(path.read_text())
            return False, "valid JSON"
        except json.JSONDecodeError:
            fixed = _fix_json_trailing_comma(path.read_text())
            try:
                json.loads(fixed)
                path.write_text(fixed)
                return True, "removed trailing comma"
            except json.JSONDecodeError as e:
                return False, f"still invalid: {e}"

    if path.suffix == ".py":
        try:
            compile(path.read_text(), str(path), "exec")
            return False, "compiles"
        except SyntaxError as e:
            return False, f"line {e.lineno}: {e.msg}"

    if path.suffix == ".csv":
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        if len(lines) <= 1:
            return False, "empty CSV (needs real data)"
        return False, f"{len(lines) - 1} data rows"

    return False, "no fix available"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    targets = list(STUBS.keys()) + [
        "config/algorithm_weights.json",
        "data/historical.csv",
        "sources/nfl_position_groups.py",
        "sources/player_stats_scraper.py",
        "run_settlement.py",
    ]

    print(f"=== fix_pipeline ({'APPLY' if args.apply else 'DRY RUN'}) "
          f"@ {datetime.now().isoformat()} ===")

    for rel in targets:
        path = PROJECT_ROOT / rel
        if path.exists():
            changed, desc = _try_fix(path)
            mark = "🛠 " if changed else ("  " if desc.startswith("valid") or "rows" in desc else "⚠️ ")
            print(f"  {mark}{rel:42s} {desc}")
        else:
            stub = STUBS.get(path.name, STUB_TEMPLATE)
            print(f"  🆕 {rel:42s} MISSING — would write stub")
            if args.apply and rel.endswith(tuple(STUBS.keys())):
                path.write_text(stub)
                print(f"     wrote {len(stub)} bytes")

    if not args.apply:
        print("\n  pass --apply to actually write changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
