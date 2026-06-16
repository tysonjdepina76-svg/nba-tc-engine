"""
tc_engine.py — Triple Conservative Player Prop Engine
=====================================================
Unified NBA + WNBA TC engine. Single source of truth.

CRITICAL RULE:
    TC MATCH DOES NOT APPLY TO TEAM TOTALS.
    TC Match is ONLY for individual player prop support lines:
        - Points
        - Rebounds
        - Assists
        - 3-point shots made

Player Prop TC Formula:
    TC_PTS = pts × 0.85 × status_factor + GAP_PTS
    TC_REB = reb × 0.80 × status_factor + GAP_REB
    TC_AST = ast × 0.75 × status_factor + GAP_AST
    TC_3PM = tpm × 0.70 × status_factor + GAP_3PM

    status_factor: ACTIVE×1.0 | Q×0.55 | OUT×0.0
    Edge = TC_stat − market_prop_line

Team/Game Total Rule:
    Team totals and game totals use raw point projections only.
    They DO NOT use TC Match, prop gaps, W_FACTOR, or player prop TC support lines.
    Game totals are informational unless a separate totals model is added.

Usage:
    python tc_engine.py --backtest
    python tc_engine.py --game "PHI @ BOS" --total 208.5 --spread -11.5
    python tc_engine.py --list-teams
    python tc_engine.py --sport WNBA --game "MIN @ DAL"

API:
    uvicorn tc_engine:app --host 0.0.0.0 --port 8001
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import argparse
import csv
import json
import math
import re
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

CONS_PTS   = 0.85   # player prop points support weight
CONS_REB   = 0.80   # player prop rebounds support weight
CONS_AST   = 0.75   # player prop assists support weight
CONS_3PM   = 0.70   # player prop 3PM support weight
LINE_FACTOR= 0.88   # retained for legacy display only; NOT used for team totals
Q_FACTOR   = 0.55   # questionable status reduction
OUT_FACTOR = 0.0    # out status = zero contribution
MIN_EDGE   = 1.0    # minimum prop edge to consider

GAP_PTS    = -3.0
GAP_REB    = -1.5
GAP_AST    = -1.0
GAP_3PM    = -0.8

# Legacy calibration values retained for audit compatibility only.
# DO NOT use W_FACTOR for team/game totals.
W_FACTOR   = {"NBA": 0.912, "WNBA": 0.934}

KELLY_FRAC = 0.50   # Kelly fraction for stake sizing
MIN_HR     = 0.57   # minimum hit-rate threshold

# Odds lookup for standard -110 / +260
ODDS = {"standard": -110, "parlay_2": -110, "parlay_3": +260}

# Required schema for saved prop projections/backtests. Future projection files
# should preserve these columns so final box-score grading is automatic.
BACKTEST_SCHEMA_FIELDS = [
    "date", "league", "game_id", "team", "player", "stat",
    "tc", "target", "pick", "actual", "result", "source",
]
PROP_STATS = {"PTS", "REB", "AST", "3PM"}

# ── Stat Leader Symbol Key ─────────────────────────────────────────────────
# Applies to both NBA and WNBA roster/projection printouts. A player can carry
# more than one symbol. Leaders are determined within each team roster using raw
# season averages.
LEADER_SYMBOLS = {
    "pts": "♛",   # Points leader
    "reb": "◆",   # Rebounds leader
    "ast": "✚",   # Assists leader
    "3pm": "●",   # 3-point shots made leader
    "blk": "▣",   # Blocks leader
    "stl": "✦",   # Steals leader
}

def leader_symbol_key() -> dict:
    return {
        "♛": "points leader",
        "◆": "rebounds leader",
        "✚": "assists leader",
        "●": "3PM leader",
        "▣": "blocks leader",
        "✦": "steals leader",
    }

# ── Live WNBA Integration ───────────────────────────────────────────────────
# WNBA rosters should come from live ESPN API when available. The TC match math
# remains prop-only: PTS/REB/AST/3PM. Game/team totals remain raw-point info only.
WNBA_LIVE_ENABLED = True

def _team_name_from_abbr(abbr: str) -> str:
    names = {
        "ATL":"Atlanta Dream", "CHI":"Chicago Sky", "CON":"Connecticut Sun",
        "DAL":"Dallas Wings", "GS":"Golden State Valkyries", "IND":"Indiana Fever",
        "LV":"Las Vegas Aces", "LVA":"Las Vegas Aces", "LA":"Los Angeles Sparks",
        "LAS":"Los Angeles Sparks", "MIN":"Minnesota Lynx", "NY":"New York Liberty",
        "NYL":"New York Liberty", "PHX":"Phoenix Mercury", "POR":"Portland Fire",
        "SEA":"Seattle Storm", "TOR":"Toronto Tempo", "WSH":"Washington Mystics",
    }
    return names.get(abbr.upper(), abbr.upper())

def _normalize_wnba_abbr(abbr: str) -> str:
    value = (abbr or "").upper().strip()
    return {"LVA":"LV", "LAS":"LA", "NYL":"NY"}.get(value, value)

def _live_wnba_team(abbr: str):
    """Return a Team from the corrected ESPN-powered WNBA live engine.

    TC math remains prop-only. This function only supplies current roster,
    injury/status, and ESPN-derived player averages for PTS/REB/AST/3PM.
    """
    if not WNBA_LIVE_ENABLED:
        return None
    code = _normalize_wnba_abbr(abbr)
    try:
        from wnba_tc_live_engine import fetch_roster
        live_players = fetch_roster(code)
        players = []
        notes = []
        for lp in live_players:
            status = getattr(lp, "status", "ACTIVE") or "ACTIVE"
            name = getattr(lp, "name", "Unknown")
            if status != "ACTIVE":
                notes.append(f"{name} {status}")
            players.append(Player(
                name=name,
                pos=str(getattr(lp, "pos", "")),
                ht=str(getattr(lp, "ht", "")),
                pts=float(getattr(lp, "pts", 0.0) or 0.0),
                reb=float(getattr(lp, "reb", 0.0) or 0.0),
                ast=float(getattr(lp, "ast", 0.0) or 0.0),
                tpm=float(getattr(lp, "tpm", 0.0) or 0.0),
                status=status,
            ))
        if players:
            return Team(code, _team_name_from_abbr(code), players, notes)
    except Exception as exc:
        print(f"[WNBA live roster fallback] {code}: {exc}")
        return None
    return None

# ── Data Models ─────────────────────────────────────────────────────────────

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

    def status_factor(self) -> float:
        return {"ACTIVE": 1.0, "Q": Q_FACTOR, "OUT": OUT_FACTOR}.get(self.status, 1.0)

    def raw_stat(self, stat: str) -> float:
        stat = stat.lower()
        if stat in ("pts", "points"):
            return self.pts
        if stat in ("reb", "rebounds"):
            return self.reb
        if stat in ("ast", "assists"):
            return self.ast
        if stat in ("3pm", "tpm", "threes"):
            return self.tpm
        raise ValueError(f"Unknown prop stat: {stat}")

    def tc_prop(self, stat: str) -> float:
        """TC support line for individual player props only."""
        factor = self.status_factor()
        stat = stat.lower()
        if stat in ("pts", "points"):
            return round(max(0.0, self.pts * CONS_PTS * factor + GAP_PTS), 1)
        if stat in ("reb", "rebounds"):
            return round(max(0.0, self.reb * CONS_REB * factor + GAP_REB), 1)
        if stat in ("ast", "assists"):
            return round(max(0.0, self.ast * CONS_AST * factor + GAP_AST), 1)
        if stat in ("3pm", "tpm", "threes"):
            return round(max(0.0, self.tpm * CONS_3PM * factor + GAP_3PM), 1)
        raise ValueError(f"Unknown prop stat: {stat}")

    def tc_pts(self) -> float:
        return self.tc_prop("pts")

    def tc_reb(self) -> float:
        return self.tc_prop("reb")

    def tc_ast(self) -> float:
        return self.tc_prop("ast")

    def tc_3pm(self) -> float:
        return self.tc_prop("3pm")

    def raw_points_for_total(self) -> float:
        """Raw point projection for team/game totals. No TC Match applied."""
        return round(self.pts * self.status_factor(), 1)

    def prop_dict(self, market_lines: Optional[Dict[str, float]] = None) -> dict:
        market_lines = market_lines or {}
        out = {
            "name": self.name, "pos": self.pos, "ht": self.ht, "status": self.status,
            "raw": {"pts": self.pts, "reb": self.reb, "ast": self.ast, "3pm": self.tpm},
            "tc": {"pts": self.tc_pts(), "reb": self.tc_reb(), "ast": self.tc_ast(), "3pm": self.tc_3pm()},
        }
        edges = {}
        for stat in ("pts", "reb", "ast", "3pm"):
            if stat in market_lines:
                edges[stat] = round(out["tc"][stat] - float(market_lines[stat]), 1)
        if edges:
            out["edge"] = edges
        return out

    def as_dict(self) -> dict:
        return self.prop_dict()

@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]
    injury_notes: List[str] = field(default_factory=list)

    def prop_tc_totals(self) -> Dict[str, float]:
        """Aggregate player prop support only. Not a team total model."""
        return {
            "pts": round(sum(p.tc_pts() for p in self.players), 1),
            "reb": round(sum(p.tc_reb() for p in self.players), 1),
            "ast": round(sum(p.tc_ast() for p in self.players), 1),
            "3pm": round(sum(p.tc_3pm() for p in self.players), 1),
        }

    def raw_points_total(self) -> float:
        """Team total estimate from raw points only. No TC Match."""
        return round(sum(p.raw_points_for_total() for p in self.players), 1)

    def raw_starters_points(self) -> float:
        return round(sum(p.raw_points_for_total() for p in self.players[:5]), 1)

    def raw_bench_points(self) -> float:
        return round(sum(p.raw_points_for_total() for p in self.players[5:]), 1)

    def tc_total(self) -> float:
        """Legacy alias: aggregate TC PTS props, not team total."""
        return self.prop_tc_totals()["pts"]

    def tc_starters(self) -> float:
        return round(sum(p.tc_pts() for p in self.players[:5]), 1)

    def bench_total(self) -> float:
        return round(sum(p.tc_pts() for p in self.players[5:]), 1)

    def active_players(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"]

    def leader_flags(self) -> Dict[str, str]:
        leaders: Dict[str, str] = {}
        active = [p for p in self.players if p.status != "OUT"]
        if not active:
            return leaders
        stat_getters = {
            "pts": lambda p: p.pts,
            "reb": lambda p: p.reb,
            "ast": lambda p: p.ast,
            "3pm": lambda p: p.tpm,
            # Blocks/steals are not always present in older static roster rows.
            # They are included in the symbol key and can be hydrated by live data.
            "blk": lambda p: float(getattr(p, "blk", 0.0) or 0.0),
            "stl": lambda p: float(getattr(p, "stl", 0.0) or 0.0),
        }
        for stat, getter in stat_getters.items():
            top = max(getter(p) for p in active)
            if top <= 0:
                continue
            for p in active:
                if getter(p) == top:
                    leaders[p.name] = leaders.get(p.name, "") + LEADER_SYMBOLS[stat]
        return leaders

    def as_dict(self) -> dict:
        return {
            "abbr":    self.abbr,
            "name":    self.name,
            "raw_points_total": self.raw_points_total(),
            "raw_starters_points": self.raw_starters_points(),
            "raw_bench_points": self.raw_bench_points(),
            "prop_tc_totals": self.prop_tc_totals(),
            "players":    [dict(p.as_dict(), leaders=self.leader_flags().get(p.name, "")) for p in self.players],
            "injury_notes": self.injury_notes,
        }

# ── Rosters ─────────────────────────────────────────────────────────────────

def _P(name, pos, ht, pts, reb, ast, tpm, status="ACTIVE"):
    return Player(name, pos, ht, pts, reb, ast, tpm, status)

# ── NBA Teams ───────────────────────────────────────────────────────────────

NBA_TEAMS: Dict[str, Team] = {

    "PHI": Team("PHI", "Philadelphia 76ers", [
        _P("Joel Embiid",      "C",  "7-0",  34.0, 10.5, 4.5, 1.8, "OUT"),
        _P("Paul George",      "F",  "6-8",  22.0,  5.5, 3.5, 2.5, "OUT"),
        _P("Tyrese Maxey",     "G",  "6-2",  26.5,  4.0, 6.0, 2.2),
        _P("Kelly Oubre Jr.",  "F",  "6-7",  18.5,  5.5, 2.0, 1.8),
        _P("Jared McCain",     "G",  "6-3",  15.5,  3.5, 2.5, 2.5),
        _P("Andre Drummond",   "C",  "6-10", 9.5,  10.0, 2.0, 0.0),
        _P("Kyle Lowry",       "G",  "6-0",   8.0,  3.0, 5.0, 1.5),
        _P("Reggie Jackson",   "G",  "6-3",   9.5,  2.5, 4.5, 1.5),
        _P("KJ Martin",        "F",  "6-7",   7.5,  3.0, 1.0, 0.8),
        _P("Justin Edwards",   "F",  "6-8",   7.0,  2.5, 1.0, 0.5),
    ], ["Joel Embiid OUT (knee)", "Paul George OUT (ankle)"]),

    "BOS": Team("BOS", "Boston Celtics", [
        _P("Jayson Tatum",       "F",  "6-8", 28.5,  7.5, 5.0, 2.9),
        _P("Jaylen Brown",        "G",  "6-6", 24.5,  5.5, 4.0, 2.2),
        _P("Kristaps Porzingis", "C",  "7-1", 20.0,  7.0, 2.5, 2.8, "Q"),
        _P("Derrick White",       "G",  "6-4", 16.5,  4.0, 5.0, 2.5),
        _P("Jrue Holiday",        "G",  "6-4", 14.5,  5.0, 6.0, 1.8),
        _P("Al Horford",          "F",  "6-9", 12.5,  6.0, 3.5, 2.0),
        _P("Payton Pritchard",   "G",  "6-1", 11.5,  3.0, 3.5, 2.8),
        _P("Luke Kornet",         "C",  "7-0",  8.0,  5.0, 2.0, 0.5),
        _P("Sam Hauser",          "F",  "6-8",  7.5,  3.0, 1.5, 1.5),
        _P("Baylor Scheinman",   "F",  "6-9",  5.5,  3.0, 2.0, 0.8),
    ], ["Kristaps Porzingis Q (illness)"]),

    "DEN": Team("DEN", "Denver Nuggets", [
        _P("Nikola Jokic",         "C",  "6-11", 29.5, 12.5, 10.0, 1.8),
        _P("Jamal Murray",          "G",  "6-4",  22.0,  4.5,  6.0, 2.0),
        _P("Michael Porter Jr.",   "F",  "6-10", 18.5,  6.5,  2.0, 2.5),
        _P("Aaron Gordon",          "F",  "6-9",  16.5,  6.0,  3.0, 1.2),
        _P("Russell Westbrook",     "G",  "6-3",  12.5,  5.0,  6.5, 1.5),
        _P("Christian Braun",      "G",  "6-6",  11.5,  4.5,  2.5, 1.2),
        _P("Peyton Watson",        "F",  "6-8",   8.5,  3.5,  1.5, 0.8),
        _P("Zeke Nnaji",            "C",  "6-11",  6.5,  3.5,  0.5, 0.3),
        _P("Julian Strawther",     "G",  "6-6",   7.0,  2.5,  1.5, 1.0),
        _P("Hunter Tyson",         "F",  "6-8",   5.5,  3.0,  1.0, 0.5),
    ], []),

    "LAC": Team("LAC", "LA Clippers", [
        _P("James Harden",        "G",  "6-5",  21.0,  5.5,  8.5, 2.5),
        _P("Kawhi Leonard",       "F",  "6-7",  22.0,  6.0,  3.5, 2.0, "OUT"),
        _P("Norman Powell",       "G",  "6-5",  21.5,  3.5,  2.5, 3.2),
        _P("Ivica Zubac",          "C",  "7-0",  15.5, 10.5,  2.0, 0.0),
        _P("Derrick Jones Jr.",   "F",  "6-6",  10.5,  4.0,  1.5, 1.2),
        _P("Nicolas Batum",       "F",  "6-8",   8.0,  4.0,  2.5, 1.5),
        _P("Bones Hyland",         "G",  "6-3",  12.0,  3.0,  3.5, 2.2),
        _P("Kevin Brown",          "F",  "6-7",   8.5,  4.5,  2.0, 1.0),
        _P("Mo Bamba",            "C",  "7-0",   6.5,  5.5,  1.0, 0.8),
        _P("Kris Dunn",            "G",  "6-4",   7.5,  2.5,  4.0, 0.8),
    ], ["Kawhi Leonard OUT (knee)"]),

    "ORL": Team("ORL", "Orlando Magic", [
        _P("Paolo Banchero",      "F",  "6-10", 25.0,  7.0,  4.5, 2.0, "Q"),
        _P("Franz Wagner",        "F",  "7-0",  22.0,  5.0,  4.0, 1.8, "OUT"),
        _P("Jalen Suggs",          "G",  "6-5",  16.5,  4.0,  4.5, 1.5),
        _P("Wendell Carter Jr.",  "C",  "6-6",  14.5,  9.0,  2.5, 0.8),
        _P("Cole Anthony",        "G",  "6-2",  13.0,  4.5,  3.5, 1.2),
        _P("Goga Bitadze",         "C",  "6-11", 10.5,  6.0,  2.0, 0.5),
        _P("Jonathan Isaac",      "F",  "6-10",  6.5,  4.0,  1.0, 0.5),
        _P("Caleb Houstan",       "F",  "6-8",   7.0,  3.0,  1.5, 0.8),
        _P("Joe Ingles",           "F",  "6-8",   6.0,  2.5,  3.5, 1.2),
        _P("Admiral Schofield",   "G",  "6-5",   5.5,  2.0,  1.0, 0.8),
    ], ["Franz Wagner OUT (calf)", "Paolo Banchero Q (ankle)"]),

    "DET": Team("DET", "Detroit Pistons", [
        _P("Cade Cunningham",     "G",  "6-7",  25.5,  6.5,  9.5, 2.0),
        _P("Jaden Ivey",           "G",  "6-5",  18.0,  4.5,  4.5, 1.8),
        _P("Tim Hardaway Jr.",    "F",  "6-6",  15.5,  4.5,  2.5, 2.5),
        _P("Jalen Duren",         "C",  "6-11", 13.5,  9.5,  2.5, 0.0),
        _P("Isaiah Stewart",       "F",  "6-8",  12.5,  8.0,  2.0, 1.2),
        _P("Ausar Thompson",       "G",  "6-7",  11.5,  5.0,  4.5, 0.8),
        _P("Dorion Murray",        "G",  "6-5",  10.5,  3.5,  2.5, 1.5),
        _P("Tobias Harris",       "F",  "6-8",   9.5,  4.5,  3.0, 1.0),
        _P("Dennis Schröder",     "G",  "6-1",  13.5,  2.5,  6.5, 1.8),
        _P("Simone Fontecchio",   "F",  "6-8",   8.5,  3.5,  1.5, 1.2),
    ], []),

    "POR": Team("POR", "Portland Trail Blazers", [
        _P("Scoot Henderson",    "G",  "6-3",  18.5,  4.5,  7.5, 1.5),
        _P("Anfernee Simons",     "G",  "6-5",  21.5,  3.5,  4.5, 3.0),
        _P("Jerami Grant",        "F",  "6-8",  18.0,  5.0,  2.5, 2.2),
        _P("Deandre Ayton",       "C",  "7-0",  16.5, 10.0,  2.0, 0.0),
        _P("Toukam Saop",         "F",  "6-9",  15.5,  7.5,  2.5, 1.2),
        _P("Shaedon Sharpe",      "G",  "6-6",  15.0,  4.0,  2.5, 2.0),
        _P("Rayan Rupert",        "G",  "6-7",   8.5,  3.0,  2.0, 1.2),
        _P("Kris Murray",         "F",  "6-8",   8.0,  3.5,  1.5, 0.8),
        _P("Jabari Walker",       "F",  "6-6",   7.5,  5.0,  1.0, 0.8),
        _P("Duop Reath",          "C",  "6-10",  9.5,  4.5,  1.0, 0.5),
    ], []),

    "SA": Team("SA", "San Antonio Spurs", [
        _P("Victor Wembanyama", "F", "7-4", 27.5, 10.5, 4.0, 3.2),
        _P("Chris Paul",         "G", "6-0", 12.0,  4.0, 8.5, 1.5),
        _P("Devin Vassell",      "G", "6-6", 19.5,  4.5, 3.5, 2.8),
        _P("Jeremy Sochan",      "F", "6-9", 14.0,  6.5, 3.5, 1.0),
        _P("Keldon Johnson",     "F", "6-6", 16.5,  5.5, 2.5, 2.2),
        _P("Zach Collins",       "C", "7-0", 11.5,  6.5, 3.0, 0.8),
        _P("Devonte Graham",      "G", "6-2", 10.0,  2.5, 4.5, 2.0),
        _P("Doug McDermott",     "F", "6-8",  9.5,  3.0, 1.5, 1.5),
        _P("Malo Malos",         "G", "6-5",  8.5,  3.0, 2.5, 0.8),
        _P("Seth Curry",         "G", "6-2",  9.5,  2.0, 2.0, 1.8),
    ], []),
    "OKC": Team("OKC", "Oklahoma City Thunder", [
        _P("Shai Gilgeous-Alexander", "G", "6-6", 32.0, 5.0, 6.5, 2.8),
        _P("Chet Holmgren",           "C", "7-1", 16.0, 8.0, 2.5, 1.0),
        _P("Jalen Williams",          "F", "6-6", 18.5, 5.5, 4.0, 1.5),
        _P("Luguentz Dort",           "G", "6-4",  9.5, 3.5, 1.2, 2.0),
        _P("Isaiah Hartenstein",      "C", "7-0",  8.0, 7.5, 2.5, 0.2),
        _P("Alex Caruso",             "G", "6-5",  6.0, 2.5, 2.0, 1.2),
        _P("Isaiah Joe",              "G", "6-3",  9.0, 2.0, 0.8, 2.1),
        _P("Cason Wallace",           "G", "6-4",  8.5, 2.5, 1.5, 1.8),
        _P("Aaron Wiggins",           "G", "6-6",  7.5, 2.0, 1.0, 1.2),
        _P("Kenrich Williams",        "F", "6-7",  7.5, 5.0, 2.0, 1.2),
    ], []),

}

# ── WNBA Teams ───────────────────────────────────────────────────────────────

WNBA_TEAMS: Dict[str, Team] = {

    "MIN": Team("MIN", "Minnesota Lynx", [
        _P("Napheesa Collier", "F", "6-1", 20.0, 6.5, 3.5, 1.8),
        _P("Alana Smith",      "G", "5-9", 14.5, 3.5, 5.5, 1.5, "Q"),
        _P("Kayla McBride",    "G", "5-11",16.0, 4.0, 4.0, 2.8),
        _P("Sylvia Fowles",    "C", "6-6", 15.5,10.0, 2.0, 0.0),
        _P("Crystal Dangerfield","G","5-5", 12.0, 3.0, 3.5, 1.2),
        _P("Natalie Achonwu",  "C", "6-5",  9.5, 7.0, 2.0, 0.5),
        _P("Olivia Olu",       "F", "6-2",  7.0, 4.0, 1.5, 1.0),
        _P("Tiffany Mitchell", "G", "5-10", 9.0, 2.5, 3.0, 1.2),
        _P("Nizhoni Cowboy",   "F", "6-3",  6.5, 4.0, 1.0, 0.8),
        _P("Khayla Vazien",    "G", "5-8",  5.0, 2.0, 3.5, 0.8),
    ], ["Alana Smith Q (ankle)"]),

    "DAL": Team("DAL", "Dallas Wings", [
        _P("Arielle Wiggins",  "F", "6-4", 17.0, 6.0, 2.5, 1.2),
        _P("Satou Sabally",    "F", "6-4", 18.5, 7.5, 4.0, 2.0, "Q"),
        _P("Odyssey Sims",     "G", "5-8", 15.0, 3.5, 6.0, 1.5),
        _P("Teaira McCowan",   "C", "7-0", 16.0,11.0, 1.5, 0.0),
        _P("Crystal Dangerfield","G","5-5", 11.5, 2.5, 3.5, 1.0),
        _P("Moriah Jefferson", "G", "5-7", 10.0, 2.0, 5.5, 1.2),
        _P("Natasha Howard",    "F", "6-4", 14.0, 6.5, 2.0, 1.0, "OUT"),
        _P("Joyner Woods",     "G", "5-10", 8.5, 2.5, 3.0, 1.2),
        _P("Aaliyah Wilson",    "G", "6-0",  6.0, 3.0, 2.0, 0.8),
        _P("Jade Melbourne",   "G", "5-9",  5.5, 2.0, 2.5, 0.8),
    ], ["Satou Sabally Q (hip)", "Natasha Howard OUT (knee)"]),

    "NYL": Team("NYL", "New York Liberty", [
        _P("Breanna Stewart",  "F", "6-4", 23.0, 9.0, 4.0, 2.5),
        _P("Jonquel Jones",    "C", "6-6", 18.5, 9.5, 3.5, 1.8),
        _P("Sabrina Ionescu",  "G", "5-11",20.5, 5.0, 7.5, 3.2),
        _P("Kayla Thornton",   "F", "6-2", 11.0, 5.5, 2.5, 1.5),
        _P("Svetlana Petrov",  "G", "5-10",10.0, 3.5, 4.5, 1.8),
        _P("JiSu Park",        "C", "6-5", 10.5, 7.0, 1.5, 0.5),
        _P("Marine Johannès",  "G", "6-0", 11.5, 3.0, 4.0, 2.2),
        _P("Michele Taylor",   "F", "6-3",  7.5, 4.0, 1.5, 1.0),
        _P("Nadiya",           "G", "5-9",  5.0, 2.0, 3.0, 0.8),
        _P("Kaleai",           "F", "6-2",  5.5, 3.5, 1.0, 0.5),
    ], []),

    "LVA": Team("LVA", "Las Vegas Aces", [
        _P("A'ja Wilson",      "F", "6-4", 25.0,10.5, 3.5, 1.5),
        _P("Chelsea Gray",     "G", "5-11",17.5, 4.0, 6.5, 2.0),
        _P("Kia Wilson",        "G", "5-8", 15.0, 3.5, 5.0, 2.5),
        _P("Candace Parker",    "F", "6-4", 14.5, 8.0, 4.5, 1.2),
        _P("Dearica Hamby",    "F", "6-2", 13.0, 7.5, 3.0, 1.5),
        _P("Jasmine Thomas",   "G", "5-8",  9.5, 2.5, 5.0, 1.8),
        _P("Sydney Colson",    "G", "5-8",  6.0, 2.0, 4.0, 1.0),
        _P("Kamera Conrad",    "F", "6-2",  7.5, 4.5, 1.5, 0.8),
        _P("Cayla George",     "F", "6-4",  8.0, 5.0, 2.0, 1.2),
        _P("Queen Al",         "C", "6-6",  6.5, 5.5, 1.0, 0.5),
    ], []),

    "CON": Team("CON", "Connecticut Sun", [
        _P("Alyssa Thomas",    "F", "6-3", 16.0, 8.5, 7.5, 1.0),
        _P("DeWanna Bonner",   "F", "6-4", 18.0, 7.0, 4.0, 2.0),
        _P("Brionna Jones",    "C", "6-3", 14.5, 7.5, 2.0, 0.8),
        _P("Natasha Cloud",     "G", "5-11",12.0, 3.5, 6.0, 1.5),
        _P("Megan McKenna",    "G", "5-10",10.5, 2.5, 4.5, 2.0),
        _P("Ellienne",         "F", "6-2",  7.0, 4.0, 1.5, 1.0),
        _P("Lindsay Wisdom",   "C", "6-5",  8.5, 5.5, 1.5, 0.5),
        _P("Jasmine Nwajei",   "G", "5-9",  6.5, 2.0, 2.5, 1.2),
        _P("Paige Tolowan",   "F", "6-2",  5.5, 3.5, 1.0, 0.8),
        _P("Diana",            "G", "5-8",  5.0, 2.0, 3.0, 0.8),
    ], []),

    "SEA": Team("SEA", "Seattle Storm", [
        _P("Sue Bird",         "G", "5-9", 14.0, 3.0, 7.0, 2.5),
        _P("Natasha Howard",    "F", "6-4", 17.5, 8.0, 3.5, 1.8),
        _P("Ezi Magbegor",     "C", "6-5", 15.0, 8.5, 2.0, 1.0),
        _P("Jillian",          "G", "5-11",13.0, 4.0, 5.0, 1.8),
        _P("Mercedes",         "F", "6-3", 10.5, 5.5, 2.5, 1.5),
        _P("Kennedy",          "G", "5-10", 9.0, 2.5, 4.0, 1.2),
        _P("Satou",            "F", "6-3",  7.5, 4.5, 1.5, 1.0),
        _P("Kylie",            "G", "5-9",  6.0, 2.0, 3.5, 0.8),
        _P("Arike",            "G", "5-7",  8.5, 2.0, 3.0, 1.5),
        _P("Lily",             "C", "6-4",  5.5, 4.5, 1.0, 0.5),
    ], []),

    "IND": Team("IND", "Indiana Fever", [
        _P("Aliyah Boston",    "F", "6-5", 17.0, 9.5, 2.5, 0.8),
        _P("Caitlin Clark",    "G", "6-0", 22.5, 5.5, 8.5, 3.5),
        _P("NaLyssa Smith",    "F", "6-2", 15.0, 7.0, 2.0, 1.2),
        _P(" Kelsey Mitchell",  "G", "5-8", 18.0, 3.5, 3.5, 2.5),
        _P("Miriam",           "F", "6-3", 10.5, 5.5, 1.5, 0.8),
        _P(" Erika",           "C", "6-4",  9.0, 6.5, 1.5, 0.5),
        _P("Lexie",            "G", "5-9",  7.5, 2.5, 3.5, 1.2),
        _P("Jade",             "G", "5-8",  8.0, 2.0, 4.0, 1.5),
        _P("Khayla",           "F", "6-2",  6.5, 4.0, 1.0, 0.8),
        _P("Jillian",          "G", "5-10", 5.5, 2.0, 3.0, 0.8),
    ], []),
}

# ── Team Registry ─────────────────────────────────────────────────────────────

TEAM_REGISTRY = {"NBA": NBA_TEAMS, "WNBA": WNBA_TEAMS}

def get_teams(sport: str) -> Dict[str, Team]:
    return TEAM_REGISTRY.get(sport.upper(), NBA_TEAMS)

def get_team(abbr: str, sport: str = "NBA") -> Team:
    sport = sport.upper()
    abbr = abbr.upper().strip()
    if sport == "WNBA":
        live = _live_wnba_team(abbr)
        if live is not None:
            return live
        abbr = _normalize_wnba_abbr(abbr)
    teams = get_teams(sport)
    if abbr not in teams:
        raise ValueError(f"Unknown {sport} team: {abbr}. Available: {list(teams.keys())}")
    return teams[abbr]

# ── TC Core Math ──────────────────────────────────────────────────────────────

def calc_tc(player: Player) -> float:
    """Single-player TC points."""
    return player.tc_pts()

def calc_team_tc(team: Team) -> Dict[str, float]:
    """Legacy aggregate of player prop TC support. Not a team total model."""
    return team.prop_tc_totals()

def calc_game_total_raw(home: Team, away: Team) -> float:
    """Game total estimate from raw point projections only. No TC Match."""
    return round(home.raw_points_total() + away.raw_points_total(), 1)

def _hit_rate(edge: float, hr_tiers=None) -> float:
    """Convert edge gap to hit-rate probability."""
    if hr_tiers is None:
        hr_tiers = ((10, 0.72), (7, 0.68), (5, 0.64), (3, 0.60), (0, 0.57))
    for threshold, rate in hr_tiers:
        if abs(edge) >= threshold:
            return rate
    return 0.57

def _kelly(bankroll: float, edge: float, odds: int = -110,
           fraction: float = KELLY_FRAC) -> float:
    """Kelly stake = bankroll × Kelly fraction."""
    if edge <= 0:
        return 0.0
    b = abs(odds) / 100 if odds > 0 else 100 / abs(odds)
    p = min(0.72, 0.52 + min(edge, 10) * 0.02)
    q  = 1 - p
    kelly = (b * p - q) / b if b > 0 else 0.0
    return round(max(0.0, bankroll * kelly * fraction), 2)

# ── Game Projection ──────────────────────────────────────────────────────────

def calc_game(
    home: Team,
    away: Team,
    market_total: float,
    market_spread: float,
    sport: str = "NBA",
) -> Dict[str, Any]:
    """
    Full game projection.

    IMPORTANT:
    - Player prop TC support lines are included by player for PTS/REB/AST/3PM.
    - TC Match is NOT used for game totals, team totals, spread, or ML.
    - Game total output is raw projected points only and is informational.
    """
    home_raw_points = home.raw_points_total()
    away_raw_points = away.raw_points_total()
    raw_game_total = round(home_raw_points + away_raw_points, 1)
    total_gap = round(raw_game_total - market_total, 1)

    home_prop_tc = home.prop_tc_totals()
    away_prop_tc = away.prop_tc_totals()

    spread_raw = round(home_raw_points - away_raw_points, 1)
    spread_abs = abs(market_spread)
    raw_favored = "HOME" if spread_raw > 0 else "AWAY" if spread_raw < 0 else "PICK"
    spread_lean = "HOME" if spread_raw > spread_abs else (
                  "AWAY" if spread_raw < -spread_abs else "PASS")

    return {
        "home": home.as_dict(),
        "away": away.as_dict(),
        "game_total": {
            "model": raw_game_total,
            "market": market_total,
            "gap": total_gap,
            "note": "Raw point projection only. TC Match does not apply to totals.",
        },
        "raw_points": {"home": home_raw_points, "away": away_raw_points, "combined": raw_game_total},
        "prop_tc_totals": {"home": home_prop_tc, "away": away_prop_tc},
        "market_total": market_total,
        "tc_spread": spread_raw,
        "market_spread": market_spread,
        "spread_lean": spread_lean,
        "tc_favored": raw_favored,
    }

# ── Betting Stakes ────────────────────────────────────────────────────────────

def build_bets(
    home_abbr: str,
    away_abbr: str,
    market_total: float,
    market_spread: float,
    bankroll: float = 1000.0,
    sport: str = "NBA",
) -> Dict[str, Any]:
    """
    Build non-prop game notes only.

    No game-total bet is generated from TC Match. For prop betting, use the
    player-level `players` output and compare TC PTS/REB/AST/3PM to book lines.
    """
    home = get_team(home_abbr, sport)
    away = get_team(away_abbr, sport)
    proj = calc_game(home, away, market_total, market_spread, sport)
    return {
        "bankroll": bankroll,
        "total_stake": 0.0,
        "legs": [],
        "sport": sport,
        "note": "No game-total or spread bet created from TC Match. TC Match is prop-only.",
        "game_total_gap": proj["game_total"]["gap"],
        "spread_lean_raw_points_only": proj["spread_lean"],
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
) -> Dict[str, Any]:
    """Structured projection focused on player props for PTS/REB/AST/3PM."""
    home = get_team(home_abbr, sport)
    away = get_team(away_abbr, sport)
    proj = calc_game(home, away, market_total, market_spread, sport)
    bets = build_bets(home_abbr, away_abbr, market_total, market_spread, bankroll, sport)

    return {
        "meta": {
            "home": home_abbr.upper(),
            "away": away_abbr.upper(),
            "series": series,
            "game_time": game_time,
            "sport": sport,
            "tc_rule": "TC Match applies only to player props: PTS, REB, AST, 3PM.",
        },
        "game_total": proj["game_total"],
        "raw_points": proj["raw_points"],
        "prop_tc_totals": proj["prop_tc_totals"],
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
        "spread": {
            "raw_points_spread": proj["tc_spread"],
            "market_spread": market_spread,
            "lean_raw_points_only": proj["spread_lean"],
            "favored_raw_points_only": proj["tc_favored"],
        },
        "bets": bets,
    }

# ── Backtest ─────────────────────────────────────────────────────────────────

BACKTEST_GAMES = [
    # NBA Apr 19
    {"home": "BOS", "away": "PHI", "date": "2026-04-19",
     "market_total": 208.5, "market_spread": -11.5,
     "actual_total": 216, "actual_winner": "BOS"},
    {"home": "DEN", "away": "LAC", "date": "2026-04-19",
     "market_total": 216.5, "market_spread": -4.5,
     "actual_total": 222, "actual_winner": "DEN"},
    {"home": "DET", "away": "ORL", "date": "2026-04-19",
     "market_total": 200.5, "market_spread": -5.5,
     "actual_total": 207, "actual_winner": "DET"},
    {"home": "SA",  "away": "POR", "date": "2026-04-19",
     "market_total": 206.5, "market_spread": -8.5,
     "actual_total": 226, "actual_winner": "SA"},
]

def run_backtest(sport: str = "NBA") -> Dict[str, Any]:
    """
    Backtest wrapper kept operational for diagnostics.

    It does NOT validate TC Match against game totals because TC Match is prop-only.
    It records raw-point total direction separately as an informational check.
    """
    teams = get_teams(sport)
    results = []
    for g in BACKTEST_GAMES:
        home = teams[g["home"]]
        away = teams[g["away"]]
        proj = calc_game(home, away, g["market_total"], g["market_spread"], sport)

        model_total = proj["game_total"]["model"]
        gap = proj["game_total"]["gap"]
        actual = g["actual_total"]
        model_dir = "OVER" if model_total > g["market_total"] else "UNDER"
        actual_dir = "OVER" if actual > g["market_total"] else "UNDER"
        total_direction_hit = model_dir == actual_dir

        raw_spread = proj["tc_spread"]
        model_home_favored = raw_spread > 0
        actual_is_home = g["actual_winner"] == g["home"]
        spread_direction_hit = model_home_favored == actual_is_home

        results.append({
            "game": f"{g['away']} @ {g['home']}",
            "date": g["date"],
            "market_total": g["market_total"],
            "model_raw_total": model_total,
            "actual_total": actual,
            "gap_raw_vs_market": gap,
            "model_total_direction": model_dir,
            "actual_total_direction": actual_dir,
            "total_direction_hit": total_direction_hit,
            "raw_points_spread": raw_spread,
            "market_spread": g["market_spread"],
            "model_home_favored": model_home_favored,
            "actual_winner": g["actual_winner"],
            "spread_direction_hit": spread_direction_hit,
            "note": "TC Match not used for totals. This is raw point-model diagnostics only.",
        })

    n = len(results)
    total_dir_hr = round(sum(r["total_direction_hit"] for r in results) / n * 100, 1)
    spread_dir_hr = round(sum(r["spread_direction_hit"] for r in results) / n * 100, 1)
    avg_gap = round(sum(r["gap_raw_vs_market"] for r in results) / n, 1)

    return {
        "games": results,
        "summary": {
            "sport": sport,
            "total_games": n,
            "total_direction_hit_rate_raw_points_only": total_dir_hr,
            "spread_direction_hit_rate_raw_points_only": spread_dir_hr,
            "avg_gap_raw_points_vs_market": avg_gap,
            "tc_rule": "TC Match is prop-only and is not applied to game totals.",
        },
    }


# ── Reusable Prop Backtest Workflow ──────────────────────────────────────────

def _clean_name(value: str) -> str:
    """Normalize player names for projection ↔ box-score matching."""
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    suffixes = {"jr", "sr", "ii", "iii", "iv"}
    parts = [p for p in value.split() if p not in suffixes]
    return " ".join(parts)


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def _actual_from_box_row(row: Dict[str, Any], stat: str) -> Optional[float]:
    stat = stat.upper()
    aliases = {
        "PTS": ["pts", "PTS", "points", "Points"],
        "REB": ["reb", "REB", "rebounds", "Rebounds"],
        "AST": ["ast", "AST", "assists", "Assists"],
        "3PM": ["3pm", "3PM", "tpm", "TPM", "3pt", "three_pm"],
    }
    for key in aliases.get(stat, []):
        if key in row:
            val = _float_or_none(row.get(key))
            if val is not None:
                return val
    return None


def load_boxscore_csvs(boxscore_dir: str) -> Dict[tuple, Dict[str, Any]]:
    """Load all saved final box-score CSV rows from a directory tree.

    Keyed by (TEAM, normalized_player_name). Rows without player/team are skipped.
    """
    index: Dict[tuple, Dict[str, Any]] = {}
    root = Path(boxscore_dir)
    if not root.exists():
        return index
    for file in root.rglob("*.csv"):
        try:
            with file.open(newline="", encoding="utf-8", errors="ignore") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    team = (row.get("team") or row.get("Team") or "").upper().strip()
                    player = row.get("player") or row.get("Player") or row.get("name") or row.get("Name") or ""
                    norm = _clean_name(player)
                    if not team or not norm:
                        continue
                    row["source_file"] = str(file)
                    index[(team, norm)] = row
        except Exception:
            continue
    return index


def load_projection_csv(path: str) -> List[Dict[str, Any]]:
    """Load saved prop projections in the required schema.

    Required future columns:
    date, league, game_id, team, player, stat, tc, target, pick, actual, result, source
    Missing optional fields are filled so the grader remains backward-compatible.
    """
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            fixed = {field: row.get(field, "") for field in BACKTEST_SCHEMA_FIELDS}
            fixed.update(row)
            fixed["team"] = (fixed.get("team") or "").upper().strip()
            fixed["stat"] = (fixed.get("stat") or "").upper().strip()
            fixed["pick"] = (fixed.get("pick") or "").upper().strip()
            if fixed["stat"] in PROP_STATS:
                rows.append(fixed)
    return rows


def grade_prop_rows(projection_rows: List[Dict[str, Any]], boxscore_index: Dict[tuple, Dict[str, Any]]) -> Dict[str, Any]:
    """Grade prop projections against final box scores.

    DNP/MISSING rule:
    - If player is not found in the final box score, result = DNP/MISSING.
    - DNP/MISSING is NOT counted as a loss and NOT included in graded hit rate.
    """
    graded: List[Dict[str, Any]] = []
    hits = 0
    graded_count = 0
    by_stat: Dict[str, Dict[str, int]] = {s: {"hits": 0, "graded": 0} for s in sorted(PROP_STATS)}

    for row in projection_rows:
        team = (row.get("team") or "").upper().strip()
        player = row.get("player") or ""
        stat = (row.get("stat") or "").upper().strip()
        key = (team, _clean_name(player))
        box = boxscore_index.get(key)
        out = {field: row.get(field, "") for field in BACKTEST_SCHEMA_FIELDS}
        out["team"] = team
        out["player"] = player
        out["stat"] = stat

        if not box:
            out["actual"] = ""
            out["result"] = "DNP/MISSING"
            graded.append(out)
            continue

        actual = _actual_from_box_row(box, stat)
        target = _float_or_none(row.get("target"))
        pick = (row.get("pick") or "").upper().strip()
        out["actual"] = "" if actual is None else actual

        if actual is None or target is None or pick not in {"OVER", "UNDER"}:
            out["result"] = "UNGRADABLE"
            graded.append(out)
            continue

        hit = actual >= target if pick == "OVER" else actual <= target
        out["result"] = "HIT" if hit else "MISS"
        graded_count += 1
        by_stat.setdefault(stat, {"hits": 0, "graded": 0})["graded"] += 1
        if hit:
            hits += 1
            by_stat[stat]["hits"] += 1
        graded.append(out)

    return {
        "rows": graded,
        "summary": {
            "rows_total": len(graded),
            "graded": graded_count,
            "hits": hits,
            "hit_rate": round(hits / graded_count * 100, 1) if graded_count else 0.0,
            "dnp_missing": sum(1 for r in graded if r.get("result") == "DNP/MISSING"),
            "ungradable": sum(1 for r in graded if r.get("result") == "UNGRADABLE"),
            "by_stat": {
                stat: {
                    "hits": data["hits"],
                    "graded": data["graded"],
                    "hit_rate": round(data["hits"] / data["graded"] * 100, 1) if data["graded"] else 0.0,
                }
                for stat, data in by_stat.items()
            },
            "schema": BACKTEST_SCHEMA_FIELDS,
            "tc_rule": "TC Match is player props only: PTS, REB, AST, 3PM. Team/game totals are not TC Match.",
        },
    }


def save_prop_backtest_report(result: Dict[str, Any], out_path: str) -> str:
    """Save reusable markdown + CSV backtest report."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    csv_path = out.with_suffix(".csv")

    rows = result["rows"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=BACKTEST_SCHEMA_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in BACKTEST_SCHEMA_FIELDS})

    s = result["summary"]
    lines = [
        "# TC Prop Backtest Report",
        "",
        "## Schema repair applied",
        "- DNP/MISSING rows are not counted as losses.",
        "- Required saved fields: `date, league, game_id, team, player, stat, tc, target, pick, actual, result, source`.",
        "- TC Match applies only to player props: PTS, REB, AST, 3PM.",
        "- Team/game totals are not TC Match.",
        "",
        f"Rows total: {s['rows_total']}",
        f"Graded rows: {s['graded']}",
        f"DNP/MISSING: {s['dnp_missing']}",
        f"Ungradable: {s['ungradable']}",
        f"Hit rate: {s['hits']}/{s['graded']} = {s['hit_rate']}%",
        "",
        "## By stat",
        "| Stat | Hits | Graded | Hit Rate |",
        "|---|---:|---:|---:|",
    ]
    for stat, data in sorted(s["by_stat"].items()):
        lines.append(f"| {stat} | {data['hits']} | {data['graded']} | {data['hit_rate']}% |")
    lines.extend(["", "## Rows", "| Player | Team | Stat | TC | Target | Actual | Result | Source |", "|---|---|---:|---:|---:|---:|---|---|"])
    for row in rows:
        lines.append(
            f"| {row.get('player','')} | {row.get('team','')} | {row.get('stat','')} | {row.get('tc','')} | {row.get('target','')} | {row.get('actual','')} | {row.get('result','')} | {row.get('source','')} |"
        )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)

# ── FastAPI App ───────────────────────────────────────────────────────────────

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

app = FastAPI(title="TC Engine", version="1.0.0")

class GameRequest(BaseModel):
    home:          str
    away:          str
    market_total:  float
    market_spread: float
    series:        str = ""
    game_time:     str = "TBD"
    bankroll:      float = 1000.0
    sport:         str = "NBA"

@app.get("/")
def root():
    return {
        "message": "TC Engine API",
        "endpoints": ["/health", "/teams", "/backtest", "/project"],
    }

@app.get("/health")
def health():
    return {"status": "ok", "tc_rule": "TC Match applies only to player props: PTS, REB, AST, 3PM", "legacy_w_factor": W_FACTOR, "leader_symbols": leader_symbol_key()}

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

# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TC Engine CLI")
    parser.add_argument("--sport",   default="NBA", choices=["NBA", "WNBA"])
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--game",    type=str,
                        help="'AWAY @ HOME', e.g. 'PHI @ BOS'")
    parser.add_argument("--total",   type=float, default=210.5)
    parser.add_argument("--spread",  type=float, default=-5.0)
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--list-teams", action="store_true")
    parser.add_argument("--backtest-props", type=str, default="", help="CSV of saved prop projections to grade")
    parser.add_argument("--boxscores", type=str, default="live_sports_scrape", help="Directory containing final box-score CSV files")
    parser.add_argument("--out", type=str, default="tc-workspace/reports/prop_backtest_report.md", help="Backtest report output path")
    args = parser.parse_args()

    if args.backtest_props:
        rows = load_projection_csv(args.backtest_props)
        box = load_boxscore_csvs(args.boxscores)
        result = grade_prop_rows(rows, box)
        path = save_prop_backtest_report(result, args.out)
        print(json.dumps(result["summary"], indent=2))
        print(f"Saved: {path}")

    elif args.backtest:
        print(json.dumps(run_backtest(args.sport), indent=2))

    elif args.list_teams:
        for abbr, team in get_teams(args.sport).items():
            print(f"{abbr}: {team.name}")
            if team.injury_notes:
                for n in team.injury_notes:
                    print(f"   {n}")

    elif args.game:
        parts = args.game.split("@")
        if len(parts) < 2:
            print("Usage: --game 'AWAY @ HOME'")
            raise SystemExit(1)
        away = parts[0].strip().upper()
        home = parts[1].strip().upper()
        print(json.dumps(project_game(
            home, away, args.total, args.spread,
            series="CLI", game_time="CLI", bankroll=args.bankroll,
            sport=args.sport,
        ), indent=2))

    else:
        print("Options: --backtest | --game 'AWAY @ HOME' | --list-teams")
        print("API:     uvicorn tc_engine:app --host 0.0.0.0 --port 8001")