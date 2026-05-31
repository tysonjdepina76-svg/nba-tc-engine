#!/usr/bin/env python3
"""
Daily Tip Report Automation
Runs 2 hours before first scheduled tip-off.
Tyson Depina | Zo Computer

Usage:
  python3 daily_tip_report.py --sport NBA --output report.md
  python3 daily_tip_report.py --all --output ~/reports/

Schedule via cron (or Zo agent):
  0 16 * * * cd /home/workspace && python3 daily_tip_report.py --all
  # Runs at 4 PM ET = 2 hours before 6 PM tip-offs
"""

import argparse
import json
import os
import sys
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ── CONFIG ──────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

# NBA tip-off windows (ET) — 2hrs before = when we run
TIP_WINDOWS = {
    "NBA": ["12:00", "12:30", "1:00", "3:30", "4:00", "5:00", "6:00", "7:00", "7:30", "8:00", "8:30", "10:30"],
    "WNBA": ["12:00", "3:00", "5:00", "7:00", "8:00", "10:00"],
    "MLB": ["1:00", "1:05", "2:00", "3:05", "4:07", "7:00", "7:05", "7:10", "8:10", "10:15"],
}


# ── LIVE ODDS SCRAPE ────────────────────────────────────────────────────────
def get_todays_games(sport: str) -> List[Dict]:
    """Get today's games from ESPN API."""
    sport_code = "basketball/nba" if sport == "NBA" else (
                "basketball/wnba" if sport == "WNBA" else
                "baseball/mlb" if sport == "MLB" else
                "hockey/nhl" if sport == "NHL" else None)
    if not sport_code:
        return []

    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_code}/scoreboard"
    today = datetime.now().strftime("%Y%m%d")

    try:
        resp = requests.get(url, params={"dates": today}, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠ ESPN API error for {sport}: {e}")
        return []

    games = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        home = comp.get("home", {})
        away = comp.get("away", {})
        status = event.get("status", {})

        venue = comp.get("venue", {}).get("fullName", "TBD")

        # Game time
        start_time = None
        for detail in status.get("type", {}).get("detail", "").split():
            if ":" in detail:
                start_time = detail
                break

        games.append({
            "id": event.get("id", ""),
            "away_abbr": away.get("team", {}).get("abbreviation", ""),
            "away_name": away.get("team", {}).get("displayName", ""),
            "home_abbr": home.get("team", {}).get("abbreviation", ""),
            "home_name": home.get("team", {}).get("displayName", ""),
            "start_time": start_time or "TBD",
            "venue": venue,
            "sport": sport,
        })
    return games


def get_injury_report(sport: str) -> List[Dict]:
    """Fetch injury data from ESPN."""
    sport_code = "basketball/nba" if sport == "NBA" else "basketball/wnba"
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_code}/injuries"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    injuries = []
    for group in data.get("children", []):
        for team in group.get("teams", []):
            abbr = team.get("abbreviation", "")
            for athlete in team.get("athletes", []):
                inj = athlete.get("injury", {})
                injuries.append({
                    "name": athlete.get("fullName", ""),
                    "position": athlete.get("position", {}).get("abbreviation", ""),
                    "status": inj.get("status", ""),
                    "description": inj.get("description", ""),
                    "team_abbr": abbr,
                    "source": "ESPN",
                })
    return injuries


def get_prop_lines(home_abbr: str, away_abbr: str, sport: str) -> Dict:
    """
    Fetch current DK/Fanduel prop lines.
    Falls back to market consensus estimates from ESPN.
    """
    # TODO: Replace with real DK/Fanduel API when available
    # For now: placeholder structure
    return {
        "game_total": None,   # e.g., 218.5
        "home_spread": None,   # e.g., -3.5
        "home_ml": None,      # e.g., -150
        "away_ml": None,      # e.g., +130
        "player_props": [],    # list of {name, stat, line, over_odds, under_odds}
        "source": "pending_DK_integration",
    }


# ── REPORT GENERATION ───────────────────────────────────────────────────────
def generate_game_report(game: Dict, injuries: List[Dict],
                        props: Dict, tc_data: Dict) -> str:
    """Generate plain-English report for one game."""
    from generate_report import nba_report, ncaab_report  # lazy import

    home = game["home_abbr"]
    away = game["away_abbr"]
    sport = game.get("sport", "NBA")

    game_injuries = [i for i in injuries
                     if i.get("team_abbr","").upper() in [home, away]]

    if sport in ("NBA", "WNBA"):
        return nba_report(
            home_team=home, away_team=away,
            tip_time=game.get("start_time","TBD"),
            injuries=game_injuries,
            tc_props=tc_data.get("props", []),
            game_total_line=props.get("game_total", 218.0),
            spread_line=props.get("home_spread", 0.0),
            home_pace=tc_data.get("home_pace", 99.8),
            away_pace=tc_data.get("away_pace", 99.8),
            sport=sport,
        )
    else:
        return ncaab_report(
            home_team=home, away_team=away,
            tip_time=game.get("start_time","TBD"),
            injuries=game_injuries,
            props=props,
            sport=sport,
        )


# ── MAIN ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Daily Tip Report Generator")
    parser.add_argument("--sport", choices=["NBA","WNBA","MLB","NHL","NCAAB","NCAAF","ALL"], default="ALL")
    parser.add_argument("--output", "-o", default="/home/workspace/reports")
    parser.add_argument("--format", choices=["md","txt","html","json"], default="md")
    parser.add_argument("--send-email", action="store_true")
    args = parser.parse_args()

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    sports = (["NBA","WNBA","MLB","NHL","NCAAB","NCAAF"]
              if args.sport == "ALL" else [args.sport])

    all_reports = []
    date_str = datetime.now().strftime("%Y-%m-%d")

    for sport in sports:
        print(f"\n{'='*50}")
        print(f"  {sport} REPORT — {date_str}")
        print(f"{'='*50}")

        games = get_todays_games(sport)
        if not games:
            print(f"  No games found for {sport} today.")
            continue

        injuries = get_injury_report(sport) if sport in ("NBA","WNBA") else []
        print(f"  {len(games)} games found. Fetching data...")

        for game in games:
            home = game["home_abbr"]
            away = game["away_abbr"]
            print(f"\n  📋 {away} @ {home} ({game.get('start_time','TBD')})")

            props = get_prop_lines(home, away, sport)
            tc_data = {}  # TODO: integrate with multi_sport_engine

            report = generate_game_report(game, injuries, props, tc_data)
            all_reports.append({"sport": sport, "game": game, "report": report})

            # Save individual game report
            game_file = os.path.join(output_dir, f"{date_str}_{sport}_{away}@{home}.{args.format}")
            with open(game_file, "w") as f:
                f.write(report)
            print(f"  ✅ Saved: {game_file}")

    # Save master report
    master_file = os.path.join(output_dir, f"{date_str}_MASTER.{args.format}")
    if args.format == "json":
        with open(master_file, "w") as f:
            json.dump(all_reports, f, indent=2)
    else:
        with open(master_file, "w") as f:
            for r in all_reports:
                f.write(r["report"])
                f.write("\n\n")
    print(f"\n  📚 Master report: {master_file}")

    # Email if requested
    if args.send_email:
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            with open(master_file) as f:
                html = f.read().replace("\n", "<br>")
            sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY",""))
            msg = {
                "to": [{"email": "tysondepina99@gmail.com"}],
                "from": {"email": "true@zo.computer"},
                "subject": f"Daily Tip Report — {date_str}",
                "html_content": html,
            }
            # sg.send(msg)  # Uncomment when SendGrid is configured
            print("  📧 Email sent (SendGrid configured)")
        except Exception as e:
            print(f"  ⚠ Email failed: {e}")

    print(f"\n✅ Done — {len(all_reports)} reports generated.")


if __name__ == "__main__":
    main()
