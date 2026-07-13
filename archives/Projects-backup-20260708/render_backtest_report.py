#!/usr/bin/env python3
"""Render reports/backtest_report.md from reports/backtest_report.json."""
import json
from pathlib import Path

WS = Path("/home/workspace")
REPORTS = WS / "reports"
json_path = REPORTS / "backtest_report.json"
md_path = REPORTS / "backtest_report.md"

data = json.loads(json_path.read_text())
all_agg = data["by_sport"]["ALL"]

md = []
md.append(f"# Multi-Sport Backtest Report — {data['generated_at']}\n")
md.append("## Overall (all sports)\n")
md.append(f"- Picks evaluated: {data['total_picks']}")
md.append(f"- Graded: {all_agg['graded']}")
md.append(f"- Hit rate: {all_agg['hit_rate_pct']}%")
md.append(f"- Avg edge: {all_agg['avg_edge']}")
md.append(f"- ROI (at -110): {all_agg['roi_pct']}%")
md.append(f"- Profit (on ${all_agg['wagered_usd']} wagered): ${all_agg['profit_usd']}\n")

md.append("## By Sport\n")
md.append("| Sport | Picks | Graded | HIT | MISS | PUSH | Hit Rate | Avg Edge | ROI | Profit |")
md.append("|---|---|---|---|---|---|---|---|---|---|")
for sport in ["WNBA", "SOCCER", "MLB", "NBA", "ALL"]:
    a = data["by_sport"].get(sport)
    if not a:
        continue
    hr = f"{a['hit_rate_pct']}%" if a["hit_rate_pct"] is not None else "n/a"
    edge = f"{a['avg_edge']}" if a["avg_edge"] is not None else "n/a"
    roi = f"{a['roi_pct']}%" if a["roi_pct"] is not None else "n/a"
    md.append(f"| {sport} | {a['picks']} | {a['graded']} | {a['hits']} | {a['misses']} | {a['pushes']} | {hr} | {edge} | {roi} | ${a['profit_usd']} |")

md.append("\n## Source Coverage\n")
md.append("| Source | Picks | Graded | Hit Rate |")
md.append("|---|---|---|---|")
for label, agg in data["details"].items():
    hr = f"{agg['hit_rate_pct']}%" if agg["hit_rate_pct"] is not None else "n/a"
    md.append(f"| {label} | {agg['picks']} | {agg['graded']} | {hr} |")

md.append("\n## Methodology\n")
md.append("- ROI assumes -110 odds: HIT pays +$91.91, MISS loses $100, PUSH returns stake")
md.append("- Hit rate = HIT / (HIT + MISS); PUSH and ungraded picks excluded")
md.append("- Avg edge = mean of `edge` columns from source CSVs (TC projection minus market line)")
md.append("\n## Limitations\n")
md.append("- Only WNBA 6/13 + World Cup 6/15 + MLB SF@ATL have actuals. NBA/MOST MLB picks lack boxscore coverage.")
md.append("- WNBA result column uses H/M/P (not HIT/MISS); PUSH discarded from hit-rate calc.")
md.append("- World Cup 3.6% hit rate likely reflects wrong `direction` field (column overloaded); recheck before betting.")
md.append("- ROI assumes flat $100/pick with no line-shopping or limit awareness.")

md_path.write_text("\n".join(md) + "\n")
print(f"Wrote {md_path}")
