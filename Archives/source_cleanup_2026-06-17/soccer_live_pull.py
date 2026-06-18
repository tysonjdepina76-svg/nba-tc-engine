#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
Soccer Live Pull — game lines for all active soccer leagues on Odds API.

Free tier returns h2h / spreads / totals across 49 books (DK, FD, BetMGM, BetRivers,
Fanatics, WilliamHill, PaddyPower, Pinnacle, etc.). Player props (goals/assists/shots)
are 422 on free tier — that requires the paid plan.

Caching:
- Events list and per-event lines are cached on disk under
  /home/workspace/Daily_Log/soccer/_cache/{sport_key}/{event_id}/markets.json
- TTL is SOCCER_CACHE_TTL_MIN (default 30 min). On subsequent calls within the TTL,
  we serve from cache with zero Odds API credits used.
- This is critical because every full pull costs ~1 credit per event — without cache
  we'd burn the 13.6k remaining monthly budget in ~2 days of 5x-daily runs.

Outputs (per run):
  - /home/workspace/Daily_Log/soccer/YYYY-MM-DD/events.json   (event list)
  - /home/workspace/Daily_Log/soccer/YYYY-MM-DD/lines.json    (game lines per event)
  - /home/workspace/Daily_Log/soccer/YYYY-MM-DD/summary.json  (run summary)
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
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

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE = "https://api.the-odds-api.com/v4"
CACHE_ROOT = Path("/home/workspace/Daily_Log/soccer/_cache")
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

# Confirmed active soccer keys from the /sports endpoint (2026-06-15 audit)
SOCCER_KEYS = [
    "soccer_fifa_world_cup",
    "soccer_conmebol_copa_libertadores",
    "soccer_conmebol_copa_sudamericana",
    "soccer_brazil_serie_b",
    "soccer_china_superleague",
    "soccer_germany_dfb_pokal",
    "soccer_league_of_ireland",
    "soccer_norway_eliteserien",
    "soccer_spain_segunda_division",
    "soccer_sweden_allsvenskan",
    "soccer_sweden_superettan",
]

# Leagues where we pull full game lines (rest are event-list only to save credits)
LINE_SPORTS = [
    "soccer_fifa_world_cup",
    "soccer_conmebol_copa_libertadores",
    "soccer_conmebol_copa_sudamericana",
    "soccer_brazil_serie_b",
    "soccer_germany_dfb_pokal",
    "soccer_sweden_allsvenskan",
]

GAME_MARKETS = "h2h,spreads,totals"
PRIMARY_BOOKS = ("draftkings", "fanduel", "betmgm", "betrivers", "fanatics", "williamhill")

CACHE_TTL_MIN = int(os.environ.get("SOCCER_CACHE_TTL_MIN", "30"))


def _cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_min = (time.time() - path.stat().st_mtime) / 60
    return age_min < CACHE_TTL_MIN


def fetch_events_cached(sport_key: str) -> tuple:
    """Returns (events_list, from_cache_bool, http_status)."""
    cache_file = CACHE_ROOT / sport_key / "events.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    if _cache_fresh(cache_file):
        return json.loads(cache_file.read_text()), True, 200
    try:
        r = requests.get(
            f"{BASE}/sports/{sport_key}/events",
            params={"apiKey": ODDS_API_KEY, "dateFormat": "iso"},
            timeout=15,
        )
    except Exception as e:
        return [], False, -1
    if not r.ok:
        return [], False, r.status_code
    events = r.json()
    cache_file.write_text(json.dumps(events, indent=2))
    return events, False, r.status_code


def fetch_lines_cached(sport_key: str, event_id: str, markets: str = GAME_MARKETS) -> tuple:
    """Returns (payload, from_cache_bool, status, credits_remaining)."""
    cache_file = CACHE_ROOT / sport_key / event_id / f"{markets.replace(',', '_')}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    if _cache_fresh(cache_file):
        return json.loads(cache_file.read_text()), True, 200, None
    try:
        r = requests.get(
            f"{BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "us,eu,uk",
                "markets": markets,
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
            timeout=20,
        )
    except Exception:
        return None, False, -1, None
    if not r.ok:
        return None, False, r.status_code, r.headers.get("x-requests-remaining")
    payload = r.json()
    cache_file.write_text(json.dumps(payload, indent=2))
    return payload, False, r.status_code, r.headers.get("x-requests-remaining")


def extract_primary_book_lines(event_payload):
    """Build per-book/per-market summary from an event odds payload."""
    out = {}
    for bk in (event_payload or {}).get("bookmakers", []):
        key = bk.get("key", "")
        if key not in PRIMARY_BOOKS:
            continue
        for mkt in bk.get("markets", []):
            market_key = mkt.get("key", "")
            out.setdefault(key, {})[market_key] = [
                {"name": o.get("name"), "price": o.get("price"), "point": o.get("point")}
                for o in mkt.get("outcomes", [])
            ]
    return out


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = Path(f"/home/workspace/Daily_Log/soccer/{today}")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== Soccer Live Pull — {today}  (cache TTL: {CACHE_TTL_MIN}min) ===\n")

    all_events = {}
    per_league = []
    for sport in SOCCER_KEYS:
        events, from_cache, status = fetch_events_cached(sport)
        all_events[sport] = events
        per_league.append({
            "sport_key": sport,
            "events": len(events),
            "from_cache": from_cache,
            "status": status,
        })
        print(f"[{sport}]  events={len(events)}  cached={'Y' if from_cache else 'N'}  status={status}")

    events_path = out_dir / "events.json"
    events_path.write_text(json.dumps(all_events, indent=2))

    # Pull game lines for top leagues (uses cache for re-runs within TTL)
    all_lines = {}
    total_cached = 0
    total_fresh = 0
    credits_remaining = None
    for sport in LINE_SPORTS:
        events = all_events.get(sport, [])
        if not events:
            continue
        league_lines = {}
        for ev in events:
            payload, from_cache, status, rem = fetch_lines_cached(sport, ev["id"])
            if rem:
                credits_remaining = rem
            if status != 200 or not payload:
                continue
            if from_cache:
                total_cached += 1
            else:
                total_fresh += 1
            league_lines[ev["id"]] = {
                "commence": ev.get("commence_time"),
                "matchup": f"{ev.get('away_team','')} @ {ev.get('home_team','')}",
                "primary_books": extract_primary_book_lines(payload),
                "from_cache": from_cache,
            }
        all_lines[sport] = league_lines
        fresh_note = f"{total_fresh} fresh + {total_cached} cached" if league_lines else "0"
        print(f"  {sport}: {len(league_lines)} events pulled ({fresh_note} so far)")

    lines_path = out_dir / "lines.json"
    lines_path.write_text(json.dumps(all_lines, indent=2))

    summary = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "cache_ttl_min": CACHE_TTL_MIN,
        "leagues_monitored": len(SOCCER_KEYS),
        "leagues_with_lines": len(LINE_SPORTS),
        "events_total": sum(r["events"] for r in per_league),
        "lines_fresh": total_fresh,
        "lines_cached": total_cached,
        "credits_remaining_last": credits_remaining,
        "per_league": per_league,
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"\nWrote: {events_path}")
    print(f"Wrote: {lines_path}")
    print(f"Wrote: {summary_path}")
    print(f"\nTotals: {summary['events_total']} events | {total_fresh} fresh + {total_cached} cached lines")
    print(f"Odds API credits remaining: {credits_remaining}")
    return summary


if __name__ == "__main__":
    main()
