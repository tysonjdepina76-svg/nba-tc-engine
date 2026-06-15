#!/usr/bin/env python3
"""
World Cup Historical Backtest Puller
Pulls ALL FIFA WC matches from ESPN (free, no auth, 4 tournaments: 2010/2014/2018/2022).
Outputs a compact CSV of per-player per-match stats for TC calibration.
Uses an on-disk 30-day cache keyed by (tournament, espn_event_id) to avoid re-pulls.
"""
import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

ESPN_SB = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
ESPN_SUM = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"

# 4 World Cup tournaments: dates cover group + knockout (8 days pre → 8 days post final)
WC_TOURNAMENTS = {
    "2022": {"start": "2022-11-20", "end": "2022-12-25", "label": "Qatar 2022"},
    "2018": {"start": "2018-06-14", "end": "2018-07-20", "label": "Russia 2018"},
    "2014": {"start": "2014-06-12", "end": "2014-07-18", "label": "Brazil 2014"},
    "2010": {"start": "2010-06-11", "end": "2010-07-15", "label": "South Africa 2010"},
}

CACHE_DIR = Path("/home/workspace/Daily_Log/wc_historical/.cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR = Path("/home/workspace/Reports")

# Stat keys we pull (from each player's stats[] in ESPN boxscore)
STAT_KEYS = [
    "totalGoals", "goalAssists", "totalShots", "shotsOnTarget",
    "foulsCommitted", "foulsSuffered", "yellowCards", "redCards",
    "saves", "ownGoals", "minutesPlayed",
]

# Helper: convert ESPN sport "date" + 5-digit datetime to YYYYMMDD
def daterange(start_str, end_str):
    d0 = datetime.strptime(start_str, "%Y-%m-%d")
    d1 = datetime.strptime(end_str, "%Y-%m-%d")
    days = (d1 - d0).days + 1
    for i in range(days):
        yield (d0 + timedelta(days=i)).strftime("%Y%m%d")

def fetch_scoreboard(date_str, max_retries=2):
    for attempt in range(max_retries):
        try:
            r = requests.get(ESPN_SB, params={"dates": date_str}, timeout=12)
            if r.ok:
                return r.json().get("events", [])
        except Exception:
            pass
        time.sleep(0.3)
    return []

def fetch_summary(event_id, max_retries=2):
    cache = CACHE_DIR / f"{event_id}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    for attempt in range(max_retries):
        try:
            r = requests.get(ESPN_SUM, params={"event": event_id}, timeout=15)
            if r.ok:
                payload = r.json()
                cache.write_text(json.dumps(payload))
                return payload
        except Exception:
            pass
        time.sleep(0.3)
    return None

def extract_player_rows(event_meta, summary):
    rows = []
    eid = event_meta.get("id")
    date = event_meta.get("date", "")[:10]
    comps = event_meta.get("competitions", [{}])[0].get("competitors", [])
    if len(comps) < 2:
        return rows
    home = next((c for c in comps if c.get("homeAway") == "home"), comps[-1])
    away = next((c for c in comps if c.get("homeAway") == "away"), comps[0])
    home_abbr = (home.get("team", {}).get("abbreviation") or "").upper()
    away_abbr = (away.get("team", {}).get("abbreviation") or "").upper()
    if not home_abbr or not away_abbr:
        return rows
    match_label = f"{away_abbr}@{home_abbr}"

    for roster in summary.get("rosters", []):
        team_abbr = (roster.get("team", {}).get("abbreviation") or "").upper()
        for p in roster.get("roster", []) or []:
            ath = p.get("athlete", {}) or {}
            name = ath.get("displayName", "")
            pid = ath.get("id", "")
            starter = 1 if p.get("starter") else 0
            stats_dict = {s.get("name"): s.get("displayValue") for s in p.get("stats", []) or []}
            row = {
                "espn_event_id": eid,
                "date": date,
                "match": match_label,
                "team": team_abbr,
                "player_id": pid,
                "player": name,
                "starter": starter,
                "pos": ath.get("position", {}).get("abbreviation", ""),
            }
            for k in STAT_KEYS:
                row[k] = stats_dict.get(k, 0)
            rows.append(row)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tournaments", default="2022,2018,2014,2010",
                    help="Comma-separated years, default all 4")
    ap.add_argument("--out", help="Override output CSV path")
    ap.add_argument("--limit", type=int, default=999, help="Max events per tournament (debug)")
    ap.add_argument("--refresh", action="store_true", help="Re-pull all summaries, ignore cache")
    args = ap.parse_args()

    if args.refresh:
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()

    years = args.tournaments.split(",")
    all_events = []
    for yr in years:
        cfg = WC_TOURNAMENTS.get(yr.strip())
        if not cfg:
            continue
        print(f"\n=== {cfg['label']} ({cfg['start']} → {cfg['end']}) ===", flush=True)
        seen = set()
        for d in daterange(cfg["start"], cfg["end"]):
            for ev in fetch_scoreboard(d):
                eid = ev.get("id")
                if not eid or eid in seen:
                    continue
                seen.add(eid)
                all_events.append((yr, ev))
            if len(seen) >= args.limit:
                break
        print(f"  {len(seen)} events found", flush=True)

    print(f"\nTotal events: {len(all_events)}", flush=True)

    all_rows = []
    pulls = 0
    for i, (yr, ev) in enumerate(all_events):
        eid = ev.get("id")
        summ = fetch_summary(eid)
        pulls += 1 if summ and not (CACHE_DIR / f"{eid}.json").stat().st_size == 0 else 0
        if summ:
            all_rows.extend(extract_player_rows(ev, summ))
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(all_events)} events processed, {len(all_rows)} rows so far", flush=True)

    if args.out:
        out = Path(args.out)
    else:
        out = OUT_DIR / f"wc_historical_player_stats_{datetime.now().strftime('%Y%m%d')}.csv"
    if not all_rows:
        print("No rows extracted.")
        return
    fields = list(all_rows[0].keys())
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWrote: {out}")
    print(f"  events: {len(all_events)}")
    print(f"  player rows: {len(all_rows)}")
    print(f"  size: {out.stat().st_size} bytes")

if __name__ == "__main__":
    main()
