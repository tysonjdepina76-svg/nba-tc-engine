#!/usr/bin/env python3
"""
TC Email Builder — produces actionable, stat-specific daily email reports
with combo props, matchup context, and [TAKE THE LINE] instructions.

Usage:
  python3 email_builder.py [--date 2026-07-16] [--output /path/to/report.md]
"""

import csv, json, os, sys, argparse
from datetime import datetime
from glob import glob
from typing import Dict, List, Any

ET_TZ = __import__("zoneinfo").ZoneInfo("America/New_York")

from combo_generator import generate_combos

SPORT_EMOJI = {"WNBA": "🏀", "MLB": "⚾", "WC": "⚽", "NFL": "🏈", "NHL": "🏒"}
SPORT_NAME = {"WNBA": "WNBA", "MLB": "MLB", "WC": "World Cup"}

def load_picks(csv_path: str) -> List[Dict]:
    """Load picks from CSV, return rows with actual data."""
    if not os.path.isfile(csv_path):
        return []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            if row.get("stat") and row["stat"].strip():
                rows.append(row)
        return rows

def group_by_sport(picks: List[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = {}
    for p in picks:
        league = p.get("league", p.get("sport", "")).upper()
        if league not in groups:
            groups[league] = []
        groups[league].append(p)
    return groups

def top_picks(picks: List[Dict], n: int = 10) -> List[Dict]:
    """Return top n picks sorted by abs(edge) descending."""
    valid = [p for p in picks if p.get("edge")]
    try:
        valid.sort(key=lambda p: abs(float(p["edge"])), reverse=True)
    except (ValueError, TypeError):
        pass
    return valid[:n]

def format_pick_line(p: Dict, show_matchup: bool = True) -> str:
    """Format a single pick line with full stat context."""
    player = p.get("player", "?")
    team = p.get("team", "")
    stat = p.get("stat", "").upper()
    direction = p.get("direction", "")
    tc_proj = p.get("tc_projection", p.get("projection", "0"))
    market_line = p.get("market_line", p.get("dk_line", "0"))
    edge = p.get("edge", "0")
    matchup = p.get("matchup", "")
    period = p.get("period", "GAME")
    why = p.get("why", "")

    try:
        edge_f = float(edge)
        if abs(edge_f) < 1.0:
            edge_str = f"{edge_f*100:+.0f}%"
        elif abs(edge_f) < 10:
            edge_str = f"{edge_f:+.1f}"
        else:
            edge_str = f"{edge_f:+.0f}"
    except ValueError:
        edge_str = str(edge)

    try:
        tc_str = f"{float(tc_proj):.1f}"
    except ValueError:
        tc_str = str(tc_proj)
    try:
        line_str = f"{float(market_line):.1f}"
    except ValueError:
        line_str = str(market_line)

    line = f"{player} ({team}) — **{stat} {direction}** — TC {tc_str} vs line {line_str} → edge **{edge_str}**"

    if show_matchup and matchup:
        line += f" | {matchup}"
    if period and period != "GAME":
        line += f" | {period}"

    return line

def format_combo_line(c: Dict) -> str:
    """Format a combo pick line."""
    return (f"{c['player']} ({c['team']}) — **{c['combo_label']} {c['direction']}** — "
            f"TC {c['tc_projection']:.1f} vs line {c['market_line']:.1f} → edge **{c['edge']:+1.1f} ({c['edge_pct']:+1.1f}%)**")

def generate_matchup_map(picks: List[Dict]) -> Dict[str, List[Dict]]:
    """Group picks by matchup for context."""
    mmap: Dict[str, List[Dict]] = {}
    for p in picks:
        m = p.get("matchup", "Unknown")
        if m not in mmap:
            mmap[m] = []
        mmap[m].append(p)
    return mmap

def build_email_report(picks_csv: str, log_date: str, output_path: str) -> str:
    """Main: build the full email report."""
    picks = load_picks(picks_csv)
    if not picks:
        return "No picks available for today."

    by_sport = group_by_sport(picks)

    report_date = datetime.strptime(log_date, "%Y-%m-%d").strftime("%B %d, %Y")

    lines = []
    lines.append(f"# TC Daily Action Report — {report_date}")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now(ET_TZ).strftime('%I:%M %p ET')}")
    lines.append(f"**Total Picks**: {len(picks)} across {len(by_sport)} sports")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 🎯 TOP PICKS — TAKE THESE LINES")
    lines.append("")
    lines.append("| # | Player | Stat | Dir | TC Proj | Line | Edge | Matchup |")
    lines.append("|---|--------|------|-----|---------|------|------|---------|")

    all_ranked = []
    for sport, spicks in by_sport.items():
        for p in spicks:
            try:
                e = abs(float(p.get("edge", 0)))
            except (ValueError, TypeError):
                e = 0
            all_ranked.append((e, sport, p))

    all_ranked.sort(key=lambda x: x[0], reverse=True)

    for i, (edge, sport, p) in enumerate(all_ranked[:20], 1):
        emoji = SPORT_EMOJI.get(sport, "")
        player = p.get("player", "?")
        stat = p.get("stat", "").upper()
        direction = p.get("direction", "")
        tc_proj = p.get("tc_projection", p.get("projection", "0"))
        market_line = p.get("market_line", p.get("dk_line", "0"))
        matchup = p.get("matchup", "")[:20]

        try:
            tc_str = f"{float(tc_proj):.1f}"
            line_str = f"{float(market_line):.1f}"
            edge_str = f"{float(edge)*100 if float(edge) < 1 else float(edge):+.1f}"
        except ValueError:
            tc_str = str(tc_proj)
            line_str = str(market_line)
            edge_str = str(edge)

        lines.append(f"| {i} | {emoji} {player} | {stat} | {direction} | {tc_str} | {line_str} | **{edge_str}** | {matchup} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    for sport in ["WNBA", "MLB", "WC"]:
        if sport not in by_sport:
            continue
        spicks = by_sport[sport]
        emoji = SPORT_EMOJI.get(sport, "")
        name = SPORT_NAME.get(sport, sport)
        top = top_picks(spicks, 8)

        lines.append(f"## {emoji} {name} — Top Picks")
        lines.append("")

        matchups = generate_matchup_map(spicks)
        lines.append(f"**Matchups today**: {', '.join(matchups.keys())}")
        lines.append("")

        for i, p in enumerate(top, 1):
            lines.append(f"**{i}. {format_pick_line(p)}**")
            why = p.get("why", "")
            if why and why.strip():
                lines.append(f"   > {why}")
            lines.append(f"   > `[TAKE THE LINE at DraftKings — {sport} {p.get('stat','').upper()} {p.get('direction','')} {p.get('market_line',p.get('dk_line','N/A'))}]`")
            lines.append("")

        if sport in ("WNBA", "NBA"):
            combos = generate_combos(sport, log_date)
            if combos:
                lines.append(f"### 🔗 {name} Combo Props")
                lines.append("")
                top_combos = [c for c in combos if c["edge_pct"] >= 10.0][:8]
                for i, c in enumerate(top_combos, 1):
                    lines.append(f"**{i}. {format_combo_line(c)}**")
                    lines.append(f"   > `[TAKE THE COMBO at DraftKings — {c['player']} {c['combo_label']} {c['direction']} {c['market_line']}]`")
                    lines.append("")
                lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## 📊 Full Projection Layer")
    lines.append("")
    lines.append(f"All {len(picks)} picks with TC projections, market lines, and edges are available in the pipeline.")
    lines.append(f"See: `Daily_Log/{log_date}/picks.csv`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*TC Daily Action Report — auto-generated. Lines from DraftKings/SportsDataIO. Always verify before wagering.*")

    report = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        print(f"Report written to {output_path}")

    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--picks-csv", default=None)
    args = ap.parse_args()

    log_date = args.date or datetime.now(ET_TZ).date().isoformat()

    picks_csv = args.picks_csv or f"/home/workspace/Daily_Log/{log_date}/picks.csv"
    output = args.output or f"/home/workspace/Daily_Log/{log_date}/email_report.md"

    report = build_email_report(picks_csv, log_date, output)
    print(report)

if __name__ == "__main__":
    main()
