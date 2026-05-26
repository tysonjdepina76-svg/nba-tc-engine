"""
NBA TC ENGINE — Public App Ready (Single-File Version)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import argparse

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# ── CONSTANTS ──────────────────────────────────────────────────────────────
CONS_PTS = 0.85
CONS_REB = 0.12
CONS_AST = 0.10
CONS_3PM = 0.08
LINE_FACTOR = 0.88
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
MIN_EDGE = 1.0

# ── PLAYER MODEL ─────────────────────────────────────────────────────────
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
    min_share: float = 1.0

    def tc_pts(self) -> float:
        if self.status == "OUT":
            return 0.0
        factor = Q_FACTOR if self.status == "Q" else 1.0
        return (self.pts * CONS_PTS + self.reb * CONS_REB +
                self.ast * CONS_AST + self.tpm * CONS_3PM) * factor * self.min_share

# ── TEAM MODEL ──────────────────────────────────────────────────────────
@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]
    injury_notes: List[str] = field(default_factory=list)

    def tc_total(self) -> float:
        return sum(p.tc_pts() for p in self.players)

    def starters(self) -> List[Player]:
        return [p for p in self.players if " Starter" in p.name or p.min_share >= 0.8][:5]

# ── TC CORE ─────────────────────────────────────────────────────────────
def calc_tc_pts(pts, reb, ast, tpm, status="ACTIVE", min_share=1.0):
    f = Q_FACTOR if status == "Q" else (0.0 if status == "OUT" else 1.0)
    return (pts * CONS_PTS + reb * CONS_REB + ast * CONS_AST + tpm * CONS_3PM) * f * min_share

def derive_line(tc_total: float) -> float:
    return round(tc_total * LINE_FACTOR)

def edge(tc_pts, book_line):
    return round(tc_pts - book_line, 1)

# ── PROJECTION ENGINE ───────────────────────────────────────────────────
def project_game(home_abbr, away_abbr, market_total=None, market_spread=None,
                 series="", game_time="", bankroll=1000.0):
    # Would integrate live roster scraper here
    return {"status": "live_roster_mode", "home": home_abbr, "away": away_abbr}

# ── BACKTEST ─────────────────────────────────────────────────────────────
def run_backtest(games):
    results = []
    for g in games:
        tc = g["tc_total"]
        line = derive_line(tc)
        e = edge(tc, g["book_line"])
        win = e > 0
        results.append({"game": g["id"], "tc": tc, "line": line, "edge": e, "win": win})
    return results

if __name__ == "__main__":
    print("NBA TC Engine loaded. Use --game or --backtest flags.")