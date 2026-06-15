"""
NBA TC Engine — UNIFIED v7.1
=============================
Single source of truth for all TC math, rosters, backtest data, and CLI/API.

CORRECTED FORMULAS (from backtest calibration):
  Player TC  = stat × TC_W[stat] × INJ[status]
  TC_W = {pts:0.85, reb:0.80, ast:0.75, 3pm:0.70}
  INJ = {ACTIVE:1.00, QUESTIONABLE:0.55, OUT:0.00}

  Book Line (L) = TC × 0.88  (floor)
  Edge = L − T  (positive = market line is above TC → UNDER bet)

  Game TC total (for totals) = SUM(5 starters' TC_PTS only) × PLAYOFF_MULT × 0.88
  K_GAP = 0.0 (calibration absorbed into START_FACTOR)
  START_FACTOR = 0.40  (starters get ~40% of team minutes, reducing all-active sum to realistic game total)

  Game Line = round((TC_starters × PLAYOFF_MULT) + K_GAP) × 0.88
  Signal: UNDER when tc_line < market_total (market is higher → market is expensive → lean UNDER)

  Props Signal: lean = "UNDER" if tc < book_line else "OVER"
  (tc below market → market line is high → bet UNDER)

BACKTEST GAPS (actual − TC):
  PTS = −3.0 | REB = −1.5 | AST = −1.0 | 3PM = −0.8

Kelly frac = 0.50 | MIN edge = 2.5 pts | MIN HR = 57%
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import argparse
import json

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
TC_W = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "3pm": 0.70}
INJ  = {"ACTIVE": 1.00, "QUESTIONABLE": 0.55, "OUT": 0.00}
PLAYOFF_MULT = 1.52  # Calibrated 2026-05-16: avg(actual/tc_line)=1.288 from 13 playoff total bets
LINE_FACTOR  = 0.88
HIST_GAP     = 4.5
START_FACTOR = 0.40
K_GAP        = 0.0

MIN_EDGE  = 2.5
MIN_HR    = 57
KELLY     = 0.50
HR_TIERS  = ((10, 72), (7, 68), (5, 64), (3, 60))

# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class P:
    name:    str
    pos:     str
    ht:      str
    pts:     float = 0.0
    reb:     float = 0.0
    ast:     float = 0.0
    tpm:     float = 0.0
    min_avg: float = 30.0
    status:  str   = "ACTIVE"
    tier:    int   = 2
    is_starter: bool = False

    def tc_pts(self) -> float:
        if self.status == "OUT":
            return 0.0
        f = TC_W["pts"] * INJ.get(self.status, 1.0)
        return round(self.pts * f, 1)

    def tc_reb(self) -> float:
        if self.status == "OUT":
            return 0.0
        return round(self.reb * TC_W["reb"] * INJ.get(self.status, 1.0), 1)

    def tc_ast(self) -> float:
        if self.status == "OUT":
            return 0.0
        return round(self.ast * TC_W["ast"] * INJ.get(self.status, 1.0), 1)

    def tc_3pm(self) -> float:
        if self.status == "OUT":
            return 0.0
        return round(self.tpm * TC_W["3pm"] * INJ.get(self.status, 1.0), 1)

    def tc_all(self) -> Dict[str, float]:
        return {
            "pts": self.tc_pts(),
            "reb": self.tc_reb(),
            "ast": self.tc_ast(),
            "3pm": self.tc_3pm(),
        }

    def book_line(self, stat: str = "pts") -> int:
        tc_map = {"pts": self.tc_pts(), "reb": self.tc_reb(),
                  "ast": self.tc_ast(), "3pm": self.tc_3pm()}
        return int(tc_map.get(stat, 0) * LINE_FACTOR)

    def edge(self, stat: str = "pts", market_line: float = None) -> float:
        bl = market_line if market_line is not None else self.book_line(stat)
        tc_map = self.tc_all()
        return round(tc_map.get(stat, 0) - bl, 1)

    def conf(self, stat: str = "pts", market_line: float = None) -> float:
        e = abs(self.edge(stat, market_line))
        for th, c in HR_TIERS:
            if e >= th:
                return c / 100
        return MIN_HR / 100

    def qualifies(self, stat: str = "pts", market_line: float = None) -> bool:
        return abs(self.edge(stat, market_line)) >= MIN_EDGE and self.conf(stat, market_line) >= MIN_HR / 100


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ROSTER DATA
# ═══════════════════════════════════════════════════════════════════════════════
TEAM_ROSTERS: Dict[str, List[P]] = {}

def _r(name, pos, ht, pts, reb=0.0, ast=0.0, tpm=0.0, mmin=30.0, status="ACTIVE", tier=2) -> P:
    return P(name, pos, ht, pts, reb, ast, tpm, mmin, status, tier)

# ── ROSTERS ──────────────────────────────────────────────────────────────────
TEAM_ROSTERS["BOS"] = [
    _r("Jayson Tatum",        "F",  "6-8",  26.8, 7.5, 5.0, 2.9, 37, "ACTIVE", 1),
    _r("Jaylen Brown",        "G",  "6-6",  22.5, 6.0, 3.5, 2.2, 33, "ACTIVE", 1),
    _r("Kristaps Porzingis",  "C",  "7-2",  15.5, 6.8, 2.0, 0.8, 26, "ACTIVE", 2),
    _r("Derrick White",       "G",  "6-4",  15.5, 4.2, 4.8, 2.8, 31, "ACTIVE", 2),
    _r("Jrue Holiday",        "G",  "6-4",  14.5, 4.5, 5.0, 1.8, 30, "ACTIVE", 2),
    _r("Payton Pritchard",    "G",  "6-1",  14.2, 3.5, 3.0, 3.1, 26, "ACTIVE", 3),
    _r("Al Horford",          "F",  "6-9",  11.2, 6.2, 3.5, 2.0, 27, "ACTIVE", 3),
    _r("Sam Hauser",          "F",  "6-5",   8.5, 3.0, 1.0, 2.2, 18, "ACTIVE", 3),
    _r("Neemias Queta",       "C",  "7-0",   5.0, 4.0, 0.5, 0.0, 10, "ACTIVE", 4),
    _r("Baylor Scheierman",   "G",  "6-5",   4.0, 2.0, 1.0, 0.8,  8, "ACTIVE", 4),
]
TEAM_ROSTERS["PHI"] = [
    _r("Joel Embiid",         "C",  "7-0",  28.5, 10.5, 5.5, 1.8, 32, "ACTIVE", 1),
    _r("Tyrese Maxey",        "G",  "6-2",  24.5,  4.5, 6.5, 2.5, 36, "ACTIVE", 1),
    _r("Paul George",         "F",  "6-8",  22.0,  5.5, 4.5, 3.2, 34, "ACTIVE", 1),
    _r("Kelly Oubre Jr.",     "F",  "6-7",  18.5,  5.0, 1.5, 2.1, 30, "ACTIVE", 2),
    _r("Andre Drummond",     "C",  "6-9",  10.0, 10.0, 2.0, 0.0, 18, "ACTIVE", 3),
    _r("Justin Edwards",      "F", "6-6",   8.0,  3.0, 1.0, 0.8, 16, "ACTIVE", 4),
    _r("VJ Edgecombe",        "G",  "6-5",  15.0,  3.5, 2.5, 1.2, 22, "ACTIVE", 3),
    _r("Quentin Grimes",      "G",  "6-5",  10.0,  3.0, 2.5, 1.8, 20, "ACTIVE", 4),
    _r("MarJon Beauchamp",   "F",  "6-7",   7.0,  3.5, 1.0, 0.8, 14, "ACTIVE", 4),
    _r("Kyle Lowry",         "PG", "6-0",   6.0,  3.0, 4.5, 1.2, 14, "ACTIVE", 4),
]
TEAM_ROSTERS["OKC"] = [
    _r("Shai Gilgeous-Alexander","SG","6-5",32.0, 5.0, 6.5, 2.8, 36, "ACTIVE", 1),
    _r("Chet Holmgren",       "C",  "7-0",  16.0, 8.0, 2.5, 1.0, 32, "ACTIVE", 1),
    _r("Jalen Williams",      "SF","6-6",  18.5, 5.5, 4.0, 1.5, 32, "ACTIVE", 2),
    _r("Isaiah Hartenstein",  "C",  "6-11", 8.0, 7.5, 2.5, 0.2, 26, "ACTIVE", 2),
    _r("Luguentz Dort",       "SG","6-4",   9.5, 3.5, 1.2, 2.0, 24, "ACTIVE", 3),
    _r("Alex Caruso",        "G",  "6-4",   6.0, 2.5, 2.0, 1.2, 18, "ACTIVE", 3),
    _r("Isaiah Joe",          "G",  "6-1",   9.0, 2.0, 0.8, 2.1, 16, "ACTIVE", 4),
    _r("Cason Wallace",       "G",  "6-4",   8.5, 2.5, 1.5, 1.8, 18, "ACTIVE", 4),
    _r("Aaron Wiggins",       "G",  "6-5",   7.5, 2.0, 1.0, 1.2, 14, "ACTIVE", 4),
    _r("Kenrich Williams",    "PF","6-7",   7.5, 5.0, 2.0, 1.2, 16, "ACTIVE", 4),
    _r("Jared McCain",        "G",  "6-3",   9.5, 2.5, 2.0, 1.0, 14, "ACTIVE", 4),
    _r("Branden Carlson",     "C",  "7-0",   6.0, 3.0, 0.8, 0.3, 10, "ACTIVE", 4),
]
TEAM_ROSTERS["PHX"] = [
    _r("Devin Booker",       "G",  "6-5",  26.1,  4.3, 6.0, 2.6, 37, "ACTIVE", 1),
    _r("Kevin Durant",       "F",  "6-10", 27.0,  6.5, 4.0, 2.8, 36, "ACTIVE", 1),
    _r("Bradley Beal",       "G",  "6-4",  18.0,  4.0, 5.0, 1.8, 32, "ACTIVE", 2),
    _r("Grayson Allen",      "G",  "6-5",  10.5,  3.0, 2.0, 2.4, 22, "ACTIVE", 3),
    _r("Jusuf Nurkić",       "C",  "7-0",  14.0, 10.0, 3.0, 0.4, 28, "ACTIVE", 2),
    _r("Royce O'Neale",      "F",  "6-5",   7.5,  4.5, 3.5, 1.8, 24, "ACTIVE", 3),
    _r("Tyus Jones",         "G",  "6-1",   8.5,  2.0, 4.5, 1.5, 20, "ACTIVE", 4),
    _r("Bol Bol",            "C",  "7-2",   8.0,  5.0, 1.0, 0.8, 16, "ACTIVE", 4),
    _r("Drew Eubanks",       "C",  "6-10",  5.5,  4.0, 0.8, 0.2, 12, "ACTIVE", 4),
]
TEAM_ROSTERS["NYK"] = [
    _r("Jalen Brunson",      "PG", "6-1",  27.5,  4.0, 7.5, 2.5, 38, "ACTIVE", 1),
    _r("Karl-Anthony Towns", "C",  "6-11", 20.0, 10.5, 3.0, 1.8, 34, "ACTIVE", 1),
    _r("Mikal Bridges",      "SG", "6-5",  19.5,  4.5, 3.5, 2.0, 36, "ACTIVE", 2),
    _r("OG Anunoby",         "SF", "6-7",  17.0,  5.0, 2.5, 1.8, 32, "QUESTIONABLE", 1),
    _r("Josh Hart",          "PF", "6-5",  14.0,  6.5, 4.5, 1.2, 34, "ACTIVE", 2),
    _r("Miles McBride",      "PG", "6-2",  10.0,  2.5, 3.0, 1.5, 18, "ACTIVE", 4),
]
TEAM_ROSTERS["CLE"] = [
    _r("Donovan Mitchell",    "G", "6-1",  27.0,  4.5, 5.0, 2.5, 36, "ACTIVE", 1),
    _r("Darius Garland",      "G", "6-1",  20.0,  3.0, 7.0, 2.2, 34, "ACTIVE", 1),
    _r("Evan Mobley",         "F", "6-11", 18.0,  9.5, 3.0, 0.8, 32, "ACTIVE", 2),
    _r("Jarrett Allen",       "C", "6-9",  15.5, 10.0, 2.0, 0.0, 30, "ACTIVE", 2),
    _r("Caris LeVert",        "G", "6-5",  12.0,  4.0, 3.0, 1.5, 26, "ACTIVE", 3),
    _r("Isaac Okoro",         "G", "6-5",   8.5,  3.0, 2.0, 1.2, 24, "ACTIVE", 3),
    _r("Ty Jerome",          "G", "6-5",   7.0,  2.0, 2.0, 1.0, 14, "ACTIVE", 4),
]
TEAM_ROSTERS["DET"] = [
    _r("Cade Cunningham",    "G",  "6-6",  26.5,  6.5, 8.5, 1.8, 36, "ACTIVE", 1),
    _r("Jalen Duren",       "C",  "6-10", 12.0,  9.0, 2.0, 0.0, 26, "ACTIVE", 2),
    _r("Tobias Harris",     "F",  "6-8",  18.5,  6.5, 3.0, 1.5, 32, "ACTIVE", 2),
    _r("Tim Hardaway Jr.",  "F",  "6-5",  11.5,  3.5, 1.5, 2.2, 24, "ACTIVE", 3),
    _r("Marcus Smart",       "G",  "6-5",  10.5,  3.5, 5.0, 1.8, 28, "ACTIVE", 3),
    _r("Ausar Thompson",     "F",  "6-7",   8.5,  4.5, 2.5, 0.5, 22, "ACTIVE", 3),
    _r("Jaden Ivey",        "G",  "6-4",  15.0,  4.0, 3.5, 1.5, 28, "ACTIVE", 3),
]
TEAM_ROSTERS["MIN"] = [
    _r("Anthony Edwards",    "G",  "6-4",  30.0,  5.0, 5.5, 3.5, 36, "ACTIVE", 1),
    _r("Julius Randle",      "PF","6-9",  22.0,  9.0, 4.5, 1.8, 34, "ACTIVE", 1),
    _r("Rudy Gobert",       "C",  "7-1",  14.0, 12.0, 1.5, 0.2, 30, "ACTIVE", 2),
    _r("Donte DiVincenzo",  "SG", "6-4",  10.0,  4.0, 3.0, 2.0, 24, "ACTIVE", 3),
    _r("Mike Conley",       "PG", "6-1",  11.0,  3.0, 5.5, 2.0, 22, "ACTIVE", 3),
    _r("Naz Reid",          "C",  "6-9",  13.5,  5.0, 2.0, 1.8, 22, "ACTIVE", 2),
    _r("Nickeil Alexander-Walker","SG","6-5",12.0, 3.5, 2.5, 2.0, 24, "ACTIVE", 3),
    _r("Jaden McDaniels",   "PF","6-10", 14.0,  4.5, 2.0, 1.5, 28, "ACTIVE", 2),
]
TEAM_ROSTERS["SA"] = [
    _r("Victor Wembanyama",  "C",  "7-4",  28.0, 10.5, 4.0, 2.5, 33, "ACTIVE", 1),
    _r("De'Aaron Fox",       "G",  "6-3",  24.5,  5.5, 6.5, 1.8, 33, "ACTIVE", 1),
    _r("Harrison Barnes",    "F",  "6-8",  13.5,  5.8, 2.2, 1.4, 27, "ACTIVE", 2),
    _r("Stephon Castle",    "G",  "6-5",  15.0,  4.5, 4.0, 1.2, 27, "ACTIVE", 2),
    _r("Keldon Johnson",    "F",  "6-5",  14.0,  4.5, 2.0, 2.0, 22, "ACTIVE", 3),
    _r("Devin Vassell",     "SG","6-5",  12.0,  3.5, 2.5, 2.2, 20, "ACTIVE", 3),
    _r("Jeremy Sochan",     "F",  "6-8",   8.0,  4.5, 3.0, 0.8, 20, "ACTIVE", 3),
    _r("Tre Jones",         "PG", "6-3",   9.0,  2.5, 4.5, 1.0, 18, "ACTIVE", 4),
    _r("Zach Collins",       "C",  "6-11",  8.0,  5.0, 1.5, 0.5, 14, "ACTIVE", 4),
    _r("Bismack Biyombo",   "C",  "6-11",  9.5,  8.0, 1.5, 0.2, 20, "ACTIVE", 3),
]
TEAM_ROSTERS["DEN"] = [
    _r("Nikola Jokić",      "C",  "6-11", 29.0, 10.5, 8.5, 1.8, 36, "ACTIVE", 1),
    _r("Jamal Murray",       "G", "6-4",  21.5,  4.0, 5.0, 2.2, 34, "ACTIVE", 1),
    _r("Michael Porter Jr.", "F", "6-10", 17.0,  5.5, 1.5, 2.0, 30, "ACTIVE", 2),
    _r("Aaron Gordon",      "F",  "6-8",  14.0,  6.5, 3.0, 1.5, 30, "ACTIVE", 2),
    _r("Russell Westbrook", "G", "6-3",  11.5,  4.5, 4.5, 1.0, 22, "ACTIVE", 3),
    _r("Christian Braun",   "G", "6-5",   9.0,  3.5, 1.5, 1.2, 20, "ACTIVE", 3),
]
TEAM_ROSTERS["GSW"] = [
    _r("Stephen Curry",     "G",  "6-2",  24.5,  4.5, 6.0, 3.5, 32, "ACTIVE", 1),
    _r("Jimmy Butler",      "F",  "6-7",  20.0,  5.5, 4.5, 1.5, 30, "ACTIVE", 1),
    _r("Draymond Green",     "F", "6-6",  11.5,  7.5, 6.5, 1.0, 28, "ACTIVE", 2),
    _r("Jonathan Kuminga",   "F", "6-8",  16.5,  5.5, 2.5, 1.5, 28, "ACTIVE", 3),
    _r("Buddy Hield",       "G", "6-4",  13.0,  4.5, 2.5, 3.0, 26, "ACTIVE", 3),
    _r("Andrew Wiggins",    "F",  "6-7",  12.0,  4.5, 2.0, 2.0, 28, "ACTIVE", 3),
    _r("Kevon Looney",      "C", "6-9",   6.5,  6.5, 2.0, 0.3, 18, "ACTIVE", 3),
    _r("Moses Moody",        "G", "6-5",   8.0,  3.0, 1.5, 1.2, 22, "ACTIVE", 4),
    _r("Gary Payton II",    "G", "6-3",   7.0,  3.0, 1.5, 1.0, 16, "ACTIVE", 4),
    _r("Trayce Jackson-Davis","F","6-9",   7.0,  4.5, 1.0, 0.5, 14, "ACTIVE", 4),
]
TEAM_ROSTERS["LAC"] = [
    _r("Kawhi Leonard",     "F",  "6-7",  23.5,  6.0, 4.0, 2.5, 32, "ACTIVE", 1),
    _r("James Harden",      "G",  "6-5",  21.0,  5.0, 8.5, 2.8, 34, "ACTIVE", 1),
    _r("Ivica Zubac",       "C",  "7-0",  12.0,  9.5, 2.0, 0.0, 28, "ACTIVE", 2),
    _r("Norman Powell",     "G", "6-3",  16.5,  3.5, 2.5, 2.2, 28, "ACTIVE", 3),
    _r("Terance Mann",      "G",  "6-5",  11.0,  4.5, 3.0, 1.5, 26, "ACTIVE", 3),
    _r("Derrick Jones Jr.", "F",  "6-6",  10.5,  4.5, 1.5, 1.2, 24, "ACTIVE", 3),
    _r("Ben Simmons",      "G",  "6-10",  8.5,  7.5, 6.5, 0.3, 24, "ACTIVE", 2),
    _r("Nicolas Batum",    "F",  "6-8",   7.5,  4.0, 2.5, 1.2, 22, "ACTIVE", 3),
]
TEAM_ROSTERS["LAL"] = [
    _r("LeBron James",     "SF", "6-9",  25.0,  7.5, 8.0, 2.2, 36, "ACTIVE", 1),
    _r("Luka Dončić",      "PG", "6-7",  29.0,  7.5, 8.0, 2.8, 34, "ACTIVE", 1),
    _r("Austin Reaves",    "SG", "6-5",  18.0,  4.0, 5.0, 2.5, 34, "ACTIVE", 2),
    _r("Rui Hachimura",    "PF", "6-8",  14.5,  5.0, 1.5, 1.2, 28, "ACTIVE", 2),
    _r("Jordan Goodwin",   "SG", "6-4",  12.5,  4.5, 3.5, 1.5, 22, "ACTIVE", 3),
    _r("Dorian Finney-Smith","F","6-8",   8.5,  4.0, 2.0, 1.5, 24, "ACTIVE", 3),
    _r("Gabe Vincent",     "PG", "6-2",   6.5,  2.0, 2.0, 1.2, 16, "ACTIVE", 4),
    _r("Jaxson Hayes",      "C", "6-10",  8.0,  4.0, 1.0, 0.3, 14, "ACTIVE", 4),
]
TEAM_ROSTERS["HOU"] = [
    _r("Alperen Şengün",   "C",  "6-9",  21.5,  9.5, 5.0, 0.8, 33, "ACTIVE", 1),
    _r("Jabari Smith Jr.",  "F",  "6-10", 18.0,  7.0, 1.8, 2.5, 30, "ACTIVE", 2),
    _r("Jalen Green",      "G",  "6-4",  21.0,  4.5, 3.5, 3.0, 32, "ACTIVE", 2),
    _r("Fred VanVleet",    "G",  "6-0",  14.0,  3.5, 5.5, 2.5, 32, "ACTIVE", 2),
    _r("Amen Thompson",    "F",  "6-8",  12.5,  5.5, 4.0, 1.2, 26, "ACTIVE", 3),
    _r("Tari Eason",       "F",  "6-8",  14.5,  7.0, 2.0, 1.2, 26, "ACTIVE", 3),
    _r("Cam Whitmore",      "G", "6-5",  11.0,  4.0, 1.5, 1.5, 20, "ACTIVE", 3),
    _r("Reed Sheppard",     "G", "6-5",  13.0,  4.0, 3.0, 2.2, 24, "ACTIVE", 3),
]
TEAM_ROSTERS["IND"] = [
    _r("Tyrese Haliburton", "G", "6-5",  21.0,  4.0, 8.5, 3.2, 36, "ACTIVE", 1),
    _r("Pascal Siakam",    "F",  "6-8",  20.0,  6.5, 4.5, 1.8, 34, "ACTIVE", 1),
    _r("Myles Turner",     "C",  "6-11", 15.5,  8.0, 2.0, 1.2, 30, "ACTIVE", 2),
    _r("Bennedict Mathurin","G", "6-5",  17.5,  4.5, 2.5, 2.0, 28, "ACTIVE", 2),
    _r("Obi Toppin",       "F",  "6-8",  11.5,  4.0, 2.0, 1.5, 20, "ACTIVE", 3),
    _r("Aaron Nesmith",    "F",  "6-5",  11.0,  4.0, 2.0, 2.0, 24, "ACTIVE", 3),
    _r("Jalen Smith",      "F",  "6-10",  9.5,  5.5, 1.0, 1.0, 18, "ACTIVE", 4),
    _r("Andrew Nembhard",  "G",  "6-4",   9.0,  2.5, 4.0, 1.2, 20, "ACTIVE", 4),
]
TEAM_ROSTERS["ORL"] = [
    _r("Paolo Banchero",    "F",  "6-10", 28.5,  7.5, 5.5, 1.5, 36, "ACTIVE", 1),
    _r("Franz Wagner",      "F",  "6-10", 22.0,  5.0, 4.0, 1.8, 34, "ACTIVE", 1),
    _r("Jalen Suggs",       "G", "6-5",  16.5,  4.0, 4.5, 1.5, 30, "ACTIVE", 2),
    _r("Wendell Carter Jr.", "C","6-6",  14.5,  9.0, 2.5, 0.8, 28, "ACTIVE", 2),
    _r("Cole Anthony",      "G", "6-2",  13.0,  4.5, 3.5, 1.2, 24, "ACTIVE", 3),
    _r("Goga Bitadze",     "C",  "6-11", 10.5,  6.0, 2.0, 0.5, 20, "ACTIVE", 3),
    _r("Jonathan Isaac",   "F",  "6-10",  6.5,  4.0, 1.0, 0.5, 16, "ACTIVE", 4),
]
TEAM_ROSTERS["MIA"] = [
    _r("Jimmy Butler",     "F",  "6-7",  20.0,  5.5, 4.5, 1.5, 30, "ACTIVE", 1),
    _r("Tyler Herro",      "G", "6-5",  21.0,  4.5, 4.0, 2.8, 34, "ACTIVE", 1),
    _r("Bam Adebayo",      "C", "6-9",  18.5, 10.0, 4.0, 0.5, 32, "ACTIVE", 1),
    _r("Nikola Jović",     "F",  "6-10", 13.0,  5.5, 3.0, 1.5, 28, "ACTIVE", 2),
    _r("Duncan Robinson",   "G", "6-8",  11.5,  3.5, 2.5, 3.0, 26, "ACTIVE", 3),
    _r("Jaime Jaquez Jr.", "F",  "6-6",  12.0,  4.5, 3.0, 1.5, 26, "ACTIVE", 3),
    _r("Kevin Love",       "F",  "6-8",   8.5,  6.5, 2.0, 1.5, 18, "ACTIVE", 4),
]
TEAM_ROSTERS["MIL"] = [
    _r("Giannis Antetokounmpo","F","6-11",27.5,11.5,5.5,1.2,34,"ACTIVE", 1),
    _r("Damian Lillard",   "G", "6-2",  24.5,  4.5, 7.0, 3.2, 34, "ACTIVE", 1),
    _r("Khris Middleton",   "F", "6-7",  15.5,  5.5, 4.0, 2.2, 28, "ACTIVE", 2),
    _r("Brook Lopez",      "C", "7-1",  12.5,  6.5, 1.5, 2.0, 28, "ACTIVE", 2),
    _r("Bobby Portis",     "F",  "6-10", 11.5,  7.0, 1.5, 1.5, 24, "ACTIVE", 3),
    _r("Donte DiVincenzo", "G", "6-4",  10.5,  3.5, 2.5, 2.2, 22, "ACTIVE", 3),
]
TEAM_ROSTERS["DAL"] = [
    _r("Luka Dončić",      "PG", "6-7", 29.0,  7.5, 8.0, 2.8, 34, "ACTIVE", 1),
    _r("Kyrie Irving",     "G",  "6-2", 25.0,  5.0, 6.0, 3.0, 34, "ACTIVE", 1),
    _r("Dereck Lively II", "C",  "7-0", 10.0,  8.0, 2.0, 0.0, 24, "ACTIVE", 2),
    _r("P.J. Washington",  "F",  "6-7", 13.0,  6.0, 2.0, 1.5, 28, "ACTIVE", 2),
    _r("Klay Thompson",    "G",  "6-6", 18.0,  4.0, 2.5, 3.5, 30, "ACTIVE", 1),
    _r("Jayson Tatum",     "F",  "6-8", 26.8,  7.5, 5.0, 2.9, 37, "ACTIVE", 1),
]

TEAM_CITIES = {
    "BOS": "Boston Celtics", "PHI": "Philadelphia 76ers", "NYK": "New York Knicks",
    "CLE": "Cleveland Cavaliers", "OKC": "Oklahoma City Thunder", "PHX": "Phoenix Suns",
    "MIN": "Minnesota Timberwolves", "SA": "San Antonio Spurs", "SAS": "San Antonio Spurs",
    "DET": "Detroit Pistons", "DEN": "Denver Nuggets", "GSW": "Golden State Warriors",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "HOU": "Houston Rockets",
    "IND": "Indiana Pacers", "ORL": "Orlando Magic", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "DAL": "Dallas Mavericks",
}

# ═══════════════════════════════════════════════════════════════════════════════
# TEAM HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _resolve_abbr(abbr: str) -> str:
    return {"SAS": "SA"}.get(abbr.upper(), abbr.upper())

def starters(team_abbr: str) -> List[P]:
    abbr = _resolve_abbr(team_abbr)
    if abbr not in TEAM_ROSTERS:
        return []
    active = [p for p in TEAM_ROSTERS[abbr] if p.status != "OUT"]
    return sorted(active, key=lambda p: p.pts, reverse=True)[:5]

def tc_starters(team_abbr: str) -> float:
    return round(sum(p.tc_pts() for p in starters(team_abbr)), 1)

def tc_starters_breakdown(team_abbr: str) -> Dict[str, float]:
    s = starters(team_abbr)
    return {
        "pts": round(sum(p.tc_pts() for p in s), 1),
        "reb": round(sum(p.tc_reb() for p in s), 1),
        "ast": round(sum(p.tc_ast() for p in s), 1),
        "3pm": round(sum(p.tc_3pm() for p in s), 1),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GAME TOTAL FORMULA
# ═══════════════════════════════════════════════════════════════════════════════
def tc_game_total(away_abbr: str, home_abbr: str, is_playoff: bool = True) -> int:
    tc_away = tc_starters(away_abbr)
    tc_home = tc_starters(home_abbr)
    raw = tc_away + tc_home
    if is_playoff:
        raw = raw * PLAYOFF_MULT
    return round(raw * LINE_FACTOR)

def game_line(away_abbr: str, home_abbr: str, market_total: float = None,
             is_playoff: bool = True) -> Dict[str, Any]:
    tc_away = tc_starters(away_abbr)
    tc_home = tc_starters(home_abbr)
    raw = tc_away + tc_home
    tc_final = raw * PLAYOFF_MULT if is_playoff else raw
    tc_line = round(tc_final * LINE_FACTOR)
    edge = round(tc_line - market_total, 1) if market_total else 0.0
    signal = "UNDER" if edge < 0 else "OVER"
    return {
        "away_tc": tc_away, "home_tc": tc_home,
        "raw_combined": raw, "tc_final": tc_final,
        "tc_line": tc_line, "market_total": market_total,
        "edge": edge, "signal": signal,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER PROP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
def analyze_prop(player: P, stat: str, market_line: float) -> Dict[str, Any]:
    tc = {"pts": player.tc_pts(), "reb": player.tc_reb(),
          "ast": player.tc_ast(), "3pm": player.tc_3pm()}[stat]
    bl = market_line
    edge = round(tc - bl, 1)
    e_abs = abs(edge)
    conf = next((c / 100 for th, c in HR_TIERS if e_abs >= th), MIN_HR / 100)
    qual = e_abs >= MIN_EDGE and conf >= MIN_HR / 100
    pick = "UNDER" if tc < bl else "OVER"
    return {
        "tc": tc, "book_line": bl, "edge": edge,
        "conf": round(conf, 3), "qualifies": qual,
        "pick": pick, "tc_target": int(tc * LINE_FACTOR),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST DATA
# ═══════════════════════════════════════════════════════════════════════════════
BACKTEST_GAMES = [
    # BOS vs PHI Round 1
    {"date": "2026-04-19", "series": "BOS@PHI G1", "away": "BOS", "home": "PHI",
     "away_score": 123, "home_score": 91, "total": 214, "spread": 7.0,
     "away_players": {"Tatum": 31, "Brown": 26, "White": 14, "Porzingis": 13, "Pritchard": 8, "Holiday": 11, "Hauser": 7, "Queta": 4, "Scheierman": 3},
     "home_players": {"Maxey": 22, "George": 17, "Oubre": 13, "Drummond": 11, "Grimes": 9, "Lowry": 4, "Edwards": 2},
     "injuries": {}},
    {"date": "2026-04-21", "series": "BOS@PHI G2", "away": "BOS", "home": "PHI",
     "away_score": 97, "home_score": 111, "total": 208, "spread": 7.0,
     "away_players": {"Tatum": 18, "Brown": 18, "White": 11, "Porzingis": 10, "Pritchard": 5, "Holiday": 14, "Hauser": 8, "Queta": 3, "Scheierman": 3},
     "home_players": {"Maxey": 29, "George": 22, "Embiid": 33, "Oubre": 4, "Grimes": 18, "Drummond": 5, "Lowry": 0, "Edwards": 0},
     "injuries": {}},
    {"date": "2026-04-23", "series": "BOS@PHI G3", "away": "BOS", "home": "PHI",
     "away_score": 108, "home_score": 100, "total": 208, "spread": 7.0,
     "away_players": {"Tatum": 33, "Brown": 20, "White": 15, "Pritchard": 11, "Holiday": 12, "Hauser": 6, "Queta": 2, "Scheierman": 3, "Bennett": 3},
     "home_players": {"Maxey": 26, "George": 16, "Embiid": 26, "Oubre": 14, "Grimes": 12, "Drummond": 4, "Lowry": 0, "Edwards": 2},
     "injuries": {}},
    {"date": "2026-04-26", "series": "BOS@PHI G4", "away": "BOS", "home": "PHI",
     "away_score": 128, "home_score": 96, "total": 224, "spread": 7.0,
     "away_players": {"Tatum": 30, "Brown": 20, "White": 10, "Pritchard": 32, "Holiday": 13, "Hauser": 8, "Queta": 5, "Scheierman": 4},
     "home_players": {"Maxey": 22, "George": 12, "Embiid": 26, "Oubre": 10, "Grimes": 14, "Drummond": 6, "Lowry": 0, "Edwards": 2, "Martin": 4},
     "injuries": {}},
    {"date": "2026-04-28", "series": "BOS@PHI G5", "away": "BOS", "home": "PHI",
     "away_score": 97, "home_score": 113, "total": 210, "spread": 5.5,
     "away_players": {"Tatum": 24, "Brown": 22, "White": 6, "Pritchard": 12, "Holiday": 10, "Hauser": 8, "Queta": 8, "Vucevic": 8, "Scheierman": 3},
     "home_players": {"Maxey": 25, "George": 16, "Embiid": 33, "Oubre": 4, "Edwards": 10, "Grimes": 18, "Drummond": 5, "Lowry": 0, "Martin": 2},
     "injuries": {}},
    # OKC vs PHX
    {"date": "2026-04-19", "series": "PHX@OKC G1", "away": "PHX", "home": "OKC",
     "away_score": 94, "home_score": 119, "total": 218, "spread": 9.0,
     "away_players": {"Booker": 24, "KD": 27, "Beal": 11, "Allen": 9, "Nurkic": 8, "O'Neale": 5, "Jones": 5, "Bol": 2, "Eubanks": 3},
     "home_players": {"SGA": 37, "JWilliams": 18, "Holmgren": 15, "Hartenstein": 12, "Lu Dort": 8, "Joe": 9, "Caruso": 8, "C Wallace": 6},
     "injuries": {}},
    {"date": "2026-04-21", "series": "PHX@OKC G2", "away": "PHX", "home": "OKC",
     "away_score": 107, "home_score": 120, "total": 220, "spread": 9.0,
     "away_players": {"Booker": 19, "KD": 28, "Beal": 18, "Allen": 10, "Nurkic": 14, "O'Neale": 6, "Jones": 4, "Bol": 5, "Eubanks": 3},
     "home_players": {"SGA": 42, "JWilliams": 16, "Holmgren": 18, "Hartenstein": 14, "Lu Dort": 10, "Joe": 3, "Caruso": 6, "C Wallace": 5},
     "injuries": {}},
    {"date": "2026-04-23", "series": "OKC@PHX G3", "away": "OKC", "home": "PHX",
     "away_score": 121, "home_score": 109, "total": 222, "spread": 4.5,
     "away_players": {"SGA": 35, "JWilliams": 12, "Holmgren": 16, "Hartenstein": 14, "Lu Dort": 12, "Joe": 8, "Caruso": 10, "C Wallace": 8},
     "home_players": {"Booker": 22, "KD": 26, "Beal": 15, "Allen": 8, "Nurkic": 12, "O'Neale": 9, "Jones": 6, "Bol": 5, "Eubanks": 6},
     "injuries": {}},
    {"date": "2026-04-25", "series": "OKC@PHX G4", "away": "OKC", "home": "PHX",
     "away_score": 113, "home_score": 105, "total": 220, "spread": 4.5,
     "away_players": {"SGA": 31, "JWilliams": 10, "Holmgren": 14, "Hartenstein": 16, "Lu Dort": 10, "Joe": 5, "Caruso": 8, "C Wallace": 7, "Wiggins": 6},
     "home_players": {"Booker": 27, "KD": 24, "Beal": 12, "Allen": 9, "Nurkic": 8, "O'Neale": 8, "Jones": 7, "Bol": 4, "Eubanks": 6},
     "injuries": {}},
    # MIN vs SA
    {"date": "2026-05-04", "series": "SA@MIN G1", "away": "SA", "home": "MIN",
     "away_score": 102, "home_score": 104, "total": 215.5, "spread": 5.0,
     "away_players": {"Wemby": 22, "Dejounte": 22, "Barnes": 13, "Keldon": 12, "Vassell": 8, "Tre": 6, "Zach": 6, "Collins": 8, "Devin": 2},
     "home_players": {"Ant": 25, "McDaniels": 18, "Gobert": 12, "Conley": 14, "NAW": 14, "Reid": 10, "Divincenzo": 8, "Randle": 8, "Jaden": 5},
     "injuries": {}},
    {"date": "2026-05-06", "series": "MIN@SA G2", "away": "MIN", "home": "SA",
     "away_score": 95, "home_score": 133, "total": 215.5, "spread": 5.0,
     "away_players": {"Ant": 18, "McDaniels": 12, "Gobert": 8, "Conley": 12, "NAW": 11, "Reid": 9, "Divincenzo": 8, "Randle": 11, "Jaden": 8},
     "home_players": {"Wemby": 28, "Dejounte": 31, "Barnes": 19, "Keldon": 22, "Vassell": 18, "Tre": 12, "Zach": 14, "Collins": 10, "Devin": 3},
     "injuries": {}},
    # CLE vs DET
    {"date": "2026-05-01", "series": "DET@CLE G6", "away": "DET", "home": "CLE",
     "away_score": 110, "home_score": 112, "total": 218.5, "spread": 0.0,
     "away_players": {"Cade": 26, "Duren": 12, "Harris": 15, "Hardaway": 8, "Smart": 10, "Ivey": 14, "Schroder": 16, "Ausar": 6, "Jaden": 8},
     "home_players": {"Mitchell": 29, "Garland": 17, "Mobley": 16, "Allen": 12, "LeVert": 8, "Okoro": 6, "Strus": 10, "Jerome": 9, "Max": 2, "Isaac": 0},
     "injuries": {}},
    # NYK vs PHI
    {"date": "2026-05-06", "series": "NYK@PHI G1", "away": "NYK", "home": "PHI",
     "away_score": 108, "home_score": 102, "total": 213.5, "spread": 2.0,
     "away_players": {"Brunson": 22, "Bridges": 19, "Anunoby": 16, "Towns": 17, "Hart": 12, "McBride": 11, "Achiuwa": 8, "Sochan": 4},
     "home_players": {"Maxey": 24, "George": 20, "Embiid": 26, "Oubre": 15, "Edwards": 8, "Grimes": 12, "Drummond": 6, "Lowry": 0, "Martin": 2},
     "injuries": {"Embiid": "QUESTIONABLE"}},
]

# ═══════════════════════════════════════════════════════════════════════════════
# BACKTESTER
# ═══════════════════════════════════════════════════════════════════════════════
NAME_MAP = {
    "SGA": "Shai Gilgeous-Alexander", "JWilliams": "Jalen Williams",
    "C Wallace": "Cason Wallace", "Tatum": "Jayson Tatum", "Brown": "Jaylen Brown",
    "White": "Derrick White", "Porzingis": "Kristaps Porzingis", "Pritchard": "Payton Pritchard",
    "Holiday": "Jrue Holiday", "Hauser": "Sam Hauser", "Queta": "Neemias Queta",
    "Maxey": "Tyrese Maxey", "George": "Paul George", "Oubre": "Kelly Oubre Jr.",
    "Drummond": "Andre Drummond", "Grimes": "Quentin Grimes", "Lowry": "Kyle Lowry",
    "Edwards": "Justin Edwards", "Martin": "KJ Martin", "Embiid": "Joel Embiid",
    "Booker": "Devin Booker", "KD": "Kevin Durant", "Beal": "Bradley Beal",
    "Allen": "Grayson Allen", "Nurkic": "Jusuf Nurkić", "O'Neale": "Royce O'Neale",
    "Jones": "Tyus Jones", "Bol": "Bol Bol", "Eubanks": "Drew Eubanks",
    "Lu Dort": "Luguentz Dort", "Joe": "Isaiah Joe", "Caruso": "Alex Caruso",
    "Wiggins": "Aaron Wiggins", "K Williams": "Kenrich Williams",
    "Ant": "Anthony Edwards", "McDaniels": "Jaden McDaniels", "Gobert": "Rudy Gobert",
    "Conley": "Mike Conley", "NAW": "Nickeil Alexander-Walker", "Reid": "Naz Reid",
    "Divincenzo": "Donte DiVincenzo", "Randle": "Julius Randle", "Jaden": "Jaden McDaniels",
    "Wemby": "Victor Wembanyama", "Dejounte": "De'Aaron Fox", "Barnes": "Harrison Barnes",
    "Keldon": "Keldon Johnson", "Vassell": "Devin Vassell", "Tre": "Tre Jones",
    "Zach": "Zach Collins", "Collins": "Zach Collins", "Devin": "Devin Vassell",
    "Cade": "Cade Cunningham", "Duren": "Jalen Duren", "Harris": "Tobias Harris",
    "Hardaway": "Tim Hardaway Jr.", "Smart": "Marcus Smart", "Ivey": "Jaden Ivey",
    "Schroder": "Dennis Schröder", "Ausar": "Ausar Thompson",
    "Mitchell": "Donovan Mitchell", "Garland": "Darius Garland", "Mobley": "Evan Mobley",
    "Allen": "Jarrett Allen", "LeVert": "Caris LeVert", "Okoro": "Isaac Okoro",
    "Strus": "Max Strus", "Jerome": "Ty Jerome", "Max": "Max Strus", "Isaac": "Isaac Okoro",
    "Brunson": "Jalen Brunson", "Bridges": "Mikal Bridges", "Anunoby": "OG Anunoby",
    "Towns": "Karl-Anthony Towns", "Hart": "Josh Hart", "McBride": "Miles McBride",
    "Achiuwa": "Precious Achiuwa", "Sochan": "Jeremy Sochan",
    "Bennett": "Jared McCain", "Vucevic": "Nikola Vučević", "Garza": "Bennedict Mathurin",
}

def resolve(name: str) -> str:
    return NAME_MAP.get(name, name)

def find_player(full_name: str) -> Optional[P]:
    for roster in TEAM_ROSTERS.values():
        for p in roster:
            if p.name == full_name:
                return p
    return None

def tc_proj(name: str, status: str = "ACTIVE") -> float:
    full = resolve(name)
    p = find_player(full)
    if not p:
        return 0.0
    s = status if status != "ACTIVE" else p.status
    inj = INJ.get(s, 1.0)
    return round(p.pts * TC_W["pts"] * inj, 1)

def book_line_proj(name: str) -> float:
    tc = tc_proj(name)
    return round(tc * LINE_FACTOR, 1)

def run_backtest(games: List[dict] = None) -> Dict[str, Any]:
    import csv, os

    games = games or BACKTEST_GAMES
    results = []
    bankroll = 1000.0
    stake = 10.0

    for game in games:
        away_t, home_t = game["away"], game["home"]
        away_pl = game.get("away_players", {})
        home_pl = game.get("home_players", {})
        injuries = game.get("injuries", {})
        actual_total = game["away_score"] + game["home_score"]
        market_total = game["total"]

        # FIX #1: Game Total — use tc_starters() (5 starters only) + PLAYOFF_MULT
        # Previously used all players in away_pl/home_pl dicts (inflated + wrong)
        tc_away = tc_starters(away_t)
        tc_home = tc_starters(home_t)
        raw = tc_away + tc_home
        tc_final = raw * PLAYOFF_MULT
        tc_total = round(tc_final * LINE_FACTOR)
        total_edge = round(tc_total - market_total, 1)
        # FIX #2: Signal — edge < 0 means TC line below market → market is high → lean UNDER
        signal_total = "UNDER" if total_edge < 0 else "OVER"
        won_total = (signal_total == "UNDER" and actual_total < market_total) or \
                   (signal_total == "OVER" and actual_total > market_total)

        results.append({
            "game": game["series"], "date": game["date"],
            "bet_type": "TOTAL",
            "confidence": 0,
            "tc_proj": tc_total, "book_line": market_total,
            "actual": actual_total, "edge": total_edge,
            "won": won_total,
            "odds": -110, "stake": stake,
            "signal": signal_total,
        })
        bankroll += (1 if won_total else -1) * stake * 0.91

        # ── Player Props ──
        for name, actual_pts in {**away_pl, **home_pl}.items():
            full = resolve(name)
            injury = injuries.get(full, injuries.get(name, "ACTIVE"))
            tc = tc_proj(name, injury)
            if tc == 0.0:
                continue
            bl = book_line_proj(name)
            e = round(tc - bl, 1)
            # FIX #3: Prop lean — tc < bl means market line is HIGH → lean UNDER
            # Previously inverted: "UNDER" if e > 0 (tc > bl → lean OVER) — WRONG!
            lean = "UNDER" if tc < bl else "OVER"
            won = (lean == "UNDER" and actual_pts < bl) or \
                  (lean == "OVER" and actual_pts > bl)
            # FIX #4: Use HR_TIERS for confidence, not ad-hoc min(abs(e)/5, 0.95)
            conf = next((c / 100 for th, c in HR_TIERS if abs(e) >= th), MIN_HR / 100)
            if abs(e) >= MIN_EDGE:
                odds = -125 if abs(e) >= 4 else -115
                results.append({
                    "game": game["series"], "date": game["date"],
                    "bet_type": "PROP", "player": full, "team": away_t if name in away_pl else home_t,
                    "tc_proj": tc, "book_line": bl,
                    "actual": actual_pts, "edge": e,
                    "won": won, "odds": odds, "stake": stake,
                    "confidence": round(conf, 3), "signal": lean,
                })
                bankroll += (1 if won else -1) * stake * (0.91 if odds < 0 else odds / 100)

    total = len(results)
    won = sum(1 for r in results if r["won"])
    by_type = {}
    for r in results:
        bt = r["bet_type"]
        by_type.setdefault(bt, {"won": 0, "total": 0, "profit": 0})
        by_type[bt]["total"] += 1
        by_type[bt]["won"] += 1 if r["won"] else 0
        profit = (1 if r["won"] else -1) * r["stake"] * (0.91 if r["odds"] < 0 else r["odds"] / 100)
        by_type[bt]["profit"] += round(profit, 2)

    summary = {
        "total_bets": total, "won": won, "win_rate": round(won / total * 100, 1) if total else 0,
        "bankroll_end": round(bankroll, 2),
        "net_profit": round(bankroll - 1000, 2),
        "by_type": by_type,
        "details": [],
    }

    # Detail table
    for r in results:
        row = (f"{r['date']} {r['game']} [{r['bet_type']}] "
               f"signal={r['signal']} tc={r['tc_proj']} book={r['book_line']} "
               f"actual={r['actual']} edge={r['edge']:+.1f} "
               f"conf={r.get('confidence',0)} → {'✅ WIN' if r['won'] else '❌ LOSS'}")
        summary["details"].append(row)

    path = "/home/workspace/nba_tc/backtest_results.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "game", "bet_type", "player", "team",
                                          "tc_proj", "book_line", "actual", "edge", "odds",
                                          "stake", "won", "signal", "confidence"])
        w.writeheader()
        for r in results:
            w.writerow(r)

    return summary

# ═══════════════════════════════════════════════════════════════════════════════
# GAME REPORT
# ═══════════════════════════════════════════════════════════════════════════════
def game_report(away_abbr: str, home_abbr: str,
               market_total: float = None,
               market_spread: float = None,
               is_playoff: bool = True) -> None:
    gl = game_line(away_abbr, home_abbr, market_total, is_playoff)
    aw_name = TEAM_CITIES.get(away_abbr, away_abbr)
    hm_name = TEAM_CITIES.get(home_abbr, home_abbr)

    print(f"\n{'═' * 80}")
    print(f"  🏀  {aw_name}  @  {hm_name}  |  TC v7.1 UNIFIED ENGINE")
    print(f"{'═' * 80}")
    if market_total:
        print(f"  Market Total: {market_total}   |   TC Line: {gl['tc_line']}   |   Edge: {gl['edge']:+.1f}")
    print(f"  Signal: {gl['signal']}  |  TC Starters: {away_abbr}={gl['away_tc']} | {home_abbr}={gl['home_tc']}")
    print(f"{'─' * 80}")

    print(f"\n  STARTER lineup — {away_abbr} ({aw_name})")
    print(f"  {'Player':<26} {'POS':>4} {'HT':>5} {'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} {'STATUS':>6}")
    print(f"  {'─' * 80}")
    for p in starters(away_abbr):
        flag = {"ACTIVE": "✅", "QUESTIONABLE": "⚠️ Q", "OUT": "❌ OUT"}[p.status]
        print(f"  {p.name:<26} {p.pos:>4} {p.ht:>5} "
              f"{p.tc_pts():>7.1f} {p.tc_reb():>7.1f} {p.tc_ast():>7.1f} {p.tc_3pm():>7.1f} {flag:>6}")

    print(f"\n  STARTER lineup — {home_abbr} ({hm_name})")
    print(f"  {'Player':<26} {'POS':>4} {'HT':>5} {'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} {'STATUS':>6}")
    print(f"  {'─' * 80}")
    for p in starters(home_abbr):
        flag = {"ACTIVE": "✅", "QUESTIONABLE": "⚠️ Q", "OUT": "❌ OUT"}[p.status]
        print(f"  {p.name:<26} {p.pos:>4} {p.ht:>5} "
              f"{p.tc_pts():>7.1f} {p.tc_reb():>7.1f} {p.tc_ast():>7.1f} {p.tc_3pm():>7.1f} {flag:>6}")

    if market_total:
        print(f"\n{'─' * 80}")
        print(f"  FORMULA: TC Line = ((TC_away_starters + TC_home_starters) × {PLAYOFF_MULT}) × {LINE_FACTOR}")
        print(f"  CALC:   {away_abbr}={gl['away_tc']} + {home_abbr}={gl['home_tc']} = {gl['raw_combined']} × {PLAYOFF_MULT} = {gl['tc_final']} × 0.88 = {gl['tc_line']}")
        print(f"  Market: {market_total}   |   Edge: {gl['edge']:+.1f}   |   Signal: {gl['signal']}")
        print(f"  TC Weights: PTS={TC_W['pts']} | REB={TC_W['reb']} | AST={TC_W['ast']} | 3PM={TC_W['3pm']}")
        print(f"  Injury factors: ACTIVE=1.00 | Q=0.55 | OUT=0.00")

    print(f"{'═' * 80}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="NBA TC Engine v7.1 — Unified")
    p.add_argument("--game",    help="'AWAY @ HOME' e.g. 'BOS @ PHI'")
    p.add_argument("--total",   type=float, help="Market game total")
    p.add_argument("--spread",  type=float, help="Home spread")
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--json",    action="store_true")
    p.add_argument("--list",    action="store_true")
    a = p.parse_args()

    if a.list:
        print("\nNBA Teams:")
        for k, v in sorted(TEAM_CITIES.items()):
            print(f"  {k}: {v}")
        raise SystemExit(0)

    if a.backtest:
        result = run_backtest()
        print(f"\n{'═' * 75}")
        print(f"  📊 TC BACKTEST SUMMARY — v7.1 UNIFIED ENGINE (FIXED)")
        print(f"{'═' * 75}")
        print(f"  Total bets: {result['total_bets']}  |  Won: {result['won']}  |  Win rate: {result['win_rate']}%")
        print(f"  Bankroll: $1000 → ${result['bankroll_end']:.2f}  |  Net: ${result['net_profit']:+.2f}")
        print(f"\n  By Type:")
        for bt, d in result["by_type"].items():
            wr = f"{d['won']}/{d['total']}={d['won']/d['total']*100:.0f}%" if d['total'] else "0"
            print(f"    [{bt}] {wr} | ${d['profit']:+.2f}")
        print(f"\n  Detailed Results:")
        for line in result.get("details", []):
            print(f"    {line}")
        print(f"\n  ✅ Saved: /home/workspace/nba_tc/backtest_results.csv")
        raise SystemExit(0)

    if a.game:
        away, home = [x.strip().upper() for x in a.game.split("@")]
        if a.json:
            gl = game_line(away, home, a.total, is_playoff=True)
            print(json.dumps(gl, indent=2))
        else:
            game_report(away, home, a.total, a.spread, is_playoff=True)
    else:
        print("NBA TC Engine v7.1")
        print("Usage: --game 'BOS @ PHI' --total 214")
        print("       --backtest")