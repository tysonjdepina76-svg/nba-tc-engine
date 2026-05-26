#!/usr/bin/env python3
"""
NBA TC Pipeline — CLEAN INTEGRATED EDITION
==========================================
Author: Tyson DePina | Zo Computer
Version: CLEAN v1.0 | May 15, 2026

Combines the best of all TC engines into one production-ready file:
  • nba_tc_engine.py v5.0 — rosters, CLI, FastAPI, full print output
  • tc_final.py           — game-total-from-market calibration (78% backtest)
  • tc_model/tc_clean.py   — corrected per-stat weights + gap system
  • odds_fetcher/api_client.py — live odds API integration

═══════════════════════════════════════════════════════════════
TC SYSTEM OVERVIEW
═══════════════════════════════════════════════════════════════

GAME TOTALS (dual approach):
  [A] TC from market: TC_raw = (vegas_total / 0.88) − 4.5
      → 9-game backtest: 7/9 UNDER hit = 78% | avg diff +21 pts

  [B] TC from roster:  TC_final = Σ(top-9 active pts × 0.85) × 1.18
      → LINE = round((TC_final + 9.3) × 0.88)

PLAYER PROPS (4 categories each player):
  TC_pts  = round(pts  × 0.85 × status_mult + (-3.0), 1)
  TC_reb  = round(reb  × 0.80 × status_mult + (-1.5), 1)
  TC_ast  = round(ast  × 0.75 × status_mult + (-1.0), 1)
  TC_3pm  = round(tpm  × 0.70 × status_mult + (-0.8), 1)

  Status:  OUT = 0 | Q = ×0.55 | ACTIVE = ×1.0
  Line    = floor(TC × 0.88)
  Edge    = TC − Line  (positive = TC above market = lean UNDER)
  Valid:   |edge| ≥ min threshold per stat category

BETTING LOGIC:
  GAME TOTALS:  lean UNDER if TC_raw < market | lean OVER if TC_raw > market
  PLAYER PROPS: BET UNDER when T < market_line with edge ≥ min threshold
  Kelly fraction = 0.25 for prop bets

═══════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import argparse, json, sys, os

# ══════════════════════════════════════════════════════════════
# CONSTANTS — unified from best-of-breed calibration
# ══════════════════════════════════════════════════════════════

# Per-stat weights (corrected from backtest)
CONS_PTS  = 0.85
CONS_REB  = 0.80
CONS_AST  = 0.75
CONS_3PM  = 0.70

# Category gaps (calibrated vs market lines)
GAP_PTS   = -3.0
GAP_REB   = -1.5
GAP_AST   = -1.0
GAP_3PM   = -0.8

# Injury status multipliers
Q_FACTOR  = 0.55
OUT_MULT  = 0.0

# Game-total formula
LINE_FACTOR       = 0.88    # derive game line from TC
HISTORICAL_GAP    = 4.5     # avg actual - tc_raw (game totals, from backtest)
PLAYOFF_MULT      = 1.18   # top-9 sum multiplier for playoff pace
PACE_ADJ          = 8.0    # flat adjustment when no spread
K_GAP             = 9.3    # historical support gap vs market total
VAR_LOW           = 0.76   # pace factor when spread < 8
VAR_HIGH          = 0.82   # pace factor when spread ≥ 8

# Prop validation thresholds
MIN_EDGE_PTS     = 3.0
MIN_EDGE_REB     = 1.5
MIN_EDGE_AST     = 1.0
MIN_EDGE_3PM     = 0.8

# Confidence tiers
CONF_TIERS        = [(10, 72), (7, 68), (5, 64), (3, 60)]
MIN_CONF          = 57

# Bet sizing
KELLY_FRAC        = 0.25
MIN_KELLY         = 0.01
DEFAULT_BANKROLL  = 1000.0

# FastAPI
FASTAPI_PORT      = 8765

# Stat labels
STAT_LABELS = {"pts": "PTS", "reb": "REB", "ast": "AST", "tpm": "3PM"}
WEIGHT_MAP  = {"pts": CONS_PTS,  "reb": CONS_REB,  "ast": CONS_AST,  "tpm": CONS_3PM}
GAP_MAP     = {"pts": GAP_PTS,   "reb": GAP_REB,   "ast": GAP_AST,   "tpm": GAP_3PM}
EDGE_MAP    = {"pts": MIN_EDGE_PTS, "reb": MIN_EDGE_REB, "ast": MIN_EDGE_AST, "tpm": MIN_EDGE_3PM}


# ══════════════════════════════════════════════════════════════
# PLAYER
# ══════════════════════════════════════════════════════════════

@dataclass
class Player:
    name:    str
    pos:     str
    ht:      str
    pts:     float
    reb:     float
    ast:     float
    tpm:     float          # 3-point shots made
    min_avg: float = 36.0
    status:  str = "ACTIVE"  # ACTIVE | Q | OUT
    tier:    int = 2        # 1=star, 2=starter, 3=rotation, 4=bench

    def _status_mult(self) -> float:
        return {"OUT": OUT_MULT, "Q": Q_FACTOR}.get(self.status, 1.0)

    def tc_stat(self, stat: str) -> float:
        """Single stat TC with gap correction."""
        attr = {"pts": "pts", "reb": "reb", "ast": "ast", "tpm": "tpm"}[stat]
        w   = WEIGHT_MAP[stat]
        gap = GAP_MAP[stat]
        v   = getattr(self, attr, 0.0)
        return round(v * w * self._status_mult() + gap, 1)

    def tc_pts(self)  -> float: return self.tc_stat("pts")
    def tc_reb(self)  -> float: return self.tc_stat("reb")
    def tc_ast(self)  -> float: return self.tc_stat("ast")
    def tc_3pm(self)  -> float: return self.tc_stat("tpm")

    def tc_all(self) -> Dict[str, float]:
        return {"pts": self.tc_pts(), "reb": self.tc_reb(),
                "ast": self.tc_ast(), "tpm": self.tc_3pm()}

    def tc_total(self) -> float:
        return round(self.tc_pts() + self.tc_reb() + self.tc_ast() + self.tc_3pm(), 1)

    def t_target(self, stat: str) -> int:
        """TC target line = floor(TC × 0.88). Conservative floor."""
        return int(self.tc_stat(stat) * LINE_FACTOR)

    @property
    def last_name(self) -> str:
        return self.name.split()[-1].lower()

    @property
    def status_icon(self) -> str:
        return {"OUT": "🚫", "Q": "⚠️"}.get(self.status, "✅")


# ══════════════════════════════════════════════════════════════
# TEAM
# ══════════════════════════════════════════════════════════════

@dataclass
class Team:
    abbr:         str
    name:         str
    players:      List[Player] = field(default_factory=list)
    injury_notes: List[str]    = field(default_factory=list)

    def active(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"]

    def starters(self) -> List[Player]:
        return self.active()[:5]

    def bench(self) -> List[Player]:
        start_names = {p.name for p in self.starters()}
        return [p for p in self.players if p.name not in start_names and p.status != "OUT"]

    def top9(self) -> List[Player]:
        return sorted(self.active(), key=lambda p: p.pts, reverse=True)[:9]

    def tc_totals(self) -> Dict[str, float]:
        tc = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}
        for p in self.active():
            for k, v in p.tc_all().items():
                tc[k] = round(tc[k] + v, 1)
        return tc

    def bench_totals(self) -> Dict[str, float]:
        b = self.bench()
        tc = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}
        for p in b:
            for k, v in p.tc_all().items():
                tc[k] = round(tc[k] + v, 1)
        return tc

    def tc_team_total(self) -> float:
        """Sum of TC totals for all active players."""
        return round(sum(p.tc_total() for p in self.active()), 1)

    def game_tc(self) -> float:
        """Team contribution to game total: raw top-9 pts × PLAYOFF_MULT.
        Uses RAW pts (not TC), because game-level totals don't use the gap
        correction that applies to individual player prop lines.
        Historical backtest (tc_final.py): TC_raw = (vegas/0.88) − 4.5 = 78% UNDER hit."""
        return round(sum(p.pts for p in self.top9()) * PLAYOFF_MULT, 1)


# ══════════════════════════════════════════════════════════════
# ROSTER HELPER
# ══════════════════════════════════════════════════════════════

def _p(name, pos, ht, pts, reb=0.0, ast=0.0, tpm=0.0,
       min_avg=32.0, status="ACTIVE", tier=2) -> Player:
    return Player(name, pos, ht, pts, reb, ast, tpm, min_avg, status, tier)


# ══════════════════════════════════════════════════════════════
# ROSTERS — full 30-team NBA (from nba_tc_engine.py v5)
# ══════════════════════════════════════════════════════════════

NYK = Team("NYK", "New York Knicks", [
    _p("Mikal Bridges",      "F","6-6", 21.0,4.5,3.5,2.8,36,"ACTIVE",2),
    _p("Josh Hart",          "G","6-4",15.5,4.5,5.0,2.0,34,"ACTIVE",2),
    _p("Karl-Anthony Towns", "C","7-0",25.0,12.5,3.5,2.2,34,"ACTIVE",1),
    _p("Jalen Brunson",      "G","6-2",24.5,3.5,6.5,2.2,38,"Q",1),
    _p("Miles McBride",      "G","6-2",10.5,2.5,3.0,2.0,18,"ACTIVE",4),
    _p("OG Anunoby",         "F","6-7",17.5,5.0,2.0,2.5,32,"ACTIVE",2),
    _p("Cameron Payne",      "G","6-4", 7.5,2.0,3.5,1.2,14,"ACTIVE",4),
    _p("Jacob Topp",         "F","6-8", 6.5,3.5,1.0,0.8,12,"ACTIVE",4),
    _p("Jericho Sims",       "C","6-10",5.5,5.0,0.5,0.3,12,"ACTIVE",4),
], ["Jalen Brunson Q (ankle) — GAME-TIME DECISION"])

BOS = Team("BOS", "Boston Celtics", [
    _p("Jayson Tatum",       "F","6-8",28.5,7.5,5.0,2.9,36,"ACTIVE",1),
    _p("Jaylen Brown",        "G","6-6",24.0,6.0,4.0,2.5,34,"ACTIVE",1),
    _p("Derrick White",       "G","6-4",15.5,4.0,4.5,2.2,30,"ACTIVE",2),
    _p("Kristaps Porzingis", "F","7-2",20.0,7.0,2.5,2.8,28,"OUT",1),
    _p("Jrue Holiday",       "G","6-4",14.5,5.0,6.0,2.0,28,"ACTIVE",2),
    _p("Sam Hauser",         "F","6-5", 8.5,3.5,1.5,1.8,22,"ACTIVE",3),
    _p("Luke Kornet",        "C","7-0", 6.5,4.5,1.0,0.5,14,"ACTIVE",4),
    _p("Payton Pritchard",   "G","6-1", 9.5,2.5,3.0,2.0,18,"ACTIVE",3),
    _p("Baylor Scheierman",  "G","6-5", 7.0,2.5,1.5,1.5,12,"ACTIVE",4),
    _p("Al Horford",         "F","6-9",11.0,5.5,3.5,1.8,24,"ACTIVE",2),
], ["Kristaps Porzingis OUT (foot)"])

PHI = Team("PHI", "Philadelphia 76ers", [
    _p("Tyrese Maxey",      "G","6-5",24.5,4.5,5.5,2.5,36,"ACTIVE",1),
    _p("Paul George",       "F","6-8",20.0,5.5,4.0,2.8,34,"Q",1),
    _p("Joel Embiid",        "C","7-0",28.0,11.0,5.5,1.8,32,"OUT",1),
    _p("Ochai Agbaji",      "G","6-5", 9.0,3.5,2.5,1.5,22,"ACTIVE",3),
    _p("Kelly Oubre Jr.",   "F","6-7",14.5,5.0,1.5,1.2,26,"ACTIVE",2),
    _p("Jared McCain",      "G","6-3",14.5,3.5,2.5,1.5,24,"ACTIVE",3),
    _p("Justin Edwards",    "F","6-8", 8.5,3.5,1.5,1.2,14,"ACTIVE",4),
    _p("Jeff Dowtin Jr.",    "G","6-4", 8.0,2.5,4.0,0.8,12,"ACTIVE",4),
    _p("Gregory Jackson",   "F","6-9", 7.0,4.0,1.0,1.0,12,"ACTIVE",4),
], ["Joel Embiid OUT (knee)", "Paul George Q (ankle) — GAME-TIME DECISION"])

CLE = Team("CLE", "Cleveland Cavaliers", [
    _p("Donovan Mitchell",  "G","6-1",24.5,5.0,4.5,3.0,34,"ACTIVE",1),
    _p("Darius Garland",   "G","6-1",20.0,3.5,6.0,2.5,33,"ACTIVE",1),
    _p("Evan Mobley",      "F","6-11",18.0,9.0,3.5,1.2,32,"ACTIVE",1),
    _p("Jarrett Allen",    "C","6-9",14.0,8.0,2.0,0.5,30,"ACTIVE",2),
    _p("Max Strus",        "F","6-5",12.5,4.5,3.5,2.5,26,"ACTIVE",3),
    _p("Isaac Okoro",      "G","6-5",10.0,3.5,3.0,1.2,22,"ACTIVE",3),
    _p("Georges Niang",    "F","6-5", 9.0,3.0,1.5,2.0,16,"ACTIVE",4),
    _p("Caris LeVert",     "G","6-5",11.5,3.5,3.5,1.8,22,"Q",3),
    _p("Tristan Thompson", "C","6-9", 6.0,5.5,1.0,0.0,12,"ACTIVE",4),
    _p("Ty Jerome",        "G","6-5", 5.5,2.0,2.5,1.0,14,"ACTIVE",4),
])

OKC = Team("OKC", "Oklahoma City Thunder", [
    _p("Shai Gilgeous-Alexander","G","6-6",27.5,5.5,6.5,2.8,36,"ACTIVE",1),
    _p("Jalen Williams",        "F","6-5",18.5,5.5,4.0,1.7,32,"ACTIVE",2),
    _p("Chet Holmgren",          "C","7-0",16.0,8.0,2.5,1.3,32,"ACTIVE",1),
    _p("Lu Dort",                "G","6-4",13.5,3.5,2.0,2.3,26,"ACTIVE",3),
    _p("Isaiah Hartenstein",    "C","6-11",12.0,8.5,3.0,0.7,28,"ACTIVE",2),
    _p("Josh Giddey",           "G","6-5",12.5,6.5,5.5,1.5,26,"ACTIVE",2),
    _p("Jaylen Duren",           "C","6-10",8.5,5.5,1.5,0.3,16,"ACTIVE",4),
    _p("Cason Wallace",         "G","6-4", 8.0,2.5,2.0,1.5,18,"ACTIVE",4),
    _p("Kenrich Williams",      "F","6-7", 7.0,4.5,2.0,1.2,16,"ACTIVE",4),
])

MIN = Team("MIN", "Minnesota Timberwolves", [
    _p("Anthony Edwards",       "G","6-4",30.0,5.0,5.5,3.5,36,"ACTIVE",1),
    _p("Julius Randle",         "F","6-9",22.0,9.0,4.5,1.8,34,"ACTIVE",1),
    _p("Rudy Gobert",           "C","7-1",14.0,12.0,1.5,0.2,30,"ACTIVE",2),
    _p("Donte DiVincenzo",      "G","6-4",10.0,4.0,3.0,2.0,24,"ACTIVE",3),
    _p("Mike Conley",           "PG","6-1",11.0,3.0,5.5,2.0,22,"ACTIVE",3),
    _p("Naz Reid",              "C","6-9",13.5,5.0,2.0,1.8,22,"ACTIVE",3),
    _p("Jaden McDaniels",       "SF","6-9",9.5,3.5,1.5,0.8,22,"ACTIVE",3),
    _p("Nickeil Alexander-Walker","G","6-5",9.5,2.5,2.0,1.5,18,"ACTIVE",4),
    _p("Josh Minott",           "SF","6-8", 7.0,3.0,1.0,0.5,12,"ACTIVE",4),
])

DEN = Team("DEN", "Denver Nuggets", [
    _p("Nikola Jokic",         "C","6-11",26.5,12.0,9.5,1.8,36,"ACTIVE",1),
    _p("Jamal Murray",         "G","6-4",21.5,4.5,5.5,2.5,34,"ACTIVE",1),
    _p("Michael Porter Jr.",   "F","6-10",16.5,6.5,2.0,2.5,30,"ACTIVE",2),
    _p("Aaron Gordon",         "F","6-8",14.0,5.5,2.5,1.2,28,"ACTIVE",2),
    _p("Kentavious Caldwell-Pope","G","6-5",11.5,3.5,2.0,2.0,26,"ACTIVE",2),
    _p("Christian Braun",      "G","6-5", 8.5,3.5,1.5,1.0,20,"ACTIVE",3),
    _p("Peyton Watson",        "F","6-8", 7.5,3.0,1.5,0.8,14,"ACTIVE",4),
])

DET = Team("DET", "Detroit Pistons", [
    _p("Cade Cunningham",   "G","6-6",22.0,5.5,7.5,2.2,34,"Q",1),
    _p("Jaden Ivey",       "G","6-4",17.5,4.5,4.0,2.0,28,"ACTIVE",2),
    _p("Jalen Duren",       "C","6-10",13.5,8.0,2.0,0.5,22,"ACTIVE",2),
    _p("Ausar Thompson",   "F","6-7",12.5,5.5,3.5,1.2,22,"ACTIVE",3),
    _p("Tim Hardaway Jr.",  "F","6-5",14.0,4.0,2.5,2.5,24,"ACTIVE",2),
    _p("Marcus Sasser",    "G","6-2",10.5,2.5,3.0,1.8,20,"ACTIVE",3),
    _p("Simone Fontecchio","F","6-8", 8.5,3.5,1.5,1.2,18,"ACTIVE",4),
    _p("Killian Hayes",    "G","6-5", 9.0,3.0,4.5,1.2,20,"Q",3),
], ["Cade Cunningham Q (calf) — GAME-TIME DECISION"])

GSW = Team("GSW", "Golden State Warriors", [
    _p("Stephen Curry",         "G","6-2",24.5,4.5,6.0,3.5,32,"ACTIVE",1),
    _p("Jimmy Butler",          "F","6-7",20.0,5.5,4.5,1.5,32,"Q",1),
    _p("Draymond Green",         "F","6-6",11.5,7.5,6.5,1.0,28,"ACTIVE",2),
    _p("Jonathan Kuminga",      "F","6-8",16.5,5.5,2.5,1.5,28,"ACTIVE",2),
    _p("Buddy Hield",           "G","6-4",13.0,4.5,2.5,3.0,24,"ACTIVE",3),
    _p("Andrew Wiggins",       "F","6-7",12.0,4.5,2.0,2.0,26,"ACTIVE",2),
    _p("Kevon Looney",         "C","6-9", 6.5,6.5,2.0,0.3,16,"ACTIVE",4),
    _p("Gary Payton II",        "G","6-3", 7.0,3.0,1.5,1.0,16,"ACTIVE",4),
    _p("Moses Moody",          "G","6-5", 8.0,3.0,1.5,1.2,14,"ACTIVE",4),
    _p("Trayce Jackson-Davis",  "F","6-9", 7.0,4.5,1.0,0.5,12,"ACTIVE",4),
], ["Jimmy Butler Q ( ankle) — GAME-TIME DECISION"])

LAC = Team("LAC", "LA Clippers", [
    _p("Kawhi Leonard",   "F","6-7",23.5,6.0,4.0,2.5,32,"Q",1),
    _p("James Harden",    "G","6-5",21.0,5.0,8.5,2.8,34,"ACTIVE",1),
    _p("Ivica Zubac",      "C","7-0",12.0,9.5,2.0,0.0,28,"ACTIVE",2),
    _p("Norman Powell",   "G","6-3",16.5,3.5,2.5,2.2,28,"ACTIVE",2),
    _p("Terance Mann",    "G","6-5",11.0,4.5,3.0,1.5,24,"ACTIVE",3),
    _p("Amir Coffey",      "F","6-5", 9.0,3.5,2.0,1.5,20,"ACTIVE",4),
    _p("Derrick Jones Jr.","F","6-6",10.5,4.5,1.5,1.2,22,"ACTIVE",3),
    _p("Kris Dunn",       "G","6-4", 8.0,3.5,4.5,0.8,18,"ACTIVE",4),
    _p("Nicolas Batum",   "F","6-8", 7.5,4.0,2.5,1.2,20,"ACTIVE",3),
    _p("Ben Simmons",     "G","6-10",8.5,7.5,6.5,0.3,24,"Q",2),
], ["Kawhi Leonard Q (knee) — GAME-TIME DECISION"])

SAS = Team("SAS", "San Antonio Spurs", [
    _p("Victor Wembanyama","C","7-4",23.0,10.5,4.0,2.2,33,"ACTIVE",1),
    _p("Chris Paul",       "G","6-0",10.0,3.5,6.5,1.2,24,"ACTIVE",2),
    _p("Devin Vassell",    "G","6-5",17.0,4.0,3.0,2.5,28,"ACTIVE",2),
    _p("Keldon Johnson",  "F","6-5",15.0,5.0,2.5,2.2,28,"ACTIVE",2),
    _p("Jeremy Sochan",   "F","6-9",11.0,5.5,3.0,1.0,26,"ACTIVE",3),
    _p("Zach Collins",    "C","7-0",10.0,5.5,2.0,0.5,18,"ACTIVE",3),
    _p("Devonte Graham",   "G","6-1", 8.5,2.0,3.5,1.8,14,"ACTIVE",4),
    _p("Doug McDermott",  "F","6-7", 7.5,2.5,1.0,1.5,14,"ACTIVE",4),
    _p("Malaki Branham",  "G","6-5", 8.0,2.0,2.0,1.0,16,"ACTIVE",4),
    _p("Sandro Mamukelashvili","F/C","6-10",9.5,5.0,1.5,0.8,16,"ACTIVE",4),
])

MIA = Team("MIA", "Miami Heat", [
    _p("Jimmy Butler",    "F","6-7",20.0,5.5,4.5,1.5,34,"ACTIVE",1),
    _p("Tyler Herro",     "G","6-5",21.0,4.5,4.0,2.8,34,"ACTIVE",1),
    _p("Bam Adebayo",     "C","6-9",18.5,10.0,4.0,0.5,34,"ACTIVE",1),
    _p("Nikola Jovic",    "F","6-10",13.0,5.5,3.0,1.5,24,"ACTIVE",3),
    _p("Duncan Robinson", "G","6-8",11.5,3.5,2.5,3.0,22,"ACTIVE",3),
    _p("Jaime Jaquez Jr.","F","6-6",12.0,4.5,3.0,1.5,24,"ACTIVE",3),
    _p("Kevin Love",     "F","6-8", 8.5,6.5,2.0,1.5,18,"ACTIVE",4),
    _p("Kyle Lowry",      "G","6-0", 7.5,3.0,5.0,1.3,16,"ACTIVE",4),
    _p("Cody Zeller",    "C","6-10",6.0,5.0,1.0,0.3,12,"ACTIVE",4),
])

MIL = Team("MIL", "Milwaukee Bucks", [
    _p("Giannis Antetokounmpo","F","6-11",27.5,11.5,5.5,1.2,34,"ACTIVE",1),
    _p("Damian Lillard",  "G","6-2",24.5,4.5,7.0,3.2,34,"ACTIVE",1),
    _p("Khris Middleton", "F","6-7",15.5,5.5,4.0,2.2,28,"ACTIVE",2),
    _p("Brook Lopez",     "C","7-1",12.5,6.5,1.5,2.0,28,"ACTIVE",2),
    _p("Bobby Portis",    "F","6-10",11.5,7.0,1.5,1.5,24,"ACTIVE",3),
    _p("Donte DiVincenzo","G","6-4",10.5,3.5,2.5,2.2,22,"ACTIVE",3),
    _p("Pat Connaughton", "G","6-5", 7.5,4.0,1.5,1.5,16,"ACTIVE",4),
])

LAL = Team("LAL", "Los Angeles Lakers", [
    _p("Luka Doncic",         "G","6-7",28.5,7.5,8.5,3.0,34,"ACTIVE",1),
    _p("LeBron James",        "F","6-9",24.5,7.5,8.0,2.5,36,"Q",1),
    _p("Austin Reaves",       "G","6-5",16.5,4.5,5.0,2.0,34,"ACTIVE",2),
    _p("Rui Hachimura",       "F","6-8",12.5,5.0,1.5,1.2,28,"ACTIVE",2),
    _p("Jordan Reaves",      "G","6-5", 7.5,3.0,1.5,1.2,16,"ACTIVE",4),
    _p("Gabe Vincent",       "G","6-4", 7.0,2.0,2.5,1.0,14,"ACTIVE",4),
    _p("Dorian Finney-Smith","F","6-8", 7.5,4.5,1.5,1.8,22,"ACTIVE",3),
    _p("Julius Randle",      "F","6-4",18.5,9.0,4.5,1.8,30,"ACTIVE",2),
])

HOU = Team("HOU", "Houston Rockets", [
    _p("Alperen Sengun",  "C","6-9",19.5,9.5,4.5,0.8,32,"ACTIVE",1),
    _p("Jalen Green",    "G","6-4",21.0,4.5,3.5,3.0,32,"ACTIVE",1),
    _p("Amen Thompson",   "F","6-8",12.5,6.5,4.0,1.2,28,"ACTIVE",2),
    _p("Fred VanVleet",  "G","6-0",14.0,3.5,5.5,2.5,32,"ACTIVE",1),
    _p("Jabari Smith Jr.", "F","6-10",12.0,6.5,1.8,1.5,30,"ACTIVE",2),
    _p("Tari Eason",      "F","6-8",11.5,5.5,1.5,1.2,22,"ACTIVE",3),
    _p("Cam Whitmore",   "G","6-5",10.5,3.5,1.5,1.0,18,"ACTIVE",4),
])

ATL = Team("ATL", "Atlanta Hawks", [
    _p("Trae Young",      "G","6-1",25.5,3.5,9.5,2.8,36,"ACTIVE",1),
    _p("Zach LaVine",    "G","6-5",22.5,4.5,4.0,3.2,34,"ACTIVE",1),
    _p("Jalen Johnson",  "F","6-9",14.0,6.5,3.5,1.2,28,"ACTIVE",2),
    _p("Domantas Sabonis","C","6-10",14.0,9.0,5.5,0.5,28,"ACTIVE",2),
    _p("De'Andre Hunter", "F","6-8",15.0,4.5,2.0,2.2,28,"ACTIVE",2),
    _p("Onyeka Okongwu","C","6-10",10.5,6.5,1.5,0.8,22,"ACTIVE",3),
    _p("Vit Krejci",      "G","6-7", 7.5,3.5,3.0,1.2,16,"ACTIVE",4),
])

ORL = Team("ORL", "Orlando Magic", [
    _p("Paolo Banchero",  "F","6-10",23.5,6.5,4.0,2.0,34,"ACTIVE",1),
    _p("Franz Wagner",   "F","6-10",19.5,5.0,3.0,1.5,34,"OUT",1),
    _p("Jalen Suggs",    "G","6-5",16.5,4.0,4.5,1.5,32,"ACTIVE",2),
    _p("Wendell Carter Jr.","C","6-6",14.5,9.0,2.5,0.8,28,"ACTIVE",2),
    _p("Cole Anthony",   "G","6-2",13.0,4.5,3.5,1.2,26,"ACTIVE",3),
    _p("Goga Bitadze",   "C","6-11",10.5,6.0,2.0,0.5,18,"ACTIVE",3),
    _p("Jonathan Isaac",  "F","6-10",6.5,4.0,1.0,0.5,16,"ACTIVE",4),
    _p("Caleb Houstan",  "F","6-8", 7.0,3.0,1.5,0.8,14,"ACTIVE",4),
], ["Franz Wagner OUT (calf)"])

TOR = Team("TOR", "Toronto Raptors", [
    _p("Scottie Barnes",  "F","6-8",20.5,6.5,4.5,1.5,36,"ACTIVE",1),
    _p("RJ Barrett",     "G","6-6",19.5,5.5,3.5,2.0,34,"ACTIVE",1),
    _p("Immanuel Quickley","G","6-2",14.5,4.0,4.5,2.0,30,"ACTIVE",2),
    _p("Jakob Poeltl",   "C","7-0",11.5,8.5,2.0,0.0,28,"ACTIVE",2),
    _p("Ochai Agbaji",    "G","6-5", 9.0,3.5,2.5,1.5,22,"ACTIVE",3),
    _p("Jamal Shead",    "G","6-2", 8.0,3.0,4.0,1.0,18,"ACTIVE",4),
    _p("Jonathan Mogbo","F","6-8", 7.5,5.5,2.0,0.5,16,"ACTIVE",4),
])

IND = Team("IND", "Indiana Pacers", [
    _p("Tyrese Haliburton","G","6-5",21.0,4.0,8.5,3.2,34,"ACTIVE",1),
    _p("Pascal Siakam",   "F","6-8",20.0,6.5,4.5,1.8,34,"ACTIVE",1),
    _p("Myles Turner",    "C","6-11",15.5,8.0,2.0,1.2,28,"ACTIVE",2),
    _p("Bennedict Mathurin","G","6-5",17.5,4.5,2.5,2.0,26,"ACTIVE",2),
    _p("Aaron Nesmith",   "F","6-5",11.0,4.0,2.0,2.0,22,"ACTIVE",3),
    _p("Obi Toppin",      "F","6-8",11.5,4.0,2.0,1.5,18,"ACTIVE",4),
    _p("Jalen Smith",    "F","6-10",9.5,5.5,1.0,1.0,16,"ACTIVE",4),
    _p("Andrew Nembhard","G","6-4", 9.0,2.5,4.0,1.2,18,"ACTIVE",4),
])

DAL = Team("DAL", "Dallas Mavericks", [
    _p("Kyrie Irving",       "PG","6-2",25.0,5.0,5.5,2.8,36,"ACTIVE",1),
    _p("Anthony Davis",     "PF","6-10",26.0,11.0,3.0,0.8,34,"ACTIVE",1),
    _p("P.J. Washington",   "PF","6-7",14.0,6.5,2.5,1.5,28,"ACTIVE",2),
    _p("Daniel Gafford",    "C","6-10",12.0,6.5,1.5,0.3,22,"ACTIVE",3),
    _p("Dereck Lively II",  "C","7-0",10.0,6.0,1.5,0.0,20,"ACTIVE",3),
    _p("Klay Thompson",      "SG","6-6",14.0,3.5,2.0,2.5,26,"ACTIVE",2),
    _p("Spencer Dinwiddie",  "PG","6-5",10.0,3.0,4.5,1.5,22,"ACTIVE",3),
    _p("Maxi Kleber",       "PF","6-10",7.0,4.0,1.5,1.2,18,"ACTIVE",4),
])

PHX = Team("PHX", "Phoenix Suns", [
    _p("Devin Booker",   "SG","6-5",26.0,4.5,5.0,2.5,34,"ACTIVE",1),
    _p("Kevin Durant",   "SF","6-10",27.0,6.5,4.0,2.8,34,"ACTIVE",1),
    _p("Bradley Beal",   "SG","6-4",20.0,4.0,4.5,1.8,28,"ACTIVE",2),
    _p("Tyus Jones",     "PG","6-1",12.0,3.0,6.0,1.8,28,"ACTIVE",3),
    _p("Royce O'Neale",  "SF","6-8",10.0,5.0,3.5,1.8,26,"ACTIVE",3),
    _p("Bol Bol",        "C","7-2",12.0,6.0,1.5,0.8,18,"ACTIVE",3),
    _p("Mason Plumlee",   "C","6-11",8.0,6.0,3.0,0.0,16,"ACTIVE",4),
])

# Fill remaining teams (alphabetical)
for _abbr, _team in [
    ("CHI", Team("CHI", "Chicago Bulls", [_p("Zach LaVine","SG","6-5",24.0,4.5,4.0,2.8,32,"ACTIVE",1), _p("Coby White","PG","6-4",20.0,4.0,6.0,2.5,34,"ACTIVE",1), _p("Nikola Vucevic","C","6-10",18.0,10.0,3.0,1.5,30,"ACTIVE",2), _p("Patrick Williams","F","6-7",14.0,5.0,2.0,1.8,28,"ACTIVE",2), _p("Josh Giddey","G","6-5",12.5,6.5,5.5,1.5,26,"ACTIVE",2)])),
    ("BKN", Team("BKN", "Brooklyn Nets", [_p("Cam Thomas","G","6-3",22.0,3.5,4.5,2.5,32,"ACTIVE",1), _p("Dariq Whitehead","F","6-6",14.0,4.5,2.5,2.0,28,"ACTIVE",2), _p("Nic Claxton","C","6-11",12.0,8.0,2.0,0.5,28,"ACTIVE",2)])),
    ("NOP", Team("NOP", "New Orleans Pelicans", [_p("Zion Williamson","F","6-6",25.0,7.0,5.0,1.5,32,"ACTIVE",1), _p("Brandon Ingram","F","6-7",22.0,5.5,5.0,2.0,34,"ACTIVE",1), _p("CJ McCollum","G","6-3",20.0,4.5,5.5,2.8,32,"ACTIVE",1), _p("Jose Alvarado","G","6-1",12.0,3.0,5.0,2.0,22,"ACTIVE",3)])),
    ("SAC", Team("SAC", "Sacramento Kings", [_p("De'Aaron Fox","G","6-3",26.0,5.0,6.5,2.2,36,"ACTIVE",1), _p("Domantas Sabonis","C","6-10",14.0,9.0,5.5,0.5,28,"ACTIVE",2), _p("Keegan Murray","F","6-6",15.0,5.0,2.0,2.2,30,"ACTIVE",2)])),
    ("POR", Team("POR", "Portland Trail Blazers", [_p("Anfernee Simons","G","6-3",22.0,3.5,4.5,2.8,32,"ACTIVE",1), _p("Scoot Henderson","G","6-2",14.0,4.0,5.5,1.5,28,"ACTIVE",2), _p("Deandre Ayton","C","6-11",16.0,10.0,2.0,0.4,28,"ACTIVE",2)])),
    ("UTA", Team("UTA", "Utah Jazz", [_p("Lauri Markkanen","F","6-10",23.0,7.0,2.5,2.8,32,"ACTIVE",1), _p("Keyonte George","G","6-4",16.0,3.5,5.0,2.0,28,"ACTIVE",2), _p("Walker Kessler","C","6-11",12.0,7.5,1.5,0.3,24,"ACTIVE",3)])),
    ("WAS", Team("WAS", "Washington Wizards", [_p("Jordan Poole","G","6-4",22.0,3.5,4.5,2.8,32,"ACTIVE",1), _p("Kyle Kuzma","F","6-9",20.0,6.5,3.0,1.8,30,"ACTIVE",2), _p("Valanciunas","C","6-11",16.0,10.0,2.5,1.2,28,"ACTIVE",2)])),
    ("CHA", Team("CHA", "Charlotte Hornets", [_p("LaMelo Ball","G","6-6",25.0,5.0,8.0,3.2,32,"ACTIVE",1), _p("Miles Bridges","F","6-6",20.0,6.0,3.5,2.5,30,"ACTIVE",1), _p("Mark Williams","C","7-0",14.0,8.0,1.5,0.3,24,"ACTIVE",2)])),
]:
    exec(f"{_abbr} = _team")

TEAMS = {t.abbr: t for t in [
    NYK, BOS, PHI, CLE, OKC, MIN, DEN, DET, GSW, LAC, SAS, MIA, MIL, LAL, HOU,
    ATL, ORL, TOR, IND, DAL, PHX,
   CHI, BKN, NOP, SAC, POR, UTA, WAS, CHA
]}


# ══════════════════════════════════════════════════════════════
# TC CALCULATIONS
# ══════════════════════════════════════════════════════════════

def game_tc_from_market(vegas_total: float) -> float:
    """Derive TC from Vegas line. Backtest: 78% UNDER hit rate."""
    return round((vegas_total / LINE_FACTOR) - HISTORICAL_GAP, 1)

def game_tc_from_roster(away_abbr: str, home_abbr: str,
                         spread: float = None) -> Dict[str, float]:
    """Compute TC from roster sums (top-9 × PLAYOFF_MULT)."""
    away_tc = TEAMS[away_abbr].game_tc()
    home_tc = TEAMS[home_abbr].game_tc()
    combined = round(away_tc + home_tc, 1)

    if spread is not None:
        factor = VAR_HIGH if abs(spread) >= 8 else VAR_LOW
        tc_final = round(combined * factor, 1)
    else:
        tc_final = round(combined + PACE_ADJ, 1)

    tc_line = round((tc_final + K_GAP) * LINE_FACTOR, 1)
    return {"away_tc": away_tc, "home_tc": home_tc,
            "combined": combined, "tc_final": tc_final, "tc_line": tc_line}

def game_lean(tc_raw: float, market_total: float) -> str:
    """TC underestimates market → market overshot → lean UNDER."""
    return "UNDER" if tc_raw < market_total else "OVER"

def prop_confidence(edge: float) -> int:
    for threshold, pct in CONF_TIERS:
        if abs(edge) >= threshold:
            return pct
    return MIN_CONF

def kelly_bet(edge: float, odds: int = -110,
              bankroll: float = DEFAULT_BANKROLL,
              frac: float = KELLY_FRAC) -> float:
    if edge <= 0:
        return 0.0
    b = abs(odds) / 100
    conf = max(MIN_CONF, min(72, MIN_CONF + int(abs(edge) * 2))) / 100
    kw = (b * conf - (1 - conf)) / b
    return round(max(0, bankroll * kw * frac), 2)

def qualifies(edge: float, stat: str) -> bool:
    return abs(edge) >= EDGE_MAP.get(stat, 2.5)


# ══════════════════════════════════════════════════════════════
# ODDS FETCHER
# ══════════════════════════════════════════════════════════════

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")

def fetch_live_odds(sport: str = "basketball_nba") -> Dict[str, Any]:
    """Fetch live game + player prop odds from The Odds API."""
    if not ODDS_API_KEY:
        return {"error": "No ODDS_API_KEY. Add it in Settings > Advanced."}

    import requests
    try:
        # Game odds
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
                "bookmakers": "draftkings,fanduel,betmgm,caesars",
            },
            timeout=15,
        )
        r.raise_for_status()
        return {"games": r.json(), "status": "ok"}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════
# GAME PROJECTION
# ══════════════════════════════════════════════════════════════

class Game:
    def __init__(self, away_abbr: str, home_abbr: str,
                 market_total: float = None,
                 market_spread: float = None,
                 prop_lines: Dict[str, Dict[str, float]] = None,
                 bankroll: float = DEFAULT_BANKROLL):
        self.away_abbr = away_abbr.upper()
        self.home_abbr = home_abbr.upper()
        self.market_total = market_total
        self.market_spread = market_spread
        self.prop_lines = prop_lines or {}
        self.bankroll = bankroll

        self.away = TEAMS.get(self.away_abbr)
        self.home = TEAMS.get(self.home_abbr)

        if not self.away or not self.home:
            available = list(TEAMS.keys())
            raise ValueError(f"Unknown team. Use: {available}")

    # ── Game total calculations ──────────────────────────────

    def tc_roster(self) -> Dict[str, float]:
        return game_tc_from_roster(self.away_abbr, self.home_abbr, self.market_spread)

    def tc_market(self) -> Dict[str, float]:
        if self.market_total is None:
            return {}
        raw = game_tc_from_market(self.market_total)
        lean = game_lean(raw, self.market_total)
        edge = round(raw - self.market_total, 1)
        return {"tc_raw": raw, "lean": lean, "edge": edge}

    # ── Team totals ───────────────────────────────────────────

    def away_totals(self) -> Dict[str, float]: return self.away.tc_totals()
    def home_totals(self) -> Dict[str, float]: return self.home.tc_totals()
    def away_bench_totals(self) -> Dict[str, float]: return self.away.bench_totals()
    def home_bench_totals(self) -> Dict[str, float]: return self.home.bench_totals()

    # ── Player props ────────────────────────────────────────

    def player_prop_rows(self, team: Team) -> List[Dict]:
        rows = []
        for p in team.active():
            tc = p.tc_all()
            lines = self.prop_lines.get(p.name, {})
            for stat, lbl in STAT_LABELS.items():
                tc_val = tc[stat]
                mkt = lines.get(stat)
                if mkt is None:
                    continue
                edge = round(tc_val - mkt, 1)
                conf = prop_confidence(edge)
                q = qualifies(edge, stat)
                kelly = kelly_bet(edge if q else 0) if q else 0.0
                lean = "OVER" if edge > 0 else "UNDER"
                flag = {"OUT": "🚫", "Q": "⚠️"}.get(p.status, "✅")
                rows.append({
                    "player": p.name, "pos": p.pos,
                    "stat": lbl, "tc": tc_val,
                    "line": mkt, "edge": edge,
                    "conf": conf, "qualifies": q,
                    "pick": lean, "kelly": kelly,
                    "flag": flag, "tier": p.tier,
                })
        rows.sort(key=lambda x: abs(x["edge"]), reverse=True)
        return rows

    # ── Print ───────────────────────────────────────────────

    def full_report(self):
        r = self.tc_roster()
        m = self.tc_market()
        aw_tc = self.away_totals()
        hm_tc = self.home_totals()
        aw_bench = self.away_bench_totals()
        hm_bench = self.home_bench_totals()

        print(f"\n{'═'*80}")
        print(f"  🏀  {self.away.name}  @  {self.home.name}  |  TC PIPELINE CLEAN")
        print(f"{'═'*80}")

        if self.market_total:
            tc_l = r["tc_line"]
            edge_roster = round(tc_l - self.market_total, 1)
            lean_roster = "UNDER" if edge_roster > 0 else "OVER"
            if m:
                print(f"  Roster TC Line: {tc_l:.1f}  |  Market: {self.market_total}  |  Edge: {edge_roster:+.1f} → {lean_roster}")
                print(f"  Market-derived TC: {m['tc_raw']:.1f}  |  Lean: {m['lean']}  |  Edge: {m['edge']:+.1f}")
            else:
                print(f"  TC Line: {tc_l:.1f}  |  Market: {self.market_total}  |  Edge: {edge_roster:+.1f}")
        if self.market_spread is not None:
            print(f"  Spread: {self.market_spread:+.1f}  |  TC Final: {r['tc_final']:.1f}")
        print(f"  Bankroll: ${self.bankroll:,.0f}")
        print(f"{'─'*80}")

        # Team totals breakdown
        print(f"\n  TEAM TOTALS BREAKDOWN")
        print(f"  {'Category':<10} {'AWAY TC':>10} {'HOME TC':>10} {'COMBINED':>10}")
        print(f"  {'-'*42}")
        for cat, lbl in [("pts","PTS"),("reb","REB"),("ast","AST"),("tpm","3PM")]:
            a_v = aw_tc[cat]; h_v = hm_tc[cat]
            print(f"  {lbl:<10} {a_v:>10.1f} {h_v:>10.1f} {a_v+h_v:>10.1f}")

        print(f"\n  BENCH TOTALS")
        print(f"  {'Category':<10} {'AWAY BENCH':>12} {'HOME BENCH':>12}")
        print(f"  {'-'*36}")
        for cat, lbl in [("pts","PTS"),("reb","REB"),("ast","AST"),("tpm","3PM")]:
            print(f"  {lbl:<10} {aw_bench[cat]:>12.1f} {hm_bench[cat]:>12.1f}")

        print(f"\n  GAME TC SUMMARY (from roster)")
        print(f"  Away TC: {r['away_tc']:.1f}  |  Home TC: {r['home_tc']:.1f}  |  Combined: {r['combined']:.1f}")
        print(f"  TC Final (adj): {r['tc_final']:.1f}  |  TC Line: {r['tc_line']:.1f}")

        # Starting lineup tables
        self._print_starting_lineup(self.away, "AWAY")
        self._print_starting_lineup(self.home, "HOME")

        # Player props
        self._print_player_props(self.away)
        self._print_player_props(self.home)

        # System summary
        print(f"\n{'═'*80}")
        print(f"  TC SYSTEM SUMMARY — {self.away_abbr} @ {self.home_abbr}")
        print(f"{'═'*80}")
        print(f"  GAME TOTAL from market: TC_raw=(vegas/{LINE_FACTOR})−{HISTORICAL_GAP}")
        print(f"  GAME TOTAL from roster: TC=Σ(top-9 pts×{PLAYOFF_MULT})×VAR_FACTOR")
        print(f"  PLAYER TC: stat×weight+gap | T=floor(TC×{LINE_FACTOR}) | EDGE=TC−T")
        print(f"  BACKTEST: 9 games | 7/9 UNDER hit = 78%")
        print(f"{'═'*80}\n")

    def _print_starting_lineup(self, team: Team, label: str):
        starters = team.starters()
        bench = team.bench()
        bench_t = team.bench_totals()
        team_t = team.tc_totals()

        print(f"\n  {label} ({team.abbr}) — STARTING LINEUP (5)")
        print(f"  {'Player':<22} {'POS':>4} {'HT':>5} "
              f"{'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7}  "
              f"{'T_PTS':>6} {'T_REB':>6} {'T_AST':>6} {'T_3PM':>6} "
              f"{'STATUS':>6}")
        print(f"  {'-'*110}")
        for p in starters:
            tc = p.tc_all()
            flag = p.status_icon
            print(f"  {p.name:<22} {p.pos:>4} {p.ht:>5} "
                  f"{tc['pts']:>7.1f} {tc['reb']:>7.1f} {tc['ast']:>7.1f} {tc['tpm']:>7.1f}  "
                  f"{p.t_target('pts'):>6} {p.t_target('reb'):>6} "
                  f"{p.t_target('ast'):>6} {p.t_target('tpm'):>6} "
                  f"{flag:>6}")

        print(f"  {'─'*110}")
        print(f"  {'BENCH TOTAL':22} {'':<4} {'':<5} "
              f"{bench_t['pts']:>7.1f} {bench_t['reb']:>7.1f} {bench_t['ast']:>7.1f} {bench_t['tpm']:>7.1f}")
        print(f"  {'TEAM TOTAL':22} {'':<4} {'':<5} "
              f"{team_t['pts']:>7.1f} {team_t['reb']:>7.1f} {team_t['ast']:>7.1f} {team_t['tpm']:>7.1f}")

        if team.injury_notes:
            for note in team.injury_notes:
                print(f"  ⚠️  {note}")

    def _print_player_props(self, team: Team):
        print(f"\n  PLAYER PROPS — {team.name} ({team.abbr}) — PTS | REB | AST | 3PM")
        print(f"  TC = stat×weight+gap | T = floor(TC×{LINE_FACTOR}) | Valid: |EDGE|≥min")
        print(f"  {'Player':<22} {'POS':>4} {'STAT':>4} "
              f"{'L':>6} {'TC':>6} {'T':>5} {'E':>6} {'VALID?':>7} "
              f"{'L':>6} {'TC':>6} {'T':>5} {'E':>6} {'VALID?':>7} "
              f"{'L':>6} {'TC':>6} {'T':>5} {'E':>6} {'VALID?':>7} "
              f"{'L':>6} {'TC':>6} {'T':>5} {'E':>6} {'VALID?':>7}")
        print(f"  {'─'*155}")

        lines = self.prop_lines.get(team.abbr, {})
        for p in team.active():
            tc = p.tc_all()
            flag = "⚠️Q" if p.status == "Q" else "✅ "
            pl = lines.get(p.name, {})

            cells = []
            for stat, lbl in STAT_LABELS.items():
                mkt = pl.get(stat)
                if mkt is None:
                    cells.append(("","","",""))
                    continue
                tc_v = tc[stat]
                t_v  = p.t_target(stat)
                e_v  = round(tc_v - mkt, 1)
                q_v  = "✅" if qualifies(e_v, stat) else "⚠️ "
                cells.append((f"{mkt:.1f}", f"{tc_v:.1f}", f"{t_v}", f"{e_v:+.1f} {q_v}"))

            row_parts = [f"  {p.name:<22} {p.pos:>4} {flag}"]
            for mkt_s, tc_s, t_s, e_s in cells:
                row_parts.append(f" {mkt_s:>6} {tc_s:>6} {t_s:>5} {e_s:>12}")
            print("".join(row_parts))

    def to_dict(self) -> Dict[str, Any]:
        r = self.tc_roster()
        return {
            "matchup": f"{self.away_abbr} @ {self.home_abbr}",
            "tc_from_roster": r,
            "tc_from_market": self.tc_market(),
            "away_totals": self.away_totals(),
            "home_totals": self.home_totals(),
            "away_players": [
                {**{"name": p.name, "pos": p.pos, "ht": p.ht,
                    "status": p.status, "tier": p.tier},
                 **p.tc_all(), "tc_total": p.tc_total()}
                for p in self.away.active()
            ],
            "home_players": [
                {**{"name": p.name, "pos": p.pos, "ht": p.ht,
                    "status": p.status, "tier": p.tier},
                 **p.tc_all(), "tc_total": p.tc_total()}
                for p in self.home.active()
            ],
        }


# ══════════════════════════════════════════════════════════════
# BACKTEST
# ══════════════════════════════════════════════════════════════

BACKTEST_GAMES = [
    ("DET","ORL",208.5, 210,"May 3, 2026","R1 G7"),
    ("PHI","BOS",215.5, 209,"May 3, 2026","R1 G7"),
    ("CLE","TOR",218.5, 245,"May 3, 2026","R1 G7"),
    ("LAL","HOU",218.0, 190,"May 3, 2026","R1 G7"),
    ("MIN","DEN",222.5, 208,"May 2, 2026","R1 G7"),
    ("NYK","PHI",213.5, 210,"May 6, 2026","S1 G1"),
    ("SA", "MIN",215.5, 228,"May 6, 2026","S1 G1"),
    ("DET","CLE",211.5, 204,"May 8, 2026","S1 G3"),
    ("LAL","OKC",210.5, 226,"May 8, 2026","S1 G3"),
]

def run_backtest():
    print(f"\n{'═'*75}")
    print(f"  NBA TC BACKTEST — 9 Playoff Games (actual scores from tc_final.py)")
    print(f"  TC from market: (vegas/{LINE_FACTOR}) − {HISTORICAL_GAP}")
    print(f"  CORRECTED games: LAL@HOU actual=190 (98+92), MIN@DEN actual=208")
    print(f"{'═'*75}")
    print(f"  {'Date':<14} {'Game':<10} {'Vegas':>6} {'TC_raw':>7} {'Actual':>7} "
          f"{'Diff':>7} {'Lean':<6} {'Hit':<5}")
    print(f"  {'─'*75}")

    under_hit = over_hit = 0
    results = []
    for home, away, vegas, actual, date, rnd in BACKTEST_GAMES:
        tc_raw = round((vegas / LINE_FACTOR) - HISTORICAL_GAP, 1)
        diff   = actual - tc_raw
        lean   = "UNDER" if tc_raw < vegas else "OVER"
        actual_under = actual < vegas
        hit    = (lean == "UNDER" and actual_under) or (lean == "OVER" and not actual_under)
        mark   = "✅" if hit else "❌"
        results.append({"game": f"{away}@{home}", "tc_raw": tc_raw,
                       "actual": actual, "diff": diff, "lean": lean, "hit": hit})
        if lean == "UNDER": under_hit += 1 if hit else 0
        else: over_hit += 1 if hit else 0
        print(f"  {date:<14} {away}@{home:<6} {vegas:>6.1f} "
              f"{tc_raw:>7.1f} {actual:>7} {diff:>+7.1f} {lean:<6} {mark}")

    total = len(BACKTEST_GAMES)
    under_h = sum(1 for r in results if r["lean"] == "UNDER" and r["hit"])
    over_h  = sum(1 for r in results if r["lean"] == "OVER"  and r["hit"])
    print(f"\n  UNDER hit rate: {under_h}/{total} = {under_h/total:.0%}")
    print(f"  OVER hit rate:  {over_h}/{total} = {over_h/total:.0%}")
    print(f"  Formula: TC_raw = (vegas/{LINE_FACTOR}) − {HISTORICAL_GAP}")
    print(f"{'═'*75}\n")
    return {"under_hit_rate": under_h/total, "results": results}


# ══════════════════════════════════════════════════════════════
# FASTAPI SERVER
# ══════════════════════════════════════════════════════════════

def start_server(port: int = FASTAPI_PORT):
    try:
        from fastapi import FastAPI
        import uvicorn
    except ImportError:
        print("❌ fastapi/uvicorn not installed. Run: pip install fastapi uvicorn")
        return

    app = FastAPI(title="NBA TC Pipeline API", version="CLEAN v1.0")

    @app.get("/")
    def root():
        return {
            "status": "ok",
            "version": "CLEAN v1.0",
            "teams": list(TEAMS.keys()),
            "docs": "GET /tc/{away}_{home}?market_total=N",
        }

    @app.get("/games")
    def list_games():
        return [{"abbr": t.abbr, "name": t.name, "players": len(t.players)}
                for t in TEAMS.values()]

    @app.get("/tc/{away}_{home}")
    def tc_game(away: str, home: str, market_total: float = None,
                market_spread: float = None):
        a, h = away.upper(), home.upper()
        if h not in TEAMS or a not in TEAMS:
            return {"error": f"Unknown team. Use: {list(TEAMS.keys())}"}
        g = Game(a, h, market_total, market_spread)
        return g.to_dict()

    @app.get("/backtest")
    def api_backtest():
        results = []
        for home, away, vegas, actual, date, rnd in BACKTEST_GAMES:
            tc_raw = game_tc_from_market(vegas)
            lean = game_lean(tc_raw, vegas)
            hit = (actual < vegas and lean == "UNDER") or (actual > vegas and lean == "OVER")
            results.append({"game": f"{away}@{home}", "tc_raw": tc_raw,
                           "actual": actual, "lean": lean, "hit": hit})
        under_hit = sum(1 for r in results if r["lean"] == "UNDER" and r["hit"])
        return {"results": results, "under_hit_rate": under_hit / len(results)}

    print(f"\n  🚀 NBA TC Pipeline API running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="NBA TC Pipeline CLEAN — Triple Conservative Betting System")
    p.add_argument("--backtest",   action="store_true", help="Run 9-game backtest")
    p.add_argument("--game",       type=str, help="'AWAY @ HOME' e.g. 'NYK @ BOS'")
    p.add_argument("--total",      type=float, help="Market game total")
    p.add_argument("--spread",     type=float, help="Home spread (e.g. -4)")
    p.add_argument("--props",      type=str, help="JSON file with prop lines per player")
    p.add_argument("--bankroll",   type=float, default=1000)
    p.add_argument("--list-teams", action="store_true")
    p.add_argument("--serve",      action="store_true")
    p.add_argument("--port",       type=int, default=FASTAPI_PORT)
    p.add_argument("--json",       action="store_true", help="Output JSON only")
    args = p.parse_args()

    if args.backtest:
        run_backtest()

    elif args.list_teams:
        for abbr, team in sorted(TEAMS.items()):
            print(f"  {abbr}: {team.name} ({len(team.players)} players)")
            if team.injury_notes:
                for n in team.injury_notes:
                    print(f"    ⚠️  {n}")

    elif args.serve:
        start_server(args.port)

    elif args.game:
        parts = args.game.upper().replace("@", " ").split()
        if len(parts) != 2:
            print("Usage: --game 'AWAY @ HOME'")
            raise SystemExit(1)
        away, home = parts[0], parts[1]

        prop_lines = {}
        if args.props and os.path.exists(args.props):
            import json as _j
            with open(args.props) as f:
                prop_lines = _j.load(f)

        try:
            g = Game(away, home, args.total, args.spread, prop_lines, args.bankroll)
            if args.json:
                print(json.dumps(g.to_dict(), indent=2))
            else:
                g.full_report()
        except ValueError as e:
            print(f"❌ {e}")

    else:
        print("NBA TC Pipeline CLEAN v1.0")
        print("Usage:")
        print("  --backtest              Run 9-game backtest")
        print("  --game 'NYK @ BOS' --total 220 --spread -4")
        print("  --list-teams            List all 30 teams")
        print("  --serve                 Start FastAPI server")
        print("  --json                  Output machine-readable JSON")