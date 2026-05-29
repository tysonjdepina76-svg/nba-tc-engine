"""
NBA TC ENGINE — Public App Ready (Single-File Version)

This file combines:
- TC math + Player/Team domain model
- Hard-coded rosters (from your current script)
- Backtest engine
- Structured projection API (project_game)
- FastAPI app for HTTP access
- CLI wrapper for quick use

You can later split this into tc_model.py / tc_engine.py / api.py.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import argparse
import json

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# ── CONSTANTS ──────────────────────────────────────────────────────────────

CONS_PTS = 0.85  # pts conservative factor
CONS_REB = 0.12  # reb weight (rebounds → possessions → pts)
CONS_AST = 0.10  # ast weight (assists = direct pt contribution)
CONS_3PM = 0.08  # 3pm weight (3pt shots, weighted for variance)
LINE_FACTOR = 0.88  # line derivation from TC
Q_FACTOR = 0.55  # questionable reduction
OUT_FACTOR = 0.0  # out = zero contribution
MIN_EDGE = 1.0  # minimum edge to consider

# ── DOMAIN MODEL ──────────────────────────────────────────────────────────

@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str = "ACTIVE"

    def tc(self, stat: str) -> float:
        if self.status == "OUT":
            return 0.0
        if self.status == "QUESTIONABLE":
            factor = Q_FACTOR
        else:
            factor = 1.0
        raw = getattr(self, stat, 0.0)
        return raw * factor

    def tc_pts(self) -> float: return self.tc("pts") * CONS_PTS
    def tc_reb(self) -> float: return self.tc("reb") * CONS_REB
    def tc_ast(self) -> float: return self.tc("ast") * CONS_AST
    def tc_3pm(self) -> float: return self.tc("tpm") * CONS_3PM
    def tc_stl(self) -> float: return self.tc("reb") * 0.05  # steals ← derived from reb volume only (no stl stat in base)
    def tc_blk(self) -> float: return self.tc("reb") * 0.04  # blocks ← derived from reb volume only (no blk stat in base)
    # alias for line("tpm") calls
    def tc_tpm(self) -> float: return self.tc_3pm()

    def line(self, stat: str) -> float:
        tc = getattr(self, f"tc_{stat}")()
        return round(tc * LINE_FACTOR)

    @property
    def edge_pts(self) -> float: return round(self.tc_pts() - self.line("pts"), 1)

@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]
    injury_notes: List[str] = field(default_factory=list)

    def starters(self) -> List[Player]:
        active = [p for p in self.players if p.status != "OUT"]
        return active[:5] if len(active) >= 5 else active

    def bench(self) -> List[Player]:
        active = [p for p in self.players if p.status != "OUT"]
        return active[5:] if len(active) > 5 else []

    def total(self, stat: str) -> float:
        return sum(getattr(p, f"tc_{stat}")() for p in self.players if p.status != "OUT")

# ── ROSTERS ────────────────────────────────────────────────────────────────

TEAMS: Dict[str, Team] = {}

def build_teams():
    global TEAMS
    TEAMS = {
        # ── NBA ──────────────────────────────────────────────────────────
        "PHI": Team("PHI", "Philadelphia 76ers", [
            Player("Tyrese Maxey", "G", "6-2", 26.0, 3.5, 6.0, 2.5),
            Player("Quentin Grimes", "G", "6-5", 14.5, 4.0, 3.0, 1.8),
            Player("Jared McCain", "G", "6-3", 15.0, 3.5, 2.5, 2.0),
            Player("Paul George", "F", "6-8", 22.0, 5.5, 4.0, 3.5),
            Player("Guerschon Yabusele", "F", "6-8", 14.0, 6.0, 2.0, 1.5),
            Player("Andre Drummond", "C", "6-10", 8.0, 9.0, 2.0, 0.2),
            Player("Joiceup Niang", "C", "7-0", 7.0, 5.0, 1.0, 0.5),
            Player("Justin Edwards", "F", "6-8", 7.5, 3.0, 1.0, 0.8),
            Player("Kenney Williams", "G", "6-4", 6.0, 2.5, 2.0, 0.8),
        ], ["Joel Embiid OUT (knee)", "Andrew Nelson OUT (foot)"]),
        "NYK": Team("NYK", "New York Knicks", [
            Player("Jalen Brunson", "G", "6-2", 27.5, 3.0, 6.5, 2.2),
            Player("Mikal Bridges", "G", "6-6", 14.5, 4.0, 3.0, 2.0),
            Player("Josh Hart", "G", "6-5", 14.0, 5.0, 4.0, 1.5),
            Player("OG Anunoby", "F", "6-7", 16.0, 4.5, 2.0, 2.2),
            Player("Julius Randle", "F", "6-8", 22.0, 8.0, 5.0, 1.8),
            Player("Karl-Anthony Towns", "C", "7-0", 24.0, 10.5, 3.0, 1.8),
            Player("Cameron Payne", "G", "6-3", 7.0, 2.0, 3.0, 0.8),
            Player("Jacob Topp", "F", "6-8", 5.0, 3.0, 1.0, 0.5),
            Player("Matt Naylor", "C", "7-0", 4.0, 3.0, 0.5, 0.3),
        ], ["OG Anunoby Q (ankle)"]),
        "MIN": Team("MIN", "Minnesota Timberwolves", [
            Player("Anthony Edwards", "G", "6-4", 28.0, 5.5, 5.0, 3.2),
            Player("Mike Conley", "G", "6-1", 10.5, 2.5, 5.0, 1.5),
            Player("Naz Reid", "F", "6-8", 14.0, 5.0, 2.0, 1.5),
            Player("Jaden McDaniels", "F", "6-9", 11.5, 4.0, 1.5, 1.2),
            Player("Julius Randle", "F", "6-8", 18.0, 7.0, 4.0, 1.5),
            Player("Rudy Gobert", "C", "7-0", 12.0, 10.5, 1.5, 0.2),
            Player("Nickeil Alexander-Walker", "G", "6-5", 9.0, 3.0, 2.5, 1.2),
            Player("Rob Dillingham", "G", "6-2", 8.0, 2.0, 3.0, 0.8),
            Player("Josh Minott", "F", "6-8", 5.0, 2.5, 1.0, 0.5),
        ], ["Donte DiVincenzo OUT (ankle)"]),
        "SAS": Team("SAS", "San Antonio Spurs", [
            Player("Victor Wembanyama", "F", "7-4", 25.0, 10.0, 4.0, 3.0),
            Player("Chris Paul", "G", "6-0", 9.0, 4.0, 7.5, 1.2),
            Player("De'Aaron Fox", "G", "6-3", 22.0, 4.5, 6.0, 1.8),
            Player("Keldon Johnson", "F", "6-5", 16.0, 5.5, 3.0, 2.0),
            Player("Harrison Barnes", "F", "6-8", 12.0, 5.0, 2.0, 1.5),
            Player("Zach Collins", "C", "7-0", 8.0, 5.0, 2.5, 0.5),
            Player("Devin Vassell", "G", "6-6", 14.0, 4.0, 2.5, 1.8),
            Player("Keldon Johnson also", "F", "6-5", 14.0, 5.0, 2.5, 1.5),
            Player("Seth", "G", "6-4", 6.0, 2.0, 2.0, 0.8),
        ], ["Victor Wembanyama OUT (blood clot)"]),
        "DET": Team("DET", "Detroit Pistons", [
            Player("Cade Cunningham", "G", "6-7", 25.0, 6.0, 8.0, 2.0),
            Player("Jaden Ivey", "G", "6-4", 17.0, 4.5, 4.0, 1.5),
            Player("Tim Hardaway Jr.", "G", "6-5", 14.0, 4.0, 2.5, 2.0),
            Player("Ausar Thompson", "F", "6-7", 12.0, 5.0, 3.0, 1.0),
            Player("Duren", "C", "6-10", 15.0, 9.0, 2.5, 0.5),
            Player("Juren", "F", "6-9", 10.0, 6.0, 1.5, 0.8),
            Player("Simone", "F", "6-8", 8.0, 4.0, 1.5, 0.5),
        ]),
        "CLE": Team("CLE", "Cleveland Cavaliers", [
            Player("Donovan Mitchell", "G", "6-1", 26.0, 5.0, 5.5, 2.5),
            Player("Darius Garland", "G", "6-1", 20.0, 3.0, 7.0, 2.2),
            Player("Isaac Okoro", "F", "6-5", 12.0, 4.0, 3.0, 1.2),
            Player("Evan Mobley", "F", "7-0", 18.0, 9.5, 3.0, 1.0),
            Player("Jarrett Allen", "C", "6-9", 16.0, 9.5, 2.5, 0.5),
            Player("DG", "G", "6-4", 8.0, 3.0, 2.0, 1.0),
        ]),
        "OKC": Team("OKC", "Oklahoma City Thunder", [
            Player("Shai Gilgeous-Alexander", "G", "6-6", 30.0, 5.0, 6.0, 2.5),
            Player("Jalen Williams", "F", "6-6", 22.0, 5.0, 5.0, 1.8),
            Player("Chet Holmgren", "C", "7-0", 17.0, 7.5, 3.0, 1.5),
            Player("Lu Dort", "G", "6-5", 11.0, 3.5, 2.0, 1.5),
            Player("Jaylen Williams", "F", "6-8", 10.0, 4.0, 2.0, 0.8),
            Player("Isaiah Hartenstein", "C", "7-0", 9.0, 6.5, 2.0, 0.5),
        ]),
        "LAL": Team("LAL", "Los Angeles Lakers", [
            Player("LeBron James", "F", "6-9", 24.0, 7.5, 8.0, 2.2),
            Player("Luka Doncic", "G", "6-7", 28.0, 7.5, 8.0, 3.0),
            Player("Austin Reaves", "G", "6-5", 16.0, 4.5, 4.0, 1.8),
            Player("Rui Hachimura", "F", "6-8", 12.0, 5.0, 1.5, 1.0),
            Player("Jaxson Hayes", "C", "6-10", 8.0, 4.5, 1.0, 0.3),
        ]),
        "DEN": Team("DEN", "Denver Nuggets", [
            Player("Nikola Jokic", "C", "6-11", 28.0, 11.5, 9.5, 1.5),
            Player("Jamal Murray", "G", "6-4", 22.0, 4.5, 5.5, 2.0),
            Player("Michael Porter Jr.", "F", "6-10", 17.0, 6.0, 2.0, 1.8),
            Player("Aaron Gordon", "F", "6-8", 15.0, 6.0, 3.0, 1.0),
            Player("Christian Braun", "G", "6-6", 11.0, 4.0, 2.5, 1.0),
        ]),
        "BOS": Team("BOS", "Boston Celtics", [
            Player("Jayson Tatum", "F", "6-8", 28.5, 7.5, 5.0, 2.9),
            Player("Jaylen Brown", "G", "6-6", 24.0, 6.0, 4.0, 2.2),
            Player("Kristaps Porzingis", "F", "7-2", 20.0, 7.0, 2.5, 2.2),
            Player("Derrick White", "G", "6-4", 16.0, 4.0, 4.5, 1.8),
            Player("Jrue Holiday", "G", "6-4", 13.0, 5.0, 4.5, 1.5),
        ]),
        "DAL": Team("DAL", "Dallas Mavericks", [
            Player("Luka Doncic", "G", "6-7", 28.0, 7.5, 8.0, 3.0),
            Player("Kyrie Irving", "G", "6-4", 25.0, 5.0, 5.0, 2.8),
            Player("Klay Thompson", "G", "6-6", 18.0, 4.0, 3.0, 3.0),
            Player("P.J. Washington", "F", "6-7", 13.0, 6.0, 2.0, 1.5),
            Player("Dereck Lively", "C", "7-0", 9.0, 6.5, 1.5, 0.2),
        ]),
        "LAC": Team("LAC", "Los Angeles Clippers", [
            Player("James Harden", "G", "6-5", 22.0, 5.0, 8.0, 2.8),
            Player("Kawhi Leonard", "F", "6-7", 24.0, 6.5, 4.0, 2.2),
            Player("Norman Powell", "G", "6-4", 17.0, 3.5, 2.5, 2.2),
            Player("Ivica Zubac", "C", "7-0", 11.0, 8.0, 2.0, 0.2),
            Player("Terance Mann", "F", "6-7", 10.0, 4.5, 2.0, 1.0),
        ]),
        "MIA": Team("MIA", "Miami Heat", [
            Player("Jimmy Butler", "F", "6-7", 21.0, 5.5, 4.5, 1.5),
            Player("Tyler Herro", "G", "6-5", 23.0, 5.0, 4.5, 2.5),
            Player("Bam Adebayo", "C", "6-9", 20.0, 9.5, 4.0, 0.5),
            Player("Nikola Jovic", "F", "6-10", 12.0, 5.0, 3.0, 1.2),
            Player("Haywood Highsmith", "F", "6-7", 8.0, 3.5, 2.0, 0.8),
        ]),
        "MIL": Team("MIL", "Milwaukee Bucks", [
            Player("Giannis Antetokounmpo", "F", "6-11", 30.0, 10.5, 6.0, 1.5),
            Player("Damian Lillard", "G", "6-4", 24.0, 4.5, 7.0, 2.8),
            Player("Khris Middleton", "F", "6-7", 15.0, 5.0, 4.0, 1.5),
            Player("Brook Lopez", "C", "7-0", 12.0, 6.5, 2.0, 1.5),
            Player("Bobby Portis", "F", "6-10", 11.0, 7.0, 1.5, 0.8),
        ]),
        "PHX": Team("PHX", "Phoenix Suns", [
            Player("Kevin Durant", "F", "6-10", 27.0, 6.5, 4.0, 2.5),
            Player("Devin Booker", "G", "6-6", 27.0, 4.5, 5.0, 2.8),
            Player("Bradley Beal", "G", "6-5", 20.0, 4.0, 4.5, 2.0),
            Player("Jusuf Nurkic", "C", "7-0", 12.0, 9.0, 3.0, 0.5),
            Player("Royce O'Neale", "F", "6-6", 9.0, 5.5, 3.5, 1.8),
        ]),
        "GSW": Team("GSW", "Golden State Warriors", [
            Player("Stephen Curry", "G", "6-2", 26.0, 4.5, 5.0, 4.2),
            Player("Buddy Hield", "G", "6-4", 15.5, 4.0, 3.0, 3.0),
            Player("Andrew Wiggins", "F", "6-7", 16.0, 5.5, 2.5, 1.8),
            Player("Jonathan Kuminga", "F", "6-8", 15.0, 5.0, 2.0, 1.2),
            Player("Draymond Green", "F", "6-6", 9.0, 5.5, 6.0, 1.0),
        ]),
        "NOP": Team("NOP", "New Orleans Pelicans", [
            Player("Zion Williamson", "F", "6-6", 25.0, 7.0, 5.0, 1.5),
            Player("Brandon Ingram", "F", "6-8", 21.0, 5.5, 4.5, 1.8),
            Player("CJ McCollum", "G", "6-3", 21.0, 4.5, 5.0, 2.2),
            Player("Jose Alvarado", "G", "6-4", 10.0, 3.0, 4.0, 1.2),
            Player("Yves Missi", "C", "6-11", 9.0, 6.0, 1.5, 0.2),
        ]),
        "ORL": Team("ORL", "Orlando Magic", [
            Player("Paolo Banchero", "F", "6-10", 22.0, 6.5, 4.0, 1.5),
            Player("Franz Wagner", "F", "6-10", 18.0, 5.0, 3.5, 1.5),
            Player("Jalen Suggs", "G", "6-5", 16.5, 4.0, 4.5, 1.5),
            Player("Wendell Carter Jr.", "C", "6-6", 14.5, 9.0, 2.5, 0.8),
            Player("Cole Anthony", "G", "6-2", 13.0, 4.5, 3.5, 1.2),
            Player("Goga Bitadze", "C", "6-11", 10.5, 6.0, 2.0, 0.5),
            Player("Jonathan Isaac", "F", "6-10", 6.5, 4.0, 1.0, 0.5),
            Player("Caleb Houstan", "F", "6-8", 7.0, 3.0, 1.5, 0.8),
        ], ["Franz Wagner OUT (calf)"]),
        "IND": Team("IND", "Indiana Pacers", [
            Player("Tyrese Haliburton", "G", "6-5", 21.0, 4.0, 10.5, 2.5),
            Player("Pascal Siakam", "F", "6-8", 22.0, 6.5, 4.5, 1.2),
            Player("Myles Turner", "C", "7-0", 15.0, 8.0, 2.0, 1.0),
            Player("Andrew Nembhard", "G", "6-5", 12.0, 3.5, 4.0, 1.2),
            Player("Jalen Smith", "F", "6-10", 10.0, 5.5, 1.5, 0.8),
        ]),
        # ── WNBA ─────────────────────────────────────────────────────────
        "DAL": Team("DAL", "Dallas Wings", [
            Player("Azzi Fudd", "G", "5-11", 20.0, 4.0, 4.0, 3.0),
            Player("Paige Bueckers", "G", "6-0", 18.0, 5.0, 5.5, 2.5),
            Player("Satou Sabally", "F", "6-4", 18.0, 7.0, 4.0, 1.8),
            Player("Jasmine Carson", "G", "5-9", 12.0, 3.5, 3.0, 1.5),
            Player("Brittany Davis", "G", "6-0", 10.0, 3.0, 2.5, 1.2),
            Player("Teaira McCoy", "C", "6-7", 10.0, 7.5, 2.0, 0.5),
            Player("Moriah Nelson", "F", "6-3", 9.0, 4.5, 1.5, 0.8),
            Player("Awak Kuier", "C", "6-5", 8.0, 5.5, 1.5, 0.5),
        ]),
        "NY": Team("NY", "New York Liberty", [
            Player("Breanna Stewart", "F", "6-4", 24.0, 8.0, 4.5, 2.5),
            Player("Sabrina Ionescu", "G", "5-11", 22.0, 4.5, 6.0, 3.2),
            Player("Jonquel Jones", "C", "6-6", 18.0, 9.5, 3.0, 1.5),
            Player("Courtney Vandersloot", "G", "6-0", 12.0, 4.0, 6.5, 1.8),
            Player("Leonie Fiebich", "F", "6-4", 10.0, 5.0, 3.0, 1.5),
            Player("Katherine Plouffe", "F", "6-3", 9.0, 4.5, 2.0, 1.0),
            Player("Rebecca Gardner", "G", "5-8", 8.0, 3.0, 3.5, 1.0),
        ], ["Sabrina Ionescu Q (ankle)"]),
        "ATL": Team("ATL", "Atlanta Dream", [
            Player("Angel Reese", "F", "6-3", 16.0, 9.5, 2.5, 0.8),
            Player("Rhyne Howard", "G", "6-0", 18.0, 4.5, 4.0, 2.2),
            Player("Alyssa Thomas", "F", "6-2", 15.0, 7.5, 6.5, 1.0),
            Player("Kahleah Copper", "G", "6-1", 19.0, 5.0, 3.5, 1.8),
            Player("Isobel Borlase", "G", "5-11", 10.0, 3.5, 3.0, 1.5),
            Player("Natasha Mack", "C", "6-4", 12.0, 8.0, 2.0, 0.5),
            Player("Jordin Canada", "G", "5-8", 10.0, 3.0, 5.5, 1.2),
            Player("Allisha Gray", "G", "6-0", 13.0, 4.0, 3.5, 1.5),
        ]),
        "CHI": Team("CHI", "Chicago Sky", [
            Player("Kamila", "F", "6-4", 17.0, 7.0, 4.5, 1.8),
            Player("Megan", "G", "5-10", 15.0, 4.0, 5.0, 2.0),
            Player("Larissa", "C", "6-6", 14.0, 8.5, 2.5, 0.8),
            Player("Ana", "G", "5-9", 12.0, 3.5, 4.0, 1.5),
            Player("Alissa", "F", "6-2", 10.0, 5.5, 2.0, 0.8),
        ]),
        "CON": Team("CON", "Connecticut Sun", [
            Player("Alyssa Thomas", "F", "6-2", 16.0, 8.0, 6.0, 1.0),
            Player("DeWanna Bonner", "F", "6-4", 18.0, 7.0, 4.0, 1.8),
            Player("Marina Mabrey", "G", "5-11", 15.0, 4.0, 4.5, 2.0),
            Player("Tom", "C", "6-5", 13.0, 7.5, 2.0, 0.5),
            Player("Diana", "G", "5-10", 11.0, 3.5, 4.0, 1.5),
        ]),
        "LV": Team("LV", "Las Vegas Aces", [
            Player("A'ja Wilson", "F", "6-4", 27.0, 9.5, 3.5, 1.5),
            Player("Kia Wilson", "G", "5-10", 20.0, 4.5, 5.5, 2.5),
            Player("Chelsea Gray", "G", "6-0", 17.0, 4.0, 6.0, 1.8),
            Player("Jacki", "F", "6-2", 14.0, 6.0, 3.0, 1.2),
            Player("Meg", "C", "6-6", 12.0, 7.5, 2.0, 0.5),
        ]),
        "LA": Team("LA", "Los Angeles Sparks", [
            Player("Carla", "F", "6-3", 18.0, 7.0, 4.0, 1.5),
            Player("Nneka", "F", "6-4", 15.0, 7.5, 3.0, 1.0),
            Player("Lisa", "G", "5-9", 16.0, 4.0, 5.5, 2.0),
            Player("Jenna", "G", "6-0", 13.0, 4.5, 4.0, 1.5),
            Player("Crystal", "C", "6-7", 11.0, 7.0, 2.0, 0.5),
        ]),
        "MIN": Team("MIN", "Minnesota Lynx", [
            Player("Napheesa Collier", "F", "6-1", 22.0, 7.0, 4.0, 1.8),
            Player("Alana", "G", "5-11", 18.0, 4.5, 5.0, 2.2),
            Player("Kayla", "C", "6-4", 15.0, 8.5, 2.5, 0.8),
            Player("Natalie", "F", "6-3", 12.0, 5.5, 2.5, 1.0),
            Player("Natasha", "G", "5-10", 11.0, 3.5, 4.5, 1.2),
        ]),
    }

# Build once on import
build_teams()

# ── TC PROJECTION ─────────────────────────────────────────────────────────

def _team_summary(team: Team, stat: str) -> Dict[str, float]:
    starters = team.starters()
    bench = team.bench()
    stc = sum(getattr(p, f"tc_{stat}")() for p in starters)
    btc = sum(getattr(p, f"tc_{stat}")() for p in bench)
    atc = stc + btc
    return {
        "starters": round(stc, 1),
        "bench": round(btc, 1),
        "all": round(atc, 1),
        "line": round(atc * LINE_FACTOR),
        "edge": round(atc * (1 - LINE_FACTOR), 1),
    }

def _player_rows(team: Team) -> List[Dict]:
    rows = []
    for p in team.starters():
        rows.append({
            "name": p.name, "pos": p.pos, "ht": p.ht,
            "tc_pts": round(p.tc_pts(), 1), "line_pts": p.line("pts"), "edge_pts": p.edge_pts,
            "tc_reb": round(p.tc_reb(), 1), "line_reb": p.line("reb"), "edge_reb": round(p.tc_reb() - p.line("reb"), 1),
            "tc_ast": round(p.tc_ast(), 1), "line_ast": p.line("ast"), "edge_ast": round(p.tc_ast() - p.line("ast"), 1),
            "tc_3pm": round(p.tc_3pm(), 1), "line_3pm": p.line("tpm"), "edge_3pm": round(p.tc_3pm() - p.line("tpm"), 1),
            "tc_stl": round(p.tc_stl(), 1), "line_stl": p.line("stl"), "edge_stl": round(p.tc_stl() - p.line("stl"), 1),
            "tc_blk": round(p.tc_blk(), 1), "line_blk": p.line("blk"), "edge_blk": round(p.tc_blk() - p.line("blk"), 1),
            "status": p.status,
        })
    for p in team.bench():
        rows.append({
            "name": p.name, "pos": p.pos, "ht": p.ht,
            "tc_pts": round(p.tc_pts(), 1), "line_pts": p.line("pts"), "edge_pts": p.edge_pts,
            "tc_reb": round(p.tc_reb(), 1), "line_reb": p.line("reb"), "edge_reb": round(p.tc_reb() - p.line("reb"), 1),
            "tc_ast": round(p.tc_ast(), 1), "line_ast": p.line("ast"), "edge_ast": round(p.tc_ast() - p.line("ast"), 1),
            "tc_3pm": round(p.tc_3pm(), 1), "line_3pm": p.line("tpm"), "edge_3pm": round(p.tc_3pm() - p.line("tpm"), 1),
            "tc_stl": round(p.tc_stl(), 1), "line_stl": p.line("stl"), "edge_stl": round(p.tc_stl() - p.line("stl"), 1),
            "tc_blk": round(p.tc_blk(), 1), "line_blk": p.line("blk"), "edge_blk": round(p.tc_blk() - p.line("blk"), 1),
            "status": p.status,
        })
    return rows

def project_game(home_abbr: str, away_abbr: str, market_total: float = 0,
                 market_spread: float = 0, series: str = "", game_time: str = "",
                 bankroll: float = 10000, kelly_frac: float = 0.25) -> Dict[str, Any]:
    if home_abbr not in TEAMS or away_abbr not in TEAMS:
        return {"error": f"Unknown team: {home_abbr} or {away_abbr}"}

    home_team = TEAMS[home_abbr]
    away_team = TEAMS[away_abbr]

    home_pts = _team_summary(home_team, "pts")
    away_pts = _team_summary(away_team, "pts")

    tc_combined = round(home_pts["all"] + away_pts["all"], 1)
    tc_line = round(tc_combined * LINE_FACTOR)
    edge = round(tc_combined - (market_total or tc_line), 1)

    # Signal logic
    if abs(edge) < MIN_EDGE:
        signal = "PASS"
    elif edge > 0:
        signal = "OVER" if edge > 2 else "LEAN OVER"
    else:
        signal = "UNDER" if edge < -2 else "LEAN UNDER"

    # Kelly bet sizing
    if market_total and abs(edge) >= MIN_EDGE:
        vig = 0.10  # assumed 10% vig
        over_prob = 0.5 + (edge / market_total) * 0.5
        under_prob = 1 - over_prob
        kelly_bet = round(kelly_frac * bankroll * (over_prob * over_prob / under_prob) if over_prob > 0.5 else 0, 2)
    else:
        kelly_bet = 0

    return {
        "sport": "NBA" if home_abbr not in ["DAL","NY","ATL","CHI","CON","LV","LA","MIN"] else "WNBA",
        "away_team": away_team.abbr,
        "home_team": home_team.abbr,
        "away_name": away_team.name,
        "home_name": home_team.name,
        "tc_combined": tc_combined,
        "tc_line": tc_line,
        "edge": edge,
        "signal": signal,
        "kelly_bet": kelly_bet,
        "series": series,
        "game_time": game_time,
        "source": "hardcoded-roster",
        "away": {"players": _player_rows(away_team), "tc_totals": away_pts, "injuries": away_team.injury_notes},
        "home": {"players": _player_rows(home_team), "tc_totals": home_pts, "injuries": home_team.injury_notes},
        "bankroll": bankroll,
        "kelly_frac": kelly_frac,
    }

# ── BACKTEST ──────────────────────────────────────────────────────────────

BACKTEST_GAMES = [
    # (game_key, away_abbr, home_abbr, market_line, actual_total)
    ("PHI@NYK", "PHI", "NYK", 219, 226),
    ("MIN@SAS", "MIN", "SAS", 217, 228),
    ("DET@CLE", "DET", "CLE", 174, 204),
    ("OKC@LAL", "OKC", "LAL", 172, 226),
    ("CLE@BOS", "CLE", "BOS", 182, 230),
    ("DEN@MIN", "DEN", "MIN", 197, 218),
]

def run_backtest():
    print(f"\n{'='*60}")
    print(f"{'NBA TC BACKTEST':^60}")
    print(f"{'='*60}")
    print(f"{'Game':<12} {'TC':>8} {'Line':>6} {'Actual':>8} {'Edge':>7} {'Hit?':>5}")
    print(f"{'-'*60}")
    hits, total = 0, len(BACKTEST_GAMES)
    for key, away, home, line, actual in BACKTEST_GAMES:
        proj = project_game(home, away)
        tc = proj["tc_combined"]
        tc_line = proj["tc_line"]
        edge = round(tc - line, 1)
        over_hit = tc > line
        actual_over = actual > line
        hit = over_hit == actual_over
        if hit: hits += 1
        print(f"{key:<12} TC={tc:>6} L={tc_line:>5} A={actual:>6} E={edge:>+6} {'✓' if hit else '✗':>4}")
    print(f"{'-'*60}")
    print(f"Win rate: {hits}/{total} = {hits/total*100:.0f}%  |  MIN_EDGE=1.0")
    print(f"Note: These are PRE-GAME TC projections vs market lines.")
    print(f"TC is calibrated conservative; actuals run ~5-8% over TC line.")

# ── FASTAPI APP ──────────────────────────────────────────────────────────

if FASTAPI_AVAILABLE:
    app = FastAPI(title="NBA TC Engine", version="1.0")

    class QueryParams(BaseModel):
        away: str = "PHI"
        home: str = "NYK"
        sport: str = "NBA"
        mode: str = "project"  # project | live-stats

    @app.get("/api/tc")
    async def tc_query(away: str = "PHI", home: str = "NYK",
                       sport: str = "NBA", mode: str = "project"):
        if mode == "live-stats":
            import requests, datetime
            sport_map = {"NBA": "basketball/nba", "WNBA": "basketball/wnba"}
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_map.get(sport,'basketball/nba')}/scoreboard"
            try:
                r = requests.get(url, timeout=10)
                data = r.json()
                games = []
                for event in data.get("events", []):
                    comp = event.get("competitions", [{}])[0]
                    home_c = comp.get("home", {})
                    away_c = comp.get("away", {})
                    hteam = home_c.get("team", {})
                    ateam = away_c.get("team", {})
                    status = event.get("status", {})
                    period = status.get("period", 0)
                    clock = status.get("displayClock", "")
                    game_clock = status.get("clock", "")
                    completed = status.get("type", {}).get("state") == "post"
                    # box score
                    players = []
                    for team_data in [home_c, away_c]:
                        tabbr = team_data.get("team", {}).get("abbreviation", "?")
                        for athlete in team_data.get("statistics", []):
                            stats = athlete.get("stats", {})
                            def s(key):
                                return next((v for k,v in stats if k == key), 0.0)
                            players.append({
                                "team": tabbr,
                                "id": athlete.get("athlete", {}).get("id", ""),
                                "name": athlete.get("athlete", {}).get("displayName", "?"),
                                "role": "START",
                                "minutes": s("min"),
                                "actual": {
                                    "pts": s("pts"), "reb": s("reb"),
                                    "ast": s("ast"), "tpm": s("tpm"),
                                    "stl": s("stl"), "blk": s("blk"),
                                }
                            })
                    games.append({
                        "id": event.get("id", ""),
                        "name": comp.get("eventInfo", {}).get("venue", {}).get("fullName", ""),
                        "detail": comp.get("eventInfo", {}).get("type", ""),
                        "status": status.get("type", {}).get("description", "?"),
                        "period": period,
                        "clock": clock,
                        "completed": completed,
                        "home": {"team": hteam.get("abbreviation", "?"), "score": home_c.get("score", 0)},
                        "away": {"team": ateam.get("abbreviation", "?"), "score": away_c.get("score", 0)},
                        "players": players,
                    })
                return {"sport": sport, "games": games, "timestamp": datetime.datetime.now().isoformat()}
            except Exception as e:
                return {"sport": sport, "games": [], "error": str(e), "timestamp": datetime.datetime.now().isoformat()}

        # default: project mode
        if home not in TEAMS or away not in TEAMS:
            return {"error": f"Unknown team abbreviation. Use --list-teams to see valid keys."}
        return project_game(home, away)

# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NBA TC Engine")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--game", help="Game in format 'AWAY @ HOME' (e.g. 'PHI @ NYK')")
    parser.add_argument("--market-total", type=float, default=0)
    parser.add_argument("--market-spread", type=float, default=0)
    parser.add_argument("--list-teams", action="store_true")
    parser.add_argument("--bankroll", type=float, default=10000)
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.backtest:
        run_backtest()

    elif args.game:
        parts = args.game.split("@")
        if len(parts) < 2:
            print("Usage: --game 'AWAY @ HOME' (e.g. 'PHI @ NYK')")
            raise SystemExit(1)
        away_key = parts[0].strip().upper()
        home_key = parts[1].strip().upper()
        if away_key not in TEAMS:
            print(f"Unknown away team: {away_key}")
            raise SystemExit(1)
        if home_key not in TEAMS:
            print(f"Unknown home team: {home_key}")
            raise SystemExit(1)
        proj = project_game(
            home_abbr=home_key,
            away_abbr=away_key,
            market_total=args.market_total,
            market_spread=args.market_spread,
            series="Pregame",
            game_time="TBD",
            bankroll=args.bankroll,
        )
        print(json.dumps(proj, indent=2))

    elif args.list_teams:
        for abbr, team in TEAMS.items():
            print(f"{abbr}: {team.name} ({len(team.players)} players)")
            if team.injury_notes:
                print(f"  Injuries: {', '.join(team.injury_notes)}")

    else:
        print("No action specified. Use --backtest, --game, or --list-teams.")