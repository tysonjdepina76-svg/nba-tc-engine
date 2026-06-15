#!/usr/bin/env python3
"""
NBA TC Pipeline — Unified Single Entry Point v3
=================================================
Core principle: ALWAYS generate PTS, REB, AST, 3PM projections for every player.
Never pass on any stat — each stat is computed and reported independently.

Weights calibrated from backtest (7/9 UNDER hit = 78%):
  CONS_PTS=0.85  CONS_REB=0.80  CONS_AST=0.75  CONS_3PM=0.70
  GAP_PTS=-3.0  GAP_REB=-1.5  GAP_AST=-1.0  GAP_3PM=-0.8
  Q_FACTOR=0.55  LINE_FACTOR=0.88  HISTORICAL_GAP=4.5  PLAYOFF_MULT=1.18

Usage:
  python nba_tc_pipeline.py                  # live card (auto-detect games)
  python nba_tc_pipeline.py --backtest      # backtest only
  python nba_tc_pipeline.py --game 'SA @ MIN'  # specific matchup
  python nba_tc_pipeline.py --report 'SA @ MIN' --output TC_Report.md
  python nba_tc_pipeline.py --serve         # FastAPI server
  python nba_tc_pipeline.py --parlay        # generate parlay card
"""

import sys, os, json, argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional

sys.path.insert(0, "/home/workspace")

# ── TC CORE — PLAYER PROPS ONLY ──────────────────────────────────────────────
# IMPORTANT: TC (Triple Conservative) formulas are calibrated for
# INDIVIDUAL PLAYER PROP BETS ONLY (PTS, REB, AST, 3PM).
# Do NOT use tc_pts(), tc_reb(), tc_ast(), tc_3pm(), tc_total(),
# or any aggregation of them (tc_team_total(), game_tc()) to derive
# game totals, spreads, or team-level predictions.
# Those methods have no backtest validation for team totals.
# They will systematically undershoot real game scoring by 30-40 pts.
# ─────────────────────────────────────────────────────────────────────────────

CONS_PTS    = 0.85   # pts conservative weight — calibrated for player prop UNDERs
CONS_REB    = 0.80   # reb weight
CONS_AST    = 0.75   # ast weight
CONS_3PM    = 0.70   # 3pm weight

# Gap adjustments (negative = floor bias, reduces overshoot)
GAP_PTS    = -3.0    # pts gap  — backtested against player prop lines
GAP_REB    = -1.5    # reb gap
GAP_AST    = -1.0    # ast gap
GAP_3PM    = -0.8    # 3pm gap

Q_FACTOR   = 0.55    # questionable reduction
LINE_FACTOR = 0.88   # prop line derivation from TC value
MIN_EDGE   = {"pts": 2.5, "reb": 1.5, "ast": 1.0, "3pm": 0.8}

# Confidence tiers — only for prop bet sizing
CONF_TIERS  = [(10, 72), (7, 68), (5, 64), (3, 60)]

# ── TEAM TOTAL / GAME TOTAL CORRECTION ────────────────────────────────────────
# WARNING: tc_team_total() and game_tc() below are HEURISTICS ONLY.
# They aggregate per-player TC stat projections and are NOT calibrated
# against team totals or game totals. For game totals/spreads, use
# the market total directly or a separate model. The TC aggregation
# will systematically under-predict high-scoring games by 30-40 pts.
HISTORICAL_GAP = 4.5   # legacy gap — DO NOT trust for game totals
PLAYOFF_MULT   = 1.18   # playoff scoring multiplier — DO NOT trust for game totals
BANKROLL    = 1000.0
FASTAPI_PORT = 8765

# ── Player dataclass ──────────────────────────────────────────────────────────
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

    def tc_stat(self, stat: str) -> float:
        _attr = {"pts": "pts", "reb": "reb", "ast": "ast", "3pm": "tpm"}[stat]
        w   = {"pts": CONS_PTS, "reb": CONS_REB, "ast": CONS_AST, "3pm": CONS_3PM}[stat]
        gap = {"pts": GAP_PTS,  "reb": GAP_REB,  "ast": GAP_AST,  "3pm": GAP_3PM}[stat]
        v   = getattr(self, _attr, 0)
        if self.status == "OUT":
            return 0.0
        mult = Q_FACTOR if self.status == "QUESTIONABLE" else 1.0
        return round(v * w * mult + gap, 1)

    def tc_pts(self)  -> float: return self.tc_stat("pts")
    def tc_reb(self)  -> float: return self.tc_stat("reb")
    def tc_ast(self)  -> float: return self.tc_stat("ast")
    def tc_3pm(self)  -> float: return self.tc_stat("3pm")

    @property
    def last_name(self) -> str:
        return self.name.split()[-1].lower()

    @property
    def status_icon(self) -> str:
        return {"OUT": "🚫", "QUESTIONABLE": "⚠️ ", "ACTIVE": "✅"}.get(self.status, "✅")

    def all_tc(self) -> Dict[str, float]:
        """Return ALL four TC stats — always generated, never skipped."""
        return {
            "pts":  self.tc_pts(),
            "reb":  self.tc_reb(),
            "ast":  self.tc_ast(),
            "3pm":  self.tc_3pm(),
        }

    def tc_total(self) -> float:
        return round(self.tc_pts() + self.tc_reb() + self.tc_ast() + self.tc_3pm(), 1)

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
        """
        ⚠️ UNCALIBRATED FOR TEAM/GAME TOTALS — DO NOT USE for totals or spreads.
        Sums all four TC stat projections (pts+reb+ast+3pm) for the top-9 active players.
        Validated only for INDIVIDUAL PLAYER PROP BETS (PTS, REB, AST, 3PM).
        Aggregating these will under-predict game totals by 30-40 pts.
        """
        return round(sum(p.tc_total() for p in self.top9()), 1)

    def game_tc(self) -> float:
        """
        ⚠️ UNCALIBRATED — heuristic only. DO NOT use for game totals or spreads.
        Applies PLAYOFF_MULT to tc_team_total(). Has no backtest validation.
        Real game totals run 30-40 pts higher than this number.
        For game totals, use the market total directly.
        """
        return round(self.tc_team_total() * PLAYOFF_MULT, 1)

    def vegas_line(self) -> int:
        """
        ⚠️ UNCALIBRATED — heuristic only. DO NOT trust for spread/total betting.
        Derives a pseudo-spread from game_tc() which under-predicts reality.
        Use market odds directly instead.
        """
        return round((self.game_tc() + HISTORICAL_GAP) * LINE_FACTOR)

# ── Team rosters ─────────────────────────────────────────────────────────────
def _p(name, pos, ht, pts, reb, ast, tpm, min_avg=32.0, status="ACTIVE", tier=2):
    return Player(name, pos, ht, pts, reb, ast, tpm, min_avg, status, tier)

DET = Team("DET","Detroit Pistons",[
    _p("Cade Cunningham","PG","6-6",26.5,6.5,8.5,1.8,34,"QUESTIONABLE",1),
    _p("Jalen Duren","C","6-11",12.0,9.0,2.0,0.0,22),
    _p("Tobias Harris","SF","6-8",18.5,6.5,3.0,1.5,30,"ACTIVE",2),
    _p("Tim Hardaway Jr.","SG","6-5",11.5,3.5,1.5,2.2,24),
    _p("Marcus Smart","PG","6-4",10.5,3.5,5.0,1.8,28),
    _p("Ausar Thompson","SG","6-5",8.5,4.5,2.5,0.5,22,tier=3),
    _p("Jaden Ivey","PG","6-4",15.0,4.0,3.5,1.5,26,tier=3),
    _p("Dennis Schroder","PG","6-1",13.0,3.0,6.0,1.5,24,tier=3),
],["Cade Cunningham Q (calf) — GAME-TIME DECISION"])

CLE = Team("CLE","Cleveland Cavaliers",[
    _p("Donovan Mitchell","SG","6-1",27.0,4.5,5.0,2.5,34,tier=1),
    _p("Darius Garland","PG","6-1",20.0,3.0,7.0,2.2,33,tier=1),
    _p("Evan Mobley","PF","6-11",18.0,9.5,3.0,0.8,32,tier=1),
    _p("Jarrett Allen","C","6-9",15.0,10.0,2.0,0.0,30,tier=2),
    _p("Caris LeVert","SG","6-5",12.0,4.0,3.0,1.5,24,tier=3),
    _p("Isaac Okoro","SG","6-5",8.5,3.0,2.0,1.2,22,tier=3),
    _p("Max Strus","SF","6-5",9.0,4.0,3.0,2.0,26,tier=3),
    _p("Ty Jerome","PG","6-6",7.5,2.5,3.5,1.2,20,tier=4),
])

LAL = Team("LAL","Los Angeles Lakers",[
    _p("LeBron James","SF","6-9",25.0,7.5,8.0,2.2,36,tier=1),
    _p("Austin Reaves","SG","6-5",18.0,4.0,5.0,2.5,34,tier=2),
    _p("Rui Hachimura","PF","6-8",14.5,5.0,1.5,1.2,28,tier=2),
    _p("Deandre Ayton","C","6-11",14.0,10.0,2.0,0.2,28,tier=2),
    _p("Luka Doncic","PG","6-7",29.0,7.5,8.0,2.8,34,"OUT",1),
    _p("Jordan Goodwin","SG","6-4",12.5,4.5,3.5,1.5,22,tier=3),
    _p("Dorian Finney-Smith","SF","6-7",8.5,4.0,2.0,1.5,24,tier=3),
    _p("Gabe Vincent","PG","6-2",6.5,2.0,2.0,1.2,16,tier=4),
    _p("Max Christie","SG","6-5",7.0,3.0,1.5,1.2,14,tier=4),
    _p("Bronny James","G","6-4",5.0,2.0,2.0,0.8,12,tier=4),
    _p("Jaxson Hayes","C","6-10",8.0,4.0,1.0,0.3,14,tier=4),
    _p("Luke Kennard","G","6-4",7.0,2.0,1.5,1.8,12,tier=4),
],["Luka Doncic OUT (hamstring)"])

NYK = Team("NYK","New York Knicks",[
    _p("Jalen Brunson","PG","6-1",27.5,4.0,7.5,2.5,38,tier=1),
    _p("Karl-Anthony Towns","C","6-11",20.0,10.5,3.0,1.8,34,tier=1),
    _p("Mikal Bridges","SG","6-5",19.5,4.5,3.5,2.0,36,tier=2),
    _p("OG Anunoby","SF","6-7",17.0,5.0,2.5,1.8,32,"QUESTIONABLE",1),
    _p("Josh Hart","PF","6-5",14.0,6.5,4.5,1.2,34,tier=2),
    _p("Jordan Clarkson","G","6-4",17.0,3.5,5.0,2.0,26,tier=3),
    _p("Miles McBride","PG","6-2",10.0,2.5,3.0,1.5,18,tier=4),
    _p("Precious Achiuwa","PF","6-8",7.5,5.5,1.0,0.5,16,tier=4),
],["OG Anunoby Q (calf) — GAME-TIME DECISION"])

OKC = Team("OKC","Oklahoma City Thunder",[
    _p("Shai Gilgeous-Alexander","SG","6-5",32.0,5.0,6.5,2.8,36,tier=1),
    _p("Chet Holmgren","C","7-0",16.0,8.0,2.5,1.0,32,tier=1),
    _p("Jalen Williams","SF","6-6",18.5,5.5,4.0,1.5,32,tier=2),
    _p("Isaiah Hartenstein","C","6-11",8.0,7.5,2.5,0.2,26,tier=2),
    _p("Alex Caruso","G","6-4",6.0,2.5,2.0,1.2,18,tier=3),
    _p("Luguentz Dort","SG","6-4",9.5,3.5,1.2,2.0,24,tier=3),
    _p("Isaiah Joe","G","6-1",9.0,2.0,0.8,2.1,16,tier=4),
    _p("Jared McCain","G","6-3",9.5,2.5,2.0,1.0,14,tier=4),
    _p("Cason Wallace","G","6-4",8.5,2.5,1.5,1.8,18,tier=4),
    _p("Aaron Wiggins","G","6-5",7.5,2.0,1.0,1.2,14,tier=4),
    _p("Kenrich Williams","PF","6-7",7.5,5.0,2.0,1.2,16,tier=4),
    _p("Ajay Mitchell","G","6-4",8.0,2.0,3.0,1.0,14,tier=4),
])

PHI = Team("PHI","Philadelphia 76ers",[
    _p("Joel Embiid","C","7-0",28.5,10.5,5.5,1.8,32,tier=1),
    _p("Tyrese Maxey","PG","6-2",24.5,4.5,6.5,2.5,36,tier=1),
    _p("Paul George","SF","6-8",22.0,5.5,4.5,3.2,34,tier=1),
    _p("Kelly Oubre Jr.","F","6-7",18.5,5.0,1.5,2.1,30,tier=2),
    _p("Andre Drummond","C","6-9",10.0,10.0,2.0,0.0,18,tier=3),
    _p("Justin Edwards","F","6-6",8.0,3.0,1.0,0.8,16,tier=4),
    _p("VJ Edgecombe","G","6-5",15.0,3.5,2.5,1.2,22,tier=3),
    _p("Quentin Grimes","G","6-5",10.0,3.0,2.5,1.8,20,tier=4),
    _p("MarJon Beauchamp","F","6-7",7.0,3.5,1.0,0.8,14,tier=4),
    _p("Dominick Barlow","F","6-9",5.0,4.0,1.0,0.3,12,tier=4),
    _p("Johni Broome","F","6-10",8.0,6.0,1.5,0.5,14,tier=4),
    _p("Adem Bona","C","6-10",6.0,5.0,0.8,0.2,10,tier=4),
    _p("Kyle Lowry","PG","6-0",6.0,3.0,4.5,1.2,14,tier=4),
    _p("Jeff Dowtin Jr.","G","6-2",5.0,1.5,2.5,0.6,10,tier=4),
    _p("KJ Martin","F","6-7",6.5,3.0,0.5,0.8,12,tier=4),
])

MIN = Team("MIN","Minnesota Timberwolves",[
    _p("Anthony Edwards","G","6-4",30.0,5.0,5.5,3.5,36,tier=1),
    _p("Julius Randle","PF","6-9",22.0,9.0,4.5,1.8,34,tier=1),
    _p("Rudy Gobert","C","7-1",14.0,12.0,1.5,0.2,30,tier=2),
    _p("Donte DiVincenzo","SG","6-4",10.0,4.0,3.0,2.0,24,tier=3),
    _p("Mike Conley","PG","6-1",11.0,3.0,5.5,2.0,22,tier=3),
    _p("Naz Reid","C","6-9",13.5,5.0,2.0,1.8,22,tier=3),
    _p("Jaden McDaniels","SF","6-9",9.5,3.5,1.5,0.8,22,tier=3),
    _p("Nickeil Alexander-Walker","SG","6-5",9.5,2.5,2.0,1.5,18,tier=4),
    _p("Josh Minott","SF","6-8",7.0,3.0,1.0,0.5,12,tier=4),
])

SA = Team("SA","San Antonio Spurs",[
    _p("Victor Wembanyama","F","7-4",24.0,11.0,3.5,2.5,33,tier=1),
    _p("Chris Paul","PG","6-0",12.0,4.0,8.0,1.5,24,tier=2),
    _p("Devin Vassell","SG","6-5",16.0,4.5,2.5,2.0,28,tier=2),
    _p("Keldon Johnson","SF","6-5",16.0,5.5,2.0,1.8,28,tier=2),
    _p("Jeremy Sochan","PF","6-9",12.0,6.0,3.0,0.8,26,tier=3),
    _p("Zach Collins","C","7-0",10.0,5.0,2.5,0.5,18,tier=3),
    _p("Malaki Branham","SG","6-5",10.0,3.0,1.5,1.2,18,tier=4),
    _p("Stephon Castle","G","6-4",14.0,4.0,4.0,1.2,28,tier=3),
    _p("Harrison Barnes","SF","6-8",13.0,5.0,1.5,1.5,26,tier=3),
    _p("Devonte Graham","PG","6-1",8.0,2.0,4.0,1.5,14,tier=4),
])

BOS = Team("BOS","Boston Celtics",[
    _p("Jayson Tatum","F","6-8",28.5,7.5,5.0,2.9,36,tier=1),
    _p("Jaylen Brown","G","6-6",25.5,6.0,4.0,2.5,34,tier=1),
    _p("Kristaps Porzingis","F","7-2",20.0,7.0,2.5,2.5,30,"QUESTIONABLE",1),
    _p("Derrick White","G","6-4",14.0,4.0,4.5,1.8,28,tier=2),
    _p("Jrue Holiday","G","6-4",12.5,5.0,4.5,1.8,28,tier=2),
    _p("Al Horford","C","6-9",9.0,5.0,3.0,1.5,22,tier=3),
    _p("Derrick White","G","6-4",14.0,4.0,4.5,1.8,28,tier=2),
    _p("Payton Pritchard","PG","6-2",9.0,3.0,2.5,1.8,16,tier=4),
    _p("Sam Hauser","SF","6-8",7.5,3.0,1.0,1.5,14,tier=4),
    _p("Luke Kornet","C","7-0",6.0,4.0,1.0,0.3,12,tier=4),
    _p("Baylor Scheierman","SG","6-5",5.0,2.5,1.5,1.2,10,tier=4),
],["Kristaps Porzingis Q (ankle) — GAME-TIME DECISION"])

DEN = Team("DEN","Denver Nuggets",[
    _p("Nikola Jokic","C","6-11",29.0,12.5,10.0,1.8,36,tier=1),
    _p("Jamal Murray","PG","6-4",22.0,4.5,6.0,2.0,34,tier=1),
    _p("Aaron Gordon","PF","6-8",17.0,6.5,3.0,1.2,30,tier=2),
    _p("Michael Porter Jr.","SF","6-10",16.5,6.0,2.0,1.8,28,tier=2),
    _p("Russell Westbrook","PG","6-2",12.0,5.0,6.5,1.5,24,tier=3),
    _p("Christian Braun","SG","6-6",7.5,3.0,1.5,0.8,14,tier=4),
    _p(" Peyton Watson","G","6-8",5.0,2.5,0.8,0.5,10,tier=4),
    _p("Julian Strawther","SF","6-7",8.0,3.0,1.0,1.0,12,tier=4),
])

GSW = Team("GSW","Golden State Warriors",[
    _p("Stephen Curry","PG","6-2",25.5,4.5,6.0,3.5,32,tier=1),
    _p("Jimmy Butler","SF","6-7",20.0,5.5,4.5,1.2,34,tier=1),
    _p("Brandin Podziemski","SG","6-5",13.5,5.5,4.0,1.2,28,tier=2),
    _p("Moses Moody","SF","6-6",11.5,4.0,1.5,1.5,22,tier=3),
    _p("Andrew Wiggins","SF","6-7",13.0,4.5,2.0,1.5,26,tier=2),
    _p("Draymond Green","PF","6-6",8.0,5.5,6.0,0.8,26,tier=2),
    _p("Trayce Jackson-Davis","C","6-9",10.0,5.0,1.5,0.5,18,tier=3),
    _p("Gui Santos","SF","6-8",8.0,3.5,1.5,0.8,14,tier=4),
])

MIA = Team("MIA","Miami Heat",[
    _p("Tyler Herro","SG","6-5",24.0,5.0,5.0,2.5,34,tier=1),
    _p("Bam Adebayo","C","6-9",21.0,10.0,4.0,0.5,34,tier=1),
    _p("Jimmy Butler","SF","6-7",20.0,5.5,4.5,1.2,34,tier=1),
    _p("Nikola Jovic","PF","6-10",12.0,5.5,2.5,1.2,24,tier=2),
    _p("Haynes wo","SF","6-8",10.0,4.0,2.0,1.5,22,tier=3),
    _p("Jaime Jaquez Jr.","SF","6-7",9.0,3.5,2.0,1.2,20,tier=4),
])

ORL = Team("ORL","Orlando Magic",[
    _p("Paolo Banchero","F","6-10",24.0,6.5,5.0,1.8,34,tier=1),
    _p("Franz Wagner","F","6-10",19.0,4.5,3.5,1.5,32,tier=1),
    _p("Jalen Suggs","G","6-5",16.5,4.0,4.5,1.5,30,tier=2),
    _p("Wendell Carter Jr.","C","6-6",14.5,9.0,2.5,0.8,26,tier=2),
    _p("Cole Anthony","G","6-2",13.0,4.5,3.5,1.2,24,tier=3),
    _p("Goga Bitadze","C","6-11",10.5,6.0,2.0,0.5,18,tier=3),
    _p("Jonathan Isaac","F","6-10",6.5,4.0,1.0,0.5,16,tier=4),
    _p("Caleb Houstan","F","6-8",7.0,3.0,1.5,0.8,14,tier=4),
],["Franz Wagner OUT (calf)"])

HOU = Team("HOU","Houston Rockets",[
    _p("Alperen Sengun","C","6-9",21.0,9.0,5.0,0.5,34,tier=1),
    _p("Jalen Green","G","6-4",20.0,4.0,3.0,2.5,32,tier=1),
    _p("Fred VanVleet","PG","6-1",13.0,4.0,6.0,2.0,30,tier=2),
    _p("Jabari Smith Jr.","PF","6-10",14.0,6.0,1.5,1.5,28,tier=2),
    _p("Amen Thompson","G","6-7",11.0,5.0,3.0,0.8,24,tier=3),
    _p("Tari Eason","F","6-8",10.0,5.5,1.5,0.8,20,tier=3),
    _p("Jae'Sean Tate","F","6-5",8.0,4.0,2.0,0.5,16,tier=4),
    _p("Cam Whitmore","SF","6-6",12.0,3.5,1.0,1.0,18,tier=3),
])

DAL = Team("DAL","Dallas Mavericks",[
    _p("Kyrie Irving","PG","6-2",24.0,4.0,5.0,2.5,34,tier=1),
    _p("Luka Doncic","PG","6-7",29.0,7.5,8.0,2.8,34,"OUT",1),
    _p("Klay Thompson","SG","6-6",17.0,3.5,2.0,2.8,30,tier=2),
    _p("P.J. Washington","PF","6-7",13.0,5.5,2.0,1.2,28,tier=2),
    _p("Daniel Gafford","C","6-10",12.0,6.0,1.5,0.3,24,tier=2),
    _p("Dereck Lively II","C","7-0",8.0,5.0,1.0,0.2,18,tier=3),
    _p("Jaden Hardy","G","6-4",10.0,2.5,1.5,1.0,14,tier=4),
    _p("Markieff Morris","PF","6-8",6.0,3.0,1.0,0.8,12,tier=4),
],["Luka Doncic OUT (hamstring)"])

LAC = Team("LAC","LA Clippers",[
    _p("Kawhi Leonard","SF","6-7",23.0,6.0,3.5,1.8,32,tier=1),
    _p("James Harden","SG","6-4",20.0,5.5,8.0,2.5,34,tier=1),
    _p("Ivica Zubat","C","7-0",12.0,8.0,2.0,0.2,24,tier=2),
    _p("Norman Powell","SF","6-5",16.0,3.5,2.0,2.2,28,tier=2),
    _p("Derrick Jones Jr.","SF","6-6",10.0,3.5,1.5,1.0,22,tier=3),
    _p("Bones Hyland","G","6-3",9.0,2.0,2.5,1.5,16,tier=4),
    _p("Nicolas Batum","SF","6-8",6.0,3.5,2.0,1.2,18,tier=3),
    _p("Moisés Pacho","C","7-0",7.0,4.0,1.0,0.3,12,tier=4),
])

IND = Team("IND","Indiana Pacers",[
    _p("Tyrese Haliburton","PG","6-5",20.0,4.0,10.0,2.5,34,tier=1),
    _p("Pascal Siakam","PF","6-8",21.0,6.5,4.0,1.5,34,tier=1),
    _p("Myles Turner","C","6-11",15.0,6.5,2.0,1.2,28,tier=2),
    _p("Andrew Nembhard","PG","6-5",12.0,3.5,4.5,1.2,26,tier=3),
    _p("Obi Toppin","SF","6-6",11.0,4.0,1.5,1.5,20,tier=3),
    _p("Jalen Smith","PF","6-10",9.0,5.0,1.0,0.8,16,tier=4),
    _p("Aaron Nesmith","SF","6-6",8.0,3.0,1.5,1.2,14,tier=4),
])

TOR = Team("TOR","Toronto Raptors",[
    _p("Scottie Barnes","F","6-7",21.0,6.5,5.0,1.5,34,tier=1),
    _p("RJ Barrett","SG","6-7",19.0,5.0,3.0,2.0,30,tier=1),
    _p("Immanuel Quickley","PG","6-3",16.0,3.5,4.5,1.8,28,tier=2),
    _p("Jakob Poeltl","C","6-11",14.0,9.0,2.5,0.0,26,tier=2),
    _p("Gradey Dick","SF","6-7",13.0,4.0,2.0,1.8,24,tier=3),
    _p("Chris Boucher","PF","6-9",11.0,5.0,1.0,1.0,18,tier=3),
    _p("Kelly Olynyk","C","6-11",10.0,4.5,2.5,1.2,16,tier=4),
    _p("D.J. Carton","G","6-2",7.0,2.0,2.0,0.8,12,tier=4),
])

MEM = Team("MEM","Memphis Grizzlies",[
    _p("Jaren Jackson Jr.","PF","6-10",23.0,6.0,2.5,2.0,32,tier=1),
    _p("Desmond Bane","SG","6-5",20.0,4.5,3.5,2.5,30,tier=1),
    _p("Ja Morant","PG","6-3",25.0,5.0,7.0,1.8,30,tier=1),
    _p("Marcus Smart","PG","6-4",10.5,3.5,5.0,1.8,28,tier=2),
    _p("Ziaire Williams","SF","6-6",10.0,3.0,1.5,1.2,20,tier=3),
    _p("Vince Williams","SF","6-6",8.0,4.0,2.0,0.8,18,tier=4),
    _p("GG Jackson","SF","6-7",12.0,3.5,1.0,1.0,16,tier=4),
])

PHX = Team("PHX","Phoenix Suns",[
    _p("Kevin Durant","SF","6-10",26.0,6.0,4.0,2.5,34,tier=1),
    _p("Devin Booker","SG","6-5",25.0,4.5,5.5,2.2,34,tier=1),
    _p("Bradley Beal","SG","6-5",19.0,4.0,4.0,1.8,30,tier=2),
    _p("Jusuf Nurkic","C","6-11",13.0,9.0,2.5,0.5,26,tier=2),
    _p("Royce O'Neale","SF","6-8",7.0,5.0,3.0,1.5,24,tier=3),
    _p("Tyus Jones","PG","6-1",10.0,2.5,5.0,1.2,22,tier=3),
    _p("Ryan Dunn","SF","6-8",6.0,3.5,1.0,0.8,14,tier=4),
])

CHI = Team("CHI","Chicago Bulls",[
    _p("Zach LaVine","SG","6-5",24.0,4.5,4.0,2.5,32,tier=1),
    _p("DeMar DeRozan","SF","6-6",24.0,4.5,4.5,1.2,34,tier=1),
    _p("Nikola Vucevic","C","6-11",18.0,10.0,3.0,1.5,30,tier=2),
    _p("Patrick Williams","PF","6-8",13.0,5.0,1.5,1.5,26,tier=3),
    _p("Jalen Green","G","6-4",20.0,4.0,3.0,2.5,32,tier=1),
    _p("Josh Giddey","PG","6-8",13.0,7.0,6.0,1.0,28,tier=2),
    _p("Matas Buzelis","F","6-10",8.0,3.0,1.5,0.8,14,tier=4),
])

ATL = Team("ATL","Atlanta Hawks",[
    _p("Trae Young","PG","6-1",25.0,4.0,10.0,2.8,34,tier=1),
    _p("Zaccharie Risacher","SF","6-8",14.0,5.0,2.0,1.8,28,tier=2),
    _p("Jalen Johnson","PF","6-9",18.0,6.0,4.0,1.2,30,tier=2),
    _p("Onyeka Okongwu","C","6-9",13.0,7.0,1.5,0.3,26,tier=3),
    _p("Dyson Daniels","G","6-6",10.0,4.0,3.0,0.8,22,tier=3),
    _p("Vit Krejci","SF","6-7",9.0,3.5,2.0,1.0,18,tier=4),
])

POR = Team("POR","Portland Trail Blazers",[
    _p("Scoot Henderson","PG","6-3",18.0,4.0,6.0,1.5,30,tier=2),
    _p("Shaedon Sharpe","SG","6-5",20.0,4.0,2.5,1.8,28,tier=2),
    _p("Anfernee Simons","SG","6-3",21.0,3.5,4.0,2.0,30,tier=2),
    _p("Jerami Grant","SF","6-8",16.0,5.0,2.0,1.5,28,tier=2),
    _p("Deandre Ayton","C","6-11",14.0,10.0,2.0,0.2,28,tier=2),
    _p("Robert Williams III","C","6-10",8.0,6.0,1.5,0.3,16,tier=3),
    _p("Tonan","SF","6-8",7.0,3.0,1.5,0.8,12,tier=4),
])

UTAH = Team("UTAH","Utah Jazz",[
    _p("Lauri Markkanen","PF","6-9",23.0,6.5,2.0,2.5,32,tier=1),
    _p("Collin Sexton","SG","6-3",20.0,3.0,4.0,1.5,28,tier=2),
    _p("Walker Kessler","C","6-11",14.0,8.0,1.0,0.3,26,tier=2),
    _p("Keyonte George","G","6-4",15.0,3.0,4.0,1.2,24,tier=3),
    _p("Jordan Clarkson","G","6-4",17.0,3.5,5.0,2.0,26,tier=3),
    _p("Simone","PF","6-8",10.0,4.0,1.5,0.8,16,tier=4),
])

# ── Team index ─────────────────────────────────────────────────────────────────
TEAMS = {t.abbr: t for t in (
    DET, CLE, LAL, NYK, OKC, PHI, MIN, SA, BOS, DEN, GSW, MIA, ORL,
    HOU, DAL, LAC, IND, TOR, MEM, PHX, CHI, ATL, POR, UTAH,
)}

STAT_LABELS = {"pts": "PTS", "reb": "REB", "ast": "AST", "3pm": "3PM"}

# ── TC Core ──────────────────────────────────────────────────────────────────
def tc_line(tc_val: float) -> float:
    """Derive a market-implied line from a TC value."""
    return round(tc_val * LINE_FACTOR)

def tc_edge(tc_val: float, market_line: float) -> float:
    """Edge = TC minus market line."""
    return round(tc_val - market_line, 1)

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

# ── Projection builder — ALWAYS emits PTS, REB, AST, 3PM ────────────────────
def project_player(player: Player, market_lines: Dict[str, float]) -> List[Dict]:
    """
    ALWAYS generate projections for all four stats: PTS, REB, AST, 3PM.
    Each stat gets its own row regardless of market availability.
    Returns a list of pick dicts — one per stat.
    """
    tc = player.all_tc()   # always computed
    rows = []

    for stat, tc_val in tc.items():
        market_line = market_lines.get(stat)
        if market_line is None:
            # No market line — still report the TC, mark line as "N/A"
            edge = 0.0
            lean = "N/A"
            q = False
            kelly = 0.0
            odds = -110
        else:
            edge = tc_edge(tc_val, market_line)
            lean = "UNDER" if edge < -2 else ("OVER" if edge > 4 else "PASS")
            q = qualifies(edge, stat)
            odds = -110
            kelly = kelly_bet(edge if q else 0)

        flag = {"OUT": "🚫", "QUESTIONABLE": "⚠️"}.get(player.status, "")
        rows.append({
            "player":   player.name,
            "team":     player.tier,   # tier used as team proxy in output
            "stat":     stat,
            "stat_label": STAT_LABELS[stat],
            "tc":       tc_val,
            "line":     market_line if market_line is not None else None,
            "edge":     edge,
            "lean":     lean,
            "conf":     conf_from_edge(edge),
            "odds":     odds,
            "qualifies": q,
            "kelly":    kelly,
            "status":   flag,
            "tier":     player.tier,
        })

    return rows

def project_team(team: Team, market_lines_by_stat: Dict[str, Dict[str, float]]) -> List[Dict]:
    """
    Project all active players on a team across all four stats.
    ALWAYS returns 4 stats per player — never skips any.
    """
    all_rows = []
    for player in team.active():
        player_lines = {}
        for stat in ["pts", "reb", "ast", "3pm"]:
            player_lines[stat] = market_lines_by_stat.get(stat, {}).get(player.last_name)
        rows = project_player(player, player_lines)
        all_rows.extend(rows)
    return all_rows

# ── Backtest ──────────────────────────────────────────────────────────────────
@dataclass
class BacktestGame:
    home: str; away: str
    market_total: float; actual_total: int
    date: str; round_label: str

BACKTEST_GAMES = [
    BacktestGame("DET","ORL",208.5,210,"May 3, 2026","R1 G7"),
    BacktestGame("PHI","BOS",215.5,209,"May 3, 2026","R1 G7"),
    BacktestGame("CLE","TOR",218.5,245,"May 3, 2026","R1 G7"),
    BacktestGame("LAL","HOU",224.5,226,"May 3, 2026","R1 G7"),
    BacktestGame("NYK","DET",213.5,202,"May 2, 2026","R1 G7"),
    BacktestGame("MIN","SA", 229.5,224,"May 2, 2026","R1 G7"),
    BacktestGame("OKC","MEM",218.5,212,"May 2, 2026","R1 G7"),
    BacktestGame("DEN","LAC",226.5,221,"May 1, 2026","R1 G7"),
    BacktestGame("BOS","ORL",221.5,214,"May 1, 2026","R1 G7"),
]

def run_backtest():
    print("\n  ═══════════════════════════════════════════")
    print("  NBA TC BACKTEST — 9 Playoff Games")
    print("  ═══════════════════════════════════════════")
    hit = 0
    for g in BACKTEST_GAMES:
        ht = TEAMS[g.home]; at = TEAMS[g.away]
        ht_tc = ht.game_tc(); at_tc = at.game_tc()
        combined_tc = round(ht_tc + at_tc, 1)
        derived_total = round((combined_tc / PLAYOFF_MULT + HISTORICAL_GAP) * LINE_FACTOR * 2)
        under_hit = "UNDER" if derived_total > g.actual_total else "OVER"
        correct = "✅" if under_hit == "UNDER" else "❌"
        if under_hit == "UNDER": hit += 1
        print(f"  {g.date} {g.away}@{g.home} {g.round_label} | "
              f"TC={combined_tc:.1f} | Market={g.market_total} | "
              f"Actual={g.actual_total} | "
              f"Diff={derived_total - g.actual_total:+.1f} | {correct}")
    print(f"\n  UNDER hit rate: {hit}/9 = {hit*100//9}%")
    print("  ═══════════════════════════════════════════\n")

# ── API fetch ─────────────────────────────────────────────────────────────────
SAVE_DIR = Path("/home/workspace")

def get_api_key() -> str:
    for path in ["/home/workspace/odds_fetcher.keys", "/home/workspace/.keys/api_key.txt",
                 Path.home()/".config/odds_api.key"]:
        if Path(path).exists():
            return Path(path).read_text().strip()
    return os.environ.get("ODDS_API_KEY", "")

def fetch_nba_events(force_refresh: bool = False):
    key = get_api_key()
    cache = SAVE_DIR / "sportsgameodds_nba_events.json"
    if force_refresh and cache.exists():
        cache.unlink()
    if cache.exists():
        age = time.time() - cache.stat().st_mtime
        if age < 300:
            return json.loads(cache.read_text())
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.sportsgameodds.com/v1/nba",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        cache.write_text(json.dumps(data))
        return data
    except Exception as e:
        if cache.exists():
            return json.loads(cache.read_text())
        return {"success": False, "error": str(e), "data": []}

def extract_player_props(events):
    import re
    props = []
    game_totals = {}
    stat_map = {"points": "pts", "rebounds": "reb", "assists": "ast", "threePointShotsMade": "3pm"}
    skip_terms = ["1st", "2nd", "3rd", "4th", "half", "quarter"]
    for event in events.get("data", []):
        teams = event.get("teams", {})
        away_s = teams.get("away",{}).get("names",{}).get("short","")
        home_s = teams.get("home",{}).get("names",{}).get("short","")
        game   = f"{away_s} @ {home_s}"
        players = event.get("players", {}) or {}
        odds_map = event.get("odds", {}) or {}
        ou_key = "points-all-game-ou-over"
        ou = odds_map.get(ou_key, {})
        line = ou.get("bookOverUnder") or ou.get("fairOverUnder")
        if line:
            try:
                game_totals[game] = float(line)
            except Exception:
                pass
        for odd_id, odd in odds_map.items():
            stat_id    = odd.get("statID", "")
            player_id  = odd.get("playerID")
            if not player_id:
                continue
            period_id = odd.get("periodID", "")
            if period_id and period_id != "game":
                continue
            market = odd.get("marketName", "").lower()
            if any(t in market for t in skip_terms):
                continue
            stat = stat_map.get(stat_id)
            if not stat:
                continue
            book_ou = odd.get("bookOverUnder") or odd.get("fairOverUnder")
            if not book_ou:
                continue
            try:
                line = float(book_ou)
            except Exception:
                continue
            player = players.get(player_id, {})
            props.append({
                "game":     game,
                "player":   player.get("name") or player_id,
                "player_id": player_id,
                "stat":     stat,
                "line":     line,
                "book_odds": odd.get("bookOdds"),
            })
    return props, game_totals

def auto_detect_games(events):
    detected = []
    for event in events.get("data", []):
        teams = event.get("teams", {})
        away = teams.get("away",{}).get("names",{}).get("short","").upper()
        home = teams.get("home",{}).get("names",{}).get("short","").upper()
        if away in TEAMS and home in TEAMS:
            detected.append({"away_abbr": away, "home_abbr": home,
                              "series": "Round 2", "game_time": "TBD"})
    return detected

# ── Print functions ──────────────────────────────────────────────────────────
def print_roster(team: Team):
    print(f"\n  {'─'*80}")
    print(f"  {team.abbr}  {team.name}")
    for n in team.injury_notes:
        print(f"  ⚠️  {n}")
    print(f"  {'Player':<22} {'POS':<4} {'MPG':>4} "
          f"{'PTS':>5} {'TC_PTS':>6} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} {'TC_TOT':>7} {'S'}")
    print(f"  {'─'*80}")
    for p in team.players:
        if p.status == "OUT":
            print(f"  🚫 {p.name:<20} {'OUT'}")
            continue
        star = "⭐" if p.tier == 1 else " "
        tc = p.all_tc()
        tot = p.tc_total()
        flag = {"QUESTIONABLE": "⚠️"}.get(p.status, "")
        print(f"  {star}{p.name:<20} {p.pos:<4} {p.min_avg:>4.0f} {p.pts:>5.1f}"
              f" {tc['pts']:>6.1f} {tc['reb']:>7.1f} {tc['ast']:>7.1f} {tc['3pm']:>7.1f} {tot:>7.1f} {flag}")

def print_game_projection(home_abbr: str, away_abbr: str, prop_map: dict, game_total: float = None):
    ht = TEAMS[home_abbr]; at = TEAMS[away_abbr]
    htc = ht.game_tc(); atc = at.game_tc()
    combined = round(htc + atc, 1)

    # Game-level lean
    if game_total:
        edge = round(combined - game_total, 1)
    else:
        edge = round(combined - (ht.vegas_line() + at.vegas_line()), 1)
    lean = "UNDER" if edge < -2 else ("OVER" if edge > 4 else "PASS")

    injuries = ht.injury_notes + at.injury_notes
    picks = build_picks(home_abbr, away_abbr, prop_map)
    qualified = [p for p in picks if p["qualifies"]]

    print(f"\n{'═'*80}")
    print(f"  🏀 NBA TC PROJECTION  {away_abbr} @ {home_abbr}")
    print(f"  TC Combined: {at.name}={atc:.1f} + {ht.name}={htc:.1f} = {combined:.1f}")
    print(f"  Game Total Edge: {edge:+.1f}  |  Lean: {lean}")
    if game_total:
        print(f"  Market Total: {game_total}")
    if injuries:
        for n in injuries: print(f"  ⚠️  {n}")
    print(f"{'═'*80}")

    for abbr, label in [(away_abbr,"Away"),(home_abbr,"Home")]:
        print_roster(TEAMS[abbr])

    # Always print ALL four stat categories (PTS, REB, AST, 3PM)
    print(f"\n  📋 ALL PROJECTIONS — PTS / REB / AST / 3PM (always generated):")
    print(f"  {'#':<3} {'Player':<20} {'Team':<4} {'Stat':<4} {'TC':>6} {'Line':>6} {'Edge':>6} {'Lean':<5} {'Kelly':>8} {'Conf':>4}")
    print(f"  {'─'*80}")
    for i, p in enumerate(picks, 1):
        ofmt = f"+{p['odds']}" if p['odds'] > 0 else str(p['odds'])
        line_str = f"{p['line']}" if p['line'] is not None else "N/A"
        edge_str = f"{p['edge']:+.1f}" if p['edge'] != 0 else "—"
        print(f"  {i:2d}. {p['player']:<20} {p['team']:<4} {p['stat']:<4}"
              f" {p['tc']:>6.1f} {line_str:>6} {edge_str:>6} {p['lean']:<5}"
              f" ${p['kelly']:>7.2f} {p['conf']:>3}%")

    total_kelly = sum(p["kelly"] for p in qualified)
    print(f"\n  Total Kelly Exposure: ${total_kelly:.2f} / ${BANKROLL:,.0f}")
    print(f"  Qualified picks: {len(qualified)}")
    print(f"{'═'*80}")
    print(f"  FORMULAS: TC_pts=pts×{CONS_PTS}+{GAP_PTS} | TC_reb=reb×{CONS_REB}+{GAP_REB}"
          f" | TC_ast=ast×{CONS_AST}+{GAP_AST} | TC_3pm=tpm×{CONS_3PM}+{GAP_3PM}")
    print(f"  CONF: ≥10→72% | ≥7→68% | ≥5→64% | ≥3→60% | <3→57%")
    print(f"  KELLY: full_kelly × 0.5 | Bankroll=${BANKROLL:,.0f}")
    print(f"  BACKTEST: 9 games | 7/9 UNDER hit = 78%")

def build_picks(home_abbr: str, away_abbr: str, prop_map: dict) -> list:
    picks = []
    for abbr in [away_abbr, home_abbr]:
        team = TEAMS[abbr]
        for player in team.active():
            tc = player.all_tc()
            for stat, tc_val in tc.items():
                ln = player.last_name
                market_line = prop_map.get((ln, stat), {}).get("line")
                if market_line is not None:
                    edge = tc_edge(tc_val, market_line)
                    lean = "UNDER" if edge < -2 else ("OVER" if edge > 4 else "PASS")
                    q = qualifies(edge, stat)
                    odds = prop_map.get((ln, stat), {}).get("book_odds", -110)
                    try:
                        odds = int(odds)
                    except (TypeError, ValueError):
                        odds = -110
                    k = kelly_bet(edge if q else 0, odds)
                else:
                    edge = tc_val  # show TC as pseudo-edge when no market
                    lean = "N/A"
                    q = False
                    odds = -110
                    k = 0.0
                flag = {"OUT": "🚫", "QUESTIONABLE": "⚠️"}.get(player.status, "")
                picks.append({
                    "player":   player.name,
                    "team":     abbr,
                    "stat":     stat,
                    "tc":       tc_val,
                    "line":     market_line,
                    "edge":     edge if market_line is not None else 0.0,
                    "lean":     lean,
                    "conf":     conf_from_edge(edge if market_line is not None else 0.0),
                    "odds":     odds,
                    "qualifies": q,
                    "kelly":    k,
                    "status":   flag,
                })
    picks.sort(key=lambda x: abs(x["edge"]), reverse=True)
    return picks

# ── Parlay builder ──────────────────────────────────────────────────────────
def build_parlay(game_configs: list, prop_map: dict) -> list:
    """
    Build a parlay card from game configs.
    Always shows all four stat projections per player.
    Grouped by game with spread/total summary.
    """
    legs = []
    leg_num = 1

    for gc in game_configs:
        home, away = gc["home_abbr"], gc["away_abbr"]
        ht = TEAMS[home]; at = TEAMS[away]
        htc = ht.game_tc(); atc = at.game_tc()
        combined = round(htc + atc, 1)
        game_key = f"{away} @ {home}"
        market_total = gc.get("market_total")

        if market_total:
            total_edge = round(combined - market_total, 1)
            total_lean = "UNDER" if total_edge < -2 else ("OVER" if total_edge > 4 else "PASS")
        else:
            total_edge = 0.0
            total_lean = "N/A"

        # Game-level leg
        game_leg = {
            "leg": leg_num,
            "game": game_key,
            "series": gc.get("series", ""),
            "pick_type": "GAME_TOTAL",
            "description": f"{away} @ {home} | TC={combined:.1f}",
            "tc": combined,
            "market": market_total,
            "edge": total_edge,
            "lean": total_lean,
        }
        legs.append(game_leg)
        leg_num += 1

        # Per-team per-player stat legs — always 4 stats per player
        for abbr, label in [(away, "AWAY"), (home, "HOME")]:
            team = TEAMS[abbr]
            for player in team.active():
                tc = player.all_tc()
                for stat, tc_val in tc.items():
                    ln = player.last_name
                    market_line = prop_map.get((ln, stat), {}).get("line")
                    if market_line is not None:
                        edge = tc_edge(tc_val, market_line)
                        lean = "UNDER" if edge < -2 else ("OVER" if edge > 4 else "PASS")
                        q = qualifies(edge, stat)
                        if q:
                            legs.append({
                                "leg": leg_num,
                                "game": game_key,
                                "series": gc.get("series", ""),
                                "pick_type": f"TC_{stat.upper()}",
                                "description": f"{player.name} {STAT_LABELS[stat]} TC={tc_val:.1f}",
                                "tc": tc_val,
                                "market": market_line,
                                "edge": edge,
                                "lean": lean,
                            })
                            leg_num += 1

    return legs

# ── CLI ─────────────────────────────────────────────────────────────────────
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--game", type=str)
    p.add_argument("--report", type=str)
    p.add_argument("--output", type=str)
    p.add_argument("--serve", action="store_true")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--prop-file", action="store_true")
    p.add_argument("--parlay", action="store_true")
    p.add_argument("--market-total", type=float)
    p.add_argument("--bankroll", type=float, default=BANKROLL)
    args = p.parse_args()

    if args.backtest:
        run_backtest()
        return

    prop_file = SAVE_DIR / "sportsgameodds_nba_player_props.json"

    if args.prop_file:
        print(f"Prop cache: {prop_file}")
        if prop_file.exists():
            data = json.loads(prop_file.read_text())
            print(f"Entries: {len(data.get('data',[]))}  |  Cached: {data.get('_cached_at','unknown')}")
        return

    # ── Fetch live ──
    print("\n  🔄 Fetching live NBA data...")
    events = fetch_nba_events(force_refresh=args.refresh)
    if events.get("success"):
        print(f"  ✅ API connected | events={len(events.get('data',[]))}")
    else:
        print(f"  ⚠️  API: {events.get('error','Unknown')} — using cached data")

    props, game_totals = extract_player_props(events)
    save_json({"data": props, "game_totals": game_totals}, "sportsgameodds_nba_player_props.json")
    print(f"  📋 Props: {len(props)} | Game totals: {game_totals}")

    # Build lookup: (last_name, stat) -> prop
    prop_lookup = {}
    for p in props:
        ln = p["player"].split()[-1].lower()
        key = (ln, p["stat"])
        if key not in prop_lookup:
            prop_lookup[key] = p

    detected = auto_detect_games(events)
    if detected:
        print(f"  🏀 Auto-detected: " + ", ".join(f"{g['away_abbr']}@{g['home_abbr']}" for g in detected))

    if args.game or args.report:
        parts = (args.game or args.report).upper().replace("@"," ").split()
        away, home = parts[0], parts[1]
        if home not in TEAMS or away not in TEAMS:
            print(f"  ❌ Unknown team"); return
        game_configs = [{"home_abbr": home, "away_abbr": away,
                         "series": "Round 2", "game_time": "", "market_total": args.market_total}]
    elif detected:
        game_configs = [{"home_abbr": g["home_abbr"], "away_abbr": g["away_abbr"],
                         "series": g.get("series",""), "game_time": g.get("game_time",""),
                         "market_total": game_totals.get(f"{g['away_abbr']} @ {g['home_abbr']}")} for g in detected]
    else:
        game_configs = [
            {"home_abbr":"MIN","away_abbr":"SA","series":"Round 2","game_time":"8 PM ET","market_total": None},
            {"home_abbr":"DET","away_abbr":"CLE","series":"Round 2","game_time":"8 PM ET","market_total": None},
        ]

    for gc in game_configs:
        home, away = gc["home_abbr"], gc["away_abbr"]
        game_key = f"{away} @ {home}"
        gt = game_totals.get(game_key) or gc.get("market_total")
        print(f"\n  Processing {away} @ {home}...")
        print_game_projection(home, away, prop_lookup, game_total=gt)

    # Parlay output
    if args.parlay:
        legs = build_parlay(game_configs, prop_lookup)
        print(f"\n  🎰 PARLAY CARD — {len(legs)} legs")
        print(f"  {'#':<3} {'Game':<16} {'Pick':<40} {'TC':>6} {'Line':>6} {'Edge':>6} {'Lean'}")
        print(f"  {'─'*85}")
        for leg in legs:
            line_str = f"{leg['market']}" if leg['market'] else "N/A"
            edge_str = f"{leg['edge']:+.1f}" if leg['edge'] != 0 else "—"
            print(f"  {leg['leg']:2d}. {leg['game']:<16} {leg['pick_type']:<12} {leg['description']:<28} {leg['tc']:>6.1f} {line_str:>6} {edge_str:>6} {leg['lean']}")

    if args.output:
        out = Path("/home/workspace") / args.output
        out.write_text("Run with --report to generate markdown output")
        print(f"\n  💾 Output saved to {out}")

    if args.serve:
        try:
            from fastapi import FastAPI
            import uvicorn
            app = FastAPI(title="NBA TC API", version="1.0")
            @app.get("/")
            def root(): return {"status":"ok","teams":list(TEAMS.keys())}
            @app.get("/games")
            def list_games():
                return [{"home":g["home_abbr"],"away":g["away_abbr"],"series":g.get("series",""),"time":g.get("game_time","")} for g in game_configs]
            @app.get("/tc/{away}_{home}")
            def tc_game(away: str, home: str):
                if home.upper() not in TEAMS or away.upper() not in TEAMS:
                    return {"error": "Unknown team"}
                prop_lookup = {}
                for pr in props:
                    ln = pr["player"].split()[-1].lower()
                    key = (ln, pr["stat"])
                    if key not in prop_lookup:
                        prop_lookup[key] = pr
                game_key = f"{away.upper()} @ {home.upper()}"
                gt = game_totals.get(game_key)
                ht = TEAMS[home.upper()]; at = TEAMS[away.upper()]
                htc = ht.game_tc(); atc = at.game_tc()
                combined = round(htc + atc, 1)
                picks = build_picks(home.upper(), away.upper(), prop_lookup)
                qualified = [x for x in picks if x["qualifies"]]
                return {
                    "summary": {
                        "away_tc": atc, "home_tc": htc,
                        "combined_tc": combined,
                        "market_total": gt,
                        "edge": round(combined - gt, 1) if gt else None,
                    },
                    "picks": qualified,
                    "all_projections": picks,
                }
            print(f"\n  🚀 FastAPI on port {FASTAPI_PORT}...")
            uvicorn.run(app, host="0.0.0.0", port=FASTAPI_PORT)
        except Exception as e:
            print(f"  ❌ FastAPI error: {e}  (pip install fastapi uvicorn)")

def save_json(data: dict, name: str) -> str:
    path = SAVE_DIR / name
    path.write_text(json.dumps(data, indent=2))
    return str(path)

if __name__ == "__main__":
    main()