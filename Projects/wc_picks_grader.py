#!/usr/bin/env python3
"""
World Cup Picks Grader
Loads FanDuel WC player props from Daily_Log/worldcup/YYYYMMDD/picks.csv
and grades them against ESPN final box scores from Reports/wc_player_stats_*.csv.

Usage:
  python3 wc_picks_grader.py                  # grade last 7 days
  python3 wc_picks_grader.py --days-back 14
"""
import csv
import json
import argparse
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOG_DIR = Path("/home/workspace/Daily_Log/worldcup")
REPORTS = Path("/home/workspace/Reports")

STAT_KEY_MAP = {
    "goals": "totalGoals",
    "assists": "goalAssists",
    "shots": "totalShots",
    "shots_on_target": "shotsOnTarget",
}


def norm_name(s):
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"\b(jr|sr|ii|iii)\b\.?", "", s)
    s = re.sub(r"[^a-z\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_matchup(mu):
    parts = [t.strip() for t in (mu or "").split("@")]
    if len(parts) == 2:
        return parts[0].upper(), parts[1].upper()
    return None, None


def build_box_index(box_rows):
    """Return dict: (espn_event_id, normalized_name) -> player row."""
    idx = {}
    for r in box_rows:
        key = (r["espn_event_id"], norm_name(r["player_name"]))
        idx[key] = r
    return idx


def grade_pick(pick, box_idx):
    """Return (result, actual, stat_key) or (None, None, None) if not gradeable."""
    stat_key = STAT_KEY_MAP.get((pick.get("stat") or "").lower())
    if not stat_key:
        return None, None, None
    if not pick.get("espn_event_id"):
        return None, None, None
    pname = norm_name(pick.get("player", ""))
    box = box_idx.get((pick["espn_event_id"], pname))
    if not box:
        return None, None, None
    try:
        actual = float(box.get(stat_key, 0) or 0)
    except (ValueError, TypeError):
        return None, None, None
    try:
        line = float(pick.get("line", 0))
    except (ValueError, TypeError):
        return None, None, None
    if pick.get("direction", "Over").lower().startswith("under"):
        result = "HIT" if actual < line else ("PUSH" if actual == line else "MISS")
    else:
        result = "HIT" if actual > line else ("PUSH" if actual == line else "MISS")
    return result, actual, stat_key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days-back", type=int, default=14)
    ap.add_argument("--stats-csv", help="Override path to wc_player_stats_*.csv")
    args = ap.parse_args()

    if args.stats_csv:
        stats_csv = Path(args.stats_csv)
    else:
        cs = sorted(REPORTS.glob("wc_player_stats_*.csv"))
        if not cs:
            print("No wc_player_stats CSV found. Run wc_boxscore_backtest.py first.")
            return
        stats_csv = cs[-1]
    print(f"Loading box scores: {stats_csv}")
    box_rows = list(csv.DictReader(stats_csv.open()))
    box_by_eid = defaultdict(list)
    for r in box_rows:
        box_by_eid[r["espn_event_id"]].append(r)
    box_idx = build_box_index(box_rows)
    print(f"Box scores loaded: {len(box_by_eid)} matches, {len(box_rows)} player rows")

    today = datetime.now(timezone.utc)
    graded = []
    skipped = 0
    for offset in range(0, args.days_back):
        day = (today - timedelta(days=offset)).strftime("%Y%m%d")
        picks_csv = LOG_DIR / day / "picks.csv"
        if not picks_csv.exists():
            continue
        match_json = picks_csv.parent / "matches.json"
        match_by_teams = {}
        if match_json.exists():
            try:
                m = json.loads(match_json.read_text())
                matches_list = m.get("events") or m.get("matches") or []
                for ev in matches_list:
                    eid = ev.get("id") or ev.get("espn_id")
                    teams = ev.get("teams", [])
                    if len(teams) >= 2:
                        home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                        away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])
                        habbr = (home.get("abbrev") or home.get("abbreviation") or "").upper()
                        aabbr = (away.get("abbrev") or away.get("abbreviation") or "").upper()
                        if habbr and aabbr:
                            match_by_teams[(aabbr, habbr)] = eid
            except Exception as e:
                print(f"  ! {day} matches.json parse failed: {e}")
        if not match_by_teams:
            print(f"  {day}: 0 matchups indexed")
            continue
        print(f"  {day}: {len(match_by_teams)} matchups indexed, sample: {list(match_by_teams.items())[:2]}")

        with picks_csv.open() as f:
            for row in csv.DictReader(f):
                if not row.get("player") or not row.get("stat"):
                    continue
                a, h = split_matchup(row.get("matchup", ""))
                eid = match_by_teams.get((a, h)) if a and h else None
                pick = {
                    "date": day,
                    "matchup": row.get("matchup", ""),
                    "player": row.get("player", ""),
                    "stat": row.get("stat", ""),
                    "direction": row.get("direction", "Over"),
                    "line": row.get("line", ""),
                    "odds": row.get("over_price") or row.get("under_price") or "",
                    "book": row.get("book", ""),
                    "espn_event_id": eid,
                }
                result, actual, stat_key = grade_pick(pick, box_idx)
                if result is None:
                    skipped += 1
                    continue
                pick.update({"result": result, "actual": actual, "stat_key": stat_key})
                graded.append(pick)

    if not graded:
        print("No picks could be graded.")
        return

    stamp = today.strftime("%Y%m%d")
    gcsv = REPORTS / f"wc_picks_graded_{stamp}.csv"
    keys = list(graded[0].keys())
    with gcsv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(graded)
    print(f"\nWrote: {gcsv}  ({len(graded)} graded picks, {skipped} skipped)")

    by_stat = defaultdict(lambda: {"HIT": 0, "MISS": 0, "PUSH": 0})
    by_match = defaultdict(lambda: {"HIT": 0, "MISS": 0, "PUSH": 0})
    by_dir = defaultdict(lambda: {"HIT": 0, "MISS": 0, "PUSH": 0})
    by_book = defaultdict(lambda: {"HIT": 0, "MISS": 0, "PUSH": 0})
    hits = misses = pushes = 0
    for p in graded:
        for d, key in [(by_stat[p["stat"]], "stat"), (by_match[p["matchup"]], "match"),
                       (by_dir[p["direction"]], "dir"), (by_book[p["book"] or "none"], "book")]:
            d[p["result"]] += 1
        if p["result"] == "HIT": hits += 1
        elif p["result"] == "MISS": misses += 1
        else: pushes += 1
    total = hits + misses + pushes
    hr = (hits / (hits + misses) * 100) if (hits + misses) else 0

    print(f"\n=== WC Hit Rate ===")
    print(f"Total: {total}  HIT: {hits}  MISS: {misses}  PUSH: {pushes}  HR: {hr:.1f}%")
    print(f"\nBy stat:")
    for k, v in sorted(by_stat.items()):
        d = v["HIT"] + v["MISS"]
        if d:
            print(f"  {k:18s}  {v['HIT']}/{d}  {v['HIT']/d*100:.1f}%")
    print(f"\nBy direction:")
    for k, v in sorted(by_dir.items()):
        d = v["HIT"] + v["MISS"]
        if d:
            print(f"  {k:18s}  {v['HIT']}/{d}  {v['HIT']/d*100:.1f}%")
    print(f"\nBy book:")
    for k, v in sorted(by_book.items()):
        d = v["HIT"] + v["MISS"]
        if d:
            print(f"  {k:18s}  {v['HIT']}/{d}  {v['HIT']/d*100:.1f}%")
    print(f"\nBy match (top 5):")
    for k, v in sorted(by_match.items(), key=lambda x: -(x[1]["HIT"]+x[1]["MISS"]))[:5]:
        d = v["HIT"] + v["MISS"]
        if d:
            print(f"  {k:18s}  {v['HIT']}/{d}  {v['HIT']/d*100:.1f}%")


if __name__ == "__main__":
    main()
