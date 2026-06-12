#!/usr/bin/env python3
"""Build a markdown report of the live WNBA DK combo lines."""
import json
from datetime import datetime
from collections import Counter
from pathlib import Path

src = json.loads(Path("/tmp/wnba_live.json").read_text())
combos = src["combos"]
out_dir = Path("/home/workspace/Reports")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / f"wnba_combos_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

typ_counts = Counter(c["combo_type"] for c in combos)
line_counts = Counter()
for c in combos:
    bucket = (
        "10-" if c["dk_line"] < 10 else
        "10-19" if c["dk_line"] < 20 else
        "20-29" if c["dk_line"] < 30 else
        "30-39" if c["dk_line"] < 40 else
        "40+"
    )
    line_counts[bucket] += 1

lines = []
lines.append("# WNBA DraftKings Combo Lines — Live Report")
lines.append("")
lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
lines.append(f"Source: dk-combos-engine (SGO → Odds API fallback)")
lines.append(f"Total combos: **{len(combos)}** across {len(typ_counts)} combo types")
lines.append("")
lines.append("## By type")
for t, n in sorted(typ_counts.items()):
    lines.append(f"- {t}: {n}")
lines.append("")
lines.append("## By line bucket")
for b in ["10-", "10-19", "20-29", "30-39", "40+"]:
    lines.append(f"- {b}: {line_counts.get(b, 0)}")
lines.append("")

for t in ["PRA", "PR", "PA"]:
    rows = [c for c in combos if c["combo_type"] == t]
    rows.sort(key=lambda c: c["dk_line"], reverse=True)
    lines.append(f"## {t} ({len(rows)} lines)")
    lines.append("")
    lines.append("| Player | Line | Odds |")
    lines.append("|---|---:|---:|")
    for c in rows[:30]:
        lines.append(f"| {c['player']} | {c['dk_line']} | {c['dk_odds']} |")
    lines.append("")

out_file.write_text("\n".join(lines))
print(f"Wrote {out_file} ({out_file.stat().st_size} bytes)")
print(f"Live endpoint: https://dk-combos-engine-true.zocomputer.io/combos?sport=WNBA")
print(f"Page: https://true.zo.space/dk-combos")
