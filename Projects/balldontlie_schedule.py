#!/usr/bin/env python3
"""
BallDontLie Schedule Diagnostic Tool
=====================================
Read-only diagnostic: fetches NBA/WNBA game schedules from balldontlie.io.
Produces NO props, NO projections, NO odds — just schedule listings.

The free tier allows 60 requests/minute without a key; add BALLDONTLIE_API_KEY
env var for higher rate limits (your $1/mo plan key goes in Settings > Advanced > Secrets).

Usage:
  python3 balldontlie_schedule.py               # today's NBA + WNBA games
  python3 balldontlie_schedule.py --sport WNBA   # WNBA only
  python3 balldontlie_schedule.py --date 2026-06-15  # specific date
  python3 balldontlie_schedule.py --week         # next 7 days
  python3 balldontlie_schedule.py --export md    # output as markdown

Output: prints to stdout; with --export writes to Daily_Log/YYYY-MM-DD/schedule_balldontlie.md
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
import urllib3
urllib3.disable_warnings()

API_KEY = os.environ.get("BALLDONTLIE_API_KEY", "")
BASE = "https://api.balldontlie.io/v1"
HEADERS = {"Authorization": API_KEY} if API_KEY else {}
HEADERS.setdefault("User-Agent", "TC-Pipeline/2.0")


def fetch_games(sport: str, date_str: str) -> list:
    league = sport.upper()
    
    # Determine season year
    year = int(date_str[:4])
    month = int(date_str[5:7])
    season = year if month >= 9 else year - 1
    
    # --- NBA ---
    if league == "NBA":
        url = f"{BASE}/games"
        params = {
            "seasons[]": season,
            "start_date": date_str,
            "end_date": date_str,
            "per_page": 100,
        }
        r = requests.get(url, params=params, headers=HEADERS if HEADERS else None, timeout=30, verify=False)
        if r.status_code == 401:
            print(f"⚠️  BallDontLie requires API key for NBA. Set BALLDONTLIE_API_KEY in secrets.", file=sys.stderr)
            return []
        r.raise_for_status()
        data = r.json()
        games = data.get("data", [])
        return games

    # --- WNBA ---
    elif league == "WNBA":
        # WNBA uses /v1/wnba/games
        url = f"{BASE}/wnba/games"
        params = {
            "seasons[]": season,
            "start_date": date_str,
            "end_date": date_str,
            "per_page": 100,
        }
        r = requests.get(url, params=params, headers=HEADERS if HEADERS else None, timeout=30, verify=False)
        if r.status_code in (401, 404):
            # WNBA endpoint may need a key or not exist on free tier
            print(f"⚠️  WNBA endpoint not available or requires key (HTTP {r.status_code})", file=sys.stderr)
            return []
        r.raise_for_status()
        data = r.json()
        games = data.get("data", [])
        return games

    else:
        print(f"❌ Unknown sport: {sport}", file=sys.stderr)
        return []


def format_game(g: dict, sport: str, date_str: str) -> dict:
    """Normalize BDL game dict into a flat schedule entry."""
    league = sport.upper()
    
    if league == "NBA":
        away = (g.get("visitor_team") or {}).get("abbreviation", "???")
        home = (g.get("home_team") or {}).get("abbreviation", "???")
        away_full = (g.get("visitor_team") or {}).get("full_name", away)
        home_full = (g.get("home_team") or {}).get("full_name", home)
        status = g.get("status", "Scheduled")
        venue = g.get("arena") or ""
        away_score = g.get("visitor_team_score")
        home_score = g.get("home_team_score")
        period = g.get("period")
        time_remaining = g.get("time") or ""
        tip_utc = g.get("datetime") or ""
    else:
        # WNBA response format
        away = (g.get("visitor_team") or {}).get("abbreviation", "???")
        home = (g.get("home_team") or {}).get("abbreviation", "???")
        away_full = (g.get("visitor_team") or {}).get("full_name", away)
        home_full = (g.get("home_team") or {}).get("full_name", home)
        status = g.get("status", "Scheduled")
        venue = g.get("arena") or ""
        away_score = g.get("visitor_team_score")
        home_score = g.get("home_team_score")
        period = g.get("period")
        time_remaining = g.get("time") or ""
        tip_utc = g.get("datetime") or ""

    # Convert tip time to ET
    tip_et = ""
    if tip_utc:
        try:
            dt = datetime.fromisoformat(tip_utc.replace("Z", "+00:00"))
            et = dt - timedelta(hours=4)
            tip_et = et.strftime("%I:%M %p ET")
        except Exception:
            tip_et = tip_utc

    # Score line if live/final
    score = ""
    if away_score is not None and home_score is not None:
        score = f"{away_score}-{home_score}"
        if period:
            score += f" ({status}{' Q'+str(period) if period else ''})"

    return {
        "away": away,
        "home": home,
        "away_full": away_full,
        "home_full": home_full,
        "status": status,
        "tip_et": tip_et,
        "venue": venue if venue else "TBD",
        "score": score,
        "time_remaining": time_remaining,
        "bdl_id": g.get("id"),
    }


def render_table(games: list) -> str:
    lines = []
    lines.append("| Away | Home | Tip (ET) | Status | Score | Venue |")
    lines.append("|------|------|----------|--------|-------|-------|")
    for g in games:
        lines.append(
            f"| {g['away']} | {g['home']} | {g['tip_et']} | {g['status']} | {g['score'] or '—'} | {g['venue']} |"
        )
    return "\n".join(lines)


def render_markdown(sport: str, date_str: str, games: list) -> str:
    md = []
    md.append(f"# {sport.upper()} Schedule — {date_str}")
    md.append(f"")
    md.append(f"_Source: BallDontLie API — diagnostic schedule only. No props, no projections._")
    md.append(f"")
    md.append(f"**Games: {len(games)}**")
    md.append("")
    if not games:
        md.append("No games found for this date. Possible causes:")
        md.append("- Off day in the {sport} schedule")
        md.append("- BallDontLie API key not configured (set BALLDONTLIE_API_KEY)")
        md.append("- Rate limit exceeded (free tier: 60 req/min)")
        return "\n".join(md)

    md.append(render_table(games))

    # Live/Recent games detail
    live = [g for g in games if g["status"] not in ("Scheduled", "Final")]
    if live:
        md.append("")
        md.append("### 🟢 Live / In Progress")
        for g in live:
            md.append(f"- **{g['away']} @ {g['home']}**: {g['score']} — {g['time_remaining']}")

    final = [g for g in games if g["status"] == "Final"]
    if final:
        md.append("")
        md.append("### 🏁 Final Scores")
        for g in final:
            md.append(f"- **{g['away']} @ {g['home']}**: {g['score']}")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="BallDontLie Schedule Diagnostic — NBA/WNBA schedules only, no props"
    )
    parser.add_argument("--sport", default="NBA,WNBA", help="NBA, WNBA, or both (default)")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date YYYY-MM-DD (default: today)")
    parser.add_argument("--week", action="store_true", help="Fetch next 7 days")
    parser.add_argument("--export", choices=["md", "json"], default="",
                        help="Export to Daily_Log/YYYY-MM-DD/")
    args = parser.parse_args()

    sports = [s.strip() for s in args.sport.split(",")]
    dates = []
    if args.week:
        base = datetime.strptime(args.date, "%Y-%m-%d")
        dates = [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    else:
        dates = [args.date]

    all_games = []
    for sport in sports:
        for d in dates:
            print(f"Fetching {sport} schedule for {d}...", file=sys.stderr)
            try:
                games = fetch_games(sport, d)
                formatted = [format_game(g, sport, d) for g in games]
                all_games.extend(formatted)
                print(f"  → {len(games)} games", file=sys.stderr)
            except Exception as e:
                print(f"  ❌ Error: {e}", file=sys.stderr)

    if not all_games:
        print("No games found. Check API key and date range.", file=sys.stderr)
        return

    # Print to stdout
    for sport in sports:
        sport_games = sorted(
            [g for g in all_games if g.get("bdl_id")],
            key=lambda g: g.get("tip_et", "Z")
        )
        if sport_games:
            print(f"\n{'='*60}")
            print(render_markdown(sport, dates[0], sport_games))

    # Export
    if args.export:
        log_dir = Path(f"/home/workspace/Daily_Log/{dates[0]}")
        log_dir.mkdir(parents=True, exist_ok=True)
        if args.export == "md":
            out_path = log_dir / "schedule_balldontlie.md"
            with open(out_path, "w") as f:
                for sport in sports:
                    sport_games = sorted(
                        [g for g in all_games if g.get("bdl_id")],
                        key=lambda g: g.get("tip_et", "Z")
                    )
                    f.write(render_markdown(sport, dates[0], sport_games))
                    f.write("\n\n")
            print(f"\n✅ Exported to {out_path}")
        elif args.export == "json":
            out_path = log_dir / "schedule_balldontlie.json"
            with open(out_path, "w") as f:
                json.dump(all_games, f, indent=2, default=str)
            print(f"\n✅ Exported to {out_path}")


if __name__ == "__main__":
    main()
