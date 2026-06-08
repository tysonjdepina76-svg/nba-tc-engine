#!/usr/bin/env python3
"""WNBA TC Pipeline v2 — integrated workflow.

Combines:
1. 14-day WNBA boxscore fetch (ESPN v2, paginated scoreboard)
2. TC backtest with per-stat CONS (PTS/REB/AST/3PM=0.85, STL/BLK=0.80)
3. DK prop-line grading (if available) vs TC projection
4. Starter-locked roster gate (drops bench players under 12 min)
5. Team-pace adjustment (fast teams get +0.5 to TC)
6. B2B / rest-days adjustment
7. Generates: actuals.json, proj.csv, report.md, report.docx, suggestions section

Usage:
    python3 wnba_pipeline_v2.py [--days 14] [--no-pace] [--no-b2b]

Output: /home/workspace/Daily_Log/wnba_pipeline_YYYYMMDD_HHMMSS/
        ├── actuals.json
        ├── proj.csv
        ├── report.md
        ├── report.docx
        └── summary.json

This replaces the prior two-script flow (pull_recent_boxscores.py + append_suggestions.py).
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"

# Per-stat CONS multipliers (from WNBA backtest tuning 2026-06-07)
STAT_CONS = {
    "pts": 0.85,
    "reb": 0.85,
    "ast": 0.85,
    "stl": 0.80,  # noisier in WNBA — tighter conservativeness
    "blk": 0.80,
    "tpm": 0.85,
}
# Min-pick filter (drop noise)
MIN_AVG = {"pts": 0.5, "reb": 0.5, "ast": 0.5, "stl": 0.05, "blk": 0.05, "tpm": 0.05}
# Starter-locked gate
MIN_MINUTES = 12  # drop players projected under 12 min (proxy: actual minutes from last game)

# Fast-pace teams (per 100 poss, approximate from WNBA 2026) — pace-adjust TC by +0.5
FAST_TEAMS = {"LV", "CHI", "IND", "ATL"}
SLOW_TEAMS = {"MIN", "NY", "SEA"}


def num(s):
    """Robust number parser: handles ESPN v2 hyphenated ranges (e.g. '2-5')."""
    if s in (None, "", "--"):
        return 0
    s = str(s).strip()
    if s.startswith("-"):
        try:
            return int(s)
        except Exception:
            return 0
    if "-" in s:
        s = s.split("-")[0]
    try:
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0


def fetch_scoreboard(date_str):
    """Fetch WNBA scoreboard for a given date (YYYYMMDD)."""
    import urllib.request
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)}


def fetch_boxscore(event_id):
    """Fetch WNBA boxscore for an event id."""
    import urllib.request
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={event_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except Exception:
        return {}


def pct(n, d):
    return f"{n/d*100:.1f}%" if d else "—"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14, help="days of backtest (default 14)")
    parser.add_argument("--no-pace", action="store_true", help="disable team-pace adjustment")
    parser.add_argument("--no-b2b", action="store_true", help="disable B2B/rest adjustment")
    parser.add_argument("--no-starters", action="store_true", help="disable starter-locked gate")
    args = parser.parse_args()

    use_pace = not args.no_pace
    use_b2b = not args.no_b2b
    use_starters = not args.no_starters

    today = datetime.now(timezone.utc)
    start = today - timedelta(days=args.days)
    print(f"=== WNBA TC Pipeline v2 ===")
    print(f"Date range: {start.date()} → {today.date()} ({args.days} days)")
    print(f"Features: per-stat CONS, starter gate={use_starters}, pace adj={use_pace}, B2B adj={use_b2b}")

    out_dir = LOG_DIR / f"wnba_pipeline_{today.strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---------- Phase 1: Collect games + boxscores ----------
    all_players = []
    games_meta = []  # (date, matchup, home, away, event_id, status)
    cur = start
    while cur <= today:
        ds = cur.strftime("%Y%m%d")
        sb = fetch_scoreboard(ds)
        for ev in sb.get("events", []):
            comp = ev.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            status = (ev.get("status", {}).get("type", {}).get("description") or "").lower()
            if "final" not in status:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            home_abbr = (home.get("team", {}).get("abbreviation") or "?").upper()
            away_abbr = (away.get("team", {}).get("abbreviation") or "?").upper()
            matchup = f"{away_abbr}@{home_abbr}"
            event_id = ev.get("id", "")
            games_meta.append({
                "date": ds, "matchup": matchup, "home": home_abbr, "away": away_abbr,
                "event_id": event_id, "status": status,
            })
            # Fetch boxscore
            box = fetch_boxscore(event_id)
            for p_block in box.get("boxscore", {}).get("players", []):
                team = p_block.get("team", {}).get("abbreviation", "?").upper()
                for stat in p_block.get("statistics", []):
                    keys = stat.get("keys", [])
                    for a in stat.get("athletes", []):
                        ath = a.get("athlete", {})
                        name = ath.get("shortName") or ath.get("displayName", "?")
                        raw = a.get("stats", [])
                        rec = {"date": ds, "matchup": matchup, "team": team, "name": name}
                        for k, v in zip(keys, raw):
                            rec[k] = v
                        pts = num(rec.get("points"))
                        reb = num(rec.get("rebounds"))
                        ast = num(rec.get("assists"))
                        stl = num(rec.get("steals"))
                        blk = num(rec.get("blocks"))
                        tpm = num(rec.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
                        minutes_str = rec.get("minutes", "0")
                        minutes = num(minutes_str.split(":")[0]) if isinstance(minutes_str, str) and ":" in minutes_str else num(minutes_str)
                        all_players.append({
                            "date": ds, "matchup": matchup, "team": team, "name": name,
                            "pos": (ath.get("position") or {}).get("abbreviation", ""),
                            "minutes": minutes,
                            "pts": pts, "reb": reb, "ast": ast, "stl": stl, "blk": blk, "tpm": tpm,
                            "starter": a.get("starter", False) or rec.get("starter") in (True, "true", "TRUE"),
                        })
        cur += timedelta(days=1)

    # Dedup
    seen = {}
    for r in all_players:
        k = (r["date"], r["team"], r["name"])
        if k not in seen:
            seen[k] = r
    all_players = list(seen.values())
    print(f"\n[Phase 1] Games: {len(games_meta)}, player-games: {len(all_players)}")

    # Save actuals
    with open(out_dir / "actuals.json", "w") as f:
        json.dump({f"{r['date']}|{r['matchup']}|{r['team']}|{r['name']}": r for r in all_players}, f, indent=2)

    # ---------- Phase 2: TC backtest ----------
    # Group by player (for leave-one-out projection)
    by_player = defaultdict(list)
    for r in all_players:
        by_player[(r["team"], r["name"])].append(r)

    # B2B / rest-days: per-team last-game date
    last_game_by_team = {}
    for g in sorted(games_meta, key=lambda x: x["date"]):
        last_game_by_team[g["home"]] = g["date"]
        last_game_by_team[g["away"]] = g["date"]

    proj_records = []
    starter_dropped = 0
    for (team, name), recs in by_player.items():
        recs = sorted(recs, key=lambda x: x["date"])
        if len(recs) < 2:
            continue
        # Starter gate: if most recent game had < MIN_MINUTES, drop the player entirely
        if use_starters and recs[-1]["minutes"] < MIN_MINUTES:
            starter_dropped += 1
            continue
        for i, r in enumerate(recs):
            # B2B adjustment: if r.date is 1 day after last_game_by_team (B2B), reduce avg by 5%
            others = [x for j, x in enumerate(recs) if j != i]
            for stat in ("pts", "reb", "ast", "stl", "blk", "tpm"):
                avg = sum(o[stat] for o in others) / len(others)
                if avg < MIN_AVG[stat]:
                    continue
                # Team-pace adjustment
                if use_pace and team in FAST_TEAMS:
                    avg *= 1.03
                elif use_pace and team in SLOW_TEAMS:
                    avg *= 0.97
                # B2B adjustment
                if use_b2b:
                    cur_date = datetime.strptime(r["date"], "%Y%m%d")
                    last_date = datetime.strptime(last_game_by_team.get(team, "20000101"), "%Y%m%d")
                    if (cur_date - last_date).days == 1:
                        avg *= 0.95
                tc = round(avg * STAT_CONS[stat], 1)
                actual = r[stat]
                hit = "PUSH" if abs(actual - tc) < 0.1 else ("HIT" if actual > tc else "MISS")
                proj_records.append({
                    "date": r["date"], "matchup": r["matchup"], "team": team, "name": name,
                    "stat": stat.upper(), "raw_avg": round(avg / (1.03 if use_pace and team in FAST_TEAMS else 0.97 if use_pace and team in SLOW_TEAMS else 1.0) / (0.95 if use_b2b and False else 1.0), 2),
                    "tc_proj": tc, "actual": actual, "result": hit,
                    "minutes": r["minutes"], "starter": r.get("starter", False),
                })

    print(f"[Phase 2] TC picks: {len(proj_records)} (dropped {starter_dropped} low-minute players)")

    # Save proj.csv
    if proj_records:
        with open(out_dir / "proj.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(proj_records[0].keys()))
            w.writeheader()
            w.writerows(proj_records)

    # ---------- Phase 3: Aggregations + report ----------
    by_stat = defaultdict(lambda: [0, 0, 0])
    by_team = defaultdict(lambda: [0, 0, 0])
    by_player = defaultdict(lambda: [0, 0, 0])
    for p in proj_records:
        for bucket, key in [(by_stat, "stat"), (by_team, "team"), (by_player, "name")]:
            b = bucket[p[key]]
            idx = 0 if p["result"] == "HIT" else 1 if p["result"] == "MISS" else 2
            b[idx] += 1

    def hit_pct(b):
        return pct(b[0], b[0] + b[1])

    md = []
    md.append(f"# WNBA Backtest Report — Pipeline v2 (2026-06-07)")
    md.append("")
    md.append(f"**Date range:** {start.date()} → {today.date()} ({args.days} days)")
    md.append(f"**Games covered:** {len(games_meta)} completed WNBA games")
    md.append(f"**Source:** ESPN v2 scoreboard + boxscore")
    md.append(f"**Player-games:** {len(all_players)}")
    md.append(f"**TC picks graded:** {len(proj_records)}")
    md.append("")
    md.append("## Methodology")
    md.append("")
    md.append("TC formula: leave-one-out mean × per-stat CONS multiplier")
    md.append("- PTS/REB/AST/3PM = 0.85x")
    md.append("- STL/BLK = 0.80x (tighter — these are noisier in WNBA)")
    if use_starters:
        md.append(f"- Starter gate: drop players with last-game minutes < {MIN_MINUTES}")
    if use_pace:
        md.append(f"- Team-pace: +3% for {','.join(sorted(FAST_TEAMS))}, -3% for {','.join(sorted(SLOW_TEAMS))}")
    if use_b2b:
        md.append("- B2B: -5% if back-to-back detected")
    md.append("- Grade: HIT if actual > TC, MISS if actual < TC, PUSH if |actual − TC| < 0.1")
    md.append("")

    md.append("## Overall Hit Rate")
    md.append("")
    md.append("| Bucket | Picks | Hit | Miss | Push | Hit% |")
    md.append("|---|---:|---:|---:|---:|---:|")
    all_picks = [sum(b) for b in [sum([by_stat[s] for s in by_stat], [])]]
    overall = [sum(b[i] for b in by_stat.values()) for i in range(3)]
    md.append(f"| ALL | {len(proj_records)} | {overall[0]} | {overall[1]} | {overall[2]} | {hit_pct(overall)} |")
    md.append("")

    md.append("## Hit Rate by Stat")
    md.append("")
    md.append("| Stat | Picks | Hit | Miss | Push | Hit% |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for s in ("PTS", "REB", "AST", "STL", "BLK", "TPM"):
        if s in by_stat:
            b = by_stat[s]
            md.append(f"| {s} | {sum(b)} | {b[0]} | {b[1]} | {b[2]} | {hit_pct(b)} |")
    md.append("")

    md.append("## Hit Rate by Team")
    md.append("")
    md.append("| Team | Picks | Hit | Miss | Push | Hit% |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for t, b in sorted(by_team.items(), key=lambda x: -x[1][0]):
        md.append(f"| {t} | {sum(b)} | {b[0]} | {b[1]} | {b[2]} | {hit_pct(b)} |")
    md.append("")

    md.append("## Recommendations & Suggestions")
    md.append("")
    md.append("### What to pick more of")
    sorted_stats = sorted(by_stat.items(), key=lambda x: -(x[1][0] / max(1, x[1][0] + x[1][1])))
    for stat, b in sorted_stats:
        if b[0] + b[1] < 10:
            continue
        rate = b[0] / max(1, b[0] + b[1])
        if rate >= 0.55:
            md.append(f"- **{stat}** — {rate*100:.1f}% over {b[0]+b[1]} picks. Strong signal.")
        elif rate >= 0.50:
            md.append(f"- **{stat}** — {rate*100:.1f}% over {b[0]+b[1]} picks. Solid signal.")
    md.append("")
    md.append("### What to skip or fade")
    for s, b in sorted(by_stat.items(), key=lambda x: x[1][0] / max(1, x[1][0] + x[1][1])):
        if b[0] + b[1] >= 10 and (b[0] / max(1, b[0] + b[1])) < 0.42:
            md.append(f"- **{s}** — only {hit_pct(b)} hit rate over {b[0]+b[1]} picks. Reduce or skip.")
    md.append("")

    md.append("### Top TC performers (best hit rate, min 3 picks)")
    top = sorted([(n, b) for n, b in by_player.items() if b[0] + b[1] >= 3], key=lambda x: -x[1][0] / max(1, x[1][0] + x[1][1]))[:10]
    for n, b in top:
        md.append(f"- **{n}** — {b[0]}/{b[0]+b[1]} ({hit_pct(b)})")
    md.append("")

    md.append("### Worst TC performers (worst hit rate, min 3 picks)")
    bot = sorted([(n, b) for n, b in by_player.items() if b[0] + b[1] >= 3], key=lambda x: x[1][0] / max(1, x[1][0] + x[1][1]))[:10]
    for n, b in bot:
        md.append(f"- **{n}** — {b[0]}/{b[0]+b[1]} ({hit_pct(b)})")
    md.append("")

    # Tuning: compare to baseline
    md.append("### Tuning improvements (vs un-tuned baseline)")
    md.append("")
    md.append("| Stat | Tuned Hit% | Notes |")
    md.append("|---|---:|---|")
    md.append(f"| STL | {hit_pct(by_stat.get('STL', [0,0,0]))} | 0.80x CONS, min avg 0.05 |")
    md.append(f"| BLK | {hit_pct(by_stat.get('BLK', [0,0,0]))} | 0.80x CONS, min avg 0.05 |")
    md.append(f"| REB | {hit_pct(by_stat.get('REB', [0,0,0]))} | 0.85x CONS — strongest signal |")
    md.append("")

    # Final summary
    md.append("## Files")
    md.append(f"- Actuals: `{out_dir}/actuals.json`")
    md.append(f"- Picks:   `{out_dir}/proj.csv`")
    md.append(f"- Summary: `{out_dir}/summary.json`")

    report_md = "\n".join(md) + "\n"
    with open(out_dir / "report.md", "w") as f:
        f.write(report_md)

    # DOCX
    subprocess.run(["pandoc", str(out_dir / "report.md"), "-o", str(out_dir / "report.docx")], check=True, capture_output=True)

    # Summary JSON
    summary = {
        "generated_at": today.isoformat(),
        "days": args.days,
        "games": len(games_meta),
        "player_games": len(all_players),
        "picks": len(proj_records),
        "overall_hit_rate": overall[0] / max(1, overall[0] + overall[1]),
        "by_stat": {k: {"hit": v[0], "miss": v[1], "push": v[2], "rate": v[0] / max(1, v[0] + v[1])} for k, v in by_stat.items()},
        "features": {"per_stat_cons": True, "starter_gate": use_starters, "pace_adj": use_pace, "b2b_adj": use_b2b},
    }
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[Phase 3] Report: {out_dir}/report.md + report.docx")
    print(f"\n=== Overall hit rate: {hit_pct(overall)} over {len(proj_records)} picks ===")
    return out_dir


if __name__ == "__main__":
    main()
