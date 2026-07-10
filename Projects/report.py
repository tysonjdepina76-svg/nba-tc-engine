#!/usr/bin/env python3
"""Generate TC performance reports (markdown / JSON)."""
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.tracking.historical_tracker import HistoricalTracker

SPORTS = ["MLB", "WNBA", "NBA", "NFL", "NHL", "WORLD_CUP"]


def build_report(days: int, fmt: str) -> dict:
    ht = HistoricalTracker()
    out = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "period_days": days,
        "by_sport": {},
        "overall": ht.performance(days=days),
        "pending": {s: len(ht.pending_bets(s)) for s in SPORTS},
    }
    for s in SPORTS:
        out["by_sport"][s] = ht.performance(sport=s, days=days)
    return out


def to_markdown(r: dict) -> str:
    lines = [
        f"# TC Performance Report — {r['period_days']}d",
        f"_Generated: {r['generated']}_",
        "",
        "## Overall",
        f"- Bets: {r['overall']['total_bets']}  |  Win rate: {r['overall']['win_rate']*100:.1f}%  |  "
        f"ROI: {r['overall']['roi']*100:.1f}%  |  Profit: ${r['overall']['total_profit']:+.2f}",
        "",
        "## By Sport",
        "| Sport | Bets | Win% | ROI | Profit | Pending |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for s, m in r["by_sport"].items():
        lines.append(
            f"| {s} | {m['total_bets']} | {m['win_rate']*100:.1f}% | "
            f"{m['roi']*100:.1f}% | ${m['total_profit']:+.2f} | {r['pending'].get(s, 0)} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=1)
    p.add_argument("--format", choices=["md", "json", "html"], default="md")
    args = p.parse_args()

    r = build_report(args.days, args.format)
    if args.format == "json":
        print(json.dumps(r, indent=2))
    else:
        print(to_markdown(r))
    out_path = Path(f"reports/report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(to_markdown(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
