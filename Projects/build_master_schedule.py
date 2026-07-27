#!/usr/bin/env python3
"""
Build consolidated schedules_master.json from individual sports schedule files.
Output: /home/workspace/data/schedules/schedules_master.json

Each sport gets: status, current_phase, key_dates, today_games, upcoming_games (7 days),
and a summary of all phases.
"""
import json
import sys
from datetime import datetime, date, timedelta

SPORTS = {
    "mlb": {
        "file": "/home/workspace/data/schedules/mlb_schedule.json",
        "status": "LIVE",
        "current_phase": "Regular Season",
        "season": "2026",
    },
    "wnba": {
        "file": "/home/workspace/data/schedules/wnba_schedule.json",
        "status": "LIVE",
        "current_phase": "Regular Season",
        "season": "2026",
    },
    "nba": {
        "file": "/home/workspace/data/schedules/nba_schedule.json",
        "status": "OFF-SEASON",
        "current_phase": "Off-Season",
        "season": "2026-27",
    },
    "nfl": {
        "file": "/home/workspace/data/schedules/nfl_schedule.json",
        "status": "PRE-SEASON",
        "current_phase": "Pre-Season",
        "season": "2026-27",
    },
    "nhl": {
        "file": "/home/workspace/data/schedules/nhl_schedule.json",
        "status": "OFF-SEASON",
        "current_phase": "Off-Season",
        "season": "2026-27",
    },
    "wc": {
        "file": "/home/workspace/data/schedules/wc_schedule.json",
        "status": "ENDED",
        "current_phase": "Tournament Complete",
        "season": "2026",
    },
}

KEY_DATES = {
    "mlb": {
        "regular_season": {"start": "2026-03-26", "end": "2026-09-28"},
        "wildcard": {"start": "2026-09-30", "end": "2026-10-03"},
        "division_series": {"start": "2026-10-05", "end": "2026-10-12"},
        "championship_series": {"start": "2026-10-14", "end": "2026-10-22"},
        "world_series": {"start": "2026-10-24", "end": "2026-11-01"},
        "all_star_game": "2026-07-14",
        "trade_deadline": "2026-08-01",
    },
    "wnba": {
        "regular_season": {"start": "2026-05-15", "end": "2026-09-13"},
        "all_star_game": "2026-07-18",
        "playoffs_round1": {"start": "2026-09-20", "end": "2026-09-27"},
        "semifinals": {"start": "2026-09-28", "end": "2026-10-08"},
        "finals": {"start": "2026-10-11", "end": "2026-10-20"},
    },
    "nba": {
        "draft": "2026-06-25",
        "free_agency": "2026-07-01",
        "summer_league": {"start": "2026-07-07", "end": "2026-07-17"},
        "training_camp": {"start": "2026-09-29", "end": "2026-10-02"},
        "preseason": {"start": "2026-10-03", "end": "2026-10-19"},
        "regular_season": {"start": "2026-10-20", "end": "2027-04-11"},
        "play_in": {"start": "2027-04-13", "end": "2027-04-16"},
        "playoffs": {"start": "2027-04-17", "end": "2027-06-01"},
        "nba_finals": {"start": "2027-06-03", "end": "2027-06-20"},
        "draft_2027": "2027-06-24",
    },
    "nfl": {
        "hall_of_fame_game": "2026-08-06",
        "preseason": {"start": "2026-08-06", "end": "2026-08-30"},
        "regular_season": {"start": "2026-09-10", "end": "2027-01-03"},
        "wild_card": {"start": "2027-01-09", "end": "2027-01-11"},
        "divisional": {"start": "2027-01-16", "end": "2027-01-17"},
        "championship": "2027-01-24",
        "pro_bowl": "2027-01-31",
        "super_bowl": "2027-02-07",
        "combine": {"start": "2027-02-23", "end": "2027-03-01"},
    },
    "nhl": {
        "draft": "2026-06-26",
        "free_agency": "2026-07-01",
        "training_camp": {"start": "2026-09-18", "end": "2026-09-30"},
        "preseason": {"start": "2026-09-21", "end": "2026-10-03"},
        "regular_season": {"start": "2026-10-06", "end": "2027-04-15"},
        "stanley_cup_playoffs": {"start": "2027-04-17", "end": "2027-06-15"},
        "stanley_cup_final": {"start": "2027-05-29", "end": "2027-06-15"},
        "draft_2027": "2027-06-25",
    },
    "wc": {
        "group_stage": {"start": "2026-06-11", "end": "2026-06-27"},
        "round_of_16": {"start": "2026-06-29", "end": "2026-07-03"},
        "quarterfinals": {"start": "2026-07-04", "end": "2026-07-08"},
        "semifinals": {"start": "2026-07-11", "end": "2026-07-12"},
        "final": "2026-07-17",
        "tournament_complete": "2026-07-17",
    },
}

TODAY = date.today()
TODAY_STR = TODAY.isoformat()
UPCOMING_END = TODAY + timedelta(days=7)


def load_schedule(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"  WARNING: Could not load {path}: {e}", file=sys.stderr)
        return None


def extract_games_for_dates(games_list, start_date, end_date):
    if not games_list:
        return []
    result = []
    start_s = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
    end_s = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
    for g in games_list:
        gd = g.get("date", "")
        if start_s <= gd <= end_s:
            result.append({
                "date": gd,
                "away": g.get("away", ""),
                "home": g.get("home", ""),
                "venue": g.get("venue", ""),
                "time_et": g.get("time_et", g.get("time", "")),
                "phase": g.get("phase", ""),
            })
    return result


def is_game_live_today(g):
    gd = g.get("date", "")
    return gd == TODAY_STR


def extract_phases_summary(data):
    phases = data.get("phases", data.get("phases_schedule", []))
    if isinstance(phases, dict):
        summary = {}
        for pk, pv in phases.items():
            games_val = pv.get("games", 0)
            if isinstance(games_val, int):
                gc = games_val
            elif isinstance(games_val, list):
                gc = len(games_val)
            else:
                gc = 0
            summary[pk] = {
                "label": pv.get("label", pk),
                "start": pv.get("start", ""),
                "end": pv.get("end", ""),
                "game_count": gc,
            }
        return summary
    elif isinstance(phases, list):
        return [{"phase": p} for p in phases]
    return []


def build():
    master = {
        "generated": datetime.now().isoformat(),
        "generated_et": datetime.now().strftime("%Y-%m-%d %H:%M:%S ET"),
        "today": TODAY_STR,
        "active_sports": ["mlb", "wnba"],
        "offseason_sports": ["nba", "nhl"],
        "preseason_sports": ["nfl"],
        "ended_sports": ["wc"],
        "sports": {},
    }

    for sport, config in SPORTS.items():
        print(f"Processing {sport.upper()}...")
        data = load_schedule(config["file"])

        sport_data = {
            "status": config["status"],
            "current_phase": config["current_phase"],
            "season": config["season"],
            "key_dates": KEY_DATES.get(sport, {}),
            "today_games": [],
            "upcoming_games": [],
            "today_game_count": 0,
            "total_scheduled_games": 0,
        }

        if data:
            games = data.get("games", [])
            sport_data["total_scheduled_games"] = len(games)

            # Extract phases
            sport_data["phases"] = extract_phases_summary(data)

            # Today's games
            today_games = extract_games_for_dates(games, TODAY_STR, TODAY_STR)
            sport_data["today_games"] = today_games
            sport_data["today_game_count"] = len(today_games)

            # Upcoming 7 days
            upcoming = extract_games_for_dates(games, TODAY_STR, UPCOMING_END.isoformat())
            sport_data["upcoming_games"] = upcoming
            sport_data["upcoming_game_count"] = len(upcoming)

            # Next game date (if any upcoming)
            if upcoming:
                sport_data["next_game"] = upcoming[0]["date"]
            else:
                sport_data["next_game"] = None

            # Search for next game further out if nothing in 7 days
            if not upcoming and games:
                for g in games:
                    if g.get("date", "") > UPCOMING_END.isoformat():
                        sport_data["next_game"] = g.get("date", "")
                        break

        # For off-season / ended sports without game data
        if sport in ("nba", "wc"):
            if sport == "nba":
                sport_data["next_game"] = "2026-10-03"  # Preseason
                sport_data["next_phase"] = "Preseason: 2026-10-03"
            elif sport == "wc":
                sport_data["next_game"] = None
                sport_data["next_phase"] = "Tournament ended 2026-07-17"

        elif sport == "nhl":
            sport_data["next_game"] = "2026-09-21"  # Preseason
            sport_data["next_phase"] = "Preseason: 2026-09-21"

        elif sport == "nfl":
            sport_data["next_game"] = "2026-08-06"  # Hall of Fame Game
            sport_data["next_phase"] = "Hall of Fame Game: 2026-08-06"

        master["sports"][sport] = sport_data

    # Summary counts
    total_today = sum(s["today_game_count"] for s in master["sports"].values())
    master["total_games_today"] = total_today

    return master


if __name__ == "__main__":
    master = build()
    output_path = "/home/workspace/data/schedules/schedules_master.json"
    with open(output_path, "w") as f:
        json.dump(master, f, indent=2, default=str)

    print(f"\n✅ Master schedule written to {output_path}")
    print(f"   Total games today: {master['total_games_today']}")
    for sport, s in master["sports"].items():
        print(f"   {sport.upper()}: {s['status']} | {s['today_game_count']} today | {s['total_scheduled_games']} total | next: {s.get('next_game', 'N/A')}")
