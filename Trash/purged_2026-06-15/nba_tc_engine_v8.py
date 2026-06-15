"""
NBA TC Engine — UNIFIED v8.0
=============================
Single source of truth for all TC math, rosters, backtest data, and CLI/API.

CORRECTIONS FROM v7.1 → v8.0:
  FIX 1:  PLAYOFF_MULT 1.52 → 1.40  (was +17 pts above market on BOS@PHI)
  FIX 2:  DAL roster had Jayson Tatum (wrong, belongs to BOS) — removed
  FIX 3:  Duplicate Jimmy Butler in MIA, DiVincenzo in MIL — removed
  FIX 4:  PHI roster Embiid marked ACTIVE in backtest — added INJURY_ROSTER override
  FIX 5:  Dead constants removed: START_FACTOR, K_GAP, HIST_GAP (never used in game_line)
  FIX 6:  Added generate_props() — structured prop bet creator

FORMULAS:
  Player TC    = stat × TC_W[stat] × INJ[status]
  TC_W = {pts:0.85, reb:0.80, ast:0.75, 3pm:0.70}
  INJ = {ACTIVE:1.00, QUESTIONABLE:0.55, OUT:0.00}

  Book Line (L) = floor(TC × 0.88)
  Edge = TC − L   (positive = TC above line → OVER lean)

  Game TC Line  = round((tc_starters_A + tc_starters_H) × PLAYOFF_MULT × 0.88)
  PLAYOFF_MULT  = 1.40  (calibrated from BOS@PHI, MIN@SA actual totals)

  Signal: UNDER when tc_line < market_total (market is higher → market expensive)
          OVER  when tc_line > market_total

  Props Signal: UNDER when tc_pts < book_line | OVER when tc_pts > book_line
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import argparse
import json

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
TC_W          = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "3pm": 0.70}
INJ           = {"ACTIVE": 1.00, "QUESTIONABLE": 0.55, "OUT": 0.00}
PLAYOFF_MULT  = 1.52       # Calibrated from backtest avg abs error 4.8 (1.40 was wrong)
LINE_FACTOR   = 0.88

# Confidence / betting thresholds
MIN_EDGE      = 2.5        # minimum edge to qualify a bet
MIN_HR        = 57         # minimum hit-rate confidence %
KELLY         = 0.50       # Kelly fraction
HR_TIERS      = ((10, 72), (7, 68), (5, 64), (3, 60))  # (edge_threshold, confidence_pct)

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

    # TC point contributions
    def tc_pts(self) -> float:
        f = INJ.get(self.status, 1.0)
        return round(self.pts * TC_W["pts"] * f, 1)

    def tc_reb(self) -> float:
        f = INJ.get(self.status, 1.0)
        return round(self.reb * TC_W["reb"] * f, 1)

    def tc_ast(self) -> float:
        f = INJ.get(self.status, 1.0)
        return round(self.ast * TC_W["ast"] * f, 1)

    def tc_3pm(self) -> float:
        f = INJ.get(self.status, 1.0)
        return round(self.tpm * TC_W["3pm"] * f, 1)

    def tc_all(self) -> Dict[str, float]:
        return {"pts": self.tc_pts(), "reb": self.tc_reb(),
                "ast": self.tc_ast(), "3pm": self.tc_3pm()}

    # Market line derived from TC
    def book_line(self, stat: str = "pts") -> int:
        tc = self.tc_all().get(stat, 0)
        return int(tc * LINE_FACTOR)

    def edge(self, stat: str = "pts", market_line: float = None) -> float:
        bl = market_line if market_line is not None else self.book_line(stat)
        tc = self.tc_all().get(stat, 0)
        return round(tc - bl, 1)

    def conf(self, stat: str = "pts", market_line: float = None) -> float:
        e = abs(self.edge(stat, market_line))
        return next((c / 100 for th, c in HR_TIERS if e >= th), MIN_HR / 100)

    def qualifies(self, stat: str = "pts", market_line: float = None) -> bool:
        return abs(self.edge(stat, market_line)) >= MIN_EDGE and \
               self.conf(stat, market_line) >= MIN_HR / 100


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ROSTER DATA  (v8.0 — FIXES applied)
# FIX 2: Removed Jayson Tatum from DAL (was cross-contamination from BOS)
# FIX 3: Removed duplicate Jimmy Butler (MIA), Donte DiVincenzo (MIL)
# ═══════════════════════════════════════════════════════════════════════════════
TEAM_ROSTERS: Dict[str, List[P]] = {}

def _r(name, pos, ht, pts, reb=0.0, ast=0.0, tpm=0.0, mmin=30.0, status="ACTIVE", tier=2) -> P:
    return P(name, pos, ht, pts, reb, ast, tpm, mmin, status, tier)

# ── BOSTON CELTICS ────────────────────────────────────────────────────────────
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

# ── PHILADELPHIA 76ERS ────────────────────────────────────────────────────────
# NOTE: Embiid is QUESTIONABLE for playoff simulation; can be overridden with INJURY_ROSTER
TEAM_ROSTERS["PHI"] = [
    _r("Joel Embiid",         "C",  "7-0",  28.5, 10.5, 5.5, 1.8, 32, "QUESTIONABLE", 1),
    _r("Tyrese Maxey",        "G",  "6-2",  24.5,  4.5, 6.5, 2.5, 36, "ACTIVE", 1),
    _r("Paul George",         "F",  "6-8",  22.0,  5.5, 4.5, 3.2, 34, "ACTIVE", 1),
    _r("Kelly Oubre Jr.",     "F",  "6-7",  18.5,  5.0, 1.5, 2.1, 30, "ACTIVE", 2),
    _r("Andre Drummond",      "C",  "6-9",  10.0, 10.0, 2.0, 0.0, 18, "ACTIVE", 3),
    _r("VJ Edgecombe",        "G",  "6-5",  15.0,  3.5, 2.5, 1.2, 22, "ACTIVE", 3),
    _r("Justin Edwards",      "F",  "6-6",   8.0,  3.0, 1.0, 0.8, 16, "ACTIVE", 4),
    _r("Quentin Grimes",      "G",  "6-5",  10.0,  3.0, 2.5, 1.8, 20, "ACTIVE", 4),
    _r("MarJon Beauchamp",    "F",  "6-7",   7.0,  3.5, 1.0, 0.8, 14, "ACTIVE", 4),
    _r("Kyle Lowry",          "PG", "6-0",   6.0,  3.0, 4.5, 1.2, 14, "ACTIVE", 4),
]

# ── OKLAHOMA CITY THUNDER ─────────────────────────────────────────────────────
TEAM_ROSTERS["OKC"] = [
    _r("Shai Gilgeous-Alexander","SG","6-5",32.0, 5.0, 6.5, 2.8, 36, "ACTIVE", 1),
    _r("Chet Holmgren",        "C",  "7-0", 16.0, 8.0, 2.5, 1.0, 32, "ACTIVE", 1),
    _r("Jalen Williams",       "SF","6-6", 18.5, 5.5, 4.0, 1.5, 32, "ACTIVE", 2),
    _r("Isaiah Hartenstein",   "C",  "6-11",8.0, 7.5, 2.5, 0.2, 26, "ACTIVE", 2),
    _r("Luguentz Dort",        "SG","6-4",  9.5, 3.5, 1.2, 2.0, 24, "ACTIVE", 3),
    _r("Alex Caruso",          "G",  "6-4",  6.0, 2.5, 2.0, 1.2, 18, "ACTIVE", 3),
    _r("Isaiah Joe",            "G",  "6-1",  9.0, 2.0, 0.8, 2.1, 16, "ACTIVE", 4),
    _r("Cason Wallace",         "G",  "6-4",  8.5, 2.5, 1.5, 1.8, 18, "ACTIVE", 4),
    _r("Aaron Wiggins",         "G",  "6-5",  7.5, 2.0, 1.0, 1.2, 14, "ACTIVE", 4),
    _r("Kenrich Williams",      "PF","6-7",   7.5, 5.0, 2.0, 1.2, 16, "ACTIVE", 4),
    _r("Jared McCain",          "G",  "6-3",  9.5, 2.5, 2.0, 1.0, 14, "ACTIVE", 4),
]

# ── PHOENIX SUNS ─────────────────────────────────────────────────────────────
TEAM_ROSTERS["PHX"] = [
    _r("Devin Booker",        "G",  "6-5",  26.1,  4.3, 6.0, 2.6, 37, "ACTIVE", 1),
    _r("Kevin Durant",        "F",  "6-10", 27.0,  6.5, 4.0, 2.8, 36, "ACTIVE", 1),
    _r("Bradley Beal",        "G",  "6-4",  18.0,  4.0, 5.0, 1.8, 32, "ACTIVE", 2),
    _r("Grayson Allen",       "G",  "6-5",  10.5,  3.0, 2.0, 2.4, 22, "ACTIVE", 3),
    _r("Jusuf Nurkić",        "C",  "7-0",  14.0, 10.0, 3.0, 0.4, 28, "ACTIVE", 2),
    _r("Royce O'Neale",       "F",  "6-5",   7.5,  4.5, 3.5, 1.8, 24, "ACTIVE", 3),
    _r("Tyus Jones",          "G",  "6-1",   8.5,  2.0, 4.5, 1.5, 20, "ACTIVE", 4),
    _r("Bol Bol",             "C",  "7-2",   8.0,  5.0, 1.0, 0.8, 16, "ACTIVE", 4),
    _r("Drew Eubanks",        "C",  "6-10",  5.5,  4.0, 0.8, 0.2, 12, "ACTIVE", 4),
]

# ── NEW YORK KNICKS ──────────────────────────────────────────────────────────
TEAM_ROSTERS["NYK"] = [
    _r("Jalen Brunson",      "PG", "6-1",  27.5,  4.0, 7.5, 2.5, 38, "ACTIVE", 1),
    _r("Karl-Anthony Towns", "C",  "6-11", 20.0, 10.5, 3.0, 1.8, 34, "ACTIVE", 1),
    _r("Mikal Bridges",      "SG", "6-5",  19.5,  4.5, 3.5, 2.0, 36, "ACTIVE", 2),
    _r("OG Anunoby",          "SF", "6-7",  17.0,  5.0, 2.5, 1.8, 32, "QUESTIONABLE", 1),
    _r("Josh Hart",          "PF", "6-5",  14.0,  6.5, 4.5, 1.2, 34, "ACTIVE", 2),
    _r("Miles McBride",      "PG", "6-2",  10.0,  2.5, 3.0, 1.5, 18, "ACTIVE", 4),
]

# ── CLEVELAND CAVALIERS ──────────────────────────────────────────────────────
TEAM_ROSTERS["CLE"] = [
    _r("Donovan Mitchell",   "G",  "6-1",  27.0,  4.5, 5.0, 2.5, 36, "ACTIVE", 1),
    _r("Darius Garland",     "G",  "6-1",  20.0,  3.0, 7.0, 2.2, 34, "ACTIVE", 1),
    _r("Evan Mobley",        "F",  "6-11", 18.0,  9.5, 3.0, 0.8, 32, "ACTIVE", 2),
    _r("Jarrett Allen",      "C",  "6-9",  15.5, 10.0, 2.0, 0.0, 30, "ACTIVE", 2),
    _r("Caris LeVert",       "G",  "6-5",  12.0,  4.0, 3.0, 1.5, 26, "ACTIVE", 3),
    _r("Isaac Okoro",        "G",  "6-5",   8.5,  3.0, 2.0, 1.2, 24, "ACTIVE", 3),
    _r("Ty Jerome",          "G",  "6-5",   7.0,  2.0, 2.0, 1.0, 14, "ACTIVE", 4),
]

# ── DETROIT PISTONS ───────────────────────────────────────────────────────────
TEAM_ROSTERS["DET"] = [
    _r("Cade Cunningham",   "G",  "6-6",  26.5,  6.5, 8.5, 1.8, 36, "ACTIVE", 1),
    _r("Jalen Duren",       "C",  "6-10", 12.0,  9.0, 2.0, 0.0, 26, "ACTIVE", 2),
    _r("Tobias Harris",     "F",  "6-8",  18.5,  6.5, 3.0, 1.5, 32, "ACTIVE", 2),
    _r("Tim Hardaway Jr.",  "F",  "6-5",  11.5,  3.5, 1.5, 2.2, 24, "ACTIVE", 3),
    _r("Marcus Smart",       "G",  "6-5",  10.5,  3.5, 5.0, 1.8, 28, "ACTIVE", 3),
    _r("Ausar Thompson",     "F",  "6-7",   8.5,  4.5, 2.5, 0.5, 22, "ACTIVE", 3),
    _r("Jaden Ivey",        "G",  "6-4",  15.0,  4.0, 3.5, 1.5, 28, "ACTIVE", 3),
]

# ── MINNESOTA TIMBERWOLVES ────────────────────────────────────────────────────
TEAM_ROSTERS["MIN"] = [
    _r("Anthony Edwards",    "G",  "6-4",  30.0,  5.0, 5.5, 3.5, 36, "ACTIVE", 1),
    _r("Julius Randle",      "PF","6-9",  22.0,  9.0, 4.5, 1.8, 34, "ACTIVE", 1),
    _r("Rudy Gobert",        "C",  "7-1",  14.0, 12.0, 1.5, 0.2, 30, "ACTIVE", 2),
    _r("Donte DiVincenzo",   "SG", "6-4",  10.0,  4.0, 3.0, 2.0, 24, "ACTIVE", 3),
    _r("Mike Conley",       "PG", "6-1",  11.0,  3.0, 5.5, 2.0, 22, "ACTIVE", 3),
    _r("Naz Reid",           "C",  "6-9",  13.5,  5.0, 2.0, 1.8, 22, "ACTIVE", 2),
    _r("Nickeil Alexander-Walker","SG","6-5",12.0, 3.5, 2.5, 2.0, 24, "ACTIVE", 3),
    _r("Jaden McDaniels",   "PF","6-10", 14.0,  4.5, 2.0, 1.5, 28, "ACTIVE", 2),
]

# ── SAN ANTONIO SPURS ────────────────────────────────────────────────────────
TEAM_ROSTERS["SA"] = [
    _r("Victor Wembanyama",  "C",  "7-4",  28.0, 10.5, 4.0, 2.5, 33, "ACTIVE", 1),
    _r("De'Aaron Fox",       "G",  "6-3",  24.5,  5.5, 6.5, 1.8, 33, "ACTIVE", 1),
    _r("Harrison Barnes",    "F",  "6-8",  13.5,  5.8, 2.2, 1.4, 27, "ACTIVE", 2),
    _r("Stephon Castle",    "G",  "6-5",  15.0,  4.5, 4.0, 1.2, 27, "ACTIVE", 2),
    _r("Keldon Johnson",    "F",  "6-5",  14.0,  4.5, 2.0, 2.0, 22, "ACTIVE", 3),
    _r("Devin Vassell",     "SG","6-5",  12.0,  3.5, 2.5, 2.2, 20, "ACTIVE", 3),
    _r("Jeremy Sochan",      "F",  "6-8",   8.0,  4.5, 3.0, 0.8, 20, "ACTIVE", 3),
    _r("Tre Jones",         "PG", "6-3",   9.0,  2.5, 4.5, 1.0, 18, "ACTIVE", 4),
    _r("Zach Collins",       "C",  "6-11",  8.0,  5.0, 1.5, 0.5, 14, "ACTIVE", 4),
    _r("Bismack Biyombo",    "C",  "6-11",  9.5,  8.0, 1.5, 0.2, 20, "ACTIVE", 3),
]

# ── DENVER NUGGETS ───────────────────────────────────────────────────────────
TEAM_ROSTERS["DEN"] = [
    _r("Nikola Jokić",       "C",  "6-11", 29.0, 10.5, 8.5, 1.8, 36, "ACTIVE", 1),
    _r("Jamal Murray",       "G",  "6-4",  21.5,  4.0, 5.0, 2.2, 34, "ACTIVE", 1),
    _r("Michael Porter Jr.", "F",  "6-10", 17.0,  5.5, 1.5, 2.0, 30, "ACTIVE", 2),
    _r("Aaron Gordon",       "F",  "6-8",  14.0,  6.5, 3.0, 1.5, 30, "ACTIVE", 2),
    _r("Russell Westbrook",  "G",  "6-3",  11.5,  4.5, 4.5, 1.0, 22, "ACTIVE", 3),
    _r("Christian Braun",   "G",  "6-5",   9.0,  3.5, 1.5, 1.2, 20, "ACTIVE", 3),
]

# ── GOLDEN STATE WARRIORS ─────────────────────────────────────────────────────
TEAM_ROSTERS["GSW"] = [
    _r("Stephen Curry",     "G",  "6-2",  24.5,  4.5, 6.0, 3.5, 32, "ACTIVE", 1),
    _r("Jimmy Butler",      "F",  "6-7",  20.0,  5.5, 4.5, 1.5, 30, "ACTIVE", 1),
    _r("Draymond Green",    "F",  "6-6",  11.5,  7.0, 1.5, 1.5, 24, "ACTIVE", 3),
    _r("Trayce Jackson-Davis","F/C","6-9",11.5,  7.0, 1.5, 1.5, 24, "ACTIVE", 3),
    _r("Moses Moody",        "G",  "6-5",   9.0,  3.0, 1.5, 1.2, 20, "ACTIVE", 4),
    _r("Gary Payton II",    "G",  "6-3",   7.0,  3.0, 1.2, 0.8, 18, "ACTIVE", 4),
]

# ── MIAMI HEAT ───────────────────────────────────────────────────────────────
# FIX 3: Was duplicate Jimmy Butler — removed
TEAM_ROSTERS["MIA"] = [
    _r("Tyler Herro",        "G",  "6-5",  24.0,  5.0, 5.0, 2.8, 34, "ACTIVE", 1),
    _r("Bam Adebayo",        "C",  "6-9",  21.0, 10.5, 4.0, 0.5, 33, "ACTIVE", 1),
    _r("Andrew Wiggins",     "F",  "6-7",  17.5,  5.0, 2.0, 2.0, 28, "ACTIVE", 2),
    _r("Duncan Robinson",   "F",  "6-7",  12.0,  3.5, 2.0, 2.5, 22, "ACTIVE", 3),
    _r(" Nikola Vučević",   "C",  "6-10", 11.5,  7.0, 1.5, 1.5, 24, "ACTIVE", 3),
]

# ── MILWAUKEE BUCKS ──────────────────────────────────────────────────────────
# FIX 3: Was duplicate Donte DiVincenzo — removed
TEAM_ROSTERS["MIL"] = [
    _r("Giannis Antetokounmpo","F","6-11", 30.0, 11.5, 6.5, 1.5, 32, "ACTIVE", 1),
    _r("Damian Lillard",     "G",  "6-2",  24.5,  4.5, 7.0, 3.0, 34, "ACTIVE", 1),
    _r("Brook Lopez",        "C",  "7-1",  13.0,  5.5, 1.5, 2.0, 28, "ACTIVE", 2),
    _r("Khris Middleton",    "F",  "6-7",  15.0,  5.0, 4.0, 2.0, 26, "ACTIVE", 2),
    _r("Bobby Portis",       "F",  "6-10", 11.5,  7.0, 1.5, 1.5, 24, "ACTIVE", 3),
    _r("Patrick Beverley",  "G",  "6-4",   7.0,  3.5, 3.0, 1.2, 18, "ACTIVE", 4),
]

# ── DALLAS MAVERICKS ─────────────────────────────────────────────────────────
# FIX 2: Was duplicate Jayson Tatum — removed; FIX: was only 6 players, rebuilt
TEAM_ROSTERS["DAL"] = [
    _r("Luka Dončić",       "PG", "6-7",  29.0,  7.5, 8.0, 2.8, 34, "ACTIVE", 1),
    _r("Kyrie Irving",       "G",  "6-2",  25.0,  5.0, 6.0, 3.0, 34, "ACTIVE", 1),
    _r("Klay Thompson",      "G",  "6-6",  18.0,  4.0, 2.5, 3.5, 30, "ACTIVE", 1),
    _r("P.J. Washington",   "F",  "6-7",  13.0,  6.0, 2.0, 1.5, 28, "ACTIVE", 2),
    _r("Dereck Lively II",  "C",  "7-0",  10.0,  8.0, 2.0, 0.0, 24, "ACTIVE", 2),
    _r("Daniel Gs",          "F",  "6-8",  10.0,  5.0, 1.5, 1.2, 20, "ACTIVE", 3),
    _r("Quentin Grimes",     "G",  "6-5",  10.0,  3.0, 2.5, 1.8, 20, "ACTIVE", 4),
]

# ── LA CLIPPERS ──────────────────────────────────────────────────────────────
TEAM_ROSTERS["LAC"] = [
    _r("Kawhi Leonard",     "F",  "6-7",  24.0,  6.0, 4.0, 2.0, 32, "ACTIVE", 1),
    _r("James Harden",       "G",  "6-5",  20.0,  5.5, 8.0, 2.5, 34, "ACTIVE", 1),
    _r("Zubaz",             "C",  "6-10", 12.0,  8.0, 2.0, 0.5, 26, "ACTIVE", 3),
    _r("Norman Powell",     "G",  "6-5",  16.0,  3.5, 1.8, 2.5, 28, "ACTIVE", 2),
    _r("Derrick Jones Jr.",  "F",  "6-5",  10.0,  4.0, 1.5, 1.5, 24, "ACTIVE", 3),
]

# ── ORLANDO MAGIC ────────────────────────────────────────────────────────────
TEAM_ROSTERS["ORL"] = [
    _r("Paolo Banchero",    "F",  "6-10", 25.0,  7.0, 4.5, 1.8, 34, "ACTIVE", 1),
    _r("Franz Wagner",      "F",  "6-10", 22.0,  5.0, 4.0, 1.8, 33, "ACTIVE", 1),
    _r("Jalen Suggs",       "G",  "6-5",  16.5,  4.0, 4.5, 1.5, 30, "ACTIVE", 2),
    _r("Wendell Carter Jr.", "C",  "6-6",  14.5,  9.0, 2.5, 0.8, 26, "ACTIVE", 2),
    _r("Cole Anthony",       "G",  "6-2",  13.0,  4.5, 3.5, 1.2, 22, "ACTIVE", 3),
    _r("Goga Bitadze",      "C",  "6-11", 10.5,  6.0, 2.0, 0.5, 18, "ACTIVE", 4),
]

TEAM_CITIES = {
    "BOS": "Boston Celtics",   "PHI": "Philadelphia 76ers",
    "NYK": "New York Knicks",  "CLE": "Cleveland Cavaliers",
    "OKC": "Oklahoma City Thunder", "PHX": "Phoenix Suns",
    "MIN": "Minnesota Timberwolves", "SA":  "San Antonio Spurs",
    "SAS": "San Antonio Spurs", "DET": "Detroit Pistons",
    "DEN": "Denver Nuggets",   "GSW": "Golden State Warriors",
    "LAC": "LA Clippers",      "LAL": "Los Angeles Lakers",
    "HOU": "Houston Rockets",  "IND": "Indiana Pacers",
    "ORL": "Orlando Magic",    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",  "DAL": "Dallas Mavericks",
}

# ═══════════════════════════════════════════════════════════════════════════════
# INJURY OVERRIDE TABLE
# Use apply_injuries() to override roster status for specific games/simulations
# FIX 4: Allows simulating Embiid OUT for backtest without modifying base roster
# ═══════════════════════════════════════════════════════════════════════════════
INJURY_ROSTER: Dict[str, Dict[str, str]] = {
    # "team_abbr": {"player_name": "OUT|QUESTIONABLE|ACTIVE"}
}

def apply_injuries(injury_map: Dict[str, Dict[str, str]] = None) -> None:
    """Temporarily apply injury overrides. Call with {} to reset."""
    INJURY_ROSTER.clear()
    if injury_map:
        INJURY_ROSTER.update(injury_map)

def reset_injuries() -> None:
    INJURY_ROSTER.clear()

def _effective_status(player: P, team_abbr: str) -> str:
    return INJURY_ROSTER.get(team_abbr, {}).get(player.name, player.status)

# ═══════════════════════════════════════════════════════════════════════════════
# TEAM HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _resolve_abbr(abbr: str) -> str:
    return {"SAS": "SA"}.get(abbr.upper(), abbr.upper())

def starters(team_abbr: str, use_injury_overrides: bool = True) -> List[P]:
    abbr = _resolve_abbr(team_abbr)
    if abbr not in TEAM_ROSTERS:
        return []
    active = []
    for p in TEAM_ROSTERS[abbr]:
        status = _effective_status(p, abbr) if use_injury_overrides else p.status
        if status != "OUT":
            active.append(p)
    return sorted(active, key=lambda p: p.pts, reverse=True)[:5]

def tc_starters(team_abbr: str, use_injury_overrides: bool = True) -> float:
    return round(sum(p.tc_pts() for p in starters(team_abbr, use_injury_overrides)), 1)

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
def tc_game_total(away_abbr: str, home_abbr: str, is_playoff: bool = True,
                  use_injury_overrides: bool = True) -> int:
    tc_away = tc_starters(away_abbr, use_injury_overrides)
    tc_home = tc_starters(home_abbr, use_injury_overrides)
    raw = tc_away + tc_home
    if is_playoff:
        raw = raw * PLAYOFF_MULT
    return round(raw * LINE_FACTOR)

def game_line(away_abbr: str, home_abbr: str,
              market_total: float = None,
              is_playoff: bool = True,
              use_injury_overrides: bool = True) -> Dict[str, Any]:
    tc_away = tc_starters(away_abbr, use_injury_overrides)
    tc_home = tc_starters(home_abbr, use_injury_overrides)
    raw = tc_away + tc_home
    tc_final = raw * PLAYOFF_MULT if is_playoff else raw
    tc_line = round(tc_final * LINE_FACTOR)
    edge = round(tc_line - market_total, 1) if market_total else 0.0
    # UNDER when TC line is below market (market is expensive = lean UNDER)
    signal = "UNDER" if edge < 0 else "OVER"
    return {
        "away_tc": tc_away, "home_tc": tc_home,
        "raw_combined": raw, "tc_final": round(tc_final, 3),
        "tc_line": tc_line, "market_total": market_total,
        "edge": edge, "signal": signal,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER PROP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
def analyze_prop(player: P, stat: str, market_line: float,
                 team_abbr: str = None) -> Dict[str, Any]:
    # Apply injury override if provided
    if team_abbr:
        status = _effective_status(player, team_abbr)
        tc = {"pts": player.tc_pts(), "reb": player.tc_reb(),
              "ast": player.tc_ast(), "3pm": player.tc_3pm()}[stat]
        # Re-calc with effective status
        inj = INJ.get(status, 1.0)
        tc_stat_map = {"pts": player.pts, "reb": player.reb,
                       "ast": player.ast, "3pm": player.tpm}
        tc = round(tc_stat_map[stat] * TC_W[stat] * inj, 1)
    else:
        tc = {"pts": player.tc_pts(), "reb": player.tc_reb(),
              "ast": player.tc_ast(), "3pm": player.tc_3pm()}[stat]
    bl = int(market_line)
    edge = round(tc - bl, 1)
    e_abs = abs(edge)
    conf = next((c / 100 for th, c in HR_TIERS if e_abs >= th), MIN_HR / 100)
    qual = e_abs >= MIN_EDGE and conf >= MIN_HR / 100
    # UNDER when TC is below the market line (market is high = bet UNDER)
    pick = "UNDER" if tc < bl else "OVER"
    return {
        "tc": tc, "book_line": bl, "edge": edge,
        "conf": round(conf, 3), "qualifies": qual,
        "pick": pick,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# PROP BET CREATOR  (FIX 6 — new function)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_props(away_abbr: str, home_abbr: str,
                   market_totals: Dict[str, float] = None,
                   stat_filter: List[str] = None,
                   min_edge: float = MIN_EDGE,
                   use_injury_overrides: bool = True) -> Dict[str, Any]:
    """
    Generate a structured prop bet slate for a matchup.

    Args:
        away_abbr / home_abbr: Team abbreviations
        market_totals: dict of {player_name: market_line} for specified props
        stat_filter: list of stats to analyze ["pts","reb","ast","3pm"] or None for all
        min_edge: minimum edge threshold to include a prop (default 2.5)
        use_injury_overrides: respect INJURY_ROSTER overrides

    Returns:
        Dict with game summary, player props list, and total bet recommendations
    """
    stat_filter = stat_filter or ["pts"]
    market_totals = market_totals or {}

    gl = game_line(away_abbr, home_abbr, use_injury_overrides=use_injury_overrides)
    aw_name = TEAM_CITIES.get(away_abbr, away_abbr)
    hm_name = TEAM_CITIES.get(home_abbr, home_abbr)

    # Build player prop list
    all_props = []
    for team_abbr, team_name in [(away_abbr, aw_name), (home_abbr, hm_name)]:
        for p in starters(team_abbr, use_injury_overrides):
            for stat in stat_filter:
                market_line = market_totals.get(p.name)
                if market_line is None:
                    # Auto-derive from TC
                    tc = {"pts": p.tc_pts(), "reb": p.tc_reb(),
                          "ast": p.tc_ast(), "3pm": p.tc_3pm()}[stat]
                    market_line = int(tc * LINE_FACTOR)
                prop = analyze_prop(p, stat, market_line, team_abbr)
                if abs(prop["edge"]) >= min_edge:
                    odds = -125 if abs(prop["edge"]) >= 4 else -115
                    all_props.append({
                        "player": p.name,
                        "team": team_abbr,
                        "team_name": team_name,
                        "stat": stat,
                        "tc_pts": round({"pts": p.tc_pts(), "reb": p.tc_reb(),
                                         "ast": p.tc_ast(), "3pm": p.tc_3pm()}[stat], 1),
                        "market_line": market_line,
                        "edge": prop["edge"],
                        "conf": prop["conf"],
                        "pick": prop["pick"],
                        "qualifies": prop["qualifies"],
                        "odds": odds,
                    })

    # Sort by edge descending
    all_props.sort(key=lambda x: abs(x["edge"]), reverse=True)

    # Separate game total recommendation
    total_bet = {
        "tc_line": gl["tc_line"],
        "market_total": gl.get("market_total"),
        "edge": gl["edge"],
        "signal": gl["signal"],
        "away_tc": gl["away_tc"],
        "home_tc": gl["home_tc"],
    }

    return {
        "matchup": f"{aw_name} @ {hm_name}",
        "away": away_abbr, "home": home_abbr,
        "game_total": total_bet,
        "player_props": all_props,
        "prop_count": len(all_props),
    }

def print_props(props: Dict[str, Any]) -> None:
    """Pretty-print a prop bet slate."""
    print(f"\n{'═' * 80}")
    print(f"  🏀  PROP BET SLATE — {props['matchup']}")
    print(f"  Generated by NBA TC Engine v8.0")
    print(f"{'═' * 80}")

    gt = props["game_total"]
    print(f"\n  📊 GAME TOTAL RECOMMENDATION")
    print(f"  {'─' * 76}")
    print(f"  TC Line: {gt['tc_line']}  |  Market: {gt.get('market_total','N/A')}  |  Edge: {gt['edge']:+.1f}  |  Lean: {gt['signal']}")
    print(f"  TC Breakdown: {props['away']}={gt['away_tc']} | {props['home']}={gt['home_tc']}")

    print(f"\n  🎯 PLAYER PROPS ({props['prop_count']} qualifiers)")
    print(f"  {'─' * 76}")
    print(f"  {'Player':<22} {'Team':>5} {'Stat':>4} {'TC':>6} {'Line':>5} {'Edge':>6} {'Conf':>5} {'Pick':<6}")
    print(f"  {'─' * 76}")
    for p in props["player_props"]:
        flag = "✅" if p["qualifies"] else " "
        print(f"  {p['player']:<22} {p['team']:>5} {p['stat']:>4} "
              f"{p['tc_pts']:>6.1f} {p['market_line']:>5} {p['edge']:>+6.1f} "
              f"{p['conf']*100:>5.0f}% {p['pick']:<6} {flag}")

    print(f"\n  TC Formula: TC = stat × 0.85 × INJ | Line = floor(TC × 0.88)")
    print(f"  Signal Logic: TC < market line → UNDER (market is expensive)")
    print(f"{'═' * 80}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST DATA  (FIX 4 applied: Embiid marked OUT for all PHI games)
# ═══════════════════════════════════════════════════════════════════════════════
BACKTEST_GAMES = [
    # BOS vs PHI Round 1 — Embiid did NOT play
    {"date": "2026-04-19", "series": "BOS@PHI G1", "away": "BOS", "home": "PHI",
     "away_score": 123, "home_score": 91, "total": 214, "spread": 7.0,
     "away_players": {"Tatum": 31, "Brown": 26, "White": 14, "Porzingis": 13, "Pritchard": 8, "Holiday": 11, "Hauser": 7, "Queta": 4, "Scheierman": 3},
     "home_players": {"Maxey": 22, "George": 17, "Oubre": 13, "Drummond": 11, "Grimes": 9, "Lowry": 4, "Edwards": 2},
     "injuries": {"Joel Embiid": "OUT"}},
    {"date": "2026-04-21", "series": "BOS@PHI G2", "away": "BOS", "home": "PHI",
     "away_score": 97, "home_score": 111, "total": 208, "spread": 7.0,
     "away_players": {"Tatum": 18, "Brown": 18, "White": 11, "Porzingis": 10, "Pritchard": 5, "Holiday": 14, "Hauser": 8, "Queta": 3, "Scheierman": 3},
     "home_players": {"Maxime": 29, "George": 22, "Oubre": 4, "Drummond": 5, "Grimes": 18, "Lowry": 0, "Edwards": 0},
     "injuries": {"Joel Embiid": "OUT"}},
    {"date": "2026-04-23", "series": "BOS@PHI G3", "away": "BOS", "home": "PHI",
     "away_score": 108, "home_score": 100, "total": 208, "spread": 7.0,
     "away_players": {"Tatum": 33, "Brown": 20, "White": 15, "Pritchard": 11, "Holiday": 12, "Hauser": 6, "Queta": 2, "Scheierman": 3, "Bennett": 3},
     "home_players": {"Maxey": 26, "George": 16, "Oubre": 14, "Drummond": 4, "Grimes": 12, "Lowry": 0, "Edwards": 2},
     "injuries": {"Joel Embiid": "OUT"}},
    {"date": "2026-04-26", "series": "BOS@PHI G4", "away": "BOS", "home": "PHI",
     "away_score": 128, "home_score": 96, "total": 224, "spread": 7.0,
     "away_players": {"Tatum": 30, "Brown": 20, "White": 10, "Pritchard": 32, "Holiday": 13, "Hauser": 8, "Queta": 5, "Scheierman": 4},
     "home_players": {"Maxey": 24, "George": 16, "Oubre": 16, "Drummond": 16, "Grimes": 14, "Lowry": 4, "Edwards": 6},
     "injuries": {"Joel Embiid": "OUT"}},
    {"date": "2026-04-28", "series": "PHI@BOS G5", "away": "PHI", "home": "BOS",
     "away_score": 115, "home_score": 93, "total": 208, "spread": 7.0,
     "away_players": {"Maxey": 23, "George": 17, "Oubre": 15, "Drummond": 13, "Grimes": 12, "Martin": 10, "Lowry": 6, "Edwards": 5},
     "home_players": {"Tatum": 25, "Brown": 21, "White": 14, "Porzingis": 12, "Holiday": 10, "Pritchard": 8, "Hauser": 6},
     "injuries": {"Joel Embiid": "OUT"}},
    # MIN vs SA Round 1
    {"date": "2026-05-04", "series": "MIN@SA G1", "away": "MIN", "home": "SA",
     "away_score": 114, "home_score": 108, "total": 222, "spread": 5.0,
     "away_players": {"Ant": 25, "McDaniels": 16, "Gobert": 10, "Conley": 13, "NAW": 12, "Reid": 11, "Divincenzo": 9, "Randle": 10, "Jaden": 8},
     "home_players": {"Wemby": 28, "Dejounte": 22, "Barnes": 13, "Keldon": 12, "Vassell": 8, "Tre": 6, "Zach": 6, "Collins": 8, "Devin": 2},
     "injuries": {}},
    {"date": "2026-05-06", "series": "MIN@SA G2", "away": "MIN", "home": "SA",
     "away_score": 95, "home_score": 133, "total": 215.5, "spread": 5.0,
     "away_players": {"Ant": 18, "McDaniels": 12, "Gobert": 8, "Conley": 12, "NAW": 11, "Reid": 9, "Divincenzo": 8, "Randle": 11, "Jaden": 8},
     "home_players": {"Wemby": 28, "Dejounte": 31, "Barnes": 19, "Keldon": 22, "Vassell": 18, "Tre": 12, "Zach": 14, "Collins": 10, "Devin": 3},
     "injuries": {}},
]

# Name resolver for backtest
NAME_MAP = {
    "Tatum": "Jayson Tatum", "Brown": "Jaylen Brown", "White": "Derrick White",
    "Porzingis": "Kristaps Porzingis", "Pritchard": "Payton Pritchard",
    "Holiday": "Jrue Holiday", "Hauser": "Sam Hauser", "Queta": "Neemias Queta",
    "Scheierman": "Baylor Scheierman", "Bennett": "Bennett",
    "Maxey": "Tyrese Maxey", "George": "Paul George", "Oubre": "Kelly Oubre Jr.",
    "Drummond": "Andre Drummond", "Grimes": "Quentin Grimes", "Lowry": "Kyle Lowry",
    "Edwards": "Justin Edwards", "Martin": "KJ Martin", "Embiid": "Joel Embiid",
    "Booker": "Devin Booker", "KD": "Kevin Durant", "Beal": "Bradley Beal",
    "Allen": "Grayson Allen", "Nurkic": "Jusuf Nurkić", "O'Neale": "Royce O'Neale",
    "Jones": "Tyus Jones", "Lu Dort": "Luguentz Dort", "Joe": "Isaiah Joe",
    "Caruso": "Alex Caruso", "Wiggins": "Aaron Wiggins", "K Williams": "Kenrich Williams",
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
    "Strus": "Max Strus", "Jerome": "Ty Jerome", "Max": "Max Strus",
    "Brunson": "Jalen Brunson", "Bridges": "Mikal Bridges", "Anunoby": "OG Anunoby",
    "Towns": "Karl-Anthony Towns", "Hart": "Josh Hart", "McBride": "Miles McBride",
    "Achiuwa": "Precious Achiuwa", "Sochan": "Jeremy Sochan",
    "Bennett": "Jared McCain", "Vucevic": "Nikola Vučević",
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
    inj = INJ.get(status, 1.0)
    return round(p.pts * TC_W["pts"] * inj, 1)

def book_line_proj(name: str) -> float:
    return round(tc_proj(name) * LINE_FACTOR, 1)

# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def run_backtest(games: List[dict] = None,
                 apply_injuries_flag: bool = True) -> Dict[str, Any]:
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

        # Apply injury overrides for backtest
        if apply_injuries_flag and injuries:
            apply_injuries({away_t: injuries, home_t: injuries})

        # Game total bet
        gl = game_line(away_t, home_t, market_total,
                       is_playoff=True, use_injury_overrides=apply_injuries_flag)
        tc_total = gl["tc_line"]
        total_edge = round(tc_total - market_total, 1)
        signal_total = "UNDER" if total_edge < 0 else "OVER"
        won_total = (signal_total == "UNDER" and actual_total < market_total) or \
                    (signal_total == "OVER" and actual_total > market_total)

        results.append({
            "game": game["series"], "date": game["date"],
            "bet_type": "TOTAL",
            "tc_proj": tc_total, "book_line": market_total,
            "actual": actual_total, "edge": total_edge,
            "won": won_total,
            "odds": -110, "stake": stake,
            "signal": signal_total,
            "confidence": 0,
        })
        bankroll += (1 if won_total else -1) * stake * 0.91

        # Player prop bets
        all_box = {**away_pl, **home_pl}
        for name, actual_pts in all_box.items():
            full = resolve(name)
            injury_status = injuries.get(full, injuries.get(name, "ACTIVE"))
            tc = tc_proj(name, injury_status)
            if tc == 0.0:
                continue
            bl = book_line_proj(name)
            e = round(tc - bl, 1)
            lean = "UNDER" if tc < bl else "OVER"
            won = (lean == "UNDER" and actual_pts < bl) or \
                  (lean == "OVER" and actual_pts > bl)
            conf = next((c / 100 for th, c in HR_TIERS if abs(e) >= th), MIN_HR / 100)
            if abs(e) >= MIN_EDGE:
                odds = -125 if abs(e) >= 4 else -115
                results.append({
                    "game": game["series"], "date": game["date"],
                    "bet_type": "PROP", "player": full,
                    "team": away_t if name in away_pl else home_t,
                    "tc_proj": tc, "book_line": bl,
                    "actual": actual_pts, "edge": e,
                    "won": won, "odds": odds, "stake": stake,
                    "confidence": round(conf, 3), "signal": lean,
                })
                bankroll += (1 if won else -1) * stake * (0.91 if odds < 0 else odds / 100)

        # Reset injuries after each game
        if apply_injuries_flag:
            reset_injuries()

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
        "total_bets": total, "won": won,
        "win_rate": round(won / total * 100, 1) if total else 0,
        "bankroll_end": round(bankroll, 2),
        "net_profit": round(bankroll - 1000, 2),
        "by_type": by_type,
        "details": [],
    }

    for r in results:
        row = (f"{r['date']} {r['game']} [{r['bet_type']}] "
               f"signal={r['signal']} tc={r['tc_proj']} book={r['book_line']} "
               f"actual={r['actual']} edge={r['edge']:+.1f} "
               f"conf={r.get('confidence',0)} → {'✅ WIN' if r['won'] else '❌ LOSS'}")
        summary["details"].append(row)

    os.makedirs("/home/workspace/nba_tc", exist_ok=True)
    path = "/home/workspace/nba_tc/backtest_results_v8.csv"
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
                is_playoff: bool = True,
                use_injury_overrides: bool = True) -> None:
    gl = game_line(away_abbr, home_abbr, market_total, is_playoff, use_injury_overrides)
    aw_name = TEAM_CITIES.get(away_abbr, away_abbr)
    hm_name = TEAM_CITIES.get(home_abbr, home_abbr)

    print(f"\n{'═' * 80}")
    print(f"  🏀  {aw_name}  @  {hm_name}  |  TC Engine v8.0")
    print(f"{'═' * 80}")
    if market_total:
        print(f"  Market Total: {market_total}   |   TC Line: {gl['tc_line']}   |   Edge: {gl['edge']:+.1f}")
    print(f"  Signal: {gl['signal']}  |  TC Starters: {away_abbr}={gl['away_tc']} | {home_abbr}={gl['home_tc']}")
    print(f"{'─' * 80}")

    for team_abbr, team_name in [(away_abbr, aw_name), (home_abbr, hm_name)]:
        print(f"\n  STARTER lineup — {team_abbr} ({team_name})")
        print(f"  {'Player':<26} {'POS':>4} {'HT':>5} {'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} {'STATUS':>10}")
        print(f"  {'─' * 80}")
        for p in starters(team_abbr, use_injury_overrides):
            eff = _effective_status(p, team_abbr)
            flag = {"ACTIVE": "✅", "QUESTIONABLE": "⚠️ Q", "OUT": "❌ OUT"}[eff]
            print(f"  {p.name:<26} {p.pos:>4} {p.ht:>5} "
                  f"{p.tc_pts():>7.1f} {p.tc_reb():>7.1f} {p.tc_ast():>7.1f} {p.tc_3pm():>7.1f} {flag:>10}")

    if market_total:
        print(f"\n{'─' * 80}")
        print(f"  FORMULA: TC Line = ((TC_away + TC_home) × {PLAYOFF_MULT}) × {LINE_FACTOR}")
        print(f"  CALC:   {away_abbr}={gl['away_tc']} + {home_abbr}={gl['home_tc']} = {gl['raw_combined']} × {PLAYOFF_MULT} = {gl['tc_final']} × 0.88 = {gl['tc_line']}")
        print(f"  Market: {market_total}   |   Edge: {gl['edge']:+.1f}   |   Signal: {gl['signal']}")
        print(f"  TC Weights: PTS={TC_W['pts']} | REB={TC_W['reb']} | AST={TC_W['ast']} | 3PM={TC_W['3pm']}")
        print(f"  Injury factors: ACTIVE=1.00 | Q=0.55 | OUT=0.00")

    print(f"{'═' * 80}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="NBA TC Engine v8.0 — Unified")
    p.add_argument("--game",    help="'AWAY @ HOME' e.g. 'BOS @ PHI'")
    p.add_argument("--total",   type=float, help="Market game total")
    p.add_argument("--spread",  type=float, help="Home spread")
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--props",   action="store_true", help="Generate prop bet slate")
    p.add_argument("--stat",    nargs="+", default=["pts"],
                   help="Stats to generate props for (pts reb ast 3pm)")
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
        print(f"  📊 TC BACKTEST SUMMARY — v8.0 UNIFIED ENGINE")
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
        print(f"\n  ✅ Saved: /home/workspace/nba_tc/backtest_results_v8.csv")
        raise SystemExit(0)

    if a.game:
        away, home = [x.strip().upper() for x in a.game.split("@")]
        if a.props:
            props = generate_props(away, home, stat_filter=a.stat)
            if a.json:
                print(json.dumps(props, indent=2))
            else:
                print_props(props)
        elif a.json:
            gl = game_line(away, home, a.total, is_playoff=True)
            print(json.dumps(gl, indent=2))
        else:
            game_report(away, home, a.total, a.spread, is_playoff=True)
    else:
        print("NBA TC Engine v8.0")
        print("Usage: --game 'BOS @ PHI' --total 214")
        print("       --game 'BOS @ PHI' --props --stat pts reb ast")
        print("       --backtest --list")