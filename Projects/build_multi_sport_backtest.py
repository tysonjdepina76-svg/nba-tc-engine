#!/usr/bin/env python3
"""
Builds a comprehensive multi-sport backtest report from Daily_Log data.
Includes: NBA, WNBA live results + newly pulled MLB/NHL/World Cup lines.
"""
import csv, json, os
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

LOG_DIR = Path("/home/workspace/Daily_Log")
TODAY = datetime.now().strftime("%Y-%m-%d")
OUT_DIR = LOG_DIR / "backtests" / TODAY
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_day_picks(day: str):
    """Load picks.csv for a given day."""
    p = LOG_DIR / day / "picks.csv"
    if not p.exists():
        return []
    picks = []
    with open(p) as f:
        reader = csv.DictReader(f)
        for row in reader:
            picks.append(row)
    return picks

def load_day_summaries(day: str):
    """Load summaries.json for a given day."""
    p = LOG_DIR / day / "summaries.json"
    if not p.exists():
        return []
    return json.loads(p.read_text())

def load_all_picks():
    """Load all picks from all dated folders."""
    all_picks = []
    for d in sorted(LOG_DIR.iterdir()):
        if not d.is_dir() or not d.name.startswith("20"):
            continue
        picks = load_day_picks(d.name)
        all_picks.extend(picks)
    return all_picks

def compute_hit_rates(picks):
    """Compute hit rates by sport, stat, direction, team."""
    # Only picks with actual results (non-PENDING)
    resolved = [p for p in picks if p.get("actual") and p.get("result") and p.get("result") != "PENDING"]
    if not resolved:
        return {"total_resolved": 0, "hits": 0}
    
    hits = [p for p in resolved if p.get("result") == "HIT"]
    
    by_sport = defaultdict(lambda: {"resolved": 0, "hits": 0})
    by_stat = defaultdict(lambda: {"resolved": 0, "hits": 0})
    by_direction = defaultdict(lambda: {"resolved": 0, "hits": 0})
    by_team = defaultdict(lambda: {"resolved": 0, "hits": 0})
    
    for p in resolved:
        sport = p.get("league", "NBA")
        stat = p.get("stat", "")
        direction = p.get("direction", "")
        team = p.get("team", "")
        is_hit = p.get("result") == "HIT"
        
        by_sport[sport]["resolved"] += 1
        by_stat[stat]["resolved"] += 1
        by_direction[direction]["resolved"] += 1
        by_team[team]["resolved"] += 1
        if is_hit:
            by_sport[sport]["hits"] += 1
            by_stat[stat]["hits"] += 1
            by_direction[direction]["hits"] += 1
            by_team[team]["hits"] += 1
    
    def rate(d):
        return {k: {"resolved": v["resolved"], "hits": v["hits"], 
                     "rate": round(v["hits"]/v["resolved"]*100, 1) if v["resolved"] else 0}
                for k, v in sorted(d.items(), key=lambda x: -x[1]["resolved"])}
    
    return {
        "total_resolved": len(resolved),
        "total_hits": len(hits),
        "overall_hit_rate": round(len(hits)/len(resolved)*100, 1),
        "by_sport": rate(by_sport),
        "by_stat": rate(by_stat),
        "by_direction": rate(by_direction),
        "by_team": rate(by_team),
    }

def load_lines_data():
    """Load pulled sports lines."""
    p = LOG_DIR / TODAY / "all_sports_lines.json"
    if p.exists():
        return json.loads(p.read_text())
    # Also check per-sport files
    files = list((LOG_DIR / TODAY).glob("*_lines.json"))
    data = {}
    for f in files:
        sport = f.stem.replace("_lines", "")
        data[sport] = json.loads(f.read_text())
    return data

def build_report():
    all_picks = load_all_picks()
    lines = load_lines_data()
    
    # Build report
    lines_data = []
    lines_data.append("# Multi-Sport Backtest Report")
    lines_data.append(f"Generated: {datetime.now().isoformat()}")
    lines_data.append("")
    
    # Section 1: TC Pick History
    lines_data.append("## 1. TC Pick History (NBA + WNBA)")
    lines_data.append("")
    hits = compute_hit_rates(all_picks)
    lines_data.append(f"- **Total resolved picks**: {hits.get('total_resolved', 0)}")
    lines_data.append(f"- **Total hits**: {hits.get('total_hits', 0)}")
    lines_data.append(f"- **Overall hit rate**: {hits.get('overall_hit_rate', 0):.1f}%")
    lines_data.append(f"- **Total picks (incl. pending)**: {len(all_picks)}")
    lines_data.append("")
    
    if hits.get("by_sport"):
        lines_data.append("### By Sport")
        lines_data.append("| Sport | Resolved | Hits | Rate |")
        lines_data.append("|---|---|---|---|")
        for sport, data in hits["by_sport"].items():
            lines_data.append(f"| {sport} | {data['resolved']} | {data['hits']} | {data['rate']:.1f}% |")
        lines_data.append("")
    
    if hits.get("by_stat"):
        lines_data.append("### By Stat")
        lines_data.append("| Stat | Resolved | Hits | Rate |")
        lines_data.append("|---|---|---|---|")
        for stat, data in hits["by_stat"].items():
            lines_data.append(f"| {stat} | {data['resolved']} | {data['hits']} | {data['rate']:.1f}% |")
        lines_data.append("")
    
    if hits.get("by_direction"):
        lines_data.append("### By Direction")
        lines_data.append("| Direction | Resolved | Hits | Rate |")
        lines_data.append("|---|---|---|---|")
        for d, data in hits["by_direction"].items():
            lines_data.append(f"| {d} | {data['resolved']} | {data['hits']} | {data['rate']:.1f}% |")
        lines_data.append("")
    
    # Section 2: Live Lines Pulled Today
    lines_data.append("## 2. Live Lines — All Sports (June 13)")
    lines_data.append("")
    
    if lines:
        if isinstance(lines, dict):
            # Flatten SGO + Odds counts
            sgo_count = 0
            odds_count = 0
            sport_counts = Counter()
            for k, v in lines.items():
                if isinstance(v, list):
                    sport_counts[k.replace("sgo_", "").replace("oddsapi_", "")] += len(v)
                    if k.startswith("sgo_"): sgo_count += len(v)
                    else: odds_count += len(v)
            
            lines_data.append(f"- **Total entries**: {sgo_count + odds_count} (SGO: {sgo_count}, Odds API: {odds_count})")
            lines_data.append("")
            lines_data.append("| Sport | Source | Entries |")
            lines_data.append("|---|---|---|")
            for k, v in lines.items():
                if isinstance(v, list):
                    sport = k.replace("sgo_", "").replace("oddsapi_", "")
                    source = "SGO" if k.startswith("sgo_") else "Odds API"
                    lines_data.append(f"| {sport.upper()} | {source} | {len(v)} |")
    
    lines_data.append("")
    
    # Section 3: Daily Run Summary
    lines_data.append("## 3. Daily Pipeline Runs (Last 8 Days)")
    lines_data.append("")
    
    days = sorted([d.name for d in LOG_DIR.iterdir() if d.is_dir() and d.name.startswith("20")])
    for day in days:
        s = load_day_summaries(day)
        if not s:
            continue
        total_picks = sum(g.get("valid_prop_count", 0) for g in s)
        lines_data.append(f"### {day} — {len(s)} games, {total_picks} picks")
        for g in s:
            match = g.get("matchup", "?")
            sport = g.get("sport", "?")
            signal = g.get("signal", "?")
            edge = g.get("edge", 0)
            dk_total = g.get("dk_total", "N/A")
            picks = g.get("valid_prop_count", 0)
            lines_data.append(f"| {sport} | {match} | {picks} picks | signal={signal} (edge={edge}) | DK total: {dk_total} |")
        lines_data.append("")
    
    # Section 4: WNBA Combos
    combos_path = LOG_DIR / TODAY / "wnba_combos.json"
    if combos_path.exists():
        combos = json.loads(combos_path.read_text())
        lines_data.append("## 4. WNBA Combo Lines (PRA/PR/PA)")
        lines_data.append(f"- **Total combos**: {combos.get('count', 0)}")
        lines_data.append("")
        top = sorted(combos.get("combos", []), key=lambda x: x.get("dk_line", 0), reverse=True)[:15]
        lines_data.append("| Player | Type | DK Line | Odds |")
        lines_data.append("|---|---|---|---|")
        for c in top:
            lines_data.append(f"| {c['player']} | {c['combo_type']} | {c['dk_line']} | {c['dk_odds']} |")
        lines_data.append("")
    
    # Write report
    report_path = OUT_DIR / "multi_sport_backtest_report.md"
    report_path.write_text("\n".join(lines_data))
    
    # Save raw data
    (OUT_DIR / "backtest_hit_rates.json").write_text(json.dumps(hits, indent=2))
    
    print(f"✅ Report saved to {report_path}")
    print(f"✅ Hit rates saved to {OUT_DIR / 'backtest_hit_rates.json'}")
    return hits

if __name__ == "__main__":
    build_report()
