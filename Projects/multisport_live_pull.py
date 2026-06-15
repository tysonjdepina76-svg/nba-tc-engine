#!/usr/bin/env python3
"""
Multi-Sport Live Props Pull — MLB, NHL, World Cup, NBA, NFL
Uses Odds API free-tier player prop markets per sport.

WNBA uses its own pull (wnba_props_live_pull.py) since the ESPN bridge is
WNBA-specific.

Sport-to-market map is calibrated for the Odds API free tier. Some sports
have NO player props on free tier (e.g., MLB) — those are skipped with a note.

Usage:
    python3 multisport_live_pull.py            # pull all active sports
    python3 multisport_live_pull.py --sport NBA WNBA  # override
"""
import os, sys, json, csv, argparse
import requests
from datetime import datetime, timezone
from pathlib import Path

# Load secrets
_sec = Path("/root/.zo/secrets.env")
if _sec.exists():
    for _line in _sec.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE = "https://api.the-odds-api.com/v4"

# Sport config: (odds_api_key, prop_markets_or_None_if_unsupported)
SPORT_CONFIG = {
    "NBA":   ("basketball_nba",   ["player_points", "player_rebounds", "player_assists", "player_threes", "player_points_rebounds_assists", "player_points_rebounds", "player_points_assists", "player_rebounds_assists", "player_blocks", "player_steals", "player_turnovers"]),
    "WNBA":  ("basketball_wnba",  ["player_points", "player_rebounds", "player_assists", "player_threes", "player_points_rebounds_assists", "player_points_rebounds", "player_points_assists", "player_rebounds_assists", "player_blocks", "player_steals", "player_turnovers"]),
    "NHL":   ("icehockey_nhl",    ["player_points", "player_assists", "player_shots", "player_shots_on_goal", "player_goals", "player_total_saves", "player_power_play_points", "player_blocked_shots"]),
    "NFL":   ("americanfootball_nfl", ["player_pass_yards", "player_pass_tds", "player_pass_completions", "player_pass_attempts", "player_rush_yards", "player_receptions", "player_reception_yards", "player_reception_tds", "player_anytime_td"]),
    "MLB":   ("baseball_mlb",     None),  # Free tier has no MLB player props
    "WORLD CUP": ("soccer_fifa_world_cup", ["player_goals_scored", "player_shots", "player_shots_on_target", "player_assists"]),
    "MLS":   ("soccer_usa_mls",   ["player_goals_scored", "player_shots", "player_shots_on_target", "player_assists"]),
}

SPORT_BOOKS = {
    "NBA":   ("draftkings",),                    # DK primary
    "WNBA":  ("draftkings", "fanduel", "betrivers"),
    "NHL":   ("draftkings", "fanduel"),
    "NFL":   ("draftkings", "fanduel", "betmgm"),  # FD is primary for NFL
    "MLB":   ("draftkings",),                    # no props on free tier anyway
    "WORLD CUP": ("fanduel",),                   # DK doesn't carry WC props on free tier
    "MLS":   ("fanduel", "draftkings"),
}

CACHE_ROOT = Path("/home/workspace/Daily_Log/live_props/_cache")
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
CACHE_TTL_MIN = int(os.environ.get("MULTISPORT_CACHE_TTL_MIN", "60"))


def get_events(sport_key):
    r = requests.get(f"{BASE}/sports/{sport_key}/events", params={"apiKey": API_KEY, "dateFormat": "iso"}, timeout=15)
    if not r.ok:
        return [], r.status_code
    return r.json(), 200


def get_event_props(sport_key, event_id, markets, regions="us"):
    r = requests.get(
        f"{BASE}/sports/{sport_key}/events/{event_id}/odds",
        params={"apiKey": API_KEY, "regions": regions, "markets": ",".join(markets), "oddsFormat": "american", "dateFormat": "iso"},
        timeout=20,
    )
    return r


def to_rows(event, payload, book_filter="draftkings"):
    rows = []
    commence = event.get("commence_time")
    odds_eid = event.get("id")
    for bk in payload.get("bookmakers", []):
        if book_filter and bk.get("key") != book_filter:
            continue
        for mkt in bk.get("markets", []):
            for oc in mkt.get("outcomes", []):
                rows.append({
                    "odds_event_id": odds_eid,
                    "commence": commence,
                    "away_team": event.get("away_team", ""),
                    "home_team": event.get("home_team", ""),
                    "book": bk.get("key"),
                    "stat": mkt.get("key"),
                    "player": oc.get("description", ""),
                    "direction": oc.get("name", ""),
                    "line": oc.get("point"),
                    "odds": oc.get("price"),
                })
    return rows


def pull_sport(sport, out_dir, target_books=("draftkings",)):
    cfg = SPORT_CONFIG.get(sport)
    if not cfg:
        return {"sport": sport, "error": "unknown sport"}
    sport_key, markets = cfg
    events, status = get_events(sport_key)
    result = {"sport": sport, "sport_key": sport_key, "events": len(events), "status": status, "rows": 0, "rows_by_book": {}}
    if status != 200 or not events:
        result["skip"] = "no events"
        return result
    if not markets:
        result["skip"] = "no player-prop markets on free tier"
        return result
    all_rows = []
    credits_remaining = None
    for ev in events:
        r = get_event_props(sport_key, ev["id"], markets)
        credits_remaining = r.headers.get("x-requests-remaining")
        if not r.ok:
            continue
        for book in target_books:
            rows = to_rows(ev, r.json(), book_filter=book)
            all_rows.extend(rows)
    result["rows"] = len(all_rows)
    result["rows_by_book"] = {b: sum(1 for row in all_rows if row["book"] == b) for b in target_books}
    result["credits_remaining"] = credits_remaining
    if all_rows:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = out_dir / f"live_props_{sport}_{today}.csv"
        with out_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        result["path"] = str(out_path)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", nargs="*", default=None)
    args = ap.parse_args()
    sports = args.sport or list(SPORT_CONFIG.keys())
    out_dir = Path("/home/workspace/Daily_Log/live_props")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== Multi-Sport Live Props Pull — {datetime.now(timezone.utc).isoformat()} ===")
    results = []
    for s in sports:
        print(f"\n[{s}]")
        books = SPORT_BOOKS.get(s, ("draftkings",))
        r = pull_sport(s, out_dir, target_books=books)
        results.append(r)
        for k, v in r.items():
            print(f"  {k}: {v}")
    # Persist summary
    summary_path = out_dir / f"summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    summary_path.write_text(json.dumps(results, indent=2))
    print(f"\nSummary: {summary_path}")


if __name__ == "__main__":
    main()
