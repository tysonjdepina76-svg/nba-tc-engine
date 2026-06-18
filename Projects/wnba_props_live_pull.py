#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
WNBA Live Props Pull — uses the new team_game_mapper to resolve Odds API events
to our canonical ESPN abbrs, then pulls DK player props for tonight's slate.

Writes:
- /home/workspace/Daily_Log/wnba_props_<YYYY-MM-DD>.json   (raw per-book props)
- /home/workspace/Daily_Log/wnba_props_<YYYY-MM-DD>_dk.csv (DK-only, for TC)
"""
import os
import sys
import json
import csv
import re
import requests
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from team_game_mapper import (
    canon_abbr,
    canon_pair,
    fetch_espn_wnba_slate,
    fetch_odds_api_wnba_events,
    fetch_sgo_events,
    build_canonical_game_map,
    find_espn_event_for_teams,
)

# Force-load secrets from /root/.zo/secrets.env (env vars don't survive between runs)
for line in Path('/root/.zo/secrets.env').read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k, v)

ODDS_API_KEY = os.environ['ODDS_API_KEY']
BASE = "https://api.the-odds-api.com/v4"

GAME_MARKETS = ["h2h", "spreads", "totals"]  # game-line markets
PLAYER_PROP_MARKETS = [
    "player_points", "player_rebounds", "player_assists",
    "player_threes", "player_points_rebounds_assists",
    "player_points_rebounds", "player_points_assists",
    "player_rebounds_assists", "player_double_double",
    "player_triple_double", "player_blocks", "player_steals",
    "player_turnovers",
]


def pull_event_props(event_id, markets=",".join(PLAYER_PROP_MARKETS), regions="us"):
    url = f"{BASE}/sports/basketball_wnba/events/{event_id}/odds"
    r = requests.get(url, params={
        "apiKey": ODDS_API_KEY,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }, timeout=20)
    if r.status_code != 200:
        return None, r.status_code, r.headers.get("x-requests-remaining")
    return r.json(), r.status_code, r.headers.get("x-requests-remaining")


def to_dk_rows(event, props_payload):
    """Convert Odds API per-book payload to a flat list of DK player-prop rows."""
    rows = []
    commence = event.get("commence_time")
    home_full = event.get("home_team", "")
    away_full = event.get("away_team", "")
    home_abbr = normalize_team(home_full) or "UNK"
    away_abbr = normalize_team(away_full) or "UNK"
    odds_event_id = event.get("id")
    espn_event_id = event.get("_espn_event_id", "")
    for bk in props_payload.get("bookmakers", []):
        if bk.get("key") != "draftkings":
            continue
        for mkt in bk.get("markets", []):
            stat = mkt["key"]
            for oc in mkt.get("outcomes", []):
                rows.append({
                    "odds_event_id": odds_event_id,
                    "espn_event_id": espn_event_id,
                    "commence": commence,
                    "book": "draftkings",
                    "home_abbr": home_abbr,
                    "away_abbr": away_abbr,
                    "player": oc.get("description", ""),
                    "stat": stat,
                    "direction": oc.get("name", ""),  # Over / Under
                    "line": oc.get("point"),
                    "odds": oc.get("price"),
                })
    return rows


normalize_team = canon_abbr  # legacy alias used in pull script


def main():
    out_dir = Path("/home/workspace/Daily_Log")
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    print(f"=== WNBA Live Props Pull — {today} ===")
    print(f"Odds API remaining: {os.environ.get('_PRE_PULL_REM', '?')}\n")

    # 1) ESPN slate
    espn_slates = fetch_espn_wnba_slate(target_date=now.date())
    print(f"ESPN slates fetched: {len(espn_slates)}")
    for s in espn_slates:
        print(f"  {s['espn_event_id']}  {s['away']}@{s['home']}  {s['start_utc']}")

    # 2) Odds API events dict (from mapper)
    odds_map = fetch_odds_api_wnba_events()  # {event_id: {away_canon, home_canon, commence_utc}}
    print(f"\nOdds API events: {len(odds_map)}")
    for oid, meta in odds_map.items():
        print(f"  odds={oid[:12]}  {meta['away_canon']}@{meta['home_canon']}  commence={meta['commence_utc']}")

    # 3) Build canonical map (ESPN <-> Odds API) using the mapper helper
    canonical = build_canonical_game_map(target_date=now.date())
    n_with_odds = sum(1 for g in canonical.values() if g.get("odds_api_event_id"))
    print(f"\nCanonical games resolved: {n_with_odds} of {len(canonical)}")
    for espn_id, g in canonical.items():
        if g.get("odds_api_event_id"):
            print(f"  ESPN {espn_id} <-> Odds {g['odds_api_event_id'][:12]}  {g['away']}@{g['home']}")

    # 4) Pull props for each Odds API event
    all_rows = []
    credits_remaining = None
    for oid, meta in odds_map.items():
        # Build a minimal event dict so to_dk_rows can use it
        e = {"id": oid, "commence_time": meta["commence_utc"],
             "away_team": meta["away_canon"], "home_team": meta["home_canon"]}
        # Attach espn_event_id from canonical if matched
        for g in canonical.values():
            if g.get("odds_api_event_id") == oid:
                e["_espn_event_id"] = g["espn_event_id"]
                break
        payload, status, remaining = pull_event_props(oid)
        credits_remaining = remaining
        if status != 200:
            print(f"  ! {oid[:12]}  status={status}  {payload if isinstance(payload, dict) else ''}")
            continue
        rows = to_dk_rows(e, payload)
        print(f"  {oid[:12]}  {meta['away_canon']}@{meta['home_canon']}  -> {len(rows)} DK rows")
        all_rows.extend(rows)

    # 5) Persist
    raw_path = out_dir / f"wnba_props_{today}_raw.json"
    csv_path = out_dir / f"wnba_props_{today}_dk.csv"
    raw_path.write_text(json.dumps({
        "pulled_at": now.isoformat(),
        "espn_slates": espn_slates,
        "odds_map": odds_map,
        "canonical_map": canonical,
        "dk_rows": all_rows,
        "credits_remaining_after": credits_remaining,
    }, indent=2))
    print(f"\nWrote: {raw_path}")

    if all_rows:
        with csv_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        print(f"Wrote: {csv_path}  ({len(all_rows)} DK prop rows)")
    else:
        print("(no DK rows — empty CSV)")

    print(f"\nOdds API credits remaining: {credits_remaining}")
    return all_rows


if __name__ == "__main__":
    main()
