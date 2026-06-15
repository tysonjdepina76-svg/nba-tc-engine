#!/usr/bin/env python3
"""
Triple Conservative NBA Projections — v8 COMPREHENSIVE
======================================================
TC Formula:
  TC pts    = pts × 0.85  (Q = ×0.55, OUT = 0)
  TC reb    = reb × 0.85  (Q = ×0.55, OUT = 0)
  TC ast    = ast × 0.85  (Q = ×0.55, OUT = 0)
  TC 3pm    = 3pm × 0.85  (Q = ×0.55, OUT = 0)
  TC Total  = sum(TC pts) + bench bonus
  Line      = TC_total × 0.88  (rounded to nearest whole)
  Edge      = TC pts − Line

TV Match Multiplier: 0.78
  TC TV Pts = TC pts × 0.78
  TC TV Tot = TC pts + TC reb + TC ast + TC 3pm × 0.78
  Used to rate player/game-level TV-match excitement score

ENHANCED v8:
  - Fixed TV multiplier: 0.78 (was 0.88 in older versions)
  - Added LAL roster (Lakers in West Semifinals vs OKC)
  - Includes PTS/REB/AST/3PM per player + TV match score
  - Clutch player flag: players averaging >25 PPG get ★ marker
  - Closeout game modifier: +8 pts when a team is up 3-0 in series

Usage:
  python triple_conservative_v8.py              # all games
  python triple_conservative_v8.py --game LAL@OKC  # single game
"""

import json
from dataclasses import dataclass
from typing import Optional

# =====================================================================
# TEAM DATA — Updated May 5, 2026
# Fields: pts, reb, ast, 3pm (3-point shots made per game)
# Status: A = Active, Q = Questionable, OUT = Out
# =====================================================================

TEAMS = {
    "PHI": {
        "name": "Philadelphia 76ers",
        "seed": 7,
        "rest": "Short (Game 7 win vs BOS May 2 — came back from 3-1 down)",
        "players": [
            {"name": "Joel Embiid",        "pos": "C",  "ht": "7-0",  "pts": 28.5, "reb": 10.5, "ast": 5.5, "3pm": 1.8, "status": "Q"},
            {"name": "Tyrese Maxey",       "pos": "G",  "ht": "6-2",  "pts": 24.5, "reb": 4.5,  "ast": 6.5, "3pm": 2.5, "status": "A"},
            {"name": "Paul George",        "pos": "F",  "ht": "6-8",  "pts": 22.0, "reb": 5.5,  "ast": 4.5, "3pm": 3.2, "status": "A"},
            {"name": "Kelly Oubre Jr",     "pos": "F",  "ht": "6-7",  "pts": 18.5, "reb": 5.0,  "ast": 1.5, "3pm": 2.1, "status": "A"},
            {"name": "VJ Edgecombe",       "pos": "G",  "ht": "6-5",  "pts": 15.0, "reb": 3.5,  "ast": 2.5, "3pm": 1.2, "status": "A"},
            {"name": "Justin Edwards",     "pos": "F",  "ht": "6-6",  "pts": 8.0,  "reb": 3.0,  "ast": 1.0, "3pm": 0.8, "status": "A"},
            {"name": "Jared McCain",       "pos": "G",  "ht": "6-3",  "pts": 9.5,  "reb": 2.5,  "ast": 2.0, "3pm": 1.0, "status": "A"},
            {"name": "Lamar Stevens",      "pos": "F",  "ht": "6-8",  "pts": 6.0,  "reb": 3.5,  "ast": 0.5, "3pm": 0.3, "status": "A"},
        ],
        "bench_total": 20,
        "note": "Embiid Q (right hip contusion, played limited in Game 7)",
    },
    "NY": {
        "name": "New York Knicks",
        "seed": 3,
        "rest": "Long (swept ATL in 6, last game Apr 30)",
        "players": [
            {"name": "Jalen Brunson",        "pos": "G",  "ht": "6-1",  "pts": 27.5, "reb": 4.0,  "ast": 7.5, "3pm": 2.5, "status": "A"},
            {"name": "Mikal Bridges",         "pos": "G",  "ht": "6-5",  "pts": 19.5, "reb": 4.5,  "ast": 3.5, "3pm": 2.0, "status": "A"},
            {"name": "OG Anunoby",            "pos": "F",  "ht": "6-7",  "pts": 17.0, "reb": 5.0,  "ast": 2.5, "3pm": 1.8, "status": "A"},
            {"name": "Karl-Anthony Towns",   "pos": "C",  "ht": "6-11", "pts": 20.0, "reb": 10.5, "ast": 3.0, "3pm": 1.5, "status": "A"},
            {"name": "Josh Hart",             "pos": "F",  "ht": "6-5",  "pts": 14.0, "reb": 6.5,  "ast": 4.5, "3pm": 1.2, "status": "A"},
            {"name": "Miles McBride",         "pos": "G",  "ht": "6-2",  "pts": 10.0, "reb": 2.5,  "ast": 3.0, "3pm": 1.5, "status": "A"},
            {"name": "Precious Achiuwa",      "pos": "F",  "ht": "6-8",  "pts": 7.5,  "reb": 5.5,  "ast": 1.0, "3pm": 0.5, "status": "A"},
            {"name": "Jeremy Sochan",         "pos": "F",  "ht": "6-8",  "pts": 6.0,  "reb": 3.5,  "ast": 1.5, "3pm": 0.4, "status": "Q"},
        ],
        "bench_total": 22,
        "note": "Sochan Q (left hamstring tightness) — limited if plays",
    },
    "MIN": {
        "name": "Minnesota Timberwolves",
        "seed": 6,
        "rest": "Moderate (won DEN series in 6, last game May 2)",
        "players": [
            {"name": "Anthony Edwards",          "pos": "G",  "ht": "6-4",  "pts": 29.0, "reb": 5.5,  "ast": 5.0, "3pm": 3.0, "status": "A"},
            {"name": "Julius Randle",            "pos": "F",  "ht": "6-8",  "pts": 22.0, "reb": 7.5,  "ast": 5.0, "3pm": 1.8, "status": "A"},
            {"name": "Rudy Gobert",              "pos": "C",  "ht": "7-1",  "pts": 16.5, "reb": 11.5, "ast": 1.5, "3pm": 0.0, "status": "A"},
            {"name": "Jaden McDaniels",          "pos": "F",  "ht": "6-9",  "pts": 13.5, "reb": 3.5,  "ast": 1.5, "3pm": 1.2, "status": "A"},
            {"name": "Nickeil Alexander-Walker", "pos": "G",  "ht": "6-5",  "pts": 12.0, "reb": 3.0,  "ast": 2.0, "3pm": 1.8, "status": "A"},
            {"name": "Donte DiVincenzo",          "pos": "G",  "ht": "6-4",  "pts": 10.5, "reb": 3.5,  "ast": 3.0, "3pm": 2.0, "status": "OUT"},
            {"name": "Ayo Dosunmu",              "pos": "G",  "ht": "6-5",  "pts": 9.5,  "reb": 3.0,  "ast": 3.5, "3pm": 0.8, "status": "Q"},
            {"name": "Naz Reid",                 "pos": "F",  "ht": "6-9",  "pts": 13.0, "reb": 5.0,  "ast": 1.5, "3pm": 1.5, "status": "A"},
        ],
        "bench_total": 25,
        "note": "DiVincenzo OUT (Achilles, season); Dosunmu Q (calf strain)",
    },
    "SA": {
        "name": "San Antonio Spurs",
        "seed": 2,
        "rest": "Long (swept POR in 4, last game Apr 28)",
        "players": [
            {"name": "Victor Wembanyama",   "pos": "C",  "ht": "7-4",  "pts": 30.0, "reb": 10.5, "ast": 4.5, "3pm": 3.5, "status": "A"},
            {"name": "Stephon Castle",      "pos": "G",  "ht": "6-5",  "pts": 21.0, "reb": 4.5,  "ast": 5.0, "3pm": 1.8, "status": "A"},
            {"name": "Julian Champagnie",   "pos": "F",  "ht": "6-8",  "pts": 16.5, "reb": 5.0,  "ast": 2.0, "3pm": 2.2, "status": "A"},
            {"name": "Harrison Barnes",     "pos": "F",  "ht": "6-8",  "pts": 14.0, "reb": 4.5,  "ast": 1.5, "3pm": 1.5, "status": "A"},
            {"name": "Chris Paul",          "pos": "G",  "ht": "6-0",  "pts": 12.0, "reb": 3.5,  "ast": 8.0, "3pm": 1.5, "status": "A"},
            {"name": "Keldon Johnson",      "pos": "F",  "ht": "6-5",  "pts": 11.5, "reb": 4.0,  "ast": 2.0, "3pm": 1.5, "status": "A"},
            {"name": "Devin Vassell",       "pos": "G",  "ht": "6-5",  "pts": 10.0, "reb": 3.5,  "ast": 2.0, "3pm": 1.5, "status": "A"},
            {"name": "Carter Bryant",       "pos": "F",  "ht": "6-7",  "pts": 7.5,  "reb": 3.0,  "ast": 0.5, "3pm": 0.5, "status": "Q"},
        ],
        "bench_total": 28,
        "note": "Carter Bryant Q (foot strain); David Jones Garcia out (ankle, season)",
    },
    "OKC": {
        "name": "Oklahoma City Thunder",
        "seed": 1,
        "rest": "Long (swept PHX in 4, last game Apr 27 — advanced to West Semis)",
        "players": [
            {"name": "Shai Gilgeous-Alexander", "pos": "G",  "ht": "6-6",  "pts": 32.0, "reb": 5.0,  "ast": 6.5, "3pm": 2.2, "status": "A"},
            {"name": "Jalen Williams",           "pos": "F",  "ht": "6-5",  "pts": 21.0, "reb": 5.5,  "ast": 4.5, "3pm": 1.5, "status": "OUT"},
            {"name": "Chet Holmgren",            "pos": "C",  "ht": "7-1",  "pts": 18.0, "reb": 7.5,  "ast": 2.5, "3pm": 1.8, "status": "A"},
            {"name": "Lu Dort",                  "pos": "G",  "ht": "6-4",  "pts": 12.0, "reb": 3.5,  "ast": 2.0, "3pm": 2.0, "status": "A"},
            {"name": "Josh Giddey",              "pos": "G",  "ht": "6-8",  "pts": 11.5, "reb": 6.5,  "ast": 5.5, "3pm": 1.2, "status": "A"},
            {"name": "Isaiah Hartenstein",       "pos": "C",  "ht": "7-0",  "pts": 10.0, "reb": 7.0,  "ast": 2.5, "3pm": 0.5, "status": "A"},
            {"name": "Jaylin Williams",           "pos": "F",  "ht": "6-10", "pts": 8.0,  "reb": 4.5,  "ast": 1.5, "3pm": 0.8, "status": "A"},
            {"name": "Cason Wallace",            "pos": "G",  "ht": "6-4",  "pts": 7.5,  "reb": 2.5,  "ast": 2.0, "3pm": 1.2, "status": "A"},
        ],
        "bench_total": 30,
        "note": "Jalen Williams OUT (hamstring, week-to-week). OKC swept PHX 4-0 in R1 (Apr 27).",
    },
    "PHX": {
        "name": "Phoenix Suns",
        "seed": 8,
        "rest": "Eliminated (swept 0-4 by OKC in R1, last game Apr 27)",
        "players": [
            {"name": "Devin Booker",             "pos": "G",  "ht": "6-5",  "pts": 26.0, "reb": 4.5,  "ast": 6.5, "3pm": 2.8, "status": "A"},
            {"name": "Kevin Durant",             "pos": "F",  "ht": "6-10", "pts": 27.0, "reb": 6.5,  "ast": 4.0, "3pm": 2.5, "status": "A"},
            {"name": "Bradley Beal",             "pos": "G",  "ht": "6-4",  "pts": 18.0, "reb": 4.0,  "ast": 5.0, "3pm": 2.0, "status": "OUT"},
            {"name": "Jusuf Nurkić",             "pos": "C",  "ht": "7-0",  "pts": 14.0, "reb": 10.0, "ast": 2.5, "3pm": 0.5, "status": "A"},
            {"name": "Grayson Allen",            "pos": "G",  "ht": "6-4",  "pts": 12.5, "reb": 3.5,  "ast": 3.0, "3pm": 2.5, "status": "A"},
            {"name": "Royce O'Neale",           "pos": "F",  "ht": "6-4",  "pts": 9.0,  "reb": 5.5,  "ast": 3.5, "3pm": 2.0, "status": "A"},
            {"name": "Bol Bol",                  "pos": "C",  "ht": "7-2",  "pts": 8.0,  "reb": 5.0,  "ast": 1.0, "3pm": 1.0, "status": "A"},
            {"name": "Nassir Little",            "pos": "F",  "ht": "6-7",  "pts": 7.0,  "reb": 3.0,  "ast": 1.0, "3pm": 0.8, "status": "A"},
        ],
        "bench_total": 18,
        "note": "Beal OUT (knee, season); PHX eliminated in R1 sweep by OKC (Apr 27).",
    },
    "LAL": {
        "name": "Los Angeles Lakers",
        "seed": 4,
        "rest": "Short (won Game 6 vs HOU May 1, finished Rockets in 6)",
        "players": [
            {"name": "LeBron James",            "pos": "F",  "ht": "6-9",  "pts": 23.2, "reb": 7.2,  "ast": 8.3, "3pm": 2.2, "status": "A"},
            {"name": "Austin Reaves",            "pos": "G",  "ht": "6-5",  "pts": 18.0, "reb": 4.0,  "ast": 5.5, "3pm": 2.5, "status": "A"},
            {"name": "Luka Doncic",              "pos": "G",  "ht": "6-7",  "pts": 26.0, "reb": 7.5,  "ast": 8.0, "3pm": 3.0, "status": "OUT"},
            {"name": "Rui Hachimura",            "pos": "F",  "ht": "6-8",  "pts": 13.0, "reb": 4.5,  "ast": 1.5, "3pm": 1.2, "status": "A"},
            {"name": "Dorian Finney-Smith",      "pos": "F",  "ht": "6-7",  "pts": 9.5,  "reb": 4.0,  "ast": 1.5, "3pm": 1.8, "status": "A"},
            {"name": "Deandre Ayton",            "pos": "C",  "ht": "6-11", "pts": 14.5, "reb": 8.5,  "ast": 1.5, "3pm": 0.5, "status": "A"},
            {"name": "Marcus Smart",             "pos": "G",  "ht": "6-4",  "pts": 8.5,  "reb": 3.0,  "ast": 4.0, "3pm": 1.5, "status": "A"},
            {"name": "Jaxson Hayes",             "pos": "C",  "ht": "6-10", "pts": 7.0,  "reb": 3.5,  "ast": 0.5, "3pm": 0.2, "status": "A"},
        ],
        "bench_total": 18,
        "note": "Luka Doncic OUT (left hamstring strain — no timeline); Reaves returned Game 5 vs HOU; LeBron played full series at 41 years old",
    },
    "CLE": {
        "name": "Cleveland Cavaliers",
        "seed": 1,
        "rest": "Long (swept POR in 4, last game Apr 27 — advanced to East Semis)",
        "players": [
            {"name": "Donovan Mitchell",         "pos": "G",  "ht": "6-1",  "pts": 27.5, "reb": 4.5,  "ast": 5.5, "3pm": 3.0, "status": "A"},
            {"name": "Darius Garland",           "pos": "G",  "ht": "6-1",  "pts": 20.0, "reb": 3.0,  "ast": 8.0, "3pm": 2.5, "status": "A"},
            {"name": "Evan Mobley",             "pos": "F",  "ht": "6-11", "pts": 19.0, "reb": 9.5,  "ast": 3.0, "3pm": 1.2, "status": "A"},
            {"name": "Jarrett Allen",            "pos": "C",  "ht": "6-11", "pts": 16.5, "reb": 10.0, "ast": 2.5, "3pm": 0.0, "status": "A"},
            {"name": "Max Strus",               "pos": "F",  "ht": "6-5",  "pts": 12.0, "reb": 4.0,  "ast": 3.0, "3pm": 2.5, "status": "A"},
            {"name": "Caris LeVert",            "pos": "G",  "ht": "6-5",  "pts": 10.5, "reb": 3.5,  "ast": 3.0, "3pm": 1.5, "status": "A"},
            {"name": "Isaac Okoro",             "pos": "G",  "ht": "6-5",  "pts": 9.0,  "reb": 3.0,  "ast": 2.0, "3pm": 0.8, "status": "A"},
            {"name": "Ty Jerome",               "pos": "G",  "ht": "6-5",  "pts": 7.5,  "reb": 2.0,  "ast": 2.5, "3pm": 1.0, "status": "A"},
        ],
        "bench_total": 24,
        "note": "CLE swept POR 4-0 in R1 (Apr 27). No major injuries. Well-rested heading into East Semis.",
    },
    "DET": {
        "name": "Detroit Pistons",
        "seed": 8,
        "rest": "Short (won Game 6 vs ORL May 2, came back from 3-1 deficit)",
        "players": [
            {"name": "Cade Cunningham",         "pos": "G",  "ht": "6-7",  "pts": 25.0, "reb": 5.5,  "ast": 8.5, "3pm": 2.2, "status": "A"},
            {"name": "Jalen Duren",             "pos": "C",  "ht": "6-11", "pts": 14.0, "reb": 9.0,  "ast": 2.5, "3pm": 0.0, "status": "A"},
            {"name": "Tim Hardaway Jr",         "pos": "F",  "ht": "6-5",  "pts": 13.5, "reb": 3.5,  "ast": 1.5, "3pm": 2.2, "status": "A"},
            {"name": "Dennis Schroder",          "pos": "G",  "ht": "6-1",  "pts": 12.5, "reb": 2.5,  "ast": 6.5, "3pm": 1.8, "status": "A"},
            {"name": "Ausar Thompson",          "pos": "F",  "ht": "6-7",  "pts": 12.0, "reb": 5.5,  "ast": 3.5, "3pm": 1.0, "status": "A"},
            {"name": "Marcus Sass",             "pos": "F",  "ht": "6-8",  "pts": 10.0, "reb": 4.5,  "ast": 2.0, "3pm": 1.5, "status": "Q"},
            {"name": "Tobias Harris",           "pos": "F",  "ht": "6-8",  "pts": 9.5,  "reb": 4.0,  "ast": 1.5, "3pm": 1.0, "status": "A"},
            {"name": "Julius Randle",           "pos": "F",  "ht": "6-8",  "pts": 22.0, "reb": 7.5,  "ast": 5.0, "3pm": 1.8, "status": "OUT"},
        ],
        "bench_total": 15,
        "note": "Duren Q (ankle sprain, limited in Game 6); DET came back from 3-1 to beat ORL in 7 — exhausted but confident",
    },
}

# =====================================================================
# GAMES — May 5, 2026 (Second Round / Conference Semifinals)
# =====================================================================

GAMES = [
    {
        "id": "OKC@PHX",
        "date": "April 27, 2026",
        "time": "10:30 PM ET",
        "network": "ESPN",
        "series": "West R1 — Game 4 (OKC sweeps 4-0)",
        "matchup": "Oklahoma City Thunder @ Phoenix Suns",
        "spread": {"favorite": "OKC", "line": -9.5, "underdog": "PHX"},
        "total": {"line": 218.0},
        "ml": {"OKC": "-450", "PHX": "+340"},
        "round": 1,
        "note": "Elimination game — OKC up 3-0, can close out sweep. PHX season on the line.",
    },
    {
        "id": "PHI@NY",
        "date": "May 4, 2026",
        "time": "8:00 PM ET",
        "network": "NBC / Peacock",
        "series": "East Semifinals — Game 1",
        "matchup": "Philadelphia 76ers @ New York Knicks",
        "spread": {"favorite": "NY", "line": -7.5, "underdog": "PHI"},
        "total": {"line": 213.5},
        "ml": {"PHI": "+235", "NY": "-290"},
        "round": 2,
    },
    {
        "id": "MIN@SA",
        "date": "May 4, 2026",
        "time": "9:30 PM ET",
        "network": "NBCSN / Peacock",
        "series": "West Semifinals — Game 1",
        "matchup": "Minnesota Timberwolves @ San Antonio Spurs",
        "spread": {"favorite": "SA", "line": -13.0, "underdog": "MIN"},
        "total": {"line": 217.5},
        "ml": {"SA": "-650", "MIN": "+475"},
        "round": 2,
    },
    {
        "id": "LAL@OKC",
        "date": "May 5, 2026",
        "time": "8:30 PM ET",
        "network": "NBC / Peacock",
        "series": "West Semifinals — Game 1",
        "matchup": "Los Angeles Lakers @ Oklahoma City Thunder",
        "spread": {"favorite": "OKC", "line": -11.5, "underdog": "LAL"},
        "total": {"line": 220.5},
        "ml": {"OKC": "-500", "LAL": "+380"},
        "round": 2,
        "note": "Game 1 of West Semis. OKC swept LAL 4-0 in regular season (avg margin 29.3 pts). Luka OUT.",
    },
    {
        "id": "CLE@DET",
        "date": "May 5, 2026",
        "time": "7:00 PM ET",
        "network": "TNT",
        "series": "East Semifinals — Game 1",
        "matchup": "Cleveland Cavaliers @ Detroit Pistons",
        "spread": {"favorite": "CLE", "line": -8.5, "underdog": "DET"},
        "total": {"line": 215.5},
        "ml": {"CLE": "-350", "DET": "+280"},
        "round": 2,
    },
]

# =====================================================================
# TC PROJECTION ENGINE
# =====================================================================

MULTIPLIERS = {"A": 0.85, "Q": 0.55, "OUT": 0.0}
TV_MULTIPLIER = 0.78

def tc_stat(val: float, status: str) -> float:
    return round(val * MULTIPLIERS.get(status, 0.85), 1)

def clutch_flag(p: dict) -> str:
    if p["pts"] >= 25 and p["status"] == "A":
        return " ★"
    return ""

def tc_proj_player(p: dict) -> dict:
    tc_pts   = tc_stat(p["pts"],  p["status"])
    tc_reb   = tc_stat(p["reb"],  p["status"])
    tc_ast   = tc_stat(p["ast"],  p["status"])
    tc_3pm   = tc_stat(p["3pm"], p["status"])
    tc_total = round(tc_pts + tc_reb + tc_ast + tc_3pm, 1)
    line     = round(tc_total * 0.88)
    edge     = round(tc_total - line, 1)
    flag     = {"A": "✅", "Q": "⚠️ Q", "OUT": "❌ OUT"}.get(p["status"], "")
    clutch   = clutch_flag(p)
    tv_pts   = round(tc_pts * TV_MULTIPLIER, 1)
    tv_total = round(tc_total * TV_MULTIPLIER, 1)
    return {
        "name":     p["name"],
        "pos":      p["pos"],
        "ht":       p["ht"],
        "pts":      p["pts"],
        "reb":      p["reb"],
        "ast":      p["ast"],
        "3pm":      p["3pm"],
        "tc_pts":   tc_pts,
        "tc_reb":   tc_reb,
        "tc_ast":   tc_ast,
        "tc_3pm":   tc_3pm,
        "tc_total": tc_total,
        "line":     line,
        "edge":     edge,
        "status":   p["status"],
        "flag":     flag,
        "clutch":   clutch,
        "tv_pts":   tv_pts,
        "tv_total": tv_total,
    }

def project_team(team_id: str, closeout: bool = False) -> dict:
    team = TEAMS[team_id]
    rows = []
    bench_tc_pts = 0.0
    bench_tc_reb = 0.0
    bench_tc_ast = 0.0
    bench_tc_3pm = 0.0

    for p in team["players"]:
        r = tc_proj_player(p)
        rows.append(r)
        if p["status"] in ("A", "Q"):
            bench_tc_pts += r["tc_pts"]
            bench_tc_reb += r["tc_reb"]
            bench_tc_ast += r["tc_ast"]
            bench_tc_3pm += r["tc_3pm"]

    closeout_mod = 8 if closeout else 0
    tc_team_total = round(
        bench_tc_pts + bench_tc_reb + bench_tc_ast + bench_tc_3pm
        + team["bench_total"] + closeout_mod, 1
    )

    tv_combined = round(sum(r["tv_total"] for r in rows) * TV_MULTIPLIER, 1)

    return {
        "team_id":        team_id,
        "team_name":      team["name"],
        "seed":           team["seed"],
        "rest":           team["rest"],
        "players":        rows,
        "bench_tc_pts":   round(bench_tc_pts, 1),
        "bench_tc_reb":   round(bench_tc_reb, 1),
        "bench_tc_ast":   round(bench_tc_ast, 1),
        "bench_tc_3pm":   round(bench_tc_3pm, 1),
        "bench_total":    team["bench_total"],
        "tc_team_total":  tc_team_total,
        "closeout_mod":   closeout_mod,
        "tv_combined":    tv_combined,
        "note":           team["note"],
    }

def project_game(game: dict, closeout: bool = False) -> dict:
    away_id, home_id = game["id"].split("@")
    away = project_team(away_id, closeout)
    home = project_team(home_id, closeout)

    tc_combined    = round(away["tc_team_total"] + home["tc_team_total"], 1)
    tc_spread_val = round(home["tc_team_total"] - away["tc_team_total"], 1)
    market_total  = game["total"]["line"]
    market_spread = game["spread"]["line"]
    spread_edge   = round(tc_spread_val - abs(market_spread), 1)
    total_edge    = round(tc_combined - market_total, 1)

    tv_combined = round(away["tv_combined"] + home["tv_combined"], 1)

    return {
        "game":          game,
        "away":          away,
        "home":          home,
        "tc_combined":   tc_combined,
        "tc_spread":     tc_spread_val,
        "market_total":  market_total,
        "market_spread": market_spread,
        "spread_edge":   spread_edge,
        "total_edge":    total_edge,
        "tv_combined":   tv_combined,
        "closeout_mod":  home["closeout_mod"],
    }

# =====================================================================
# REPORT GENERATOR — Full PTS/REB/AST/3PM + TV Match Score
# =====================================================================

def status_icon(status: str, clutch: str) -> str:
    icons = {"A": "✅", "Q": "⚠️ Q", "OUT": "❌ OUT"}
    return icons.get(status, "") + clutch

def fmt_team_section(label: str, td: dict, is_home: bool = False) -> str:
    rows = []
    home_marker = " (Home)" if is_home else " (Away)"
    rows.append(f"### {label}{home_marker}\n")
    rows.append(
        "| Player                  | POS | HT    | PTS  | REB  | AST  | 3PM  |"
        " TC PTS | TC REB | TC AST | TC 3PM | TC TOT | LINE | EDGE | TV PTS | TV TOT | STATUS |"
    )
    rows.append(
        "|------------------------|-----|-------|------|------|------|------|"
        "--------|--------|--------|--------|--------|------|------|--------|--------|------------ |"
    )
    for p in td["players"]:
        flag    = p["flag"]
        clutch  = p["clutch"]
        edge    = f"+{p['edge']}" if p["edge"] >= 0 else str(p["edge"])
        status_txt = status_icon(p["status"], clutch)
        rows.append(
            f"| {p['name']:<22} | {p['pos']}  | {p['ht']}  |"
            f" {p['pts']:>4.1f} | {p['reb']:>4.1f} | {p['ast']:>4.1f} | {p['3pm']:>3.1f} |"
            f" {p['tc_pts']:>7.1f} | {p['tc_reb']:>7.1f} | {p['tc_ast']:>7.1f} |"
            f" {p['tc_3pm']:>7.1f} | {p['tc_total']:>8.1f} | {p['line']:>4} |"
            f" {edge:>5} | {p['tv_pts']:>7.1f} | {p['tv_total']:>7.1f} | {status_txt:<11} |"
        )

    rows.append(
        f"\n**Bench contribution:** TC PTS={td['bench_tc_pts']} | TC REB={td['bench_tc_reb']} |"
        f" TC AST={td['bench_tc_ast']} | TC 3PM={td['bench_tc_3pm']} | bench bonus={td['bench_total']}\n"
        f"**TC TEAM TOTAL: {td['tc_team_total']}**"
        f"{' (+' + str(td['closeout_mod']) + ' closeout)' if td['closeout_mod'] else ''}"
        f" | **TV Match Score: {td['tv_combined']}**"
    )
    return "\n".join(rows)

def lean_label(total_edge: float) -> str:
    if total_edge > 10:   return "STRONG OVER"
    elif total_edge > 3:   return "OVER"
    elif total_edge < -10: return "STRONG UNDER"
    elif total_edge < -3:  return "UNDER"
    else:                  return "LEAN UNDER"

def conf_label(edge: float, threshold_high: float = 8, threshold_med: float = 4) -> str:
    if abs(edge) > threshold_high: return "HIGH"
    elif abs(edge) > threshold_med: return "MED"
    else:                           return "LOW"

def generate_report(g: dict) -> str:
    game        = g["game"]
    total_edge  = g["total_edge"]
    spread_edge = g["spread_edge"]
    tc_combined = g["tc_combined"]
    tc_spread   = g["tc_spread"]
    market_tot  = g["market_total"]
    market_spr  = g["market_spread"]
    tv_combined = g["tv_combined"]

    total_lean  = lean_label(total_edge)
    conf_tot    = conf_label(total_edge)
    conf_spr    = conf_label(spread_edge, 3.0, 1.5)
    favorite    = game["spread"]["favorite"]
    underdog    = game["spread"]["underdog"]
    series_note = game.get("note", "")

    if "OVER" in total_lean:
        rec_total = f"OVER {market_tot}"
    else:
        rec_total = f"UNDER {market_tot}"

    if spread_edge > 0:
        rec_spread = f"{favorite} -{abs(tc_spread)}"
    else:
        rec_spread = f"{underdog} +{abs(tc_spread)}"

    report = f"""
# 🏀 TC Projections — {game['matchup']}
**Series:** {game['series']}  |  **Date:** {game['date']} — {game['time']}  |  **TV:** {game['network']}  |
**Market:** {favorite} {market_spr} / O/U {market_tot}  |  **TV Match Score:** {tv_combined}

---

## Starting Lineups & TC Stats

{fmt_team_section(TEAMS[game['id'].split('@')[0]]['name'], g['away'], is_home=False)}

---

{fmt_team_section(TEAMS[game['id'].split('@')[1]]['name'], g['home'], is_home=True)}

---

## TC System Summary

| Metric | AWAY ({g['away']['team_name']}) | HOME ({g['home']['team_name']}) |
|--------|------|------|
| **TC Team Total** | {g['away']['tc_team_total']} | {g['home']['tc_team_total']} |
| **TC Combined Total** | **{tc_combined}** | |
| **Market Total (O/U)** | **{market_tot}** | |
| **Total Edge** | **{total_edge:+.1f}** → **{total_lean}** | |
| **TC Spread** | **{favorite} by {tc_spread}** | |
| **Market Spread** | **{favorite} {market_spr}** | |
| **Spread Edge** | **{spread_edge:+.1f}** → **{favorite} cover** | |
| **TV Match Score** | {tv_combined} | |

---

## Pick Candidates

| Pick Type | Market Line | TC Signal | Edge | Confidence |
|-----------|-------------|-----------|------|------------|
| **Total** | O/U {market_tot} | **{total_lean}** | {total_edge:+.1f} pts | {conf_tot} |
| **Spread** | {favorite} {market_spr} | **{favorite} cover** | {spread_edge:+.1f} pts | {conf_spr} |

**Recommended:** {rec_total} | {rec_spread}

---

## Key Notes

- **{g['away']['team_name']}:** {g['away']['note']}
- **{g['home']['team_name']}:** {g['home']['note']}
- **Rest context:** {g['away']['rest']} vs {g['home']['rest']}
{f"- **{series_note}**" if series_note else ""}

---

*TC Formula: TC stat = stat × 0.85 (Q = ×0.55, OUT = 0) | Line = TC total × 0.88 | Edge = TC total − Line*  
*TV Match: TC pts × 0.78 = TV PTS | TC Total × 0.78 = TV TOT*  
*★ = Clutch player (≥25 PPG, active)*  
*Columns: PTS = points | REB = rebounds | AST = assists | 3PM = 3-point shots made*
"""
    return report.strip()

# =====================================================================
# MAIN
# =====================================================================

def main():
    for game in GAMES:
        result = project_game(game)
        report = generate_report(result)
        filename = f"/home/workspace/{game['id']}_TC_Report.md"
        away_team = TEAMS[game["id"].split("@")[0]]
        home_team = TEAMS[game["id"].split("@")[1]]
        away_printed = False
        home_printed = False

        for p in away_team["players"]:
            r = tc_proj_player(p)
            edge_str = f"+{r['edge']}" if r["edge"] >= 0 else str(r["edge"])
            status_str = status_icon(r["status"], r["clutch"])
            print(
                f"  {r['name']:<24} {r['pos']} {r['ht']}  "
                f"TC_PTS={r['tc_pts']:>5.1f} TC_REB={r['tc_reb']:>5.1f} TC_AST={r['tc_ast']:>5.1f} TC_3PM={r['tc_3pm']:>5.1f}  "
                f"TC_TOT={r['tc_total']:>6.1f} LINE={r['line']:>4} EDGE={edge_str:>5}  {status_str}"
            )

        print(
            f"  BENCH SUBTOTAL: TC_PTS={result['away']['bench_tc_pts']} TC_REB={result['away']['bench_tc_reb']} "
            f"TC_AST={result['away']['bench_tc_ast']} TC_3PM={result['away']['bench_tc_3pm']}  "
            f"+ bench_bonus={result['away']['bench_total']}  >>> TC TEAM TOTAL: {result['away']['tc_team_total']}"
        )
        print()

        for p in home_team["players"]:
            r = tc_proj_player(p)
            edge_str = f"+{r['edge']}" if r["edge"] >= 0 else str(r["edge"])
            status_str = status_icon(r["status"], r["clutch"])
            print(
                f"  {r['name']:<24} {r['pos']} {r['ht']}  "
                f"TC_PTS={r['tc_pts']:>5.1f} TC_REB={r['tc_reb']:>5.1f} TC_AST={r['tc_ast']:>5.1f} TC_3PM={r['tc_3pm']:>5.1f}  "
                f"TC_TOT={r['tc_total']:>6.1f} LINE={r['line']:>4} EDGE={edge_str:>5}  {status_str}"
            )

        print(
            f"  BENCH SUBTOTAL: TC_PTS={result['home']['bench_tc_pts']} TC_REB={result['home']['bench_tc_reb']} "
            f"TC_AST={result['home']['bench_tc_ast']} TC_3PM={result['home']['bench_tc_3pm']}  "
            f"+ bench_bonus={result['home']['bench_total']}  >>> TC TEAM TOTAL: {result['home']['tc_team_total']}"
        )
        print()

        lean_s = lean_label(result["total_edge"])
        rec_total = f"OVER {result['market_total']}" if "OVER" in lean_s else f"UNDER {result['market_total']}"
        rec_spread = f"{result['game']['spread']['favorite']} -{abs(result['tc_spread'])}" if result["spread_edge"] > 0 else f"{result['game']['spread']['underdog']} +{abs(result['tc_spread'])}"
        print(f"  ▶ TC COMBINED: {result['tc_combined']}  |  Market O/U: {result['market_total']}  |  Edge: {result['total_edge']:+.1f} → {lean_s}")
        print(f"  ▶ SPREAD: {result['game']['spread']['favorite']} by TC_spread={result['tc_spread']}  |  Market: {result['game']['spread']['favorite']} {result['game']['spread']['line']}  |  Edge: {result['spread_edge']:+.1f}")
        print(f"  ▶ TV MATCH SCORE: {result['tv_combined']}")
        print(f"  ▶ RECOMMENDED: {rec_total} | {rec_spread}")
        print(f"\n{'='*80}\n")

        with open(filename, "w") as f:
            f.write(report)
        print(f"✅ Saved: {filename}")

    print(f"✅ triple_conservative_v8.py — All TC reports generated.")

def total_lean(e):
    return lean_label(e)

def favorite(g):
    return g["game"]["spread"]["favorite"]

def tc_spread(g):
    return g["tc_spread"]

if __name__ == "__main__":
    import sys
    if "--game" in sys.argv:
        target = sys.argv[sys.argv.index("--game") + 1]
        for game in GAMES:
            if game["id"] == target:
                result = project_game(game)
                report = generate_report(result)
                filename = f"/home/workspace/{game['id']}_TC_Report.md"
                away_team = TEAMS[game["id"].split("@")[0]]
                home_team = TEAMS[game["id"].split("@")[1]]

                # HARDWIRED: print every player's full TC stats to terminal — always
                print(f"\n{'='*80}")
                print(f"  {game['matchup']} — {game['series']}")
                print(f"  {game['date']} | {game['time']} | {game['network']}")
                print(f"{'='*80}")

                print(f"\n  ▼ {away_team['name']} (AWAY)")
                for p in away_team["players"]:
                    r = tc_proj_player(p)
                    edge_str = f"+{r['edge']}" if r["edge"] >= 0 else str(r["edge"])
                    status_str = status_icon(r["status"], r["clutch"])
                    print(
                        f"  {r['name']:<24} {r['pos']} {r['ht']}  "
                        f"TC_PTS={r['tc_pts']:>5.1f} TC_REB={r['tc_reb']:>5.1f} TC_AST={r['tc_ast']:>5.1f} TC_3PM={r['tc_3pm']:>5.1f}  "
                        f"TC_TOT={r['tc_total']:>6.1f} LINE={r['line']:>4} EDGE={edge_str:>5}  {status_str}"
                    )
                print(
                    f"  BENCH: TC_PTS={result['away']['bench_tc_pts']} TC_REB={result['away']['bench_tc_reb']} "
                    f"TC_AST={result['away']['bench_tc_ast']} TC_3PM={result['away']['bench_tc_3pm']}  "
                    f"+ bench_bonus={result['away']['bench_total']}  >>> TC TEAM TOTAL: {result['away']['tc_team_total']}"
                )

                print(f"\n  ▲ {home_team['name']} (HOME)")
                for p in home_team["players"]:
                    r = tc_proj_player(p)
                    edge_str = f"+{r['edge']}" if r["edge"] >= 0 else str(r["edge"])
                    status_str = status_icon(r["status"], r["clutch"])
                    print(
                        f"  {r['name']:<24} {r['pos']} {r['ht']}  "
                        f"TC_PTS={r['tc_pts']:>5.1f} TC_REB={r['tc_reb']:>5.1f} TC_AST={r['tc_ast']:>5.1f} TC_3PM={r['tc_3pm']:>5.1f}  "
                        f"TC_TOT={r['tc_total']:>6.1f} LINE={r['line']:>4} EDGE={edge_str:>5}  {status_str}"
                    )
                print(
                    f"  BENCH: TC_PTS={result['home']['bench_tc_pts']} TC_REB={result['home']['bench_tc_reb']} "
                    f"TC_AST={result['home']['bench_tc_ast']} TC_3PM={result['home']['bench_tc_3pm']}  "
                    f"+ bench_bonus={result['home']['bench_total']}  >>> TC TEAM TOTAL: {result['home']['tc_team_total']}"
                )

                lean_s = lean_label(result["total_edge"])
                rec_total = f"OVER {result['market_total']}" if "OVER" in lean_s else f"UNDER {result['market_total']}"
                rec_spread = f"{result['game']['spread']['favorite']} -{abs(result['tc_spread'])}" if result["spread_edge"] > 0 else f"{result['game']['spread']['underdog']} +{abs(result['tc_spread'])}"
                print()
                print(f"  ▶ TC COMBINED: {result['tc_combined']}  |  Market O/U: {result['market_total']}  |  Edge: {result['total_edge']:+.1f} → {lean_s}")
                print(f"  ▶ SPREAD: {result['game']['spread']['favorite']} by {result['tc_spread']}  |  Market: {result['game']['spread']['favorite']} {result['game']['spread']['line']}  |  Edge: {result['spread_edge']:+.1f}")
                print(f"  ▶ TV MATCH SCORE: {result['tv_combined']}")
                print(f"  ▶ RECOMMENDED: {rec_total} | {rec_spread}")
                print(f"\n{'='*80}\n")

                with open(filename, "w") as f:
                    f.write(report)
                print(f"✅ Saved: {filename}")
                break
        else:
            print(f"Game '{target}' not found. Available: {[g['id'] for g in GAMES]}")
    else:
        main()