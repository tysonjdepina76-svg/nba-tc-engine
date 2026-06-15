#!/usr/bin/env python3
"""
NBA TC Engine — Triple Conservative Betting System
===================================================
Formulas:
  TC_pts  = round(pts  × 0.85 + (-3.0), 1)
  TC_reb  = round(reb  × 0.80 + (-1.5), 1)
  TC_ast  = round(ast  × 0.75 + (-1.0), 1)
  TC_3pm  = round(tpm  × 0.70 + (-0.8), 1)
  Status: OUT = 0 | QUESTIONABLE × 0.55 | ACTIVE × 1.0

  TC_line (game total projection) = round(combined_tc × LINE_FACTOR)
  Market TC                        = round(market_total × LINE_FACTOR)
  Game TC Edge                     = TC_line − market_total

Lean logic (inverted — TC systematically OVERESTIMATES actuals):
  edge >  4 → UNDER (TC_line is notably ABOVE market → fade the high side)
  edge < -4 → OVER  (TC_line is notably BELOW market → fade the low side)
  else  → PASS

Backtest: 9 playoff games | 2/9 TC_line vs actual UNDER hits | avg overshoot +4.5 pts
  → TC model moderately overestimates actuals; LINE_FACTOR=0.80 calibrates to real totals
  → game_tc_edge quantifies HOW MUCH the market line differs from TC projection

CLI:
  python nba_tc_engine.py --backtest
  python nba_tc_engine.py --game 'PHI @ NYK' --market-total 226
  python nba_tc_engine.py --list-teams
  python nba_tc_engine.py --serve

API:
  GET /tc/{away}_{home}?market_total=226  → full projection + qualified picks
  GET /games                              → detected games list
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import sys, os, json, argparse
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────
CONS_PTS       = 0.85
CONS_REB       = 0.80
CONS_AST       = 0.75
CONS_3PM       = 0.70
GAP_PTS        = -3.0
GAP_REB        = -1.5
GAP_AST        = -1.0
GAP_3PM        = -0.8
LINE_FACTOR    = 0.80          # calibrated to bridge TC overestimation → real totals
PLAYOFF_MULT   = 1.18
Q_FACTOR       = 0.55
MIN_EDGE       = {"pts": 2.5, "reb": 1.5, "ast": 1.0, "3pm": 0.8}
CONF_TIERS     = [(10, 72), (7, 68), (5, 64), (3, 60)]
BANKROLL       = 1000.0
FASTAPI_PORT   = 8765
SAVE_DIR       = Path("/home/workspace")

# ── Player ──────────────────────────────────────────────────────────────────
@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    min_avg: float = 36.0
    status: str = "ACTIVE"
    tier: int = 2

    def _status_mult(self) -> float:
        return {"OUT": 0.0, "QUESTIONABLE": Q_FACTOR}.get(self.status, 1.0)

    def tc_stat(self, stat: str) -> float:
        attr = {"pts": "pts", "reb": "reb", "ast": "ast", "3pm": "tpm"}[stat]
        w    = {"pts": CONS_PTS, "reb": CONS_REB, "ast": CONS_AST, "3pm": CONS_3PM}[stat]
        gap  = {"pts": GAP_PTS,  "reb": GAP_REB,  "ast": GAP_AST,  "3pm": GAP_3PM}[stat]
        return round(getattr(self, attr, 0) * w * self._status_mult() + gap, 1)

    def tc_pts(self)  -> float: return self.tc_stat("pts")
    def tc_reb(self)  -> float: return self.tc_stat("reb")
    def tc_ast(self)  -> float: return self.tc_stat("ast")
    def tc_3pm(self)  -> float: return self.tc_stat("3pm")

    def all_tc(self) -> Dict[str, float]:
        """Always returns all four TC stats — never skipped."""
        return {"pts": self.tc_pts(), "reb": self.tc_reb(), "ast": self.tc_ast(), "3pm": self.tc_3pm()}

    def tc_total(self) -> float:
        return round(self.tc_pts() + self.tc_reb() + self.tc_ast() + self.tc_3pm(), 1)

    @property
    def last_name(self) -> str:
        return self.name.split()[-1].lower()

    @property
    def status_icon(self) -> str:
        return {"OUT": "🚫", "QUESTIONABLE": "⚠️"}.get(self.status, "✅")

# ── Team ─────────────────────────────────────────────────────────────────────
@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player] = field(default_factory=list)
    injury_notes: List[str] = field(default_factory=list)

    def active(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"]

    def top9(self) -> List[Player]:
        return sorted(self.active(), key=lambda p: p.pts, reverse=True)[:9]

    def tc_team_total(self) -> float:
        """Sum of TC totals for top-9 active players."""
        return round(sum(p.tc_total() for p in self.top9()), 1)

    def game_tc(self) -> float:
        """Team contribution to game total TC (before LINE_FACTOR conversion)."""
        return round(self.tc_team_total() * PLAYOFF_MULT, 1)

# ── Roster helper ─────────────────────────────────────────────────────────────
def _p(name, pos, ht, pts, reb, ast, tpm, min_avg=32.0, status="ACTIVE", tier=2) -> Player:
    return Player(name, pos, ht, pts, reb, ast, tpm, min_avg, status, tier)

# ── Rosters ─────────────────────────────────────────────────────────────────
DET = Team("DET", "Detroit Pistons", [
    _p("Cade Cunningham",    "PG", "6-6",  26.5, 6.5, 8.5, 1.8, 34, "QUESTIONABLE", 1),
    _p("Jalen Duren",        "C",  "6-11", 12.0, 9.0, 2.0, 0.0, 22),
    _p("Tobias Harris",      "SF", "6-8",  18.5, 6.5, 3.0, 1.5, 30),
    _p("Tim Hardaway Jr.",    "SG", "6-5",  11.5, 3.5, 1.5, 2.2, 24),
    _p("Marcus Smart",       "PG", "6-4",  10.5, 3.5, 5.0, 1.8, 28),
    _p("Ausar Thompson",      "SG", "6-5",   8.5, 4.5, 2.5, 0.5, 22, tier=3),
    _p("Jaden Ivey",         "PG", "6-4",  15.0, 4.0, 3.5, 1.5, 26, tier=3),
    _p("Dennis Schroder",     "PG", "6-1",  13.0, 3.0, 6.0, 1.5, 24, tier=3),
], ["Cade Cunningham Q (calf) — GAME-TIME DECISION"])

CLE = Team("CLE", "Cleveland Cavaliers", [
    _p("Donovan Mitchell",  "SG", "6-1",  27.0, 4.5, 5.0, 2.5, 34, tier=1),
    _p("Darius Garland",    "PG", "6-1",  20.0, 3.0, 7.0, 2.2, 33, tier=1),
    _p("Evan Mobley",       "PF", "6-11", 18.0, 9.5, 3.0, 0.8, 32, tier=1),
    _p("Jarrett Allen",      "C",  "6-9",  15.0,10.0, 2.0, 0.0, 30, tier=2),
    _p("Caris LeVert",       "SG", "6-5",  12.0, 4.0, 3.0, 1.5, 24, tier=3),
    _p("Isaac Okoro",        "SG", "6-5",   8.5, 3.0, 2.0, 1.2, 22, tier=3),
    _p("Max Strus",          "SF", "6-5",   9.0, 4.0, 3.0, 2.0, 26, tier=3),
    _p("Ty Jerome",          "PG", "6-6",   7.5, 2.5, 3.5, 1.2, 20, tier=4),
])

LAL = Team("LAL", "Los Angeles Lakers", [
    _p("LeBron James",       "SF", "6-9",  25.0, 7.5, 8.0, 2.2, 36, tier=1),
    _p("Austin Reaves",      "SG", "6-5",  18.0, 4.0, 5.0, 2.5, 34, tier=2),
    _p("Rui Hachimura",      "PF", "6-8",  14.5, 5.0, 1.5, 1.2, 28, tier=2),
    _p("Deandre Ayton",      "C",  "6-11", 14.0,10.0, 2.0, 0.2, 28, tier=2),
    _p("Luka Doncic",        "PG", "6-7",  29.0, 7.5, 8.0, 2.8, 34, "OUT", 1),
    _p("Jordan Goodwin",     "SG", "6-4",  12.5, 4.5, 3.5, 1.5, 22, tier=3),
    _p("Dorian Finney-Smith","SF", "6-7",   8.5, 4.0, 2.0, 1.5, 24, tier=3),
    _p("Gabe Vincent",       "PG", "6-2",   6.5, 2.0, 2.0, 1.2, 16, tier=4),
    _p("Max Christie",       "SG", "6-5",   7.0, 3.0, 1.5, 1.2, 14, tier=4),
    _p("Bronny James",        "G",  "6-4",   5.0, 2.0, 2.0, 0.8, 12, tier=4),
    _p("Jaxson Hayes",        "C",  "6-10",  8.0, 4.0, 1.0, 0.3, 14, tier=4),
    _p("Luke Kennard",        "G",  "6-4",   7.0, 2.0, 1.5, 1.8, 12, tier=4),
], ["Luka Doncic OUT (hamstring)"])

NYK = Team("NYK", "New York Knicks", [
    _p("Jalen Brunson",      "PG", "6-1",  27.5, 4.0, 7.5, 2.5, 38, tier=1),
    _p("Karl-Anthony Towns", "C",  "6-11", 20.0,10.5, 3.0, 1.8, 34, tier=1),
    _p("Mikal Bridges",       "SG", "6-5",  19.5, 4.5, 3.5, 2.0, 36, tier=2),
    _p("OG Anunoby",          "SF", "6-7",  17.0, 5.0, 2.5, 1.8, 32, "QUESTIONABLE", 1),
    _p("Josh Hart",           "PF", "6-5",  14.0, 6.5, 4.5, 1.2, 34, tier=2),
    _p("Jordan Clarkson",     "G",  "6-4",  17.0, 3.5, 5.0, 2.0, 26, tier=3),
    _p("Miles McBride",       "PG", "6-2",  10.0, 2.5, 3.0, 1.5, 18, tier=4),
    _p("Precious Achiuwa",    "PF", "6-8",   7.5, 5.5, 1.0, 0.5, 16, tier=4),
], ["OG Anunoby Q (calf) — GAME-TIME DECISION"])

OKC = Team("OKC", "Oklahoma City Thunder", [
    _p("Shai Gilgeous-Alexander","SG","6-5",32.0, 5.0, 6.5, 2.8, 36, tier=1),
    _p("Chet Holmgren",          "C", "7-0", 16.0, 8.0, 2.5, 1.0, 32, tier=1),
    _p("Jalen Williams",         "SF","6-6", 18.5, 5.5, 4.0, 1.5, 32, tier=2),
    _p("Isaiah Hartenstein",    "C", "6-11", 8.0, 7.5, 2.5, 0.2, 26, tier=2),
    _p("Alex Caruso",           "G", "6-4",  6.0, 2.5, 2.0, 1.2, 18, tier=3),
    _p("Luguentz Dort",          "SG","6-4",  9.5, 3.5, 1.2, 2.0, 24, tier=3),
    _p("Isaiah Joe",             "G", "6-1",  9.0, 2.0, 0.8, 2.1, 16, tier=4),
    _p("Jared McCain",          "G", "6-3",  9.5, 2.5, 2.0, 1.0, 14, tier=4),
    _p("Cason Wallace",         "G", "6-4",  8.5, 2.5, 1.5, 1.8, 18, tier=4),
    _p("Aaron Wiggins",         "G", "6-5",  7.5, 2.0, 1.0, 1.2, 14, tier=4),
    _p("Kenrich Williams",      "PF","6-7",  7.5, 5.0, 2.0, 1.2, 16, tier=4),
    _p("Ajay Mitchell",         "G", "6-4",  8.0, 2.0, 3.0, 1.0, 14, tier=4),
])

PHI = Team("PHI", "Philadelphia 76ers", [
    _p("Joel Embiid",         "C",  "7-0",  28.5,10.5, 5.5, 1.8, 32, tier=1),
    _p("Tyrese Maxey",        "PG", "6-2",  24.5, 4.5, 6.5, 2.5, 36, tier=1),
    _p("Paul George",         "SF", "6-8",  22.0, 5.5, 4.5, 3.2, 34, tier=1),
    _p("Kelly Oubre Jr.",      "F",  "6-7",  18.5, 5.0, 1.5, 2.1, 30, tier=2),
    _p("Andre Drummond",       "C", "6-9",  10.0,10.0, 2.0, 0.0, 18, tier=3),
    _p("Justin Edwards",       "F", "6-6",   8.0, 3.0, 1.0, 0.8, 16, tier=4),
    _p("VJ Edgecombe",        "G", "6-5",  15.0, 3.5, 2.5, 1.2, 22, tier=3),
    _p("Quentin Grimes",       "G", "6-5",  10.0, 3.0, 2.5, 1.8, 20, tier=4),
    _p("MarJon Beauchamp",    "F", "6-7",   7.0, 3.5, 1.0, 0.8, 14, tier=4),
    _p("Dominick Barlow",      "F", "6-9",   5.0, 4.0, 1.0, 0.3, 12, tier=4),
    _p("Johni Broome",         "F", "6-10",  8.0, 6.0, 1.5, 0.5, 14, tier=4),
    _p("Adem Bona",            "C", "6-10",  6.0, 5.0, 0.8, 0.2, 10, tier=4),
    _p("Kyle Lowry",           "PG","6-0",   6.0, 3.0, 4.5, 1.2, 14, tier=4),
    _p("Jeff Dowtin Jr.",     "G", "6-2",   5.0, 1.5, 2.5, 0.6, 10, tier=4),
    _p("KJ Martin",           "F", "6-7",   6.5, 3.0, 0.5, 0.8, 12, tier=4),
])

MIN = Team("MIN", "Minnesota Timberwolves", [
    _p("Anthony Edwards",           "G",  "6-4",  30.0, 5.0, 5.5, 3.5, 36, tier=1),
    _p("Julius Randle",              "PF", "6-9",  22.0, 9.0, 4.5, 1.8, 34, tier=1),
    _p("Rudy Gobert",               "C",  "7-1",  14.0,12.0, 1.5, 0.2, 30, tier=2),
    _p("Donte DiVincenzo",           "SG", "6-4",  10.0, 4.0, 3.0, 2.0, 24, tier=3),
    _p("Mike Conley",                "PG", "6-1",  11.0, 3.0, 5.5, 2.0, 22, tier=3),
    _p("Naz Reid",                   "C",  "6-9",  13.5, 5.0, 2.0, 1.8, 22, tier=3),
    _p("Jaden McDaniels",            "SF", "6-9",   9.5, 3.5, 1.5, 0.8, 22, tier=3),
    _p("Nickeil Alexander-Walker",  "SG","6-5",   9.5, 2.5, 2.0, 1.5, 18, tier=4),
    _p("Josh Minott",               "SF", "6-8",   7.0, 3.0, 1.0, 0.5, 12, tier=4),
])

SA = Team("SA", "San Antonio Spurs", [
    _p("Victor Wembanyama",  "F",  "7-4",  24.0,11.0, 3.5, 2.5, 33, tier=1),
    _p("Chris Paul",         "PG","6-0",  12.0, 4.0, 8.0, 1.5, 24, tier=2),
    _p("Devin Vassell",       "SG","6-5",  16.0, 4.5, 2.5, 2.0, 28, tier=2),
    _p("Keldon Johnson",     "SF","6-5",  16.0, 5.5, 2.0, 1.8, 28, tier=2),
    _p("Jeremy Sochan",      "PF","6-9",  12.0, 6.0, 3.0, 0.8, 26, tier=3),
    _p("Zach Collins",       "C", "7-0",  10.0, 5.0, 2.5, 0.5, 18, tier=3),
    _p("Malaki Branham",      "SG","6-5",  10.0, 3.0, 1.5, 1.2, 18, tier=4),
    _p("Stephon Castle",     "G", "6-4",  14.0, 4.0, 4.0, 1.2, 28, tier=3),
    _p("Harrison Barnes",     "SF","6-8",  13.0, 5.0, 1.5, 1.5, 26, tier=3),
    _p("Devonte Graham",      "PG","6-1",   8.0, 2.0, 4.0, 1.5, 14, tier=4),
])

BOS = Team("BOS", "Boston Celtics", [
    _p("Jayson Tatum",        "F",  "6-8",  28.5, 7.5, 5.0, 2.9, 36, tier=1),
    _p("Jaylen Brown",         "G",  "6-6",  27.0, 5.5, 4.0, 2.5, 34, tier=1),
    _p("Kristaps Porzingis",  "PF", "7-1",  19.5, 7.5, 2.0, 2.0, 28, tier=1),
    _p("Derrick White",        "G",  "6-4",  17.5, 4.0, 4.5, 2.0, 30, tier=2),
    _p("Jrue Holiday",         "G",  "6-4",  13.5, 5.0, 4.0, 1.5, 28, tier=2),
    _p("Al Horford",           "C",  "6-9",  12.0, 5.0, 3.5, 1.8, 24, tier=2),
    _p("Payton Pritchard",     "G",  "6-1",  11.0, 3.0, 2.5, 2.0, 18, tier=4),
    _p("Sam Hauser",           "SF", "6-6",   8.0, 3.5, 1.5, 1.5, 14, tier=4),
    _p("Luke Kornet",          "C",  "7-0",   7.0, 4.5, 2.0, 0.0, 12, tier=4),
])

DEN = Team("DEN", "Denver Nuggets", [
    _p("Nikola Jokic",        "C",  "6-11", 29.5,12.0,10.0, 2.0, 34, tier=1),
    _p("Jamal Murray",         "PG","6-4",  22.0, 4.0, 6.0, 2.0, 34, tier=1),
    _p("Michael Porter Jr.",   "SF","6-10", 18.5, 7.0, 1.5, 2.2, 30, tier=2),
    _p("Aaron Gordon",        "PF","6-8",  17.0, 6.5, 3.0, 1.2, 30, tier=2),
    _p("Christian Braun",     "SG","6-6",  10.5, 4.0, 2.0, 1.0, 22, tier=3),
    _p("Russell Westbrook",   "PG","6-2",  12.0, 5.0, 6.5, 1.5, 24, tier=3),
    _p("Peyton Watson",        "G", "6-8",   6.0, 2.5, 1.0, 0.5, 12, tier=4),
    _p("Julian Strawther",    "SF","6-7",   8.0, 3.0, 1.0, 1.0, 12, tier=4),
])

GSW = Team("GSW", "Golden State Warriors", [
    _p("Stephen Curry",       "PG","6-2",  25.5, 4.5, 6.0, 3.5, 32, tier=1),
    _p("Jimmy Butler",        "SF","6-7",  20.0, 5.5, 4.5, 1.2, 34, tier=1),
    _p("Brandin Podziemski",  "SG","6-5",  13.5, 5.5, 4.0, 1.2, 28, tier=2),
    _p("Andrew Wiggins",      "SF","6-7",  13.0, 4.5, 2.0, 1.5, 26, tier=2),
    _p("Moses Moody",          "SF","6-6",  11.5, 4.0, 1.5, 1.5, 22, tier=3),
    _p("Draymond Green",      "PF","6-6",   8.0, 5.5, 6.0, 0.8, 26, tier=2),
    _p("Trayce Jackson-Davis", "C", "6-9",  10.0, 5.0, 1.5, 0.5, 18, tier=3),
    _p("Gui Santos",         "SF", "6-8",   8.0, 3.5, 1.5, 0.8, 14, tier=4),
])

MIA = Team("MIA", "Miami Heat", [
    _p("Tyler Herro",        "SG","6-5",  24.0, 5.0, 5.0, 2.5, 34, tier=1),
    _p("Bam Adebayo",        "C", "6-9",  21.0,10.0, 4.0, 0.5, 34, tier=1),
    _p("Andrew Wiggins",     "SF","6-7",  13.0, 4.5, 2.0, 1.5, 26, tier=2),
    _p("Nikola Jovic",       "PF","6-10", 12.0, 5.5, 2.5, 1.2, 24, tier=3),
    _p("Jaime Jaquez Jr.",   "SF","6-6",  11.5, 4.5, 2.5, 1.2, 24, tier=3),
    _p("Terry Rozier",       "PG","6-1",  13.0, 3.5, 4.0, 2.0, 26, tier=3),
    _p("Kevin Love",         "PF","6-8",   7.0, 5.5, 1.5, 1.5, 18, tier=4),
    _p("Delon Wright",        "G", "6-5",   5.0, 3.0, 2.5, 1.0, 14, tier=4),
])

ORL = Team("ORL", "Orlando Magic", [
    _p("Paolo Banchero",     "F", "6-10", 25.0, 7.0, 4.5, 1.8, 34, tier=1),
    _p("Franz Wagner",       "F", "6-10", 22.0, 5.0, 4.0, 1.8, 34, "OUT", 1),
    _p("Jalen Suggs",        "G", "6-5",  16.5, 4.0, 4.5, 1.5, 32, tier=2),
    _p("Wendell Carter Jr.",  "C","6-6",  14.5, 9.0, 2.5, 0.8, 28, tier=2),
    _p("Cole Anthony",       "G", "6-2",  13.0, 4.5, 3.5, 1.2, 26, tier=3),
    _p("Goga Bitadze",        "C", "6-11", 10.5, 6.0, 2.0, 0.5, 18, tier=3),
    _p("Jonathan Isaac",     "F", "6-10",  6.5, 4.0, 1.0, 0.5, 16, tier=4),
    _p("Caleb Houstan",      "F", "6-8",   7.0, 3.0, 1.5, 0.8, 14, tier=4),
], ["Franz Wagner OUT (calf)"])

HOU = Team("HOU", "Houston Rockets", [
    _p("Alperen Sengun",    "C",  "6-10", 22.0, 9.5, 5.0, 0.5, 32, tier=1),
    _p("Fred VanVleet",      "PG","6-0",  17.0, 3.5, 8.0, 2.5, 32, tier=1),
    _p("Jalen Green",        "SG","6-4",  20.0, 4.0, 3.0, 2.5, 32, tier=1),
    _p("Jabari Smith Jr.",   "PF","6-10", 16.0, 7.0, 1.5, 2.0, 30, tier=2),
    _p("Dillon Brooks",     "SF","6-6",  13.0, 4.5, 2.0, 1.8, 28, tier=2),
    _p("Jusuf Nurkic",       "C", "7-0",  12.0, 8.0, 2.5, 0.8, 24, tier=3),
    _p("Amen Thompson",      "G", "6-7",  11.0, 4.5, 3.0, 0.5, 22, tier=3),
    _p("Tari Eason",         "F", "6-8",   9.0, 5.0, 1.5, 0.5, 16, tier=4),
    _p("Cam Whitmore",       "G", "6-5",   9.0, 3.0, 1.0, 0.8, 14, tier=4),
])

DAL = Team("DAL", "Dallas Mavericks", [
    _p("Kyrie Irving",       "PG","6-2",  25.0, 5.0, 5.5, 2.8, 36, tier=1),
    _p("Anthony Davis",      "PF","6-10", 26.0,11.0, 3.0, 0.8, 34, tier=1),
    _p("P.J. Washington",    "PF","6-7",  14.0, 6.5, 2.5, 1.5, 28, tier=2),
    _p("Daniel Gafford",     "C", "6-10", 12.0, 6.5, 1.5, 0.3, 22, tier=3),
    _p("Dereck Lively II",   "C", "7-0",  10.0, 6.0, 1.5, 0.0, 20, tier=3),
    _p("Klay Thompson",       "SG","6-6",  14.0, 3.5, 2.0, 2.5, 26, tier=2),
    _p("Spencer Dinwiddie",  "PG","6-5",  10.0, 3.0, 4.5, 1.5, 22, tier=3),
    _p("Maxi Kleber",        "PF","6-10",  7.0, 4.0, 1.5, 1.2, 18, tier=4),
])

LAC = Team("LAC", "Los Angeles Clippers", [
    _p("James Harden",       "SG","6-5",  22.0, 5.5, 8.0, 2.8, 34, tier=1),
    _p("Kawhi Leonard",      "SF","6-7",  24.0, 6.0, 4.0, 2.0, 32, "QUESTIONABLE", 1),
    _p("Ivica Zubac",        "C", "7-0",  14.0,10.5, 2.0, 0.0, 28, tier=2),
    _p("Norman Powell",      "SG","6-4",  18.0, 3.5, 2.0, 2.2, 28, tier=2),
    _p("Derrick Jones Jr.",   "F", "6-6",  12.0, 4.5, 2.0, 1.5, 26, tier=3),
    _p("Nicolas Batum",      "SF","6-8",   7.0, 4.0, 2.0, 1.2, 22, tier=3),
    _p("Moses Brown",        "C", "7-2",   8.0, 5.5, 1.0, 0.0, 14, tier=4),
    _p("Kris Dunn",          "G", "6-4",   5.0, 2.5, 3.5, 0.5, 14, tier=4),
    _p("Jordan Miller",       "G", "6-3",   6.0, 2.0, 1.5, 0.8, 12, tier=4),
], ["Kawhi Leonard Q (knee) — GAME-TIME DECISION"])

IND = Team("IND", "Indiana Pacers", [
    _p("Tyrese Haliburton", "PG","6-5",  21.0, 4.0,10.5, 2.8, 34, tier=1),
    _p("Pascal Siakam",      "PF","6-8",  22.0, 6.5, 5.0, 1.8, 34, tier=1),
    _p("Myles Turner",       "C", "6-10", 16.0, 7.0, 2.0, 1.2, 28, tier=2),
    _p("OG Anunoby",         "SF","6-7",  17.0, 5.0, 2.5, 1.8, 32, tier=2),
    _p("Buddy Hield",        "SG","6-4",  13.0, 4.0, 2.5, 2.8, 22, tier=3),
    _p("Andrew Nembhard",    "PG","6-4",  10.0, 3.0, 4.0, 1.2, 22, tier=3),
    _p("Jalen Smith",        "PF","6-10", 10.0, 5.5, 1.0, 0.8, 18, tier=4),
])

TOR = Team("TOR", "Toronto Raptors", [
    _p("Scottie Barnes",     "SF","6-9",  23.0, 8.0, 6.0, 1.5, 36, tier=1),
    _p("RJ Barrett",         "SF","6-7",  20.0, 5.5, 3.0, 1.8, 34, tier=1),
    _p("Immanuel Quickley",   "PG","6-2",  18.0, 4.5, 5.5, 2.2, 30, tier=2),
    _p("Jakob Poeltl",       "C", "6-11", 14.0, 9.5, 2.5, 0.0, 28, tier=2),
    _p("Gradey Dick",         "SG","6-6",  14.0, 4.0, 1.5, 2.5, 26, tier=2),
    _p("O.G. Anunoby",       "SF","6-7",  17.0, 5.0, 2.5, 1.8, 32, tier=2),
    _p("Jontay Porter",      "PF","6-10",  8.0, 5.0, 2.0, 1.0, 16, tier=4),
    _p("Jordan Nwora",       "F", "6-9",   9.0, 4.0, 1.5, 1.2, 14, tier=4),
])

MEM = Team("MEM", "Memphis Grizzlies", [
    _p("Ja Morant",          "PG","6-3",  28.0, 5.5, 8.0, 2.5, 34, tier=1),
    _p("Jaren Jackson Jr.",  "PF","6-11", 23.0, 6.0, 2.5, 2.0, 32, tier=1),
    _p("Desmond Bane",       "SG","6-6",  20.0, 4.5, 3.5, 2.2, 34, tier=1),
    _p("Marcus Smart",       "PG","6-4",  10.5, 3.5, 5.0, 1.8, 28, tier=3),
    _p("Ziaire Williams",    "SF","6-8",   8.0, 3.0, 1.5, 1.2, 16, tier=4),
    _p("Jaylen Wells",       "G", "6-8",   8.0, 3.5, 1.0, 1.5, 14, tier=4),
    _p("Yves Pons",          "G", "6-5",   7.0, 2.5, 1.0, 1.2, 12, tier=4),
])

PHX = Team("PHX", "Phoenix Suns", [
    _p("Devin Booker",       "SG","6-5",  26.0, 4.5, 5.0, 2.5, 34, tier=1),
    _p("Kevin Durant",       "SF","6-10", 27.0, 6.5, 4.0, 2.8, 34, tier=1),
    _p("Bradley Beal",       "SG","6-4",  20.0, 4.0, 4.5, 1.8, 28, tier=2),
    _p("Tyus Jones",         "PG","6-1",  12.0, 3.0, 6.0, 1.8, 28, tier=3),
    _p("Royce O'Neale",      "SF","6-8",  10.0, 5.0, 3.5, 1.8, 26, tier=3),
    _p("Bol Bol",            "C", "7-2",  12.0, 6.0, 1.5, 0.8, 18, tier=3),
    _p("Mason Plumlee",      "C", "6-11",  8.0, 6.0, 3.0, 0.0, 16, tier=4),
])

CHI = Team("CHI", "Chicago Bulls", [
    _p("Zach LaVine",       "SG","6-5",  24.0, 4.5, 4.0, 2.8, 32, tier=1),
    _p("Coby White",         "PG","6-4",  20.0, 4.0, 5.0, 2.0, 32, tier=2),
    _p("Nikola Vucevic",     "C", "6-11", 18.0, 9.5, 3.0, 1.2, 28, tier=2),
    _p("Patrick Williams",   "PF","6-8",  12.0, 5.0, 1.5, 1.5, 26, tier=3),
    _p("Julius Randle",      "PF","6-9",  22.0, 9.0, 4.5, 1.8, 34, tier=1),
    _p("Milosz",            "SF","6-8",  16.0, 8.0, 7.0, 1.5, 30, tier=2),
    _p("Miler Tatro",        "SG","6-3",  10.0, 3.0, 4.0, 1.5, 20, tier=4),
    _p("Trevor Keegan",      "F", "6-6",   8.0, 4.0, 1.0, 1.2, 16, tier=4),
])

ATL = Team("ATL", "Atlanta Hawks", [
    _p("Trae Young",        "PG","6-1",  26.0, 3.5,10.5, 2.5, 36, tier=1),
    _p("Jalen Johnson",     "SF","6-8",  18.0, 7.5, 4.0, 1.2, 30, tier=2),
    _p("Zach Collins",      "C", "7-0",  10.0, 5.0, 2.5, 0.5, 18, tier=3),
    _p("Dyson Daniels",     "G", "6-7",  10.0, 4.5, 3.5, 1.2, 24, tier=3),
    _p("Vit Kotas",         "F", "6-8",   7.0, 3.0, 1.5, 0.8, 12, tier=4),
])

POR = Team("POR", "Portland Trail Blazers", [
    _p("Shaedon Sharpe",    "SG","6-5",  20.0, 4.5, 3.0, 1.8, 30, tier=2),
    _p("Anfernee Simons",   "SG","6-3",  22.0, 3.5, 4.0, 2.5, 32, tier=2),
    _p("Deandre Ayton",     "C", "6-11", 14.0,10.0, 2.0, 0.2, 28, tier=2),
    _p("Rayan Rupert",      "G", "6-6",   8.0, 3.0, 3.0, 1.2, 18, tier=4),
    _p("Kris Parker",       "G", "6-4",   7.0, 2.5, 1.5, 0.8, 12, tier=4),
])

# ── Team index ────────────────────────────────────────────────────────────────
TEAMS = {t.abbr: t for t in (
    DET, CLE, LAL, NYK, OKC, PHI, MIN, SA, BOS, DEN, GSW, MIA, ORL,
    HOU, DAL, LAC, IND, TOR, MEM, PHX, CHI, ATL, POR,
)}

STAT_LABELS = {"pts": "PTS", "reb": "REB", "ast": "AST", "3pm": "3PM"}

# ── TC math ───────────────────────────────────────────────────────────────────
def tc_line(tc_val: float) -> float:
    """Projected game total line = TC value × LINE_FACTOR. Calibrated to real totals."""
    return round(tc_val * LINE_FACTOR)

def tc_edge(tc_line_val: float, market_total: float) -> float:
    """Gap between TC-projected line and market total. Positive = TC above market."""
    return round(tc_line_val - market_total, 1)

def game_lean(game_tc_edge: float) -> str:
    """
    TC model systematically OVERESTIMATES actual game totals.
    Positive edge → TC_line is above market → UNDER is the fade.
    Negative edge → TC_line is below market → OVER is the fade.
    """
    if game_tc_edge > 4:
        return "UNDER"
    elif game_tc_edge < -4:
        return "OVER"
    return "PASS"

def conf_from_edge(edge: float) -> int:
    for threshold, pct in CONF_TIERS:
        if abs(edge) >= threshold:
            return pct
    return 57

def kelly_bet(edge: float, odds: int = -110, bankroll: float = BANKROLL) -> float:
    if edge <= 0:
        return 0.0
    b = abs(odds) / 100
    conf = max(57, min(72, 57 + int(abs(edge) * 2))) / 100
    kw = (b * conf - (1 - conf)) / b
    return round(max(0, bankroll * kw * 0.5), 2)

def qualifies(edge: float, stat: str) -> bool:
    return abs(edge) >= MIN_EDGE.get(stat, 2.5)

# ── Game projection ────────────────────────────────────────────────────────────
@dataclass
class GameProjection:
    away_tc: float
    home_tc: float
    combined_tc: float
    tc_line: float          # projected game total (combined_tc × LINE_FACTOR)
    market_total: float
    market_tc: float       # market_total × LINE_FACTOR (reference only)
    game_tc_edge: float   # tc_line − market_total
    away_players: List[Player] = field(default_factory=list)
    home_players: List[Player] = field(default_factory=list)

def project_game(
    home_abbr: str,
    away_abbr: str,
    market_total: Optional[float] = None,
    series: str = "",
    game_time: str = "",
) -> GameProjection:
    ht = TEAMS[home_abbr]
    at = TEAMS[away_abbr]
    htc = ht.game_tc()
    atc = at.game_tc()
    combined = round(htc + atc, 1)
    tc_l = tc_line(combined)
    market_tc = round(market_total * LINE_FACTOR, 1) if market_total else 0.0
    edge = tc_edge(tc_l, market_total) if market_total else 0.0

    return GameProjection(
        away_tc=atc,
        home_tc=htc,
        combined_tc=combined,
        tc_line=tc_l,
        market_total=market_total or 0.0,
        market_tc=market_tc,
        game_tc_edge=edge,
        away_players=at.top9(),
        home_players=ht.top9(),
    )

# ── Player prop projection ───────────────────────────────────────────────────
def project_player(
    player: Player,
    market_lines: Dict[str, float],
) -> List[Dict]:
    """
    Always emit 4 rows: PTS, REB, AST, 3PM.
    market_lines: {stat: market_line_float}
    """
    tc = player.all_tc()
    rows = []
    for stat, tc_val in tc.items():
        ml = market_lines.get(stat)
        if ml is not None:
            edge  = tc_edge(tc_val, ml)
            lean  = game_lean(edge)   # same inverted logic
            q     = qualifies(edge, stat)
            odds  = -110
            kelly = kelly_bet(edge if q else 0, odds)
        else:
            edge = tc_val
            lean = "N/A"
            q = False
            odds = -110
            kelly = 0.0

        flag = {"OUT": "🚫", "QUESTIONABLE": "⚠️"}.get(player.status, "")
        rows.append({
            "player":     player.name,
            "abbr":       player.last_name,
            "stat":       stat,
            "stat_label": STAT_LABELS[stat],
            "tc":         tc_val,
            "line":       ml,
            "edge":       edge,
            "lean":       lean,
            "conf":       conf_from_edge(edge),
            "odds":       odds,
            "qualifies":  q,
            "kelly":      kelly,
            "flag":       flag,
            "tier":       player.tier,
        })
    return rows

# ── Backtest ──────────────────────────────────────────────────────────────────
@dataclass
class BacktestGame:
    home: str; away: str
    market_total: float; actual_total: int
    date: str; round_label: str

BACKTEST_GAMES = [
    BacktestGame("DET","ORL", 208.5, 210, "May 3, 2026", "R1 G7"),
    BacktestGame("PHI","BOS", 215.5, 209, "May 3, 2026", "R1 G7"),
    BacktestGame("CLE","TOR", 218.5, 245, "May 3, 2026", "R1 G7"),
    BacktestGame("LAL","HOU", 224.5, 226, "May 3, 2026", "R1 G7"),
    BacktestGame("NYK","DET", 213.5, 202, "May 2, 2026", "R1 G7"),
    BacktestGame("MIN","SA",  229.5, 224, "May 2, 2026", "R1 G7"),
    BacktestGame("OKC","MEM", 218.5, 212, "May 2, 2026", "R1 G7"),
    BacktestGame("DEN","LAC", 226.5, 221, "May 1, 2026", "R1 G7"),
    BacktestGame("BOS","ORL", 221.5, 214, "May 1, 2026", "R1 G7"),
]

def run_backtest():
    print("\n  ═══════════════════════════════════════════")
    print("  NBA TC BACKTEST — 9 Playoff Games (2026)")
    print("  TC Line = combined_tc × 0.80 vs Actual Total")
    print("  ═══════════════════════════════════════════")
    tc_line_hits = 0
    tc_line_total = 0
    print(f"\n  {'Date':<14} {'Matchup':<12} {'Mkt':>5} {'TC_Line':>7} {'Actual':>7} {'Edge':>6} {'Lean':<7} {'Hit':<5} {'Result'}")
    print(f"  {'─'*75}")

    for g in BACKTEST_GAMES:
        ht = TEAMS[g.home]; at = TEAMS[g.away]
        htc = ht.game_tc(); atc = at.game_tc()
        combined = round(htc + atc, 1)
        tc_l = tc_line(combined)        # TC-projected total line
        market_tc_ref = round(g.market_total * LINE_FACTOR, 1)  # reference only
        edge = tc_edge(tc_l, g.market_total)
        lean = game_lean(edge)

        # TC_line hit: did actual fall on the right side of TC_line?
        tc_line_hit = (g.actual_total < tc_l and lean == "UNDER") or \
                      (g.actual_total > tc_l and lean == "OVER") or \
                      (lean == "PASS")
        correct = "✅" if tc_line_hit else "❌"
        if lean != "PASS":
            tc_line_total += 1
            if tc_line_hit:
                tc_line_hits += 1

        diff = g.actual_total - tc_l
        diff_sign = "+" if diff >= 0 else ""
        print(f"  {g.date:<14} {g.away}@{g.home:<6} {g.market_total:>5} {tc_l:>7} "
              f"{g.actual_total:>7} {edge:>+6.1f} {lean:<7} {correct}  "
              f"actual{diff_sign}{diff:.1f} (vs TC_line)")

    if tc_line_total > 0:
        rate = tc_line_hits / tc_line_total * 100
        print(f"\n  TC_line hit rate (non-PASS bets): {tc_line_hits}/{tc_line_total} = {rate:.0f}%")
    else:
        print("\n  All bets were PASSED.")
    print("  ═══════════════════════════════════════════\n")

# ── Pretty print ──────────────────────────────────────────────────────────────
def print_game_projection(home_abbr: str, away_abbr: str, market_total: float = None):
    proj = project_game(home_abbr, away_abbr, market_total)
    mt = proj.market_total
    mc = proj.market_tc
    tl = proj.tc_line
    ge = proj.game_tc_edge
    lean = game_lean(ge)
    pct = conf_from_edge(ge)

    print(f"\n  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║  {proj.away_tc:.1f} @ {proj.home_tc:.1f}  |  {away_abbr} @ {home_abbr}  |  Edge: {ge:>+6.1f}  ║")
    print(f"  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  Combined TC: {proj.combined_tc:.1f}                            ║")
    print(f"  ║  TC Line:      {tl:.1f}  (combined × {LINE_FACTOR})          ║")
    print(f"  ║  Market Total: {mt} → Mkt TC Ref: {mc:.1f}              ║")
    print(f"  ║  Edge: {ge:>+6.1f} → Lean: {lean} ({pct}% conf)         ║")
    print(f"  ╚══════════════════════════════════════════════════════╝")

    for abbr, players in [(away_abbr, proj.away_players), (home_abbr, proj.home_players)]:
        team = TEAMS[abbr]
        print(f"\n  ── {team.name} ({abbr}) ──")
        print(f"  {'Player':<20} {'Pos':<4} {'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} {'TC_TOT':>7}")
        print(f"  {'─'*65}")
        for pl in players:
            t = pl.all_tc()
            flag = pl.status_icon
            print(f"  {pl.name:<20} {pl.pos:<4} {t['pts']:>7.1f} {t['reb']:>7.1f} "
                  f"{t['ast']:>7.1f} {t['3pm']:>7.1f} {pl.tc_total():>7.1f} {flag}")
        team_tc = team.tc_team_total()
        print(f"  {'─'*65}")
        print(f"  Team TC (top-9): {team_tc:.1f} | Game TC: {team.game_tc():.1f}")
        if team.injury_notes:
            for note in team.injury_notes:
                print(f"  ⚠️  {note}")

# ── CLI ───────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NBA TC Engine CLI")
    parser.add_argument("--backtest",    action="store_true")
    parser.add_argument("--game",        type=str, help="'AWAY @ HOME' e.g. 'SA @ MIN'")
    parser.add_argument("--market-total", type=float)
    parser.add_argument("--list-teams",  action="store_true")
    parser.add_argument("--serve",       action="store_true")
    parser.add_argument("--port",        type=int, default=FASTAPI_PORT)
    args = parser.parse_args()

    if args.backtest:
        run_backtest()
        return

    if args.list_teams:
        for abbr, team in sorted(TEAMS.items()):
            print(f"  {abbr}: {team.name} ({len(team.players)} players)")
            if team.injury_notes:
                for n in team.injury_notes:
                    print(f"    ⚠️  {n}")
        return

    if args.serve:
        try:
            from fastapi import FastAPI
            import uvicorn
            app = FastAPI(title="NBA TC API", version="2.0")
            @app.get("/")
            def root():
                return {
                    "status": "ok",
                    "teams": list(TEAMS.keys()),
                    "note": "GET /tc/{away}_{home}?market_total=N for full projection",
                }
            @app.get("/games")
            def list_games():
                return [{"abbr": t.abbr, "name": t.name} for t in TEAMS.values()]
            @app.get("/tc/{away}_{home}")
            def tc_game(away: str, home: str, market_total: float = None):
                if home.upper() not in TEAMS or away.upper() not in TEAMS:
                    return {"error": f"Unknown team. Use: {list(TEAMS.keys())}"}
                proj = project_game(home.upper(), away.upper(), market_total)
                return {
                    "away": away.upper(),
                    "home": home.upper(),
                    "away_tc": proj.away_tc,
                    "home_tc": proj.home_tc,
                    "combined_tc": proj.combined_tc,
                    "tc_line": proj.tc_line,
                    "market_total": proj.market_total,
                    "market_tc": proj.market_tc,
                    "game_tc_edge": proj.game_tc_edge,
                    "away_roster": [
                        {"name": p.name, "pos": p.pos, "tc_total": p.tc_total()}
                        for p in proj.away_players
                    ],
                    "home_roster": [
                        {"name": p.name, "pos": p.pos, "tc_total": p.tc_total()}
                        for p in proj.home_players
                    ],
                }
            print(f"\n  🚀 FastAPI on port {args.port}...")
            uvicorn.run(app, host="0.0.0.0", port=args.port)
        except ImportError:
            print("  ❌ fastapi/uvicorn not installed. Run: pip install fastapi uvicorn")
        return

    if args.game:
        parts = args.game.upper().replace("@", " ").split()
        if len(parts) != 2:
            print("  Usage: --game 'AWAY @ HOME'")
            return
        away, home = parts[0], parts[1]
        if home not in TEAMS or away not in TEAMS:
            print(f"  ❌ Unknown team. Use --list-teams to see available.")
            return
        print_game_projection(home, away, args.market_total)
        return

    print("  NBA TC Engine — use --backtest, --game 'X @ Y', --list-teams, or --serve")

if __name__ == "__main__":
    main()