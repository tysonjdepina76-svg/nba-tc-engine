"""
Multi-Sport Schedule Service - Hardwired + Live Hybrid
Covers: MLB, WNBA, NBA, NHL, NFL, World Cup
Phase: Regular + Playoffs + Pre-season per sport
"""

import json
import time
import datetime
import urllib.request
from pathlib import Path

DATA_DIR = Path("/home/workspace/data/schedules")
DATA_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL = {
    "mlb_live": 3600,
    "wnba_live": 3600,
    "hardwired": 86400,
}

# ═════════════════════════════════════════════════
# HARDWIRED SEASON STRUCTURES
# ═════════════════════════════════════════════════

HARDWIRED = {
    "MLB": {
        "season": "2026",
        "status": "REGULAR",
        "regular_start": "2026-04-01",
        "regular_end": "2026-09-27",
        "all_star_break": "2026-07-13",
        "playoffs_start": "2026-10-06",
        "world_series": "2026-10-23",
        "world_series_end": "2026-11-01",
        "total_games": 162,
        "teams": 30,
        "conference_structure": {"AL": ["East", "Central", "West"], "NL": ["East", "Central", "West"]},
        "key_dates": [
            {"label": "Opening Day", "date": "2026-04-01"},
            {"label": "All-Star Game", "date": "2026-07-14"},
            {"label": "Trade Deadline", "date": "2026-08-01"},
            {"label": "Regular Season Ends", "date": "2026-09-27"},
            {"label": "Wild Card Round", "date": "2026-10-06"},
            {"label": "Division Series", "date": "2026-10-10"},
            {"label": "League Championship Series", "date": "2026-10-17"},
            {"label": "World Series Game 1", "date": "2026-10-23"},
            {"label": "World Series Game 7", "date": "2026-11-01"},
        ],
    },
    "WNBA": {
        "season": "2026",
        "status": "REGULAR",
        "regular_start": "2026-05-15",
        "regular_end": "2026-09-13",
        "all_star_break": "2026-07-26",
        "playoffs_start": "2026-09-17",
        "finals_start": "2026-10-04",
        "finals_end": "2026-10-18",
        "total_games": 44,
        "teams": 12,
        "conference_structure": {"East": 6, "West": 6},
        "key_dates": [
            {"label": "Opening Night", "date": "2026-05-15"},
            {"label": "Commissioner's Cup Championship", "date": "2026-07-01"},
            {"label": "All-Star Game (AT&T WNBA All-Star 2026)", "date": "2026-07-26"},
            {"label": "Regular Season Ends", "date": "2026-09-13"},
            {"label": "Playoffs Round 1", "date": "2026-09-17"},
            {"label": "Semifinals", "date": "2026-09-24"},
            {"label": "WNBA Finals Game 1", "date": "2026-10-04"},
            {"label": "WNBA Finals Game 5 (if nec)", "date": "2026-10-18"},
        ],
    },
    "NBA": {
        "season": "2026-27",
        "status": "OFF-SEASON",
        "regular_start": "2026-10-20",
        "regular_end": "2027-04-11",
        "play_in": "2027-04-13",
        "playoffs_start": "2027-04-17",
        "finals_start": "2027-06-03",
        "finals_end": "2027-06-20",
        "draft": "2026-06-25",
        "total_games": 82,
        "teams": 30,
        "conference_structure": {"East": 15, "West": 15},
        "key_dates": [
            {"label": "NBA Draft 2026", "date": "2026-06-25"},
            {"label": "Summer League", "date": "2026-07-07"},
            {"label": "Free Agency Begins", "date": "2026-07-01"},
            {"label": "Training Camp Opens", "date": "2026-09-26"},
            {"label": "Preseason Begins", "date": "2026-10-04"},
            {"label": "Regular Season Tip-Off", "date": "2026-10-20"},
            {"label": "Christmas Day Games", "date": "2026-12-25"},
            {"label": "MLK Day Games", "date": "2027-01-18"},
            {"label": "All-Star Weekend", "date": "2027-02-19"},
            {"label": "Trade Deadline", "date": "2027-02-11"},
            {"label": "Regular Season Ends", "date": "2027-04-11"},
            {"label": "Play-In Tournament", "date": "2027-04-13"},
            {"label": "Playoffs Start", "date": "2027-04-17"},
            {"label": "NBA Finals Game 1", "date": "2027-06-03"},
            {"label": "NBA Finals Game 7 (if nec)", "date": "2027-06-20"},
        ],
    },
    "NHL": {
        "season": "2026-27",
        "status": "OFF-SEASON",
        "regular_start": "2026-10-07",
        "regular_end": "2027-04-14",
        "playoffs_start": "2027-04-19",
        "stanley_cup_start": "2027-05-29",
        "stanley_cup_end": "2027-06-15",
        "total_games": 82,
        "teams": 32,
        "conference_structure": {"East": ["Atlantic", "Metropolitan"], "West": ["Central", "Pacific"]},
        "key_dates": [
            {"label": "NHL Draft 2026", "date": "2026-06-26"},
            {"label": "Free Agency Opens", "date": "2026-07-01"},
            {"label": "Rookie Camps", "date": "2026-09-15"},
            {"label": "Preseason Begins", "date": "2026-09-22"},
            {"label": "Regular Season Opens", "date": "2026-10-07"},
            {"label": "Winter Classic", "date": "2027-01-01"},
            {"label": "All-Star Weekend", "date": "2027-02-06"},
            {"label": "Trade Deadline", "date": "2027-03-05"},
            {"label": "Regular Season Ends", "date": "2027-04-14"},
            {"label": "Stanley Cup Playoffs Start", "date": "2027-04-19"},
            {"label": "Stanley Cup Final Game 1", "date": "2027-05-29"},
            {"label": "Stanley Cup Final Game 7 (if nec)", "date": "2027-06-15"},
        ],
    },
    "NFL": {
        "season": "2026",
        "status": "PRE-SEASON",
        "preseason_start": "2026-08-06",
        "preseason_end": "2026-08-30",
        "regular_start": "2026-09-10",
        "regular_end": "2027-01-03",
        "playoffs_start": "2027-01-09",
        "super_bowl": "2027-02-07",
        "total_games": 17,
        "teams": 32,
        "conference_structure": {"AFC": ["East", "North", "South", "West"], "NFC": ["East", "North", "South", "West"]},
        "key_dates": [
            {"label": "Hall of Fame Game", "date": "2026-08-06"},
            {"label": "Preseason Week 1", "date": "2026-08-13"},
            {"label": "Roster Cut to 53", "date": "2026-09-01"},
            {"label": "Kickoff Game (Chiefs host)", "date": "2026-09-10"},
            {"label": "Week 1 Sunday", "date": "2026-09-13"},
            {"label": "Thanksgiving Games", "date": "2026-11-26"},
            {"label": "Week 18 (Final)", "date": "2027-01-03"},
            {"label": "Wild Card Weekend", "date": "2027-01-09"},
            {"label": "Divisional Round", "date": "2027-01-16"},
            {"label": "Conference Championships", "date": "2027-01-24"},
            {"label": "Pro Bowl", "date": "2027-01-31"},
            {"label": "Super Bowl LXI", "date": "2027-02-07"},
        ],
    },
    "WC": {
        "season": "2026",
        "status": "COMPLETED",
        "start": "2026-06-11",
        "end": "2026-07-19",
        "teams": 48,
        "hosts": ["United States", "Canada", "Mexico"],
        "key_dates": [
            {"label": "Opening Match", "date": "2026-06-11"},
            {"label": "Group Stage Ends", "date": "2026-06-27"},
            {"label": "Round of 32", "date": "2026-06-28"},
            {"label": "Round of 16", "date": "2026-07-05"},
            {"label": "Quarterfinals", "date": "2026-07-09"},
            {"label": "Semifinals", "date": "2026-07-13"},
            {"label": "Third Place Match", "date": "2026-07-18"},
            {"label": "Final (MetLife Stadium)", "date": "2026-07-19"},
        ],
    },
}

# ═════════════════════════════════════════════════
# LIVE SCHEDULE FETCHERS
# ═════════════════════════════════════════════════

def _fetch_mlb_live(days=7):
    """Fetch MLB games from statsapi for next N days."""
    cache_file = DATA_DIR / "mlb_live_cache.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if time.time() - data.get("_ts", 0) < CACHE_TTL["mlb_live"]:
                return data.get("games", [])
        except:
            pass

    today = datetime.date.today()
    games = []
    if days <= 1:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=team,linescore,decisions"
    else:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={today}&endDate={today+datetime.timedelta(days=days)}&hydrate=team,linescore"

    try:
        r = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read())
        for d in data.get("dates", []):
            for g in d.get("games", []):
                status = g["status"]["detailedState"]
                games.append({
                    "date": g["officialDate"],
                    "home": g["teams"]["home"]["team"]["name"],
                    "home_abbr": g["teams"]["home"]["team"]["abbreviation"],
                    "away": g["teams"]["away"]["team"]["name"],
                    "away_abbr": g["teams"]["away"]["team"]["abbreviation"],
                    "time_utc": g.get("gameDate", ""),
                    "time_et": _utc_to_et(g.get("gameDate", "")),
                    "status": status,
                    "venue": g.get("venue", {}).get("name", ""),
                    "home_score": g.get("teams", {}).get("home", {}).get("score", 0),
                    "away_score": g.get("teams", {}).get("away", {}).get("score", 0),
                    "is_live": status == "In Progress",
                    "is_final": status == "Final",
                    "double_header": g.get("doubleHeader", "N"),
                    "game_num": g.get("gameNumber", 1),
                })
        cache_file.write_text(json.dumps({"_ts": time.time(), "games": games}))
    except Exception as e:
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text()).get("games", [])
            except:
                pass
    return games


def _fetch_wnba_live():
    """Fetch upcoming WNBA games from ESPN."""
    cache_file = DATA_DIR / "wnba_live_cache.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if time.time() - data.get("_ts", 0) < CACHE_TTL["wnba_live"]:
                return data.get("games", [])
        except:
            pass

    games = []
    try:
        url = "http://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
        r = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read())
        for e in data.get("events", []):
            comps = e.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [{}, {}])
            home = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
            away = competitors[1] if competitors[0].get("homeAway") == "home" else competitors[0]
            status = e["status"]["type"]["name"]
            games.append({
                "date": e["date"],
                "home": home.get("team", {}).get("displayName", ""),
                "home_abbr": home.get("team", {}).get("abbreviation", ""),
                "away": away.get("team", {}).get("displayName", ""),
                "away_abbr": away.get("team", {}).get("abbreviation", ""),
                "home_score": home.get("score", "0"),
                "away_score": away.get("score", "0"),
                "status": status,
                "period": e["status"].get("period", 0),
                "clock": e["status"].get("displayClock", ""),
                "is_live": status == "STATUS_IN_PROGRESS",
                "is_final": status == "STATUS_FINAL",
            })
        cache_file.write_text(json.dumps({"_ts": time.time(), "games": games}))
    except:
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text()).get("games", [])
            except:
                pass
    return games


def _utc_to_et(utc_str):
    """Convert UTC timestamp string to ET string."""
    if not utc_str:
        return ""
    try:
        from datetime import datetime as dt, timezone, timedelta
        t = dt.fromisoformat(utc_str.replace("Z", "+00:00"))
        et = t - timedelta(hours=4)
        return et.strftime("%Y-%m-%d %H:%M ET")
    except:
        return utc_str


# ═════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════

def get_all_schedules():
    """Return hardwired season info for all sports + live games for active sports."""
    result = {}

    for sport in ["MLB", "WNBA", "NBA", "NHL", "NFL", "WC"]:
        hw = dict(HARDWIRED[sport])
        result[sport] = hw

    # Inject live games for active sports
    try:
        result["MLB"]["live_games"] = _fetch_mlb_live(days=1)
    except:
        result["MLB"]["live_games"] = []
    try:
        result["WNBA"]["live_games"] = _fetch_wnba_live()
    except:
        result["WNBA"]["live_games"] = []

    result["_generated"] = datetime.datetime.now().isoformat()
    return result


def get_sport_schedule(sport):
    """Get schedule for a single sport."""
    sport = sport.upper()
    if sport not in HARDWIRED:
        return None

    result = dict(HARDWIRED[sport])

    if sport == "MLB":
        try:
            result["live_games"] = _fetch_mlb_live(days=1)
        except:
            result["live_games"] = []
    elif sport == "WNBA":
        try:
            result["live_games"] = _fetch_wnba_live()
        except:
            result["live_games"] = []

    result["_generated"] = datetime.datetime.now().isoformat()
    return result


def get_upcoming_key_dates(sport, limit=5):
    """Return the next N key dates for a sport."""
    sport = sport.upper()
    if sport not in HARDWIRED:
        return []

    today = datetime.date.today().isoformat()
    dates = HARDWIRED[sport].get("key_dates", [])
    upcoming = [d for d in dates if d["date"] >= today]
    return upcoming[:limit]


def get_todays_games(sport=None):
    """Return today's games for sport(s)."""
    today = datetime.date.today().isoformat()
    if sport:
        sport = sport.upper()
        if sport == "MLB":
            all_games = _fetch_mlb_live(days=1)
        elif sport == "WNBA":
            all_games = _fetch_wnba_live()
        else:
            return []
        return [g for g in all_games if g.get("date") == today]
    else:
        result = {}
        try:
            mlb = [g for g in _fetch_mlb_live(days=1) if g.get("date") == today]
            result["MLB"] = mlb
        except:
            result["MLB"] = []
        try:
            wnba = [g for g in _fetch_wnba_live() if g.get("date")[:10] == today]
            result["WNBA"] = wnba
        except:
            result["WNBA"] = []
        return result


def get_next_n_games(sport, n=5):
    """Return next N games for a sport."""
    sport = sport.upper()
    if sport == "MLB":
        games = _fetch_mlb_live(days=14)
    elif sport == "WNBA":
        games = _fetch_wnba_live()
    else:
        return []
    today = datetime.date.today().isoformat()
    upcoming = [g for g in games if g.get("date", "") >= today and not g.get("is_final")]
    return upcoming[:n]


if __name__ == "__main__":
    today = datetime.date.today().isoformat()
    print(f"Schedule Service — {today}")
    print("=" * 50)
    print()
    for s in ["MLB", "WNBA", "NBA", "NHL", "NFL", "WC"]:
        hw = HARDWIRED[s]
        print(f"  {s}: {hw['season']} — {hw['status']}")
        print(f"         Regular: {hw.get('regular_start', 'N/A')} → {hw.get('regular_end', 'N/A')}")
        if hw.get("playoffs_start"):
            print(f"         Playoffs: {hw['playoffs_start']}")
        print(f"         Key Upcoming:")
        for kd in get_upcoming_key_dates(s, 3):
            print(f"           {kd['date']}: {kd['label']}")
        print()
    print(f"  MLB Today: {len(get_todays_games('MLB'))} games")
    print(f"  WNBA Today: {len(get_todays_games('WNBA'))} games")
