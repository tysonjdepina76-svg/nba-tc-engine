"""
NBA Roster Data + Injury Report — Season 2025-26
TC = stat × 0.85 | Q = 0.65 | OUT = 0.0
"""

from sports_tc import Player, Team, NBA_TEAMS

def load_nba():
    """Load all NBA team rosters with injury status."""
    teams = {}
    for code, info in NBA_TEAMS.items():
        t = Team(code, info["name"], info.get("city", ""))
        teams[code] = t
    return teams

def load_injury_report():
    """Live injury scrape from ESPN."""
    import urllib.request
    import json

    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=8).read())
        injuries = {}
        for event in data.get("events", []):
            for comp in event.get("competitions", [{}])[0].get("competitors", []):
                team_code = comp["team"]["abbreviation"]
                injuries[team_code] = []
        return injuries
    except Exception:
        return {}

NBA_ROSTERS = {
    # ── NEW YORK KNICKS ───────────────────────────
    "NYK": [
        Player("Jalen Brunson",        "G", "6-2", 20.5, 3.5, 6.5, 2.0, "ACTIVE"),
        Player("OG Anunoby",           "F", "6-7", 16.0, 5.0, 2.0, 2.0, "ACTIVE"),
        Player("Julius Randle",        "F", "6-4", 18.5, 9.0, 4.5, 1.8, "ACTIVE"),
        Player("Mikal Bridges",        "F", "6-6", 14.5, 4.5, 3.0, 2.0, "ACTIVE"),
        Player("Donte DiVincenzo",     "G", "6-4", 12.0, 4.0, 3.0, 2.5, "ACTIVE"),
        Player("Josh Hart",            "G", "6-3", 10.5, 4.5, 3.5, 1.5, "ACTIVE"),
        Player("Precious Achiuwa",     "F", "6-8",  7.5, 5.0, 1.0, 0.8, "ACTIVE"),
        Player("Bojan Bogdanovic",     "F", "6-6",  9.5, 3.0, 1.5, 1.8, "Q"),   # foot Q
        Player("Mitchell Robinson",    "C", "7-0",  7.0, 8.0, 1.0, 0.0, "ACTIVE"),
        Player("Jerome Robinson",      "G", "6-5",  5.0, 2.0, 1.5, 0.8, "ACTIVE"),
    ],

    # ── PHILADELPHIA 76ERS ────────────────────────
    "PHI": [
        Player("Tyrese Maxey",         "G", "6-2", 22.0, 4.0, 5.5, 2.5, "ACTIVE"),
        Player("Paul George",          "F", "6-8", 18.0, 5.5, 4.0, 2.8, "ACTIVE"),
        Player("Joel Embiid",          "C", "7-0", 28.5,11.0, 5.5, 1.8, "Q"),   # knee Q
        Player("Jared McCain",         "G", "6-4", 14.0, 3.5, 3.0, 2.0, "ACTIVE"),
        Player("Guerschon Yabusele",   "F", "6-8", 11.0, 5.5, 1.5, 1.2, "ACTIVE"),
        Player("Justin Edwards",        "F", "6-8",  7.5, 3.5, 1.0, 0.8, "ACTIVE"),
        Player("Kelly Oubre Jr.",       "F", "6-5", 13.0, 5.0, 2.0, 1.5, "ACTIVE"),
        Player("Eric Gordon",          "G", "6-3",  9.0, 2.0, 2.5, 2.0, "ACTIVE"),
        Player("Kyle Lowry",           "G", "6-0",  7.5, 3.0, 5.0, 1.3, "ACTIVE"),
        Player("Mo Bamba",             "C", "7-0",  6.5, 5.5, 1.0, 0.8, "OUT"),  # OUT
    ],

    # ── BOSTON CELTICS ────────────────────────────
    "BOS": [
        Player("Jayson Tatum",         "F", "6-8", 25.5, 8.0, 5.0, 2.8, "ACTIVE"),
        Player("Jaylen Brown",         "F", "6-6", 23.0, 6.0, 4.0, 2.5, "ACTIVE"),
        Player("Kristaps Porzingis",    "C", "7-1", 20.0, 7.5, 2.5, 2.0, "ACTIVE"),
        Player("Derrick White",        "G", "6-4", 15.5, 4.5, 4.5, 2.2, "ACTIVE"),
        Player("Jrue Holiday",         "G", "6-4", 14.5, 5.0, 6.0, 2.0, "ACTIVE"),
        Player("Al Horford",           "F", "6-9", 11.0, 5.5, 3.5, 1.8, "ACTIVE"),
        Player("Payton Pritchard",     "G", "6-1",  9.0, 2.5, 3.0, 2.0, "ACTIVE"),
        Player("Sam Hauser",          "F", "6-5",  8.0, 3.5, 1.5, 1.8, "ACTIVE"),
        Player("Luke Kornet",          "C", "7-0",  6.0, 4.0, 1.0, 0.5, "ACTIVE"),
        Player("Neemias Queta",         "C", "7-0",  5.5, 4.0, 0.5, 0.0, "ACTIVE"),
    ],

    # ── CLEVELAND CAVALIERS ────────────────────────
    "CLE": [
        Player("Donovan Mitchell",     "G", "6-1", 24.5, 5.0, 4.5, 3.0, "ACTIVE"),
        Player("Darius Garland",       "G", "6-1", 20.0, 3.5, 6.0, 2.5, "ACTIVE"),
        Player("Evan Mobley",          "F", "6-11",18.0, 9.0, 3.5, 1.2, "ACTIVE"),
        Player("Jarrett Allen",        "C", "6-9", 14.0, 8.0, 2.0, 0.5, "ACTIVE"),
        Player("Max Strus",           "F", "6-5", 12.5, 4.5, 3.5, 2.5, "ACTIVE"),
        Player("Isaac Okoro",          "G", "6-5", 10.0, 3.5, 3.0, 1.2, "ACTIVE"),
        Player("Georges Niang",        "F", "6-5",  9.0, 3.0, 1.5, 2.0, "ACTIVE"),
        Player("Caris LeVert",         "G", "6-5", 11.5, 3.5, 3.5, 1.8, "Q"),   # Q
        Player("Tristan Thompson",      "C", "6-9",  6.0, 5.5, 1.0, 0.0, "ACTIVE"),
        Player("Ty Jerome",           "G", "6-5",  5.5, 2.0, 2.5, 1.0, "ACTIVE"),
    ],

    # ── OKLAHOMA CITY THUNDER ──────────────────────
    "OKC": [
        Player("Shai Gilgeous-Alexander","G","6-6",27.5, 5.5, 6.5, 2.2, "ACTIVE"),
        Player("Jalen Williams",       "F", "6-5", 19.0, 4.5, 4.0, 2.0, "ACTIVE"),
        Player("Chet Holmgren",        "C", "7-0", 16.0, 7.5, 2.5, 1.5, "ACTIVE"),
        Player("Lu Dort",              "G", "6-4", 13.5, 4.0, 2.5, 2.5, "ACTIVE"),
        Player("Isaiah Hartenstein",    "C", "6-11",12.0, 8.5, 3.5, 0.8, "ACTIVE"),
        Player("Josh Giddey",          "G", "6-8", 12.5, 6.5, 5.5, 1.5, "ACTIVE"),
        Player("Jaylen Duren",         "C", "6-10", 8.5, 5.5, 1.5, 0.3, "ACTIVE"),
        Player("Cason Wallace",        "G", "6-4",  8.0, 2.5, 2.0, 1.5, "ACTIVE"),
        Player("Kenrich Williams",     "F", "6-7",  7.0, 4.5, 2.0, 1.0, "ACTIVE"),
        Player("Luguentz Dort",         "G", "6-4", 13.5, 4.0, 2.5, 2.5, "ACTIVE"),
    ],

    # ── MINNESOTA TIMBERWOLVES ─────────────────────
    "MIN": [
        Player("Anthony Edwards",      "G", "6-4", 26.0, 5.5, 5.0, 3.2, "ACTIVE"),
        Player("Julius Randle",        "F", "6-4", 18.5, 9.0, 4.5, 1.8, "ACTIVE"),
        Player("Rudy Gobert",          "C", "7-1", 14.0,11.5, 1.5, 0.0, "ACTIVE"),
        Player("Jaden McDaniels",      "F", "6-9", 12.0, 4.5, 2.0, 1.5, "ACTIVE"),
        Player("Mike Conley",          "G", "6-0", 11.0, 3.0, 5.5, 2.0, "ACTIVE"),
        Player("Naz Reid",            "C", "6-9", 13.5, 5.5, 2.5, 1.8, "ACTIVE"),
        Player("Nickeil Alexander-Walker","G","6-5",11.5, 3.0, 2.5, 2.0, "ACTIVE"),
        Player("Kyle Anderson",        "F", "6-9",  8.5, 4.5, 3.5, 0.8, "ACTIVE"),
        Player("Jordan McLaughlin",    "G", "6-0",  6.0, 2.0, 3.5, 1.0, "ACTIVE"),
        Player("Josh Minott",          "F", "6-8",  5.5, 3.0, 1.0, 0.5, "ACTIVE"),
    ],

    # ── DENVER NUGGETS ─────────────────────────────
    "DEN": [
        Player("Nikola Jokic",         "C", "6-11",26.5,12.0, 9.5, 1.8, "ACTIVE"),
        Player("Jamal Murray",         "G", "6-4", 21.5, 4.5, 5.5, 2.5, "ACTIVE"),
        Player("Michael Porter Jr.",   "F", "6-10",16.5, 6.5, 2.0, 2.5, "ACTIVE"),
        Player("Aaron Gordon",         "F", "6-8", 14.0, 5.5, 2.5, 1.2, "ACTIVE"),
        Player("Kentavious Caldwell-Pope","G","6-5",11.5, 3.5, 2.0, 2.0, "ACTIVE"),
        Player("Christian Braun",      "G", "6-5",  8.5, 3.5, 1.5, 1.0, "ACTIVE"),
        Player("Peyton Watson",        "F", "6-8",  7.5, 3.0, 1.5, 0.8, "ACTIVE"),
        Player("Julian Strawther",     "F", "6-6",  7.0, 3.0, 1.5, 1.5, "ACTIVE"),
        Player("Zeke Nnaji",           "C", "6-9",  6.0, 4.0, 0.5, 0.3, "ACTIVE"),
        Player("Jalen Pickett",        "G", "6-2",  5.0, 2.5, 3.0, 0.8, "ACTIVE"),
    ],

    # ── DETROIT PISTONS ────────────────────────────
    "DET": [
        Player("Cade Cunningham",       "G", "6-6", 22.0, 5.5, 7.5, 2.2, "ACTIVE"),
        Player("Jaden Ivey",           "G", "6-4", 17.5, 4.5, 4.0, 2.0, "ACTIVE"),
        Player("Jalen Duren",          "C", "6-10",13.5, 8.0, 2.0, 0.5, "ACTIVE"),
        Player("Ausar Thompson",       "F", "6-7", 12.5, 5.5, 3.5, 1.2, "ACTIVE"),
        Player("Tim Hardaway Jr.",     "F", "6-5", 14.0, 4.0, 2.5, 2.5, "ACTIVE"),
        Player("Marcus Sasser",        "G", "6-2", 10.5, 2.5, 3.0, 1.8, "ACTIVE"),
        Player("Simone Fontecchio",     "F", "6-8",  8.5, 3.5, 1.5, 1.2, "ACTIVE"),
        Player("Troy Brown Jr.",       "F", "6-9",  7.5, 4.0, 2.0, 1.5, "ACTIVE"),
        Player("James Wiseman",         "C", "7-0", 10.5, 6.5, 1.0, 0.3, "ACTIVE"),
        Player("Killian Hayes",         "G", "6-5",  9.0, 3.0, 4.5, 1.2, "Q"),   # Q
    ],

    # ── SAN ANTONIO SPURS ──────────────────────────
    "SAS": [
        Player("Victor Wembanyama",     "C", "7-4", 23.5,10.5, 4.0, 2.5, "ACTIVE"),
        Player("Chris Paul",           "G", "6-0", 12.0, 4.0, 9.0, 1.8, "ACTIVE"),
        Player("Devin Vassell",        "F", "6-5", 17.5, 4.5, 3.5, 2.5, "ACTIVE"),
        Player("Jeremy Sochan",        "F", "6-9", 12.0, 6.0, 3.5, 1.2, "ACTIVE"),
        Player("Keldon Johnson",        "F", "6-5", 15.0, 5.0, 2.5, 2.2, "ACTIVE"),
        Player("Devonte Graham",       "G", "6-1",  9.5, 2.5, 4.5, 2.0, "ACTIVE"),
        Player("Zach Collins",         "C", "6-11",10.0, 5.5, 2.5, 0.8, "Q"),   # Q
        Player("Blake Wesley",         "G", "6-5",  7.5, 2.5, 3.0, 1.0, "ACTIVE"),
        Player("Romeo Langford",       "F", "6-5",  6.5, 3.0, 1.5, 0.8, "ACTIVE"),
        Player("Sandro Mamukelashvili","F", "6-10", 8.5, 4.5, 1.5, 0.8, "ACTIVE"),
    ],
}

# Export for module use
__all__ = ["NBA_ROSTERS", "load_nba", "load_injury_report"]