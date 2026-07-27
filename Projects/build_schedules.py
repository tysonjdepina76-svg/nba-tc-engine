#!/usr/bin/env python3
"""Build hardwired sports schedules with full phase/milestone metadata for dashboard display.
   Uses statsapi for MLB; generates realistic skeleton schedules for WNBA, NFL, NHL.
   NBA and World Cup are off-season/complete placeholders."""

import json, os, sys, random
from datetime import date, datetime, timedelta

OUT = "/home/workspace/data/schedules"
os.makedirs(OUT, exist_ok=True)
rng = random.Random(42)

def write_sport(key, data):
    path = os.path.join(OUT, f"{key}_schedule.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    gc = len(data.get("games", []))
    pc = len(data.get("phases", {}))
    print(f"  ✅ {key}: {gc} games, {pc} phases → {path}")

def key_dates(phases, key):
    """Extract key milestones for summary display."""
    for pk, pd in phases.items():
        if "milestones" not in pd:
            pd["milestones"] = []
        for m in pd.get("rounds", []):
            pd["milestones"].append({"label": m.get("round", m.get("label","")), "date": m.get("start", m.get("date","")), "note": m.get("note","")})
        # clean up
        for m in list(pd.get("milestones", [])):
            if not m.get("label"):
                pd["milestones"].remove(m)

def build_mlb():
    print("MLB 2026...")
    games = []
    has_live = False
    try:
        import statsapi
        games_data = statsapi.schedule(start_date="2026-03-19", end_date="2026-10-04")
        for g in games_data:
            games.append({
                "id": g.get("game_id", ""),
                "date": str(g.get("game_date", "")),
                "time": str(g.get("game_datetime", "")),
                "status": str(g.get("status", "")),
                "home": str(g.get("home_name", "")),
                "away": str(g.get("away_name", "")),
                "home_score": g.get("home_score", None),
                "away_score": g.get("away_score", None),
                "venue": str(g.get("venue_name", "")),
            })
        has_live = True
        print(f"  statsapi: {len(games)} games")
    except Exception as e:
        print(f"  statsapi failed: {e}")

    phases = {
        "preseason": {"label": "Spring Training", "start": "2026-02-20", "end": "2026-03-23",
                      "milestones": [{"label": "Spring Training Starts", "date": "2026-02-20"}]},
        "regular_season": {"label": "Regular Season", "start": "2026-03-26", "end": "2026-09-27", "games": 162,
                           "milestones": [
                               {"label": "Opening Day", "date": "2026-03-26"},
                               {"label": "All-Star Break", "date": "2026-07-13", "note": "Midseason"},
                               {"label": "Trade Deadline", "date": "2026-07-30"},
                               {"label": "Regular Season Ends", "date": "2026-09-27"},
                           ]},
        "postseason": {"label": "Postseason", "start": "2026-10-01", "end": "2026-11-04",
                       "rounds": [
                           {"round": "Wild Card Series", "format": "Best of 3", "start": "2026-10-01"},
                           {"round": "Division Series", "format": "Best of 5", "start": "2026-10-05"},
                           {"round": "League Championship", "format": "Best of 7", "start": "2026-10-15"},
                           {"round": "World Series", "format": "Best of 7", "start": "2026-10-25"},
                       ]},
    }
    key_dates(phases, "mlb")
    data = {"sport": "MLB", "season": "2026", "phases": phases, "game_count": len(games),
            "games": games, "source": "statsapi" if has_live else "hardwired",
            "built": str(datetime.now())}
    write_sport("mlb", data)
    return True

def build_wnba():
    print("WNBA 2026...")
    teams = [
        ("ATL","Atlanta Dream"),("CHI","Chicago Sky"),("CON","Connecticut Sun"),
        ("DAL","Dallas Wings"),("IND","Indiana Fever"),("LVA","Las Vegas Aces"),
        ("LAS","Los Angeles Sparks"),("MIN","Minnesota Lynx"),("NYL","New York Liberty"),
        ("PHO","Phoenix Mercury"),("SEA","Seattle Storm"),("WAS","Washington Mystics"),
    ]
    season_start = date(2026, 5, 15)
    season_end = date(2026, 9, 13)
    days = []
    d = season_start
    while d <= season_end:
        if d.weekday() in (2,4,5,6):  # Wed, Fri, Sat, Sun
            days.append(d)
        d += timedelta(days=1)
    games = []
    for i, t1 in enumerate(teams):
        for t2 in teams[i+1:]:
            for _ in range(4):
                gday = rng.choice(days)
                games.append({"date": str(gday), "home": t1[1], "home_abbr": t1[0],
                              "away": t2[1], "away_abbr": t2[0], "status": "SCHEDULED"})
    games.sort(key=lambda g: g["date"])

    phases = {
        "regular_season": {"label": "Regular Season", "start": "2026-05-15", "end": "2026-09-13",
                           "milestones": [
                               {"label": "Opening Day", "date": "2026-05-15"},
                               {"label": "All-Star Game", "date": "2026-07-18", "note": "Phoenix, AZ"},
                               {"label": "Regular Season Ends", "date": "2026-09-13"},
                           ]},
        "playoffs": {"label": "Playoffs", "start": "2026-09-20", "end": "2026-10-20",
                     "rounds": [
                         {"round": "First Round", "format": "Best of 3", "start": "2026-09-20"},
                         {"round": "Semifinals", "format": "Best of 5", "start": "2026-09-28"},
                         {"round": "WNBA Finals", "format": "Best of 5", "start": "2026-10-11"},
                     ]},
    }
    key_dates(phases, "wnba")
    data = {"sport": "WNBA", "season": "2026", "phases": phases, "game_count": len(games),
            "games": games, "source": "hardwired skeleton", "built": str(datetime.now())}
    write_sport("wnba", data)
    return True

def build_nfl():
    print("NFL 2026...")
    games = []
    # NFL 2026: Preseason Aug 13-29, Season Sep 10 - Jan 3, Playoffs Jan 9 - Feb 14
    conferences = {"AFC": ["BUF","MIA","NE","NYJ","BAL","CIN","CLE","PIT","HOU","IND","JAX","TEN","DEN","KC","LAC","LV"],
                   "NFC": ["DAL","NYG","PHI","WAS","CHI","DET","GB","MIN","ATL","CAR","NO","TB","ARI","LAR","SEA","SF"]}
    all_teams = [(abbr, abbr) for conf in conferences.values() for abbr in conf]
    full_names = {a: a for a, _ in all_teams}

    # Preseason: 3 weeks, Thu-Mon, each team ~3 games
    ps_start = date(2026, 8, 13)
    ps_end = date(2026, 8, 31)
    ps_days = []
    d = ps_start
    while d <= ps_end:
        if d.weekday() in (3,4,5,6,0):  # Thu, Fri, Sat, Sun, Mon
            ps_days.append(d)
        d += timedelta(days=1)
    for i in range(48):  # ~16 games/week × 3 weeks
        t1, t2 = rng.sample(all_teams, 2)
        gday = rng.choice(ps_days)
        games.append({"date": str(gday), "home": t1[1], "home_abbr": t1[0],
                      "away": t2[1], "away_abbr": t2[0], "status": "SCHEDULED", "phase": "PRESEASON"})
    # Regular season: 17 weeks, each team plays 17 games
    reg_start = date(2026, 9, 10)
    reg_end = date(2027, 1, 3)
    reg_days = []
    d = reg_start
    while d <= reg_end:
        if d.weekday() in (0,3,4,6):  # Sun, Thu, Mon, Sun
            reg_days.append(d)
        d += timedelta(days=1)
    for i in range(272):  # 16 games × 17 weeks
        t1, t2 = rng.sample(all_teams, 2)
        gday = rng.choice(reg_days)
        games.append({"date": str(gday), "home": t1[1], "home_abbr": t1[0],
                      "away": t2[1], "away_abbr": t2[0], "status": "SCHEDULED", "phase": "REGULAR"})
    # Playoffs: Wild Card, Divisional, Championship, Super Bowl
    for rnd, rstart, rlabel in [("Wild Card", "2027-01-09", "WILD_CARD"),
                                 ("Divisional", "2027-01-16", "DIVISIONAL"),
                                 ("Championship", "2027-01-23", "CHAMPIONSHIP"),
                                 ("Super Bowl", "2027-02-14", "SUPER_BOWL")]:
        rday = date.fromisoformat(rstart)
        games.append({"date": str(rday), "round": rnd, "home": "TBD", "home_abbr": "TBD",
                      "away": "TBD", "away_abbr": "TBD", "status": "TBD", "phase": "PLAYOFFS"})

    games.sort(key=lambda g: g["date"])
    phases = {
        "preseason": {"label": "Preseason", "start": "2026-08-13", "end": "2026-08-29",
                      "milestones": [{"label": "Hall of Fame Game", "date": "2026-08-06", "note": "Canton, OH"},
                                     {"label": "Preseason Week 1", "date": "2026-08-13"}]},
        "regular_season": {"label": "Regular Season", "start": "2026-09-10", "end": "2027-01-03", "games": 272,
                           "milestones": [
                               {"label": "Opening Night", "date": "2026-09-10"},
                               {"label": "Thanksgiving Games", "date": "2026-11-26"},
                               {"label": "Week 18 - Final", "date": "2027-01-03"},
                           ]},
        "playoffs": {"label": "Playoffs", "start": "2027-01-09", "end": "2027-02-14",
                     "rounds": [
                         {"round": "Wild Card Weekend", "format": "6 games", "start": "2027-01-09"},
                         {"round": "Divisional Round", "format": "4 games", "start": "2027-01-16"},
                         {"round": "Championship Sunday", "format": "2 games", "start": "2027-01-23"},
                         {"round": "Super Bowl LXI", "format": "SoFi Stadium", "start": "2027-02-14", "note": "Inglewood, CA"},
                     ]},
    }
    key_dates(phases, "nfl")
    data = {"sport": "NFL", "season": "2026", "phases": phases, "game_count": len(games),
            "games": games, "source": "hardwired skeleton", "built": str(datetime.now())}
    write_sport("nfl", data)
    return True

def build_nhl():
    print("NHL 2026-27...")
    teams = [
        ("BOS","Boston Bruins"),("BUF","Buffalo Sabres"),("DET","Detroit Red Wings"),("FLA","Florida Panthers"),
        ("MTL","Montreal Canadiens"),("OTT","Ottawa Senators"),("TB","Tampa Bay Lightning"),("TOR","Toronto Maple Leafs"),
        ("CAR","Carolina Hurricanes"),("CBJ","Columbus Blue Jackets"),("NJ","New Jersey Devils"),("NYI","New York Islanders"),
        ("NYR","New York Rangers"),("PHI","Philadelphia Flyers"),("PIT","Pittsburgh Penguins"),("WAS","Washington Capitals"),
        ("CHI","Chicago Blackhawks"),("COL","Colorado Avalanche"),("DAL","Dallas Stars"),("MIN","Minnesota Wild"),
        ("NSH","Nashville Predators"),("STL","St. Louis Blues"),("UTA","Utah HC"),("WPG","Winnipeg Jets"),
        ("ANA","Anaheim Ducks"),("CGY","Calgary Flames"),("EDM","Edmonton Oilers"),("LA","Los Angeles Kings"),
        ("SJ","San Jose Sharks"),("SEA","Seattle Kraken"),("VAN","Vancouver Canucks"),("VGK","Vegas Golden Knights"),
    ]
    season_start = date(2026, 10, 7)
    season_end = date(2027, 4, 13)
    days = []
    d = season_start
    while d <= season_end:
        if d.weekday() in (1,2,4,5,6):  # Tue, Wed, Fri, Sat, Sun
            days.append(d)
        d += timedelta(days=1)
    games = []
    for i, t1 in enumerate(teams):
        for t2 in teams[i+1:]:
            n_games = 4 if i % 7 < 3 else 3  # division rivals: 4, others: 3
            for _ in range(n_games):
                gday = rng.choice(days)
                games.append({"date": str(gday), "home": t1[1], "home_abbr": t1[0],
                              "away": t2[1], "away_abbr": t2[0], "status": "SCHEDULED"})
    games.sort(key=lambda g: g["date"])
    phases = {
        "regular_season": {"label": "Regular Season", "start": "2026-10-07", "end": "2027-04-13", "games": 1312,
                           "milestones": [
                               {"label": "Opening Night", "date": "2026-10-07"},
                               {"label": "Winter Classic", "date": "2027-01-01", "note": "Outdoor"},
                               {"label": "All-Star Weekend", "date": "2027-02-06"},
                               {"label": "Regular Season Ends", "date": "2027-04-13"},
                           ]},
        "playoffs": {"label": "Stanley Cup Playoffs", "start": "2027-04-18", "end": "2027-06-15",
                     "rounds": [
                         {"round": "First Round", "format": "Best of 7", "start": "2027-04-18"},
                         {"round": "Second Round", "format": "Best of 7", "start": "2027-05-02"},
                         {"round": "Conference Finals", "format": "Best of 7", "start": "2027-05-18"},
                         {"round": "Stanley Cup Final", "format": "Best of 7", "start": "2027-06-02"},
                     ]},
    }
    key_dates(phases, "nhl")
    data = {"sport": "NHL", "season": "2026-27", "phases": phases, "game_count": len(games),
            "games": games, "source": "hardwired skeleton", "built": str(datetime.now())}
    write_sport("nhl", data)
    return True

def build_nba():
    print("NBA 2026-27 (off-season)...")
    phases = {
        "offseason": {"label": "Offseason", "start": "2026-06-20", "end": "2026-10-01",
                      "milestones": [
                          {"label": "NBA Draft", "date": "2026-06-24"},
                          {"label": "Free Agency Opens", "date": "2026-06-30"},
                          {"label": "Summer League", "date": "2026-07-11", "note": "Las Vegas"},
                          {"label": "Training Camps", "date": "2026-09-28"},
                      ]},
        "preseason": {"label": "Preseason", "start": "2026-10-02", "end": "2026-10-18"},
        "regular_season": {"label": "Regular Season", "start": "2026-10-20", "end": "2027-04-11", "games": 2460,
                           "milestones": [
                               {"label": "Opening Night", "date": "2026-10-20"},
                               {"label": "Christmas Day Games", "date": "2026-12-25"},
                               {"label": "All-Star Weekend", "date": "2027-02-20"},
                               {"label": "Regular Season Ends", "date": "2027-04-11"},
                           ]},
        "playoffs": {"label": "Playoffs", "start": "2027-04-15", "end": "2027-06-20",
                     "rounds": [
                         {"round": "Play-In Tournament", "format": "1-2 games", "start": "2027-04-15"},
                         {"round": "First Round", "format": "Best of 7", "start": "2027-04-18"},
                         {"round": "Conference Semis", "format": "Best of 7", "start": "2027-05-04"},
                         {"round": "Conference Finals", "format": "Best of 7", "start": "2027-05-20"},
                         {"round": "NBA Finals", "format": "Best of 7", "start": "2027-06-05"},
                     ]},
    }
    key_dates(phases, "nba")
    data = {"sport": "NBA", "season": "2026-27", "phases": phases, "game_count": 0,
            "games": [], "source": "off-season placeholder", "built": str(datetime.now())}
    write_sport("nba", data)
    return True

def build_wc():
    print("World Cup 2026 (completed)...")
    phases = {
        "group_stage": {"completed": True, "label": "Group Stage", "start": "2026-06-11", "end": "2026-06-26",
                        "milestones": [
                            {"label": "Opening Match", "date": "2026-06-11", "note": "Mexico City"},
                            {"label": "USA vs TBD", "date": "2026-06-12", "note": "Los Angeles"},
                        ]},
        "round_of_16": {"completed": True, "label": "Round of 16", "start": "2026-06-28", "end": "2026-07-02"},
        "quarterfinal": {"completed": True, "label": "Quarterfinals", "start": "2026-07-04", "end": "2026-07-05"},
        "semifinal": {"completed": True, "label": "Semifinals", "start": "2026-07-08", "end": "2026-07-09"},
        "final": {"completed": True, "label": "FINAL", "start": "2026-07-13",
                  "milestones": [{"label": "World Cup Final", "date": "2026-07-13", "note": "MetLife Stadium, NJ"}]},
    }
    key_dates(phases, "wc")
    data = {"sport": "WORLD CUP", "season": "2026", "phases": phases, "game_count": 0,
            "games": [], "source": "completed tournament", "built": str(datetime.now())}
    write_sport("wc", data)
    return True

if __name__ == "__main__":
    print("🏆 TC SPORTS SCHEDULE BUILDER\n")
    results = {}
    for name, fn in [("mlb", build_mlb), ("wnba", build_wnba), ("nfl", build_nfl),
                     ("nhl", build_nhl), ("nba", build_nba), ("wc", build_wc)]:
        try:
            results[name] = "OK" if fn() else "FAIL"
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            results[name] = f"ERROR: {e}"
    print(f"\n✅ SCHEDULE BUILD COMPLETE: {results}")
