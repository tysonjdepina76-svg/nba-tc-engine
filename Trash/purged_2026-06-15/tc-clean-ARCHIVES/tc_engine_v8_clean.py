"""
tc_engine.py — Triple Conservative Engine v8.0 (Clean Integrated)
=================================================================
Single source of truth for NBA + WNBA TC projections.
v8.0 adds game-total calibration separate from TC Match (player props only).

CRITICAL ARCHITECTURAL RULE:
    TC MATCH = stat × CONS × status_factor + GAP  →  player props ONLY (PTS/REB/AST/3PM)
    GAME TOTAL = raw_pts × star_mult × status_factor + bench_adj + home_court → separate model

TC Match does NOT apply to team totals, game totals, spread, or ML.
Both models are independent and can be used simultaneously.

Author: Tyson (Zo Computer)
Date: 2026-05-25
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import argparse
import json

# ── CONSTANTS: TC MATCH (Player Props) ──────────────────────────────────────

CONS_PTS   = 0.85
CONS_REB   = 0.80
CONS_AST   = 0.75
CONS_3PM   = 0.70

GAP_PTS    = -3.0
GAP_REB    = -1.5
GAP_AST    = -1.0
GAP_3PM    = -0.8

LINE_FACTOR = 0.88
Q_FACTOR    = 0.55
OUT_FACTOR  = 0.0
MIN_EDGE    = 1.0

# ── CONSTANTS: GAME TOTAL v8 (Separate from TC Match) ───────────────────────

STAR_MULTIPLIER = 0.90
ALL_NBA_PLAYERS = {
    "Shai Gilgeous-Alexander": 0.90,
    "Nikola Jokic": 0.90,
    "Victor Wembanyama": 0.90,
    "Luka Doncic": 0.90,
    "Jayson Tatum": 0.90,
    "Giannis Antetokounmpo": 0.90,
    "Donovan Mitchell": 0.87,
    "Jalen Brunson": 0.87,
    "Anthony Edwards": 0.87,
    "Kevin Durant": 0.87,
    "Jaylen Brown": 0.87,
    "Karl-Anthony Towns": 0.87,
}

BENCH_DIFF_THRESHOLD = 15.0
BENCH_DIFF_BONUS     = 4.0
HOME_COURT_BONUS     = 2.0

KELLY_FRAC = 0.50
MIN_HR     = 0.57

ODDS = {"standard": -110, "parlay_2": -110, "parlay_3": +260}

SERIES_BENCH_PTS: Dict[str, Dict[str, float]] = {
    "OKC": {"G1": 33.0, "G2": 45.0, "G3": 76.0, "G4": 23.0},
    "SAS": {"G1": 25.0, "G2": 19.0, "G3": 19.0, "G4": 23.0},
    "CLE": {"G1": 28.0, "G2": 31.0, "G3": 19.0, "G4": 22.0},
    "BOS": {"G1": 35.0, "G2": 29.0, "G3": 38.0, "G4": 19.0},
}

# ── PLAYER CLASS ─────────────────────────────────────────────────────────────

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

    def status_factor(self) -> float:
        s = self.status.upper()
        if s == "OUT": return OUT_FACTOR
        if s == "Q":   return Q_FACTOR
        return 1.0

    def tc_prop(self, stat: str) -> float:
        factor = self.status_factor()
        stat = stat.lower()
        if stat in ("pts", "points"):
            return round(max(0.0, self.pts * CONS_PTS * factor + GAP_PTS), 1)
        if stat in ("reb", "rebounds"):
            return round(max(0.0, self.reb * CONS_REB * factor + GAP_REB), 1)
        if stat in ("ast", "assists"):
            return round(max(0.0, self.ast * CONS_AST * factor + GAP_AST), 1)
        if stat in ("3pm", "tpm"):
            return round(max(0.0, self.tpm * CONS_3PM * factor + GAP_3PM), 1)
        raise ValueError(f"Unknown prop stat: {stat}")

    def tc_pts(self) -> float:   return self.tc_prop("pts")
    def tc_reb(self) -> float:  return self.tc_prop("reb")
    def tc_ast(self) -> float:  return self.tc_prop("ast")
    def tc_3pm(self) -> float:  return self.tc_prop("3pm")

    def raw_points_for_total(self) -> float:
        factor = self.status_factor()
        base = self.pts * factor
        if self.name in ALL_NBA_PLAYERS:
            base *= ALL_NBA_PLAYERS[self.name]
        return round(base, 1)

    def prop_dict(self, market_lines: Optional[Dict[str, float]] = None) -> dict:
        market_lines = market_lines or {}
        out = {
            "name": self.name, "pos": self.pos, "ht": self.ht, "status": self.status,
            "raw_pts": self.pts, "status_factor": self.status_factor(),
            "tc_pts": self.tc_pts(), "tc_reb": self.tc_reb(),
            "tc_ast": self.tc_ast(), "tc_3pm": self.tc_3pm(),
            "tc_prop_total": round(self.tc_pts() + self.tc_reb() + self.tc_ast() + self.tc_3pm(), 1),
            "raw_points_for_total": self.raw_points_for_total(),
        }
        edges = {}
        for stat in ("pts", "reb", "ast", "3pm"):
            if stat in market_lines:
                tc_val = self.tc_prop(stat)
                edges[stat] = round(tc_val - float(market_lines[stat]), 1)
        if edges:
            out["prop_edge"] = edges
        return out

    def as_dict(self) -> dict:
        return self.prop_dict()


# ── TEAM CLASS ───────────────────────────────────────────────────────────────

@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player] = field(default_factory=list)
    injury_notes: List[str] = field(default_factory=list)

    def prop_tc_totals(self) -> Dict[str, float]:
        return {
            "pts": round(sum(p.tc_pts() for p in self.players), 1),
            "reb": round(sum(p.tc_reb() for p in self.players), 1),
            "ast": round(sum(p.tc_ast() for p in self.players), 1),
            "3pm": round(sum(p.tc_3pm() for p in self.players), 1),
        }

    def tc_starters(self) -> float:
        return round(sum(p.tc_pts() for p in self.players[:5]), 1)

    def bench_tc_total(self) -> float:
        return round(sum(p.tc_pts() for p in self.players[5:]), 1)

    def raw_points_total(self) -> float:
        return round(sum(p.raw_points_for_total() for p in self.players), 1)

    def raw_starters_points(self) -> float:
        return round(sum(p.raw_points_for_total() for p in self.players[:5]), 1)

    def raw_bench_points(self) -> float:
        return round(sum(p.raw_points_for_total() for p in self.players[5:]), 1)

    def tc_adjusted_team_total(
        self,
        is_home: bool = False,
        series_bench_avg: Optional[float] = None,
        opponent_bench_avg: Optional[float] = None,
    ) -> Dict[str, Any]:
        adj_details = []
        total = 0.0
        for p in self.players:
            total += p.raw_points_for_total()
        if is_home:
            total += HOME_COURT_BONUS
            adj_details.append(f"+{HOME_COURT_BONUS} home_court")
        if series_bench_avg is not None and opponent_bench_avg is not None:
            diff = series_bench_avg - opponent_bench_avg
            if diff > BENCH_DIFF_THRESHOLD:
                total += BENCH_DIFF_BONUS
                adj_details.append(f"+{BENCH_DIFF_BONUS:.1f} bench_diff ({diff:.1f} PPG)")
        return {
            "adjusted_total": round(total, 1),
            "raw_total": self.raw_points_total(),
            "adjustments": adj_details,
        }

    def active_players(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"]

    def as_dict(self) -> dict:
        return {
            "abbr": self.abbr, "name": self.name,
            "raw_points_total": self.raw_points_total(),
            "raw_starters_points": self.raw_starters_points(),
            "raw_bench_points": self.raw_bench_points(),
            "prop_tc_totals": self.prop_tc_totals(),
            "tc_starters_pts": self.tc_starters(),
            "bench_tc_pts": self.bench_tc_total(),
            "players": [p.as_dict() for p in self.players],
            "injury_notes": self.injury_notes,
        }


# ── TEAM FACTORY ──────────────────────────────────────────────────────────────

def _P(name, pos, ht, pts, reb, ast, tpm, status="ACTIVE") -> Player:
    return Player(name, pos, ht, pts, reb, ast, tpm, status)

# ── NBA ROSTERS ───────────────────────────────────────────────────────────────

NBA_TEAMS: Dict[str, Team] = {

    "NYK": Team("NYK", "New York Knicks", [
        _P("Jalen Brunson",      "PG", "6-2",  26.0, 3.5, 6.5, 2.5),
        _P("Karl-Anthony Towns", "C",  "6-11", 24.5,10.5, 3.0, 2.0),
        _P("Mikal Bridges",       "SG", "6-6",  19.0, 4.5, 3.5, 2.2),
        _P("OG Anunoby",          "SF", "6-7",  17.5, 5.0, 2.5, 1.8),
        _P("Josh Hart",           "PF", "6-5",  13.5, 6.5, 4.5, 1.2),
        _P("Miles McBride",       "PG", "6-2",   9.5, 2.5, 3.0, 1.5),
        _P("Precious Achiuwa",    "PF", "6-8",   7.5, 5.5, 1.0, 0.5),
        _P("Jordan Clarkson",     "G",  "6-4",  16.5, 3.5, 4.5, 1.8),
    ]),

    "PHI": Team("PHI", "Philadelphia 76ers", [
        _P("Joel Embiid",     "C",  "7-0",  28.5,10.5, 5.5, 1.8, "OUT"),
        _P("Tyrese Maxey",    "PG", "6-2",  24.5, 4.5, 6.5, 2.5),
        _P("Paul George",     "SF", "6-8",  22.0, 5.5, 4.5, 3.2),
        _P("Kelly Oubre Jr.", "F",  "6-7",  18.5, 5.0, 1.5, 2.1),
        _P("Andre Drummond",  "C",  "6-9",  10.0,10.0, 2.0, 0.0),
        _P("Justin Edwards",  "F",  "6-6",   8.0, 3.0, 1.0, 0.8),
        _P("VJ Edgecombe",    "G",  "6-5",  15.0, 3.5, 2.5, 1.2),
        _P("Quentin Grimes",  "G",  "6-5",  10.0, 3.0, 2.5, 1.8),
    ], ["Joel Embiid OUT (knee)", "Paul George OUT (ankle)"]),

    "BOS": Team("BOS", "Boston Celtics", [
        _P("Jayson Tatum",        "F",  "6-8", 28.5, 7.5, 5.0, 2.9),
        _P("Jaylen Brown",        "G",  "6-6", 23.0, 6.0, 3.5, 2.2),
        _P("Kristaps Porzingis", "C",  "7-1", 20.0, 7.0, 2.5, 2.8, "Q"),
        _P("Derrick White",       "G",  "6-4", 16.0, 4.2, 4.8, 2.8),
        _P("Jrue Holiday",        "G",  "6-4", 14.5, 4.5, 5.0, 1.8),
        _P("Al Horford",          "F",  "6-9",  9.0, 6.2, 3.5, 2.0),
        _P("Payton Pritchard",    "G",  "6-2",  8.0, 2.8, 3.0, 1.5),
    ], ["Kristaps Porzingis Q (illness)"]),

    "CLE": Team("CLE", "Cleveland Cavaliers", [
        _P("Donovan Mitchell",  "SG", "6-1", 27.0, 4.5, 5.0, 2.5),
        _P("Darius Garland",    "PG", "6-1", 20.0, 3.0, 7.0, 2.2),
        _P("Evan Mobley",        "PF", "6-11",18.0, 9.5, 3.0, 0.8),
        _P("Jarrett Allen",      "C",  "6-9", 15.0,10.0, 2.0, 0.0),
        _P("Caris LeVert",      "SG", "6-5", 12.0, 4.0, 3.0, 1.5),
        _P("Isaac Okoro",        "SG", "6-5",  8.5, 3.0, 2.0, 1.2),
        _P("Max Strus",          "SF", "6-5",  9.0, 4.0, 3.0, 2.0),
        _P("Ty Jerome",          "PG", "6-6",  7.5, 2.5, 3.5, 1.2),
    ]),

    "OKC": Team("OKC", "Oklahoma City Thunder", [
        _P("Shai Gilgeous-Alexander", "SG", "6-5", 32.0, 5.0, 6.5, 2.8),
        _P("Jalen Williams",          "SF", "6-6", 18.5, 5.5, 4.0, 1.5),
        _P("Chet Holmgren",           "C",  "7-0", 16.0, 8.0, 2.5, 1.0),
        _P("Isaiah Hartenstein",       "C",  "6-11", 8.0, 7.5, 2.5, 0.2),
        _P("Luguentz Dort",            "SG", "6-4",  9.5, 3.5, 1.2, 2.0),
        _P("Alex Caruso",              "G",  "6-4",  6.0, 2.5, 2.0, 1.2),
        _P("Isaiah Joe",               "G",  "6-1",  9.0, 2.0, 0.8, 2.1),
        _P("Cason Wallace",           "G",  "6-4",  8.5, 2.5, 1.5, 1.8),
    ]),

    "MIN": Team("MIN", "Minnesota Timberwolves", [
        _P("Anthony Edwards",          "G",  "6-4", 30.0, 5.0, 5.5, 3.5),
        _P("Julius Randle",             "PF", "6-9", 22.0, 9.0, 4.5, 1.8),
        _P("Rudy Gobert",               "C",  "7-1", 14.0,12.0, 1.5, 0.2),
        _P("Donte DiVincenzo",          "SG", "6-4", 10.0, 4.0, 3.0, 2.0),
        _P("Mike Conley",               "PG", "6-1", 11.0, 3.0, 5.5, 2.0),
        _P("Naz Reid",                   "C",  "6-9", 13.5, 5.0, 2.0, 1.8),
        _P("Kyle Anderson",             "F",  "6-9",  8.5, 5.0, 4.0, 0.8),
        _P("Nickeil Alexander-Walker",  "SG", "6-5", 12.0, 3.5, 2.5, 2.0),
    ]),

    "DEN": Team("DEN", "Denver Nuggets", [
        _P("Nikola Jokic",          "C",  "6-11",29.0,12.5,10.0, 2.0),
        _P("Jamal Murray",           "G",  "6-4",  22.0, 4.5, 6.5, 2.2),
        _P("Michael Porter Jr.",    "F",  "6-10", 16.5, 6.5, 2.5, 2.0),
        _P("Aaron Gordon",           "F",  "6-9",  14.0, 6.5, 3.0, 1.5),
        _P("Russell Westbrook",      "G",  "6-3",  12.0, 5.0, 6.5, 1.2),
        _P("Christian Braun",        "G",  "6-6",   9.0, 3.5, 2.0, 1.0),
        _P("Peyton Watson",          "F",  "6-8",  10.0, 4.0, 2.0, 0.8),
    ]),

    "SAS": Team("SAS", "San Antonio Spurs", [
        _P("Victor Wembanyama", "C",  "7-4", 28.0,10.5, 4.0, 2.5),
        _P("De'Aaron Fox",      "G",  "6-3", 24.5, 5.5, 6.5, 1.8),
        _P("Harrison Barnes",   "F",  "6-8", 13.5, 5.8, 2.2, 1.4),
        _P("Stephon Castle",    "G",  "6-5", 15.0, 4.5, 4.0, 1.2),
        _P("Keldon Johnson",     "F",  "6-5", 14.0, 4.5, 2.0, 2.0),
        _P("Devin Vassell",      "SG", "6-5", 12.0, 3.5, 2.5, 2.2),
        _P("Julian Champagnie",  "F",  "6-6",  8.0, 3.5, 1.5, 1.5),
        _P("Bismack Biyombo",    "C",  "6-11", 9.5, 8.0, 1.5, 0.2),
    ]),

    "DET": Team("DET", "Detroit Pistons", [
        _P("Cade Cunningham",   "PG", "6-6", 26.5, 6.5, 8.5, 1.8),
        _P("Jalen Duren",        "C",  "6-11",12.0, 9.0, 2.0, 0.0),
        _P("Tobias Harris",      "SF", "6-8", 18.5, 6.5, 3.0, 1.5),
        _P("Tim Hardaway Jr.",   "SG", "6-5", 11.5, 3.5, 1.5, 2.2),
        _P("Marcus Smart",       "PG", "6-4", 10.5, 3.5, 5.0, 1.8),
        _P("Ausar Thompson",     "SG", "6-5",  8.5, 4.5, 2.5, 0.5),
        _P("Jaden Ivey",         "PG", "6-4", 15.0, 4.0, 3.5, 1.5),
        _P("Dennis Schroder",    "PG", "6-1", 13.0, 3.0, 6.0, 1.5),
    ]),

    "LAL": Team("LAL", "Los Angeles Lakers", [
        _P("LeBron James",      "SF", "6-9", 25.0, 7.5, 8.0, 2.2),
        _P("Austin Reaves",      "SG", "6-5", 18.0, 4.0, 5.0, 2.5),
        _P("Rui Hachimura",      "PF", "6-8", 14.5, 5.0, 1.5, 1.2),
        _P("Luka Doncic",        "PG", "6-7", 29.0, 7.5, 8.0, 2.8, "OUT"),
        _P("Jordan Goodwin",     "SG", "6-4", 12.5, 4.5, 3.5, 1.5),
        _P("Dorian Finney-Smith","SF", "6-7",  8.5, 4.0, 2.0, 1.5),
        _P("Gabe Vincent",       "PG", "6-2",  6.5, 2.0, 2.0, 1.2),
        _P("Max Christie",       "SG", "6-5",  7.0, 3.0, 1.5, 1.2),
    ], ["Luka Doncic OUT (ankle)"]),

    "LAC": Team("LAC", "Los Angeles Clippers", [
        _P("James Harden",     "G",  "6-4",  22.0, 5.0, 8.0, 2.5),
        _P("Kawhi Leonard",    "F",  "6-7",  24.0, 6.0, 4.0, 2.5, "Q"),
        _P("Norman Powell",    "G",  "6-3",  16.0, 3.5, 2.0, 2.2),
        _P("Ivica Zubac",      "C",  "7-0",  12.0, 9.0, 2.0, 0.0),
        _P("Amir Coffey",      "G",  "6-5",  11.0, 3.0, 2.5, 1.5),
        _P("Nicolas Batum",    "F",  "6-8",   8.5, 4.5, 2.5, 1.5),
        _P("Derrick Jones Jr.","F",  "6-6",   9.0, 3.5, 1.5, 1.0),
        _P("Kris Dunn",        "G",  "6-4",   7.5, 3.0, 4.0, 0.8),
    ], ["Kawhi Leonard Q (knee)"]),

    "POR": Team("POR", "Portland Trail Blazers", [
        _P("Scoot Henderson",    "G",  "6-3",  18.5, 4.5,  7.5, 1.5),
        _P("Anfernee Simons",     "G",  "6-5",  21.5, 3.5,  4.5, 3.0),
        _P("Jerami Grant",        "F",  "6-8",  18.0, 5.0,  2.5, 2.2),
        _P("Deandre Ayton",       "C",  "7-0",  16.5,10.0,  2.0, 0.0),
        _P("Toukam Saop",         "F",  "6-9",  15.5, 7.5,  2.5, 1.2),
        _P("Shaedon Sharpe",      "G",  "6-6",  15.0, 4.0,  2.5, 2.0),
        _P("Rayan Rupert",        "G",  "6-7",   8.5, 3.0,  2.0, 1.2),
        _P("Kris Murray",         "F",  "6-8",   8.0, 3.5,  1.5, 0.8),
    ], []),

    "ORL": Team("ORL", "Orlando Magic", [
        _P("Paolo Banchero",    "F",  "6-10",28.5, 7.5, 5.5, 1.5),
        _P("Franz Wagner",      "F",  "6-10",22.0, 5.0, 4.0, 1.8, "OUT"),
        _P("Jalen Suggs",       "G",  "6-5", 16.5, 4.0, 4.5, 1.5),
        _P("Wendell Carter Jr.", "C",  "6-6", 14.5, 9.0, 2.5, 0.8),
        _P("Cole Anthony",      "G",  "6-2", 13.0, 4.5, 3.5, 1.2),
        _P("Goga Bitadze",      "C",  "6-11",10.5, 6.0, 2.0, 0.5),
        _P("Jonathan Isaac",    "F",  "6-10", 6.5, 4.0, 1.0, 0.5),
        _P("Caleb Houstan",     "F",  "6-8",  7.0, 3.0, 1.5, 0.8),
    ], ["Franz Wagner OUT (calf)"]),

    "HOU": Team("HOU", "Houston Rockets", [
        _P("Alperen Sengun",   "C",  "6-9", 21.5, 9.5, 5.0, 0.8),
        _P("Jabari Smith Jr.", "F",  "6-10",18.0, 7.0, 1.8, 2.5),
        _P("Tari Eason",       "F",  "6-8", 14.5, 7.0, 2.0, 1.2),
        _P("Reed Sheppard",     "G",  "6-2", 13.0, 4.0, 3.0, 2.2),
        _P("Amen Thompson",     "G",  "6-6", 12.5, 5.5, 3.5, 0.8),
        _P("Cam Whitmore",     "G",  "6-4", 11.0, 4.0, 1.5, 1.5),
        _P("Jalen Green",       "G",  "6-4", 18.0, 4.5, 3.0, 2.0),
        _P("Dillon Brooks",     "F",  "6-6", 12.0, 4.0, 2.0, 1.5),
    ]),

    "TOR": Team("TOR", "Toronto Raptors", [
        _P("Scottie Barnes",    "F",  "6-8", 21.5, 7.5, 5.5, 1.5),
        _P("RJ Barrett",        "G",  "6-7", 19.5, 5.5, 3.5, 2.0),
        _P("Immanuel Quickley", "G",  "6-2", 15.0, 4.0, 4.5, 1.5),
        _P("Jakob Poeltl",      "C",  "6-11",12.5, 9.5, 2.5, 0.0),
        _P("Jamal Shead",        "G",  "6-2",  9.5, 3.0, 4.5, 1.2),
        _P("Ochai Agbaji",       "G",  "6-5",  8.5, 3.5, 2.0, 1.2),
        _P("Collin Murray-Boyles","F", "6-8", 12.0, 5.5, 2.5, 0.5),
    ]),

}

# ── WNBA ROSTERS ─────────────────────────────────────────────────────────────

WNBA_TEAMS: Dict[str, Team] = {

    "NYL": Team("NYL", "New York Liberty", [
        _P("Breanna Stewart",    "F", "6-4", 23.0, 9.0, 4.0, 2.5),
        _P("Jonquel Jones",      "C", "6-6", 18.5, 9.5, 3.5, 1.8),
        _P("Sabrina Ionescu",    "G", "5-11",20.5, 5.0, 7.5, 3.2),
        _P("Kayla Thornton",     "F", "6-2", 11.0, 5.5, 2.5, 1.5),
        _P("Svetlana Petrov",   "G", "5-10",10.0, 3.5, 4.5, 1.8),
        _P("JiSu Park",          "C", "6-5", 10.5, 7.0, 1.5, 0.5),
        _P("Marine Johannès",    "G", "6-0", 11.5, 3.0, 4.0, 2.2),
        _P("Michele Taylor",     "F", "6-3",  7.5, 4.0, 1.5, 1.0),
    ]),

    "MIN": Team("MIN", "Minnesota Lynx", [
        _P("Napheesa Collier",       "F", "6-2", 20.0, 6.5, 3.5, 1.8),
        _P("Alana Smith",            "G", "5-9", 14.5, 3.5, 5.5, 1.5, "Q"),
        _P("Kayla McBride",          "G", "5-11",16.0, 4.0, 4.0, 2.8),
        _P("Crystal Dangerfield",    "G", "5-5", 12.0, 3.0, 3.5, 1.2),
        _P("Natalie Achonwu",        "C", "6-5",  9.5, 7.0, 2.0, 0.5),
        _P("Olivia Olu",             "F", "6-2",  7.0, 4.0, 1.5, 1.0),
        _P("Tiffany Mitchell",        "G", "5-10", 9.0, 2.5, 3.0, 1.2),
        _P("Nizhoni Cowboy",         "F", "6-3",  6.5, 4.0, 1.0, 0.8),
    ], ["Alana Smith Q (ankle)"]),

    "DAL": Team("DAL", "Dallas Wings", [
        _P("Arielle Wiggins",   "F", "6-4", 17.0, 6.0, 2.5, 1.2),
        _P("Satou Sabally",     "F", "6-4", 18.5, 7.5, 4.0, 2.0, "Q"),
        _P("Odyssey Sims",      "G", "5-8", 15.0, 3.5, 6.0, 1.5),
        _P("Teaira McCowan",    "C", "7-0", 16.0,11.0, 1.5, 0.0),
        _P("Crystal Dangerfield","G","5-5", 11.5, 2.5, 3.5, 1.0),
        _P("Moriah Jefferson",   "G", "5-7", 10.0, 2.0, 5.5, 1.2),
        _P("Natasha Howard",    "F", "6-4", 14.0, 6.5, 2.0, 1.0, "OUT"),
        _P("Joyner Woods",      "G", "5-10", 8.5, 2.5, 3.0, 1.2),
    ], ["Satou Sabally Q (hip)", "Natasha Howard OUT (knee)"]),

    "LVA": Team("LVA", "Las Vegas Aces", [
        _P("A'ja Wilson",      "F", "6-4", 25.0,10.5, 3.5, 1.5),
        _P("Chelsea Gray",     "G", "5-11",17.5, 4.0, 6.5, 2.0),
        _P("Kia Wilson",        "G", "5-8", 15.0, 3.5, 5.0, 2.5),
        _P("Candace Parker",   "F", "6-4", 14.5, 8.0, 4.5, 1.2),
        _P("Dearica Hamby",    "F", "6-2", 13.0, 7.5, 3.0, 1.5),
        _P("Jasmine Thomas",   "G", "5-8",  9.5, 2.5, 5.0, 1.8),
        _P("Sydney Colson",    "G", "5-8",  6.0, 2.0, 4.0, 1.0),
        _P("Kamera Conrad",    "F", "6-2",  7.5, 4.5, 1.5, 0.8),
    ]),

    "CON": Team("CON", "Connecticut Sun", [
        _P("Alyssa Thomas",   "F", "6-3", 16.0, 8.5, 7.5, 1.0),
        _P("DeWanna Bonner",  "F", "6-4", 18.0, 7.0, 4.0, 2.0),
        _P("Brionna Jones",   "C", "6-3", 14.5, 7.5, 2.0, 0.8),
        _P("Natasha Cloud",    "G", "5-11",12.0, 3.5, 6.0, 1.5),
        _P("Megan McKenna",   "G", "5-10",10.5, 2.5, 4.5, 2.0),
        _P("Ellienne",        "F", "6-2",  7.0, 4.0, 1.5, 1.0),
        _P("Lindsay Wisdom",   "C", "6-5",  8.5, 5.5, 1.5, 0.5),
        _P("Jasmine Nwajei",  "G", "5-9",  6.5, 2.0, 2.5, 1.0),
    ]),

    "CHI": Team("CHI", "Chicago Sky", [
        _P("Kahleah Copper",  "F", "6-1", 16.5, 5.5, 2.5, 1.5),
        _P("Rebekah",         "C", "6-5", 10.0, 7.0, 1.5, 0.5),
        _P("Dana",            "G", "5-6",  8.5, 2.0, 3.5, 1.2),
        _P("Ingrid",          "F", "6-3",  6.5, 4.0, 0.8, 0.5),
        _P("Yuki",            "G", "5-9",  5.5, 1.5, 1.5, 0.5),
        _P("Li",              "F", "6-4",  7.0, 4.5, 0.8, 0.5),
        _P("Alma",            "F", "6-0",  4.8, 3.2, 0.7, 0.5),
        _P("Raeg",            "G", "5-7",  4.0, 1.5, 1.8, 0.8),
    ]),

    "ATL": Team("ATL", "Atlanta Dream", [
        _P("Rhyne Howard",    "G", "6-0", 15.5, 4.5, 3.5, 2.0),
        _P("Allisha Gray",    "G", "6-0", 14.2, 3.8, 2.9, 1.9),
        _P("Elyesa Moro",     "F", "6-3",  9.8, 5.2, 1.4, 0.8),
        _P("Crystal Dangerfield","G","5-8", 8.5, 2.1, 2.8, 1.5),
        _P("Nia Coffey",      "F", "6-1",  7.2, 4.0, 1.2, 0.9),
        _P("Taj",             "C", "6-5",  5.1, 4.8, 0.5, 0.2),
        _P("Iade",            "G", "5-10", 4.0, 1.5, 1.2, 0.6),
    ]),

    "SEA": Team("SEA", "Seattle Storm", [
        _P("Breanna Stewart", "F", "6-4", 20.0, 8.5, 4.5, 2.5),
        _P("Jewell Loyd",     "G", "5-9", 16.5, 3.5, 4.0, 2.5),
        _P("Ezi",             "C", "6-5", 12.5, 9.5, 2.0, 0.4),
        _P("Mercedes Russell","C", "6-6",  7.5, 6.0, 1.0, 0.0),
        _P("Jordan",          "G", "5-10", 8.5, 2.5, 3.5, 1.5),
        _P("Briyana",         "F", "6-2",  9.0, 5.5, 1.2, 0.6),
        _P("Kylie",           "G", "5-9",  6.0, 1.5, 2.0, 0.9),
        _P("Layla",           "F", "6-1",  5.0, 3.5, 0.5, 0.3),
    ]),

}


# ── HELPERS ─────────────────────────────────────────────────────────────────

def get_team(abbr: str, sport: str = "NBA") -> Team:
    teams = NBA_TEAMS if sport.upper() == "NBA" else WNBA_TEAMS
    abbr = abbr.upper()
    if abbr not in teams:
        raise ValueError(f"Unknown team: {abbr} for sport {sport}")
    return teams[abbr]

def get_teams(sport: str = "NBA") -> Dict[str, Team]:
    return NBA_TEAMS if sport.upper() == "NBA" else WNBA_TEAMS

def calc_series_bench_avg(team_abbr: str, series_data: Dict[str, Dict[str, float]]) -> Optional[float]:
    if team_abbr not in series_data:
        return None
    games = list(series_data[team_abbr].values())
    if not games:
        return None
    return round(sum(games) / len(games), 1)


# ── BACKTEST GAMES ───────────────────────────────────────────────────────────

NBA_BACKTEST = [
    {"home": "BOS", "away": "PHI", "date": "2026-04-19",
     "market_total": 208.5, "market_spread": -11.5,
     "actual_total": 216, "actual_winner": "BOS"},
    {"home": "DEN", "away": "LAC", "date": "2026-04-19",
     "market_total": 216.5, "market_spread": -4.5,
     "actual_total": 222, "actual_winner": "DEN"},
    {"home": "DET", "away": "ORL", "date": "2026-04-19",
     "market_total": 200.5, "market_spread": -5.5,
     "actual_total": 207, "actual_winner": "DET"},
    {"home": "SAS", "away": "POR", "date": "2026-04-19",
     "market_total": 206.5, "market_spread": -8.5,
     "actual_total": 226, "actual_winner": "SAS"},
]

WNBA_BACKTEST = [
    {"home": "NYL", "away": "MIN", "date": "2025-10-10",
     "market_total": 161.5, "market_spread": -5.5,
     "actual_total": 161, "actual_winner": "NYL"},
    {"home": "LVA", "away": "NYL", "date": "2025-10-13",
     "market_total": 162.5, "market_spread": -4.5,
     "actual_total": 162, "actual_winner": "LVA"},
]


# ── GAME TOTAL v8 ────────────────────────────────────────────────────────────

def calc_game_total_v8(
    home: Team,
    away: Team,
    market_total: float,
    series_bench: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    series_bench = series_bench or SERIES_BENCH_PTS
    home_bench_avg = calc_series_bench_avg(home.abbr, series_bench)
    away_bench_avg = calc_series_bench_avg(away.abbr, series_bench)
    home_adj = home.tc_adjusted_team_total(
        is_home=True,
        series_bench_avg=home_bench_avg,
        opponent_bench_avg=away_bench_avg,
    )
    away_adj = away.tc_adjusted_team_total(
        is_home=False,
        series_bench_avg=away_bench_avg,
        opponent_bench_avg=home_bench_avg,
    )
    combined = round(home_adj["adjusted_total"] + away_adj["adjusted_total"], 1)
    gap = round(combined - market_total, 1)
    lean = "UNDER" if gap < -5 else ("OVER" if gap > 5 else "NO EDGE")
    return {
        "home": {
            "abbr": home.abbr,
            "v8_total": home_adj["adjusted_total"],
            "raw_total": home_adj["raw_total"],
            "adjustments": home_adj["adjustments"],
        },
        "away": {
            "abbr": away.abbr,
            "v8_total": away_adj["adjusted_total"],
            "raw_total": away_adj["raw_total"],
            "adjustments": away_adj["adjustments"],
        },
        "v8_combined": combined,
        "market_total": market_total,
        "gap_vs_market": gap,
        "lean": lean,
        "model_type": "v8_game_total_calibration",
        "note": "Uses raw pts × star_mult + bench_diff + home_court. TC Match does NOT apply to game totals.",
    }


# ── GAME PROJECTION ──────────────────────────────────────────────────────────

def calc_game(
    home: Team,
    away: Team,
    market_total: float,
    market_spread: float,
    sport: str = "NBA",
    series_bench: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    home_raw = home.raw_points_total()
    away_raw = away.raw_points_total()
    raw_combined = round(home_raw + away_raw, 1)
    home_tc = home.prop_tc_totals()
    away_tc = away.prop_tc_totals()
    spread_raw = round(home_raw - away_raw, 1)
    spread_abs = abs(market_spread)
    raw_favored = "HOME" if spread_raw > 0 else ("AWAY" if spread_raw < 0 else "PICK")
    spread_lean = "HOME" if spread_raw > spread_abs else (
                  "AWAY" if spread_raw < -spread_abs else "PASS")
    v8 = calc_game_total_v8(home, away, market_total, series_bench)
    tc_combined = round(home_tc["pts"] + away_tc["pts"], 1)
    tc_line = round(tc_combined * LINE_FACTOR)
    tc_edge = round(tc_combined - tc_line, 1)
    tc_signal = "OVER" if tc_edge > MIN_EDGE else ("UNDER" if tc_edge < -MIN_EDGE else "NO EDGE")
    return {
        "home": home.as_dict(),
        "away": away.as_dict(),
        "tc_match": {
            "tc_combined_pts": tc_combined,
            "tc_line_pts": tc_line,
            "tc_edge": tc_edge,
            "tc_signal": tc_signal,
            "prop_tc_totals": {"home": home_tc, "away": away_tc},
            "rule": "TC Match applies to player props: PTS/REB/AST/3PM only.",
        },
        "game_total_v8": v8,
        "raw_points": {"home": home_raw, "away": away_raw, "combined": raw_combined},
        "market_total": market_total,
        "spread": {
            "raw_points_spread": spread_raw,
            "market_spread": market_spread,
            "lean": spread_lean,
            "favored": raw_favored,
        },
    }


def project_game(
    home_abbr: str,
    away_abbr: str,
    market_total: float,
    market_spread: float,
    series: str = "",
    game_time: str = "TBD",
    bankroll: float = 1000.0,
    sport: str = "NBA",
    series_bench: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    home = get_team(home_abbr, sport)
    away = get_team(away_abbr, sport)
    proj = calc_game(home, away, market_total, market_spread, sport, series_bench)
    tc_combined = proj["tc_match"]["tc_combined_pts"]
    tc_edge = proj["tc_match"]["tc_edge"]
    return {
        "meta": {
            "home": home_abbr.upper(), "away": away_abbr.upper(),
            "series": series, "game_time": game_time, "sport": sport,
        },
        "tc_match": proj["tc_match"],
        "game_total_v8": proj["game_total_v8"],
        "raw_points": proj["raw_points"],
        "market_total": market_total,
        "spread": proj["spread"],
        "players": {
            "home": proj["home"]["players"],
            "away": proj["away"]["players"],
        },
        "starters": {
            "home": proj["home"]["players"][:5],
            "away": proj["away"]["players"][:5],
        },
        "bench": {
            "home_raw_points": proj["home"]["raw_bench_points"],
            "away_raw_points": proj["away"]["raw_bench_points"],
        },
        "injuries": {
            "home": proj["home"]["injury_notes"],
            "away": proj["away"]["injury_notes"],
        },
        "bets": {
            "tc_signal": proj["tc_match"]["tc_signal"],
            "tc_edge": tc_edge,
            "game_total_v8_lean": proj["game_total_v8"]["lean"],
            "game_total_v8_gap": proj["game_total_v8"]["gap_vs_market"],
            "bankroll": bankroll,
            "note": "Two independent models: (1) TC Match for player props, (2) v8 Game Total for game totals.",
        },
    }


# ── BACKTEST ─────────────────────────────────────────────────────────────────

def run_backtest(sport: str = "NBA") -> Dict[str, Any]:
    teams = get_teams(sport)
    suite = NBA_BACKTEST if sport == "NBA" else WNBA_BACKTEST
    results = []
    for g in suite:
        home = teams[g["home"]]
        away = teams[g["away"]]
        proj = calc_game(home, away, g["market_total"], g["market_spread"], sport)
        v8_combined = proj["game_total_v8"]["v8_combined"]
        v8_gap = proj["game_total_v8"]["gap_vs_market"]
        v8_dir = proj["game_total_v8"]["lean"]
        actual = g["actual_total"]
        actual_dir = "OVER" if actual > g["market_total"] else "UNDER"
        v8_hit = v8_dir == actual_dir
        tc_combined = proj["tc_match"]["tc_combined_pts"]
        tc_line = proj["tc_match"]["tc_line_pts"]
        tc_edge = proj["tc_match"]["tc_edge"]
        tc_signal = proj["tc_match"]["tc_signal"]
        results.append({
            "game": f"{g['away']}@{g['home']}", "date": g["date"],
            "market_total": g["market_total"],
            "v8_combined": v8_combined, "actual_total": actual,
            "v8_gap_vs_market": v8_gap, "v8_direction": v8_dir,
            "actual_direction": actual_dir, "v8_hit": v8_hit,
            "tc_combined": tc_combined, "tc_line": tc_line,
            "tc_edge": tc_edge, "tc_signal": tc_signal,
        })
    n = len(results)
    v8_hr = round(sum(r["v8_hit"] for r in results) / n * 100, 1)
    avg_gap = round(sum(r["v8_gap_vs_market"] for r in results) / n, 1)
    return {
        "games": results,
        "summary": {
            "sport": sport, "total_games": n,
            "v8_direction_hit_rate": v8_hr,
            "avg_v8_gap_vs_market": avg_gap,
        },
    }


# ── FASTAPI APP ───────────────────────────────────────────────────────────────

try:
    from fastapi import FastAPI, HTTPException, Query
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

if FASTAPI_AVAILABLE:
    app = FastAPI(title="Sports TC v8", description="TC Match + v8 Game Total", version="8.0.0")

    class GameRequest(BaseModel):
        home: str; away: str; market_total: float; market_spread: float = 0.0
        series: str = ""; game_time: str = "TBD"
        bankroll: float = 1000.0; sport: str = "NBA"

    @app.get("/")
    def root():
        return {
            "message": "Sports TC v8 — TC Match + v8 Game Total",
            "models": {
                "tc_match": "Player props: PTS×0.85/REB×0.80/AST×0.75/3PM×0.70 + GAP",
                "game_total_v8": "Raw pts × star_mult + bench_diff + home_court (separate from TC Match)",
            },
            "endpoints": ["/health", "/teams", "/backtest", "/project"],
        }

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "8.0.0",
                "tc_rule": "TC Match = player props only | Game Total = v8 calibration"}

    @app.get("/teams")
    def list_teams(sport: str = "NBA"):
        return {abbr: t.name for abbr, t in get_teams(sport).items()}

    @app.get("/backtest")
    def backtest(sport: str = "NBA"):
        return run_backtest(sport)

    @app.post("/project")
    def project(req: GameRequest):
        try:
            return project_game(req.home, req.away, req.market_total,
                                req.market_spread, req.series, req.game_time,
                                req.bankroll, req.sport)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sports TC v8 Engine")
    parser.add_argument("--sport", default="NBA", choices=["NBA", "WNBA"])
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--game", type=str, help="'AWAY @ HOME'")
    parser.add_argument("--total", type=float, default=210.5)
    parser.add_argument("--spread", type=float, default=-5.0)
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--list-teams", action="store_true")
    args = parser.parse_args()

    if args.backtest:
        print(json.dumps(run_backtest(args.sport), indent=2))
    elif args.list_teams:
        for abbr, team in get_teams(args.sport).items():
            print(f"{abbr}: {team.name}")
            for n in team.injury_notes:
                print(f"   {n}")
    elif args.game:
        parts = args.game.split("@")
        if len(parts) < 2:
            print("Usage: --game 'AWAY @ HOME'")
            raise SystemExit(1)
        away = parts[0].strip().upper()
        home = parts[1].strip().upper()
        result = project_game(home, away, args.total, args.spread,
                              series="CLI", game_time="CLI",
                              bankroll=args.bankroll, sport=args.sport)
        print(json.dumps(result, indent=2))
    else:
        print("Options: --backtest | --game 'AWAY @ HOME' | --list-teams")
        print("API:    uvicorn tc_engine:app --host 0.0.0.0 --port 8001")