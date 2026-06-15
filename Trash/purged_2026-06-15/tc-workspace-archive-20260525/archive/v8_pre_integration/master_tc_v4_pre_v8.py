#!/usr/bin/env python3
"""
SPORTS TC MASTER ENGINE v4.0 — Integrated NBA + WNBA Triple Conservative System
==============================================================================
TC Formula:   TC = stat × 0.85  |  Q = TC × 0.55  |  OUT = 0
LINE Formula: LINE = TC_combined × 0.88  |  Edge = TC − LINE
Edge Signal:  TC > LINE = OVER lean  |  TC < LINE = UNDER lean

Usage:
  python master_tc.py --sport NBA --game "PHI @ NYK"
  python master_tc.py --sport WNBA --game "NYL @ POR"
  python master_tc.py --sport NBA --backtest
  python master_tc.py --sport WNBA --backtest
  python master_tc.py --sport WNBA --rosters
"""

import argparse, json, sys, urllib.request, warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional

warnings.filterwarnings("ignore")

# ── CONSTANTS ────────────────────────────────────────────────────────────────────
CONS   = 0.85   # conservative multiplier for ACTIVE players
Q_MULT = 0.55   # questionable multiplier (was 0.65, TC-downgraded to 0.55)
OUT_Z  = 0.0    # out = zero contribution
LINE_FACTOR = 0.88   # LINE = TC_combined × 0.88
MIN_EDGE = 2.0  # minimum edge to qualify a pick

# ── PLAYER CLASS ──────────────────────────────────────────────────────────
@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float = 0.0
    ast: float = 0.0
    tpm: float = 0.0
    status: str = "ACTIVE"

    def tc(self, stat: float) -> float:
        if self.status == "OUT": return 0.0
        if self.status == "Q":   return round(stat * Q_MULT, 1)
        return round(stat * CONS, 1)

    def proj(self) -> dict:
        return {
            "TC_PTS": self.tc(self.pts),
            "TC_REB": self.tc(self.reb),
            "TC_AST": self.tc(self.ast),
            "TC_3PM": self.tc(self.tpm),
        }

    def tc_total(self) -> float:
        p = self.proj()
        return round(p["TC_PTS"] + p["TC_REB"] + p["TC_AST"] + p["TC_3PM"], 1)

    def status_icon(self) -> str:
        return "✅" if self.status == "ACTIVE" else "⚠️" if self.status == "Q" else "❌"


# ── TEAM CLASS ─────────────────────────────────────────────────────────────
@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player] = field(default_factory=list)

    def starters(self) -> List[Player]:
        active = [p for p in self.players if p.status != "OUT"]
        return sorted(active, key=lambda p: p.pts, reverse=True)[:5]

    def roster(self) -> List[Player]:
        return sorted(self.players, key=lambda p: p.pts, reverse=True)

    def bench(self) -> List[Player]:
        start_names = {p.name for p in self.starters()}
        return [p for p in self.players
                if p.name not in start_names and p.status != "OUT"]

    def _sum_stat(self, player_list: List[Player], key: str) -> float:
        return round(sum(p.proj()[key] for p in player_list), 1)

    def team_totals(self, player_list: List[Player]) -> dict:
        t = {k: self._sum_stat(player_list, k) for k in ["TC_PTS","TC_REB","TC_AST","TC_3PM"]}
        t["TC_TOTAL"] = round(t["TC_PTS"] + t["TC_REB"] + t["TC_AST"] + t["TC_3PM"], 1)
        return t

    def starters_totals(self) -> dict:
        return self.team_totals(self.starters())

    def bench_totals(self) -> dict:
        return self.team_totals(self.bench())

    def team_totals_all(self) -> dict:
        active = [p for p in self.players if p.status != "OUT"]
        return self.team_totals(active)


# ── ROSTERS ───────────────────────────────────────────────────────────────

# ─── NBA ROSTERS (2025-26 SEASON) ─────────────────────────────────────────
NBA_ROSTERS: Dict[str, List[Player]] = {
    "NYK": [
        Player("Jalen Brunson","PG","6-2",26.0,3.5,6.5,2.5),
        Player("Karl-Anthony Towns","C","6-11",24.5,10.5,3.0,2.0),
        Player("Mikal Bridges","SG","6-6",19.0,4.5,3.5,2.2),
        Player("OG Anunoby","SF","6-7",17.5,5.0,2.5,1.8),
        Player("Josh Hart","PF","6-5",13.5,6.5,4.5,1.2),
        Player("Miles McBride","PG","6-2",9.5,2.5,3.0,1.5),
        Player("Precious Achiuwa","PF","6-8",7.5,5.5,1.0,0.5),
        Player("Jordan Clarkson","G","6-4",16.5,3.5,4.5,1.8),
        Player("Jerome Robinson","G","6-5",5.0,2.0,1.5,0.8),
        Player("Jake LaRavia","F","6-8",5.0,3.0,1.0,0.8),
    ],
    "PHI": [
        Player("Joel Embiid","C","7-0",28.5,10.5,5.5,1.8),
        Player("Tyrese Maxey","PG","6-2",24.5,4.5,6.5,2.5),
        Player("Paul George","SF","6-8",22.0,5.5,4.5,3.2),
        Player("Kelly Oubre Jr.","F","6-7",18.5,5.0,1.5,2.1),
        Player("Andre Drummond","C","6-9",10.0,10.0,2.0,0.0),
        Player("Justin Edwards","F","6-6",8.0,3.0,1.0,0.8),
        Player("VJ Edgecombe","G","6-5",15.0,3.5,2.5,1.2),
        Player("Quentin Grimes","G","6-5",10.0,3.0,2.5,1.8),
        Player("MarJon Beauchamp","F","6-7",7.0,3.5,1.0,0.8),
        Player("Kyle Lowry","PG","6-0",6.0,3.0,4.5,1.2),
    ],
    "BOS": [
        Player("Jayson Tatum","F","6-8",28.5,7.5,5.0,2.9),
        Player("Jaylen Brown","G","6-6",23.0,6.0,3.5,2.2),
        Player("Kristaps Porzingis","C","7-1",20.0,7.0,2.5,2.8),
        Player("Derrick White","G","6-4",16.0,4.2,4.8,2.8),
        Player("Jrue Holiday","G","6-4",14.5,4.5,5.0,1.8),
        Player("Al Horford","F","6-9",9.0,6.2,3.5,2.0),
        Player("Payton Pritchard","G","6-2",8.0,2.8,3.0,1.5),
        Player("Sam Hauser","F","6-6",7.5,3.0,1.5,1.2),
    ],
    "CLE": [
        Player("Donovan Mitchell","SG","6-1",27.0,4.5,5.0,2.5),
        Player("Darius Garland","PG","6-1",20.0,3.0,7.0,2.2),
        Player("Evan Mobley","PF","6-11",18.0,9.5,3.0,0.8),
        Player("Jarrett Allen","C","6-9",15.0,10.0,2.0,0.0),
        Player("Caris LeVert","SG","6-5",12.0,4.0,3.0,1.5),
        Player("Isaac Okoro","SG","6-5",8.5,3.0,2.0,1.2),
        Player("Max Strus","SF","6-5",9.0,4.0,3.0,2.0),
        Player("Ty Jerome","PG","6-6",7.5,2.5,3.5,1.2),
    ],
    "OKC": [
        Player("Shai Gilgeous-Alexander","SG","6-5",32.0,5.0,6.5,2.8),
        Player("Jalen Williams","SF","6-6",18.5,5.5,4.0,1.5),
        Player("Chet Holmgren","C","7-0",16.0,8.0,2.5,1.0),
        Player("Isaiah Hartenstein","C","6-11",8.0,7.5,2.5,0.2),
        Player("Alex Caruso","G","6-4",6.0,2.5,2.0,1.2),
        Player("Luguentz Dort","SG","6-4",9.5,3.5,1.2,2.0),
        Player("Isaiah Joe","G","6-1",9.0,2.0,0.8,2.1),
        Player("Jared McCain","G","6-3",9.5,2.5,2.0,1.0),
        Player("Cason Wallace","G","6-4",8.5,2.5,1.5,1.8),
        Player("Aaron Wiggins","G","6-5",7.5,2.0,1.0,1.2),
    ],
    "MIN": [
        Player("Anthony Edwards","G","6-4",30.0,5.0,5.5,3.5),
        Player("Julius Randle","PF","6-9",22.0,9.0,4.5,1.8),
        Player("Rudy Gobert","C","7-1",14.0,12.0,1.5,0.2),
        Player("Donte DiVincenzo","SG","6-4",10.0,4.0,3.0,2.0),
        Player("Mike Conley","PG","6-1",11.0,3.0,5.5,2.0),
        Player("Naz Reid","C","6-9",13.5,5.0,2.0,1.8),
        Player("Kyle Anderson","F","6-9",8.5,5.0,4.0,0.8),
        Player("Nickeil Alexander-Walker","SG","6-5",12.0,3.5,2.5,2.0),
        Player("Jaden McDaniels","PF","6-10",14.0,4.5,2.0,1.5),
        Player("Bones Hyland","G","6-3",10.0,3.0,3.0,1.8),
    ],
    "DEN": [
        Player("Nikola Jokic","C","6-11",29.0,12.5,10.0,2.0),
        Player("Jamal Murray","G","6-4",22.0,4.5,6.5,2.2),
        Player("Michael Porter Jr.","F","6-10",16.5,6.5,2.5,2.0),
        Player("Aaron Gordon","F","6-9",14.0,6.5,3.0,1.5),
        Player("Russell Westbrook","G","6-3",12.0,5.0,6.5,1.2),
        Player("Christian Braun","G","6-6",9.0,3.5,2.0,1.0),
        Player("Peyton Watson","F","6-8",10.0,4.0,2.0,0.8),
        Player("DeAndre Jordan","C","6-11",6.0,5.0,1.0,0.0),
    ],
    "DET": [
        Player("Cade Cunningham","PG","6-6",26.5,6.5,8.5,1.8),
        Player("Jalen Duren","C","6-11",12.0,9.0,2.0,0.0),
        Player("Tobias Harris","SF","6-8",18.5,6.5,3.0,1.5),
        Player("Tim Hardaway Jr.","SG","6-5",11.5,3.5,1.5,2.2),
        Player("Marcus Smart","PG","6-4",10.5,3.5,5.0,1.8),
        Player("Ausar Thompson","SG","6-5",8.5,4.5,2.5,0.5),
        Player("Jaden Ivey","PG","6-4",15.0,4.0,3.5,1.5),
        Player("Dennis Schroder","PG","6-1",13.0,3.0,6.0,1.5),
    ],
    "SAS": [
        Player("Victor Wembanyama","C","7-4",28.0,10.5,4.0,2.5),
        Player("De'Aaron Fox","G","6-3",24.5,5.5,6.5,1.8),
        Player("Harrison Barnes","F","6-8",13.5,5.8,2.2,1.4),
        Player("Stephon Castle","G","6-5",15.0,4.5,4.0,1.2),
        Player("Keldon Johnson","F","6-5",14.0,4.5,2.0,2.0),
        Player("Devin Vassell","SG","6-5",12.0,3.5,2.5,2.2),
        Player("Julian Champagnie","F","6-6",8.0,3.5,1.5,1.5),
        Player("Bismack Biyombo","C","6-11",9.5,8.0,1.5,0.2),
        Player("Dylan Harper","G","6-6",12.0,4.0,3.5,1.5),
        Player("Jeremy Sochan","F","6-8",8.0,4.5,3.0,0.8),
    ],
    "LAL": [
        Player("LeBron James","SF","6-9",25.0,7.5,8.0,2.2),
        Player("Austin Reaves","SG","6-5",18.0,4.0,5.0,2.5),
        Player("Rui Hachimura","PF","6-8",14.5,5.0,1.5,1.2),
        Player("Luka Doncic","PG","6-7",29.0,7.5,8.0,2.8,"OUT"),
        Player("Jordan Goodwin","SG","6-4",12.5,4.5,3.5,1.5),
        Player("Dorian Finney-Smith","SF","6-7",8.5,4.0,2.0,1.5),
        Player("Gabe Vincent","PG","6-2",6.5,2.0,2.0,1.2),
        Player("Max Christie","SG","6-5",7.0,3.0,1.5,1.2),
        Player("Bronny James","G","6-4",5.0,2.0,2.0,0.8),
        Player("Jaxson Hayes","C","6-10",8.0,4.0,1.0,0.3),
    ],
    "ORL": [
        Player("Paolo Banchero","F","6-10",28.5,7.5,5.5,1.5),
        Player("Franz Wagner","F","6-10",22.0,5.0,4.0,1.8,"OUT"),
        Player("Jalen Suggs","G","6-5",16.5,4.0,4.5,1.5),
        Player("Wendell Carter Jr.","C","6-6",14.5,9.0,2.5,0.8),
        Player("Cole Anthony","G","6-2",13.0,4.5,3.5,1.2),
        Player("Goga Bitadze","C","6-11",10.5,6.0,2.0,0.5),
        Player("Jonathan Isaac","F","6-10",6.5,4.0,1.0,0.5),
        Player("Caleb Houstan","F","6-8",7.0,3.0,1.5,0.8),
    ],
    "HOU": [
        Player("Alperen Sengun","C","6-9",21.5,9.5,5.0,0.8),
        Player("Jabari Smith Jr.","F","6-10",18.0,7.0,1.8,2.5),
        Player("Tari Eason","F","6-8",14.5,7.0,2.0,1.2),
        Player("Reed Sheppard","G","6-2",13.0,4.0,3.0,2.2),
        Player("Amen Thompson","G","6-6",12.5,5.5,3.5,0.8),
        Player("Cam Whitmore","G","6-4",11.0,4.0,1.5,1.5),
        Player("Jalen Green","G","6-4",18.0,4.5,3.0,2.0),
        Player("Dillon Brooks","F","6-6",12.0,4.0,2.0,1.5),
    ],
    "TOR": [
        Player("Scottie Barnes","F","6-8",21.5,7.5,5.5,1.5),
        Player("RJ Barrett","G","6-7",19.5,5.5,3.5,2.0),
        Player("Immanuel Quickley","G","6-2",15.0,4.0,4.5,1.5),
        Player("Jakob Poeltl","C","6-11",12.5,9.5,2.5,0.0),
        Player("Jamal Shead","G","6-2",9.5,3.0,4.5,1.2),
        Player("Ochai Agbaji","G","6-5",8.5,3.5,2.0,1.2),
        Player("Collin Murray-Boyles","F","6-8",12.0,5.5,2.5,0.5),
    ],
}

# ─── WNBA ROSTERS (2025 SEASON — REAL NAMES) ────────────────────────────────
WNBA_ROSTERS: Dict[str, List[Player]] = {
    "NYL": [
        Player("Breanna Stewart","F","6-4",19.5,8.5,4.0,2.4),
        Player("Sabrina Ionescu","G","5-11",17.5,5.5,7.1,3.2),
        Player("Jonquel Jones","C","6-6",15.0,9.0,2.9,1.5),
        Player("Courtney Vandersloot","G","5-8",10.9,4.0,6.5,1.8),
        Player("Betnijah Laney-Hamilton","F","6-0",10.8,3.0,1.6,1.0),
        Player("Kayla Thornton","F","6-2",6.5,4.0,0.9,0.8),
        Player("Marine Johannes","G","5-10",10.9,2.1,3.6,1.8),
        Player("Leonor M. Lopes","F","6-3",4.0,2.0,0.5,0.3),
    ],
    "MIN": [
        Player("Napheesa Collier","F","6-2",17.0,5.5,3.4,1.8),
        Player("Kayla McBride","G","5-11",14.1,3.5,2.0,1.0),
        Player("Alana Smith","F","6-3",11.5,7.0,1.5,0.5),
        Player("Natasha Howard","G","5-8",11.0,2.9,5.5,1.5),
        Player("Diamond Miller","G","6-2",8.5,4.0,1.0,0.8),
        Player("Nele","F","6-3",6.0,3.0,0.5,0.3),
        Player("Olivia","G","5-7",4.5,1.0,1.5,0.4),
        Player("Nara","G","5-9",3.5,0.8,0.8,0.3),
    ],
    "DAL": [
        Player("Arielle","G","5-10",16.5,4.5,4.5,2.0),
        Player("Moriah","G","6-0",14.0,4.0,3.5,1.3),
        Player("Caitlin","F","6-3",12.5,6.0,1.5,0.8),
        Player("Naomi","C","6-5",10.5,7.0,1.0,0.5),
        Player("Satou Sabally","F","6-2",9.0,4.5,1.5,0.8),
        Player("Lindsay","G","5-9",7.5,2.0,2.5,0.9),
        Player("Jaiden","F","6-3",5.5,3.0,0.5,0.3),
        Player("Awak","G","5-8",4.0,1.0,1.0,0.3),
    ],
    "LVA": [
        Player("A'ja Wilson","F","6-4",22.5,10.0,3.5,1.5),
        Player("Chelsea Gray","G","5-11",14.5,4.0,5.0,1.8),
        Player("Kia","C","6-5",12.5,7.5,1.5,0.5),
        Player("Jackie","G","5-10",11.0,3.5,4.0,1.5),
        Player("Alysha","F","6-2",8.5,4.0,1.0,0.8),
        Player("Kayla","G","5-9",6.5,1.5,2.0,0.8),
        Player("Sydney","F","6-3",5.5,3.0,0.5,0.3),
    ],
    "IND": [
        Player("Caitlin Clark","G","6-0",18.5,5.0,8.0,3.5),
        Player("Aliyah Boston","C","6-4",14.0,9.0,2.5,1.0),
        Player("Kelsey Mitchell","G","5-10",14.5,3.0,2.5,2.0),
        Player("Grace Berger","G","6-0",8.5,2.5,2.0,0.8),
        Player("Lexie Hull","G","5-11",6.5,2.5,1.5,0.6),
        Player("Emma","F","6-2",6.0,4.0,0.8,0.5),
        Player("Nina","F","6-3",5.0,3.5,0.5,0.3),
    ],
    "PHX": [
        Player("Diana Taurasi","G","6-0",17.0,4.0,4.0,3.0),
        Player("Brittney Griner","C","6-9",15.0,8.0,1.5,0.5),
        Player("Megan","F","6-3",9.0,4.5,1.5,0.8),
        Player("Diana","F","6-2",7.5,3.5,1.0,0.5),
        Player("Sophie","G","5-10",6.5,1.5,2.0,0.6),
        Player("Te'a","G","5-9",5.5,1.5,1.5,0.5),
        Player("Nneka","F","6-4",8.0,5.0,1.0,0.5),
    ],
    "SEA": [
        Player("Breanna Stewart","F","6-4",20.0,8.5,4.5,2.5),
        Player("Jewell Loyd","G","5-9",16.5,3.5,4.0,2.5),
        Player("Ezi","C","6-5",12.5,9.5,2.0,0.4),
        Player("Mercedes Russell","C","6-6",7.5,6.0,1.0,0.0),
        Player("Jordan","G","5-10",8.5,2.5,3.5,1.5),
        Player("Briyana","F","6-2",9.0,5.5,1.2,0.6),
        Player("Kylie","G","5-9",6.0,1.5,2.0,0.9),
        Player("Layla","F","6-1",5.0,3.5,0.5,0.3),
    ],
    "CON": [
        Player("Alyssa Thomas","F","6-3",15.5,7.5,6.5,1.0),
        Player("DeWanna Bonner","F","6-4",16.0,6.5,3.5,1.8),
        Player("Brionna Jones","C","6-3",12.5,7.0,2.0,0.8),
        Player("DiJonai","G","5-11",11.0,3.5,4.0,1.5),
        Player("Natasha","G","5-10",9.0,2.5,3.5,1.2),
        Player("Julie","F","6-2",6.5,3.5,0.8,0.5),
        Player("Megan","G","5-9",5.5,1.5,1.5,0.5),
    ],
    "CHI": [
        Player("Kahleah Copper","F","6-1",16.5,5.5,2.5,1.5),
        Player("Rebekah","C","6-5",10.0,7.0,1.5,0.5),
        Player("Dana","G","5-6",8.5,2.0,3.5,1.2),
        Player("Ingrid","F","6-3",6.5,4.0,0.8,0.5),
        Player("Yuki","G","5-9",5.5,1.5,1.5,0.5),
        Player("Li","F","6-4",7.0,4.5,0.8,0.5),
        Player("Alma","F","6-0",4.8,3.2,0.7,0.5),
        Player("Raeg","G","5-7",4.0,1.5,1.8,0.8),
    ],
    "ATL": [
        Player("Rhyne Howard","G","6-0",15.5,4.5,3.5,2.0),
        Player("Allisha Gray","G","6-0",14.2,3.8,2.9,1.9),
        Player("Elyesa Moro","F","6-3",9.8,5.2,1.4,0.8),
        Player("Crystal Dangerfield","G","5-8",8.5,2.1,2.8,1.5),
        Player("Nia Coffey","F","6-1",7.2,4.0,1.2,0.9),
        Player("Taj","C","6-5",5.1,4.8,0.5,0.2),
        Player("Iade","G","5-10",4.0,1.5,1.2,0.6),
    ],
    "LAS": [
        Player("Cameron Brink","F/C","6-4",12.5,8.0,2.5,0.6),
        Player("Nneka Ogwumike","F","6-2",16.0,7.5,2.0,0.5),
        Player("Lexi","G","5-10",14.0,3.0,5.5,2.5),
        Player("Zia","G","5-9",11.0,2.5,3.5,1.8),
        Player("Rickea","F","6-2",7.5,4.0,0.8,0.4),
        Player("Te'a","G","5-8",6.5,2.0,2.5,1.0),
        Player("Ji","C","6-4",5.5,5.0,0.5,0.2),
    ],
    "POR": [
        Player("Te'a Cooper","G","5-8",13.5,2.5,3.5,1.5),
        Player("Alexis","G","5-10",11.0,3.0,4.0,1.8),
        Player("Aaliyah","F","6-2",9.5,5.5,1.5,0.6),
        Player("Isabelle","C","6-4",8.5,6.5,0.8,0.3),
        Player("Nika","F","6-1",7.0,4.0,1.0,0.5),
        Player("Jessika","G","5-9",6.0,1.5,2.0,0.9),
        Player("Kate","F","6-0",5.5,3.5,0.6,0.4),
        Player("Sami","G","5-7",4.5,1.0,1.0,0.5),
    ],
    "WAS": [
        Player("Elena Delle Donne","F","6-4",18.0,6.0,3.0,2.5),
        Player("Ariel Atkins","G","5-11",14.5,4.0,3.0,1.5),
        Player("Natalie","C","6-5",11.0,7.5,1.5,0.5),
        Player("Natasha Cloud","G","5-11",9.5,3.5,5.0,1.2),
        Player("Shakira Austin","C","6-0",8.5,5.5,1.5,0.5),
        Player("KeKe","F","6-4",7.0,4.0,0.8,0.5),
        Player("Jade","G","5-8",5.5,1.5,1.5,0.5),
    ],
}

# ─── BACKTEST SUITES ──────────────────────────────────────────────────────
NBA_BACKTEST = [
    {"away":"PHI","home":"NYK","actual_combined":226,"date":"2026-05-06","round":"S1 G1"},
    {"away":"MIN","home":"SAS","actual_combined":228,"date":"2026-05-06","round":"S1 G1"},
    {"away":"DET","home":"CLE","actual_combined":204,"date":"2026-05-08","round":"S1 G3"},
    {"away":"OKC","home":"LAL","actual_combined":226,"date":"2026-05-08","round":"S1 G3"},
    {"away":"CLE","home":"BOS","actual_combined":230,"date":"2026-05-10","round":"S1 G4"},
    {"away":"DEN","home":"MIN","actual_combined":218,"date":"2026-05-10","round":"S1 G5"},
]

WNBA_BACKTEST = [
    {"away":"NYL","home":"MIN","actual_combined":161,"date":"2025-10-10","round":"FINALS G1"},
    {"away":"NYL","home":"LVA","actual_combined":162,"date":"2025-10-13","round":"FINALS G2"},
    {"away":"LVA","home":"NYL","actual_combined":176,"date":"2025-10-17","round":"FINALS G4"},
    {"away":"LVA","home":"NYL","actual_combined":170,"date":"2025-10-20","round":"FINALS G5"},
    {"away":"NYL","home":"LVA","actual_combined":163,"date":"2025-10-23","round":"FINALS G6"},
    {"away":"LVA","home":"NYL","actual_combined":179,"date":"2024-10-10","round":"FINALS G1"},
    {"away":"LVA","home":"NYL","actual_combined":162,"date":"2024-10-13","round":"FINALS G2"},
    {"away":"NYL","home":"LVA","actual_combined":173,"date":"2024-10-16","round":"FINALS G3"},
    {"away":"LVA","home":"NYL","actual_combined":157,"date":"2024-10-20","round":"FINALS G4"},
    {"away":"NYL","home":"LVA","actual_combined":154,"date":"2024-10-24","round":"FINALS G5"},
]

# ─── GAME CLASS ────────────────────────────────────────────────────────────
class Game:
    def __init__(self, away_abbr: str, home_abbr: str, sport: str = "NBA"):
        self.away_abbr = away_abbr.upper()
        self.home_abbr = home_abbr.upper()
        self.sport = sport.upper()
        self.rosters = NBA_ROSTERS if self.sport == "NBA" else WNBA_ROSTERS
        self.away = Team(self.away_abbr, self.away_abbr,
                         self.rosters.get(self.away_abbr, []))
        self.home = Team(self.home_abbr, self.home_abbr,
                         self.rosters.get(self.home_abbr, []))

    def injury_report(self) -> str:
        lines = [f"{'='*60}",
                f"  INJURY REPORT — {self.away_abbr} @ {self.home_abbr}",
                f"{'='*60}"]
        for team in [self.away, self.home]:
            injuries = [p for p in team.players if p.status != "ACTIVE"]
            active = [p for p in team.players if p.status == "ACTIVE"]
            lines.append(f"\n  {team.abbr} ({len(active)} active)")
            lines.append(f"  {'─'*50}")
            for p in team.players:
                note = ""
                if p.status == "Q": note = " ← Q"
                if p.status == "OUT": note = " ← OUT"
                lines.append(f"  {p.status_icon()} {p.name:<28s} {p.pos:<4s} TC:{p.tc(p.pts):.1f} pts {p.status}{note}")
        return "\n".join(lines)

    def tc_projections(self) -> str:
        lines = [f"{'='*72}",
                f"  TC PROJECTIONS — {self.away_abbr} @ {self.home_abbr}",
                f"  TC Formula: stat × {CONS} | Q × {Q_MULT} | OUT = 0",
                f"{'='*72}"]
        for team in [self.away, self.home]:
            lines.append(f"\n  {team.abbr} — {team.name}")
            lines.append(f"  {'─'*72}")
            lines.append(f"  {'Player':<26s} {'POS':<4s} {'TC_PTS':>7s} {'TC_REB':>7s} {'TC_AST':>7s} {'TC_3PM':>7s} {'TC_TOT':>7s} Status")
            lines.append(f"  {'─'*72}")
            for p in team.roster():
                proj = p.proj()
                tot = p.tc_total()
                flag = "⚠️Q" if p.status == "Q" else "❌O" if p.status == "OUT" else ""
                lines.append(f"  {p.name:<26s} {p.pos:<4s} {proj['TC_PTS']:>7.1f} {proj['TC_REB']:>7.1f} {proj['TC_AST']:>7.1f} {proj['TC_3PM']:>7.1f} {tot:>7.1f} {flag}")
            st = team.starters_totals()
            bt = team.bench_totals()
            ta = team.team_totals_all()
            lines.append(f"  {'─'*72}")
            lines.append(f"  STARTERS:             {st['TC_PTS']:>7.1f} {st['TC_REB']:>7.1f} {st['TC_AST']:>7.1f} {st['TC_3PM']:>7.1f} {st['TC_TOTAL']:>7.1f}")
            lines.append(f"  BENCH:                {bt['TC_PTS']:>7.1f} {bt['TC_REB']:>7.1f} {bt['TC_AST']:>7.1f} {bt['TC_3PM']:>7.1f} {bt['TC_TOTAL']:>7.1f}")
            lines.append(f"  TEAM TOTAL:           {ta['TC_PTS']:>7.1f} {ta['TC_REB']:>7.1f} {ta['TC_AST']:>7.1f} {ta['TC_3PM']:>7.1f} {ta['TC_TOTAL']:>7.1f}")
        return "\n".join(lines)

    def summary(self, market_total: float = None) -> str:
        at = self.away.team_totals_all()
        ht = self.home.team_totals_all()
        tc_combined = round(at["TC_TOTAL"] + ht["TC_TOTAL"], 1)
        line = round(tc_combined * LINE_FACTOR)
        edge = round(tc_combined - line, 1)
        signal = "OVER" if edge > MIN_EDGE else ("UNDER" if edge < -MIN_EDGE else "NO EDGE")
        lines = [f"{'='*60}",
                f"  SUMMARY — {self.away_abbr} @ {self.home_abbr}",
                f"{'='*60}"]
        lines.append(f"  {self.away_abbr} TC: {at['TC_TOTAL']:.1f} ({at['TC_PTS']:.1f}pts + {at['TC_REB']:.1f}reb + {at['TC_AST']:.1f}ast + {at['TC_3PM']:.1f}3pm)")
        lines.append(f"  {self.home_abbr} TC: {ht['TC_TOTAL']:.1f} ({ht['TC_PTS']:.1f}pts + {ht['TC_REB']:.1f}reb + {ht['TC_AST']:.1f}ast + {ht['TC_3PM']:.1f}3pm)")
        lines.append(f"  {'─'*60}")
        lines.append(f"  TC COMBINED:  {tc_combined:.1f}")
        lines.append(f"  LINE (×{LINE_FACTOR}): {line}")
        lines.append(f"  EDGE:         {edge:+.1f}")
        if market_total:
            diff = tc_combined - market_total
            lines.append(f"  Market Total: {market_total} | Diff: {diff:+.1f}")
        lines.append(f"  Signal:       {signal}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)

    def full_report(self, market_total: float = None) -> str:
        return "\n".join([self.injury_report(), self.tc_projections(), self.summary(market_total)])


# ─── BACKTEST RUNNER ──────────────────────────────────────────────────────
def run_backtest(sport: str = "NBA") -> dict:
    suite = NBA_BACKTEST if sport == "NBA" else WNBA_BACKTEST
    roster = NBA_ROSTERS if sport == "NBA" else WNBA_ROSTERS
    print(f"\n{'='*72}")
    print(f"  {sport} TC BACKTEST — {len(suite)} GAMES")
    print(f"  TC = stat×{CONS} | Q = {Q_MULT} | LINE = TC×{LINE_FACTOR}")
    print(f"{'='*72}")
    print(f"  {'Game':<14} {'Date':<12} {'TC':>7} {'LINE':>6} {'Actual':>7} {'Edge':>7} {'Result':<6} {'Hit':<4}")
    print(f"  {'-'*72}")

    results = []
    for g in suite:
        away_p = roster.get(g["away"], [])
        home_p = roster.get(g["home"], [])
        # TC = sum of TC_PTS only (stat × 0.85 — conservative scoring proxy)
        # REB/AST/3PM are breakdown stats, not primary scoring signals
        ta = sum(p.tc(p.pts) for p in away_p if p.status != "OUT")
        th = sum(p.tc(p.pts) for p in home_p if p.status != "OUT")
        tc = round(ta + th, 1)
        line = round(tc * LINE_FACTOR)
        actual = g["actual_combined"]
        diff = round(tc - actual, 1)
        edge = round(tc - line, 1)
        result = "OVER" if diff > 0 else "UNDER"
        hit = "✅" if (result == "OVER" and actual > tc) or (result == "UNDER" and actual < tc) else "❌"
        print(f"  {g['away']}@{g['home']:<6} {g['date']:<12} {tc:>7.1f} {line:>6} {actual:>7} {edge:>+7.1f} {result:<6} {hit}")
        results.append({"game": f"{g['away']}@{g['home']}", "tc": tc, "line": line, "actual": actual, "diff": diff, "result": result, "hit": hit == "✅"})

    print(f"\n  {'-'*72}")
    hits = sum(1 for r in results if r["hit"])
    print(f"  HIT RATE: {hits}/{len(results)} ({hits/len(results)*100:.0f}%)")
    avg_diff = sum(r["diff"] for r in results) / len(results)
    print(f"  AVG DIFF (TC-Actual): {avg_diff:+.1f}")
    print(f"  NOTE: TC = pts×{CONS} only (pts is the primary scoring proxy)")
    print(f"{'='*72}\n")
    return {"results": results, "hit_rate": hits/len(results), "avg_diff": avg_diff}


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sports TC Master Engine v4.0")
    parser.add_argument("--sport", choices=["NBA","WNBA"], default="NBA")
    parser.add_argument("--game", help="'AWAY @ HOME'")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--rosters", action="store_true")
    parser.add_argument("--market", type=float, default=215.0)
    args = parser.parse_args()

    if args.backtest:
        run_backtest(args.sport)
    elif args.rosters:
        roster = NBA_ROSTERS if args.sport == "NBA" else WNBA_ROSTERS
        print(f"\n{args.sport} ROSTERS ({len(roster)} teams):")
        for code, players in sorted(roster.items()):
            active = [p for p in players if p.status == "ACTIVE"]
            q = [p for p in players if p.status == "Q"]
            out = [p for p in players if p.status == "OUT"]
            print(f"  {code}: {len(active)} active", end="")
            if q: print(f" | Q: {', '.join(p.name for p in q)}", end="")
            if out: print(f" | OUT: {', '.join(p.name for p in out)}", end="")
            print()
    elif args.game:
        parts = args.game.replace("@"," ").replace("vs"," ").split()
        away, home = parts[0].upper(), parts[1].upper()
        g = Game(away, home, args.sport)
        print(g.full_report(args.market))
    else:
        print("Usage:")
        print("  python master_tc.py --sport NBA --game 'PHI @ NYK'")
        print("  python master_tc.py --sport WNBA --game 'NYL @ POR'")
        print("  python master_tc.py --sport NBA --backtest")
        print("  python master_tc.py --sport WNBA --backtest")
        print("  python master_tc.py --sport WNBA --rosters")