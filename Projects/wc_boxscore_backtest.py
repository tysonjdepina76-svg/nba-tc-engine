#!/usr/bin/env python3
"""
World Cup Boxscore Backtest Puller
Fetches ESPN final box scores for completed FIFA World Cup 2026 matches and writes
per-match JSON + a flat player_stats.csv for backtest grading.

Run:
  python3 Projects/wc_boxscore_backtest.py                  # all available (auto-detects tournament start)
  python3 Projects/wc_boxscore_backtest.py --dates 20260611-20260615
  python3 Projects/wc_boxscore_backtest.py --days-back 10   # today - 10 days

Output:
  Daily_Log/final/wc_<away>_<home>_final_<espn_event>_<ts>.json
  Reports/wc_player_stats_<YYYYMMDD>.csv       (flat, one row per player per match)
  Reports/wc_matches_<YYYYMMDD>.csv            (one row per match with final score)
"""

import os
import re
import json
import time
import argparse
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load secrets
try:
    _sec = Path("/root/.zo/secrets.env")
    if _sec.exists():
        for _line in _sec.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except Exception:
    pass

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"
LOG_FINAL = Path("/home/workspace/Daily_Log/final")
LOG_FINAL.mkdir(parents=True, exist_ok=True)
REGISTRY = Path("/home/workspace/Daily_Log/wc_boxscore_registry.json")
REPORTS = Path("/home/workspace/Reports")
REPORTS.mkdir(parents=True, exist_ok=True)

PROP_STATS = [
    "totalGoals", "goalAssists", "totalShots", "shotsOnTarget",
    "foulsCommitted", "foulsSuffered", "yellowCards", "redCards",
    "ownGoals", "saves", "shotsFaced", "appearances", "subIns",
]

# Load registry (dedup) — same pattern as boxscore_saver.py
def _load_registry():
    if REGISTRY.exists():
        try:
            return set(json.loads(REGISTRY.read_text()))
        except Exception:
            return set()
    return set()

def _save_registry(ids):
    REGISTRY.write_text(json.dumps(sorted(ids), indent=2))

def fetch_events_for_date(date_yyyymmdd):
    r = requests.get(SCOREBOARD, params={"dates": date_yyyymmdd}, timeout=12)
    if not r.ok:
        return []
    return r.json().get("events", [])

def fetch_summary(event_id):
    r = requests.get(SUMMARY, params={"event": event_id}, timeout=15)
    if not r.ok:
        return None
    return r.json()

def is_completed(event):
    state = (event.get("status", {}).get("type", {}).get("name", "") or "").lower()
    return "full_time" in state or state in ("status_final", "post")

def parse_event(event):
    comps = (event.get("competitions", [{}])[0]).get("competitors", [])
    if len(comps) < 2:
        return None
    home = next((c for c in comps if c.get("homeAway") == "home"), comps[-1])
    away = next((c for c in comps if c.get("homeAway") == "away"), comps[0])
    return {
        "espn_event_id": event.get("id"),
        "date": event.get("date", "")[:10],
        "home_abbr": (home.get("team", {}).get("abbreviation") or "UNK").upper(),
        "home_name": home.get("team", {}).get("displayName") or home.get("team", {}).get("name"),
        "home_score": home.get("score", 0),
        "away_abbr": (away.get("team", {}).get("abbreviation") or "UNK").upper(),
        "away_name": away.get("team", {}).get("displayName") or away.get("team", {}).get("name"),
        "away_score": away.get("score", 0),
        "status": event.get("status", {}).get("type", {}).get("name", ""),
        "venue": (event.get("competitions", [{}])[0].get("venue", {}).get("fullName", "")),
    }

def parse_player_stats(summary, meta):
    """Yield (player_row, team_abbr) tuples from a match summary."""
    out = []
    for roster in summary.get("rosters", []):
        team_abbr = (roster.get("team", {}).get("abbreviation") or "UNK").upper()
        is_home = roster.get("homeAway") == "home"
        for p in roster.get("roster", []):
            ath = p.get("athlete", {}) or {}
            stats = {s.get("name"): s.get("value", 0) for s in p.get("stats", []) if s.get("name")}
            row = {
                "espn_event_id": meta["espn_event_id"],
                "date": meta["date"],
                "match": f"{meta['away_abbr']}@{meta['home_abbr']}",
                "player_id": ath.get("id"),
                "player_name": ath.get("displayName") or ath.get("shortName") or ath.get("fullName"),
                "jersey": p.get("jersey"),
                "position": (p.get("position") or {}).get("abbreviation", ""),
                "starter": bool(p.get("starter")),
                "team": team_abbr,
                "home_away": "home" if is_home else "away",
            }
            for s in PROP_STATS:
                row[s] = stats.get(s, 0)
            out.append(row)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days-back", type=int, default=10, help="How many days back from today to scan")
    ap.add_argument("--dates", help="Explicit YYYYMMDD-YYYYMMDD range (overrides --days-back)")
    ap.add_argument("--force", action="store_true", help="Re-pull even if in registry")
    args = ap.parse_args()

    today = datetime.now(timezone.utc)
    if args.dates:
        start_s, end_s = args.dates.split("-")
        start = datetime.strptime(start_s, "%Y%m%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_s, "%Y%m%d").replace(tzinfo=timezone.utc)
    else:
        end = today
        start = today - timedelta(days=args.days_back)

    registry = _load_registry()
    new_matches = 0
    new_players = 0
    skipped = 0
    errors = 0
    all_player_rows = []
    all_match_rows = []

    d = start
    while d <= end:
        ds = d.strftime("%Y%m%d")
        try:
            events = [e for e in fetch_events_for_date(ds) if is_completed(e)]
        except Exception as ex:
            print(f"[{ds}] ERR fetch: {ex}", flush=True)
            errors += 1
            d += timedelta(days=1); continue

        for ev in events:
            eid = ev.get("id")
            if not eid:
                continue
            if eid in registry and not args.force:
                skipped += 1
                continue
            try:
                meta = parse_event(ev)
                if not meta:
                    continue
                summary = fetch_summary(eid)
                if not summary:
                    continue
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                fname = LOG_FINAL / f"wc_{meta['away_abbr']}_{meta['home_abbr']}_final_{eid}_{ts}.json"
                fname.write_text(json.dumps({
                    "meta": meta,
                    "summary_keys": list(summary.keys()),
                    "pulled_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2))
                player_rows = parse_player_stats(summary, meta)
                all_player_rows.extend(player_rows)
                all_match_rows.append(meta)
                registry.add(eid)
                new_matches += 1
                new_players += len(player_rows)
                print(f"[{ds}] {meta['away_abbr']}@{meta['home_abbr']}  {meta['away_score']}-{meta['home_score']}  players={len(player_rows)}")
                time.sleep(0.3)
            except Exception as ex:
                print(f"[{ds}] {eid} ERR: {ex}", flush=True)
                errors += 1
        d += timedelta(days=1)

    _save_registry(registry)

    stamp = today.strftime("%Y%m%d")
    if all_player_rows:
        pcsv = REPORTS / f"wc_player_stats_{stamp}.csv"
        keys = list(all_player_rows[0].keys())
        with pcsv.open("w") as f:
            f.write(",".join(keys) + "\n")
            for r in all_player_rows:
                f.write(",".join(str(r.get(k, "")) for k in keys) + "\n")
        print(f"\nWrote: {pcsv}  ({len(all_player_rows)} player rows)")
    if all_match_rows:
        mcsv = REPORTS / f"wc_matches_{stamp}.csv"
        keys = list(all_match_rows[0].keys())
        with mcsv.open("w") as f:
            f.write(",".join(keys) + "\n")
            for r in all_match_rows:
                f.write(",".join(str(r.get(k, "")) for k in keys) + "\n")
        print(f"Wrote: {mcsv}  ({len(all_match_rows)} matches)")

    print(f"\n=== Summary ===")
    print(f"Matches pulled: {new_matches}  (skipped dedup: {skipped})")
    print(f"Player rows: {new_players}")
    print(f"Errors: {errors}")
    print(f"Registry now has: {len(registry)} WC event IDs")

if __name__ == "__main__":
    main()
