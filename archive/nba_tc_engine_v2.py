"""
NBA/WNBA TC ENGINE — Unified Triple Conservative Betting System
Version: 2.0 (NBA + WNBA integrated)

TC Formula:
  TC PTS   = stat × 0.85   (ACTIVE)
  TC REB   = stat × 0.80
  TC AST   = stat × 0.75
  TC 3PM   = stat × 0.70
  Q status = × 0.55
  OUT      = 0

  Line  = TC × 0.88   (floor)
  Edge  = TC − Line   (positive = OVER edge)

Sports supported: NBA, WNBA
Backtest modes:  live | halftime | final
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import json, math, argparse, datetime

# ── CONSTANTS ───────────────────────────────────────────────
CONS_PTS  = 0.85
CONS_REB  = 0.80
CONS_AST  = 0.75
CONS_3PM  = 0.70
CONS_STL  = 0.80
CONS_BLK  = 0.80
LINE_FAC  = 0.88
Q_FAC     = 0.55
OUT_FAC   = 0.0
MIN_EDGE  = 2.0   # minimum edge for a playable prop
PROP_EDGE_FILTERS = {"PTS":4.0,"REB":2.5,"AST":2.0,"3PM":0.8,"STL":0.8,"BLK":0.8}

# ── PLAYER MODEL ────────────────────────────────────────────
@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float = 0.0
    reb: float = 0.0
    ast: float = 0.0
    tpm: float = 0.0
    stl: float = 0.0
    blk: float = 0.0
    min: float = 0.0
    status: str = "ACTIVE"

    def tc(self, stat: str) -> float:
        f = self._factor()
        s = getattr(self, stat, 0.0) or 0.0
        if stat == "pts":  return round(s * CONS_PTS * f, 1)
        if stat == "reb":  return round(s * CONS_REB * f, 1)
        if stat == "ast":  return round(s * CONS_AST * f, 1)
        if stat == "tpm":  return round(s * CONS_3PM * f, 1)
        if stat == "stl":  return round(s * CONS_STL * f, 1)
        if stat == "blk":  return round(s * CONS_BLK * f, 1)
        return 0.0

    def line(self, stat: str) -> int:
        return math.floor(self.tc(stat) * LINE_FAC)

    def edge(self, stat: str) -> float:
        return round(self.tc(stat) - self.line(stat), 1)

    def _factor(self) -> float:
        s = self.status.upper()
        if "OUT" in s or "DNP" in s: return OUT_FAC
        if any(q in s for q in ["Q","QUESTION","DOUBTFUL","GTD"]): return Q_FAC
        return 1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "pos": self.pos, "ht": self.ht,
            "min": self.min, "status": self.status,
            "tc_pts": self.tc("pts"), "tc_reb": self.tc("reb"),
            "tc_ast": self.tc("ast"), "tc_3pm": self.tc("tpm"),
            "tc_stl": self.tc("stl"), "tc_blk": self.tc("blk"),
            "line_pts": self.line("pts"), "line_reb": self.line("reb"),
            "line_ast": self.line("ast"), "line_3pm": self.line("3pm"),
            "edge_pts": self.edge("pts"), "edge_reb": self.edge("reb"),
            "edge_ast": self.edge("ast"), "edge_3pm": self.edge("3pm"),
        }

# ── TEAM MODEL ───────────────────────────────────────────────
@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player] = field(default_factory=list)
    injury_notes: List[str] = field(default_factory=list)

    def starters(self, n=5) -> List[Player]:
        active = [p for p in self.players if p._factor() > 0]
        return sorted(active, key=lambda p: p.pts + p.reb * 0.8 + p.ast * 0.8, reverse=True)[:n]

    def bench(self) -> List[Player]:
        start_ids = {p.name for p in self.starters()}
        return [p for p in self.players if p.name not in start_ids and p._factor() > 0]

    def team_totals(self) -> Dict[str, float]:
        active = [p for p in self.players if p._factor() > 0]
        return {
            "tc_pts": round(sum(p.tc("pts") for p in active), 1),
            "tc_reb": round(sum(p.tc("reb") for p in active), 1),
            "tc_ast": round(sum(p.tc("ast") for p in active), 1),
            "tc_3pm": round(sum(p.tc("tpm") for p in active), 1),
            "tc_stl": round(sum(p.tc("stl") for p in active), 1),
            "tc_blk": round(sum(p.tc("blk") for p in active), 1),
        }

# ── TC ENGINE ────────────────────────────────────────────────
class TCEngine:
    def __init__(self, away: Team, home: Team, market_total=None, market_spread=None):
        self.away = away
        self.home = home
        self.market_total = market_total
        self.market_spread = market_spread

    def project(self) -> dict:
        at = self.away.team_totals()
        ht = self.home.team_totals()
        tc_combined = round(at["tc_pts"] + ht["tc_pts"], 1)
        tc_line = math.floor(tc_combined * LINE_FAC)
        edge = round(tc_line - (self.market_total or tc_line), 1)
        signal = ("OVER" if edge > 3 else "UNDER" if edge < -3 else "PASS") if self.market_total else "NO MARKET"

        # Build per-player projections
        away_rows = [p.to_dict() for p in self.away.players]
        home_rows = [p.to_dict() for p in self.home.players]

        return {
            "away_team": self.away.abbr,
            "home_team": self.away.name,
            "tc_combined": tc_combined,
            "tc_line": tc_line,
            "market_total": self.market_total,
            "edge": edge,
            "signal": signal,
            "away": {"totals": at, "starters": self.away.starters(), "bench": self.away.bench(), "players": away_rows},
            "home": {"totals": ht, "starters": self.home.starters(), "bench": self.home.bench(), "players": home_rows},
            "injuries": {**{self.away.abbr: self.away.injury_notes}, **{self.home.abbr: self.home.injury_notes}},
        }

    def prop_picks(self, players: List[Player]) -> List[dict]:
        picks = []
        for p in players:
            if p._factor() == 0: continue
            for stat in ["pts","reb","ast","tpm","stl","blk"]:
                tc = p.tc(stat)
                line = p.line(stat)
                edge = p.edge(stat)
                sk = stat.upper() if stat != "tpm" else "3PM"
                threshold = PROP_EDGE_FILTERS.get(sk, 999)
                direction = "OVER" if edge >= threshold else "UNDER" if edge <= -threshold else "NO BET"
                if direction != "NO BET":
                    picks.append({
                        "player": p.name, "team": p.abbr if hasattr(p,"abbr") else "",
                        "stat": sk, "tc": tc, "line": line, "edge": edge,
                        "direction": direction, "status": p.status,
                    })
        return picks

    def backtest_game(self, actual_totals: Tuple[int,int]) -> dict:
        """Compare TC combined vs actual game total."""
        at = self.away.team_totals()
        ht = self.home.team_totals()
        tc_combined = round(at["tc_pts"] + ht["tc_pts"], 1)
        tc_line = math.floor(tc_combined * LINE_FAC)
        actual_total = actual_totals[0] + actual_totals[1]
        diff = round(actual_total - tc_combined, 1)
        result = "OVER" if actual_total > tc_line else "UNDER" if actual_total < tc_line else "PUSH"
        return {
            "game": f"{self.away.abbr}@{self.home.abbr}",
            "tc_combined": tc_combined,
            "tc_line": tc_line,
            "actual_total": actual_total,
            "diff": diff,
            "result": result,
            "winner": "HIT" if result != "PASS" else "N/A",
        }

# ── BACKTEST RUNNER ─────────────────────────────────────────
def run_backtest(game_data: List[dict], source="halftime") -> dict:
    results = []
    for g in game_data:
        t = Team(g["away"], g["away_name"], [Player(**p) for p in g.get("away_players",[])])
        h = Team(g["home"], g.get("home_name",""), [Player(**p) for p in g.get("home_players",[])])
        engine = TCEngine(t, h, g.get("market_total"), g.get("market_spread"))
        res = engine.backtest_game((g["actual_away"], g["actual_home"]))
        res["source"] = source
        results.append(res)
    hits = sum(1 for r in results if r.get("winner") == "HIT")
    return {"games": results, "total": len(results), "hits": hits, "hit_rate": round(hits/len(results)*100,1) if results else 0}

# ── CLI ─────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NBA/WNBA TC Engine")
    parser.add_argument("--sport", default="NBA", choices=["NBA","WNBA"])
    parser.add_argument("--game", help='e.g. "PHI @ NYK"')
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--market-total", type=float, default=None)
    parser.add_argument("--market-spread", type=float, default=None)
    parser.add_argument("--list-teams", action="store_true")
    args = parser.parse_args()

    print(f"TC Engine v2.0 loaded — {args.sport} mode")
    if args.list_teams:
        print("Use live API or roster file to list teams.")