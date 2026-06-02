#!/usr/bin/env python3
"""
NBA TC Engine v6.0 — Full-Stat Player Props Engine (Clean / Public-Ready)
=======================================================================
Covers ALL four prop categories per player:
  • Points (PTS)   • Rebounds (REB)   • Assists (AST)   • 3-Point Shots Made (3PM)

TC Formula:
  Player TC = stat × 0.85  (ACTIVE)
            = stat × 0.85 × 0.55  (Q — Questionable)
            = 0                  (OUT)

  Player T  = floor(TC × 0.88)   ← conservative floor / betting target

Edge sign convention:
  EDGE = Market_Line − TC_Target   (positive = player exceeds line = value)
  BET:  OVER when market is high relative to TC (edge > 0 on totals)
  BET:  UNDER when TC floor < market (standard +EV bet)

Game Total:
  TC_final = raw_combined_PTS × VAR_FACTOR
           = raw_combined_PTS × 0.82  (spread ≥ 10 pts — high variance)
           = raw_combined_PTS × 0.79  (spread 4–9 pts  — mid variance)
           = raw_combined_PTS × 0.76  (spread  < 4 pts — low variance)
           = raw_combined_PTS + 8.0    (no spread — neutral pace)

  TC_Line  = round(TC_final + K_GAP, 1)
  K_GAP    = 9.3  (historical calibration gap, TC_final → market_total)

Signal: OVER when TC_Line < market_total (market overvalues total)
       UNDER when TC_Line > market_total (market undervalues total)
Edge:  positive = TC underpriced vs market | negative = TC overpriced vs market

Kelly betting: kelly_pct = KELLY_FRAC × |edge| / (implied_odds − 1)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import argparse, json, math

# ── CONSTANTS ────────────────────────────────────────────────────────────────
CONS_PTS    = 0.85   # conservative multiplier (all stat categories)
Q_MULT      = 0.55   # questionable multiplier (on top of CONS_PTS)
OUT_MULT    = 0.0    # out = zero contribution
LINE_FACTOR  = 0.88   # derive T (floor target) from TC
K_GAP        = 9.3   # calibration: TC_final gap to market_total
VAR_HIGH    = 0.82   # spread ≥ 10 → high variance, more conservative
VAR_MID     = 0.79   # spread 4–9  → mid variance
VAR_LOW     = 0.76   # spread < 4  → low variance (tight game)
PACE_ADJ    = 8.0    # flat adjustment when no spread provided
MIN_EDGE    = 3.0    # minimum edge (Market_Line − TC_Target) to validate a prop
MIN_HIT_RATE = 0.75  # 75% historical hit rate minimum to recommend
KELLY_FRAC  = 0.25   # Kelly fraction for bet sizing (full Kelly × 0.25)
MIN_KELLY   = 0.01   # minimum Kelly fraction to act

# ── PLAYER ───────────────────────────────────────────────────────────────────
@dataclass
class Player:
    name:   str
    pos:    str
    ht:     str
    pts:    float
    reb:    float
    ast:    float
    tpm:    float     # 3-point shots made
    status: str = "ACTIVE"   # ACTIVE | Q | OUT

    def tc_raw(self, stat: float) -> float:
        """Apply CONS_PTS → Q_MULT if questionable → OUT_MULT if out."""
        if self.status == "OUT":
            return 0.0
        c = stat * CONS_PTS
        return round(c * Q_MULT, 1) if self.status == "Q" else round(c, 1)

    def tc_target(self, stat: float) -> int:
        """Conservative floor target = floor(tc_raw × LINE_FACTOR)."""
        return int(math.floor(self.tc_raw(stat) * LINE_FACTOR))

    def edge(self, stat: float, market_line: float) -> float:
        """EDGE = market_line − TC_target. Positive = value bet."""
        return round(market_line - self.tc_target(stat), 1)

    def is_valid(self, stat: float, market_line: float, min_edge: float = MIN_EDGE) -> bool:
        """Prop is bettable only if edge ≥ min_edge."""
        return self.edge(stat, market_line) >= min_edge

    def proj(self) -> Dict[str, Any]:
        return {
            "TC_PTS":  self.tc_raw(self.pts),
            "TC_REB":  self.tc_raw(self.reb),
            "TC_AST":  self.tc_raw(self.ast),
            "TC_3PM":  self.tc_raw(self.tpm),
            "T_PTS":   self.tc_target(self.pts),
            "T_REB":   self.tc_target(self.reb),
            "T_AST":   self.tc_target(self.ast),
            "T_3PM":   self.tc_target(self.tpm),
            "STATUS":  self.status,
        }

    def valid_props(self, prop_lines: Dict[str, float]) -> Dict[str, Dict]:
        """Return dict of {stat: {L, T, E, valid}} for each stat with a market line."""
        result = {}
        stat_map = {"PTS": self.pts, "REB": self.reb, "AST": self.ast, "3PM": self.tpm}
        for stat_key, stat_val in stat_map.items():
            if stat_key in prop_lines:
                L = prop_lines[stat_key]
                T = self.tc_target(stat_val)
                E = self.edge(stat_val, L)
                result[stat_key] = {"L": L, "T": T, "E": E, "valid": E >= MIN_EDGE}
        return result


# ── TEAM ─────────────────────────────────────────────────────────────────────
@dataclass
class Team:
    code:          str
    name:          str
    players:       List[Player] = field(default_factory=list)
    injury_notes:  List[str]    = field(default_factory=list)

    def add(self, p: Player):
        self.players.append(p)

    def starters(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"][:5]

    def bench(self) -> List[Player]:
        start_names = {p.name for p in self.starters()}
        return [p for p in self.players
                if p.name not in start_names and p.status != "OUT"]

    def active(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"]

    def _sum_tc(self, key: str) -> float:
        return round(sum(p.proj()[key] for p in self.active()), 1)

    def totals(self) -> Dict[str, float]:
        return {
            "TC_PTS":  self._sum_tc("TC_PTS"),
            "TC_REB":  self._sum_tc("TC_REB"),
            "TC_AST":  self._sum_tc("TC_AST"),
            "TC_3PM":  self._sum_tc("TC_3PM"),
        }

    def bench_totals(self) -> Dict[str, float]:
        bench = self.bench()
        return {
            "TC_PTS":  round(sum(p.proj()["TC_PTS"] for p in bench), 1),
            "TC_REB":  round(sum(p.proj()["TC_REB"] for p in bench), 1),
            "TC_AST":  round(sum(p.proj()["TC_AST"] for p in bench), 1),
            "TC_3PM":  round(sum(p.proj()["TC_3PM"] for p in bench), 1),
        }


# ── GAME ─────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self, away_code: str, home_code: str,
                 sport: str = "NBA",
                 market_total: float = None,
                 market_spread: float = None,
                 prop_lines: Dict[str, Dict[str, float]] = None,
                 bankroll: float = 1000):
        self.away_code      = away_code
        self.home_code     = home_code
        self.sport         = sport
        self.market_total  = market_total
        self.market_spread = market_spread
        self.prop_lines    = prop_lines or {}
        self.bankroll      = bankroll

        self.away = self._build_team(away_code)
        self.home = self._build_team(home_code)

    # ── build team from roster dict ───────────────────────────────────────────
    def _build_team(self, code: str) -> Team:
        rosters = NBA_ROSTERS if self.sport == "NBA" else WNBA_ROSTERS
        teams_map = NBA_TEAMS if self.sport == "NBA" else WNBA_TEAMS
        t = Team(code, teams_map.get(code, code))
        for p_data in rosters.get(code, []):
            t.add(Player(*p_data))
        return t

    # ── TC math ────────────────────────────────────────────────────────────────
    def _var_factor(self) -> float:
        """Select VAR_FACTOR based on home spread magnitude."""
        if self.market_spread is None:
            return None   # neutral — use PACE_ADJ path
        ab = abs(self.market_spread)
        if ab >= 10:
            return VAR_HIGH
        if ab >= 4:
            return VAR_MID
        return VAR_LOW

    def _tc_final(self) -> float:
        raw = self._tc_raw_combined()
        factor = self._var_factor()
        if factor is not None:
            return round(raw * factor, 1)
        return round(raw + PACE_ADJ, 1)

    def _tc_raw_combined(self) -> float:
        return round(self.away.totals()["TC_PTS"] + self.home.totals()["TC_PTS"], 1)

    def _tc_line(self) -> float:
        return round(self._tc_final() + K_GAP, 1)

    def _tc_edge_game(self) -> float:
        """Game-level edge = TC_Line − market_total. Positive = market over."""
        if self.market_total is None:
            return 0.0
        return round(self._tc_line() - self.market_total, 1)

    def _signal(self) -> str:
        """OVER = market total high vs TC (bet under); UNDER = market total low vs TC."""
        edge = self._tc_edge_game()
        return "UNDER" if edge > 0 else "OVER"

    def _kelly_bet(self) -> float:
        edge = self._tc_edge_game()
        if edge <= 0:
            return 0.0
        odds = 110   # assumed -110 for game total
        implied = odds / 100.0
        k = KELLY_FRAC * abs(edge) / (implied - 1)
        return max(round(k, 4), MIN_KELLY if abs(edge) >= MIN_EDGE else 0)

    # ── accessors ─────────────────────────────────────────────────────────────
    def get_tc_line(self)   -> float: return self._tc_line()
    def get_tc_final(self)  -> float: return self._tc_final()
    def get_signal(self)    -> str:   return self._signal()
    def get_edge(self)      -> float: return self._tc_edge_game()
    def get_kelly_pct(self) -> float: return self._kelly_bet()

    # ── backtest helpers ──────────────────────────────────────────────────────
    def record_result(self, actual_total: float, bet: str = None) -> Dict:
        """Record a completed game result for backtest logging."""
        result = "WIN" if (bet == "OVER" and actual_total > self.get_tc_line()) \
                     or (bet == "UNDER" and actual_total < self.get_tc_line()) \
                     else "LOSS"
        return {
            "matchup":      f"{self.away_code} @ {self.home_code}",
            "tc_line":      self.get_tc_line(),
            "market_total": self.market_total,
            "actual_total": actual_total,
            "edge":         self.get_edge(),
            "signal":       self.get_signal(),
            "bet":          bet,
            "result":       result,
            "bankroll":     self.bankroll,
        }

    # ── print / display ──────────────────────────────────────────────────────
    def full_report(self):
        self._print_game_header()
        self._print_totals_section()
        self._print_starting_lineup_table(self.away, "AWAY", self.away_code)
        self._print_starting_lineup_table(self.home, "HOME", self.home_code)
        self._print_player_props_section(self.away)
        self._print_player_props_section(self.home)
        self._print_system_summary()

    def _status_flag(self, p: Player) -> str:
        if p.status == "Q":
            return "⚠️ Q"
        if p.status == "OUT":
            return "❌ OUT"
        return "✅ OK"

    def _print_game_header(self):
        edge = self.get_edge()
        arrow = "↑" if edge > 0 else ("↓" if edge < 0 else " ")
        print(f"\n{'═'*80}")
        print(f"  🏀  {self.away.name}  @  {self.home.name}  |  TC v6.0 FULL STAT PROPS")
        print(f"{'═'*80}")
        if self.market_total is not None:
            print(f"  Market Total: {self.market_total}   |   TC Line: {self.get_tc_line():.1f}   |   Edge: {edge:+.1f} {arrow}")
        if self.market_spread is not None:
            print(f"  Market Spread: {self.market_spread:+.1f}   |   TC Final: {self.get_tc_final():.1f}")
        print(f"  Signal: {self.get_signal()}  |  Kelly%: {self.get_kelly_pct()*100:.1f}%  |  Bankroll: ${self.bankroll:,.0f}")
        print(f"{'─'*80}")

    def _print_totals_section(self):
        aw = self.away.totals(); hm = self.home.totals()
        aw_b = self.away.bench_totals(); hm_b = self.home.bench_totals()

        print(f"\n  TEAM TOTALS BREAKDOWN")
        print(f"  {'Category':<10} {'AWAY TC':>10} {'HOME TC':>10} {'COMBINED':>10}")
        print(f"  {'-'*42}")
        for cat in ["TC_PTS", "TC_REB", "TC_AST", "TC_3PM"]:
            lbl = cat.replace("TC_", "")
            cv = round(aw[cat] + hm[cat], 1)
            print(f"  {lbl:<10} {aw[cat]:>10.1f} {hm[cat]:>10.1f} {cv:>10.1f}")

        print(f"\n  BENCH TOTALS")
        print(f"  {'Category':<10} {'AWAY BENCH':>12} {'HOME BENCH':>12}")
        print(f"  {'-'*36}")
        for cat in ["TC_PTS", "TC_REB", "TC_AST", "TC_3PM"]:
            lbl = cat.replace("TC_", "")
            print(f"  {lbl:<10} {aw_b[cat]:>12.1f} {hm_b[cat]:>12.1f}")

        factor = self._var_factor()
        factor_lbl = (
            f"VAR_HIGH(×{VAR_HIGH})" if factor == VAR_HIGH else
            f"VAR_MID(×{VAR_MID})"   if factor == VAR_MID  else
            f"VAR_LOW(×{VAR_LOW})"    if factor == VAR_LOW   else
            f"PACE(+{PACE_ADJ})"
        )
        print(f"\n  GAME TC SUMMARY")
        print(f"  Raw Combined TC PTS:  {self._tc_raw_combined():.1f}")
        print(f"  TC Final (adj):       {self.get_tc_final():.1f}  ({factor_lbl})")
        print(f"  TC Line:              {self.get_tc_line():.1f}  (TC_final + K={K_GAP})")
        if self.market_total is not None:
            e = self.get_edge()
            print(f"  Market Total:         {self.market_total}   |   Edge: {e:+.1f} {'↑' if e>0 else '↓'}")

    def _print_starting_lineup_table(self, team: Team, label: str, code: str):
        start = team.starters(); bench = team.bench()
        print(f"\n  {label} ({code}) — STARTING LINEUP (5)")
        print(f"  {'Player':<22} {'POS':>4} {'HT':>5} "
              f"{'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7}  "
              f"{'T_PTS':>6} {'T_REB':>6} {'T_AST':>6} {'T_3PM':>6} "
              f"{'STATUS':>6}")
        print(f"  {'-'*110}")
        for p in start:
            proj = p.proj()
            print(f"  {p.name:<22} {p.pos:>4} {p.ht:>5} "
                  f"{proj['TC_PTS']:>7.1f} {proj['TC_REB']:>7.1f} "
                  f"{proj['TC_AST']:>7.1f} {proj['TC_3PM']:>7.1f}  "
                  f"{proj['T_PTS']:>6} {proj['T_REB']:>6} "
                  f"{proj['T_AST']:>6} {proj['T_3PM']:>6} "
                  f"{self._status_flag(p):>6}")
        bt = team.bench_totals()
        print(f"  {'─'*110}")
        print(f"  {'BENCH TOTAL':22} {'':<4} {'':<5} "
              f"{bt['TC_PTS']:>7.1f} {bt['TC_REB']:>7.1f} "
              f"{bt['TC_AST']:>7.1f} {bt['TC_3PM']:>7.1f}  "
              f"{'':>6} {'':>6} {'':>6} {'':>6}")
        tt = team.totals()
        print(f"  {'TEAM TOTAL':22} {'':<4} {'':<5} "
              f"{tt['TC_PTS']:>7.1f} {tt['TC_REB']:>7.1f} "
              f"{tt['TC_AST']:>7.1f} {tt['TC_3PM']:>7.1f}")

    def _print_player_props_section(self, team: Team):
        print(f"\n  PLAYER PROPS — {team.name} ({team.code}) — PTS | REB | AST | 3PM")
        print(f"  TC = stat×{CONS_PTS} | Q×{Q_MULT} | T = floor(TC×{LINE_FACTOR})")
        print(f"  Valid: EDGE(L−T)≥{MIN_EDGE}  |  BET: OVER when E>0, UNDER when T<L")
        print(f"  {'Player':<22} {'POS':>4} {'STAT':>4} "
              f"{'L':>6} {'T':>6} {'E':>6} {'VALID?':>7} "
              f"{'L':>6} {'T':>6} {'E':>6} {'VALID?':>7} "
              f"{'L':>6} {'T':>6} {'E':>6} {'VALID?':>7} "
              f"{'L':>6} {'T':>6} {'E':>6} {'VALID?':>7}")
        print(f"  {'-'*160}")

        for p in team.active():
            proj = p.proj()
            flag = "⚠️Q" if p.status == "Q" else "✅"
            lines = self.prop_lines.get(p.name, {})
            stat_keys = [("PTS", p.pts, lines.get("PTS", p.pts)),
                         ("REB", p.reb, lines.get("REB", p.reb)),
                         ("AST", p.ast, lines.get("AST", p.ast)),
                         ("3PM", p.tpm, lines.get("3PM", p.tpm))]
            cells = []
            for sk, sv, L in stat_keys:
                T = proj[f"T_{sk}"]
                E = round(L - T, 1)
                v = "✅" if E >= MIN_EDGE else "⚠️"
                cells.extend([f"{L:>6.1f}", f"{T:>6}", f"{E:>+6.1f}", f"{v:>7}"])
            print(f"  {p.name:<22} {p.pos:>4} {flag:>4} " + " ".join(cells))

        print(f"  LEGEND: L=Market Line | T=TC Target | E=Edge(L−T) | ✅=Edge≥{MIN_EDGE} | ⚠️=Below threshold")
        print(f"  BET: OVER when E>0 (TC underprices) | UNDER when T<L with E≥{MIN_EDGE}")

    def _print_system_summary(self):
        print(f"\n{'═'*80}")
        print(f"  TC SYSTEM SUMMARY — {self.away.code} @ {self.home.code}")
        print(f"{'═'*80}")
        if self.market_total is not None:
            tc_line = self.get_tc_line()
            edge = self.get_edge()
            print(f"  Game Total:  TC_Line={tc_line:.1f}  |  Market={self.market_total:.1f}  |  Edge={edge:+.1f}")
            print(f"  Signal: {self.get_signal()}  |  Kelly: {self.get_kelly_pct()*100:.1f}%")
            print(f"  Bet: OVER if actual>{tc_line:.1f}  |  UNDER if actual<{tc_line:.1f}")
        print(f"\n  TC FORMULA REFERENCE:")
        print(f"    Player TC  = stat × {CONS_PTS} (ACTIVE) | × {CONS_PTS}×{Q_MULT}={CONS_PTS*Q_MULT} (Q) | × {OUT_MULT} (OUT)")
        print(f"    Player T   = floor(TC × {LINE_FACTOR})")
        print(f"    Game TC_Final = raw_PTS × {VAR_HIGH} (|spread|≥10) | ×{VAR_MID} (4-9) | ×{VAR_LOW} (<4) | +{PACE_ADJ} (no spread)")
        print(f"    Game TC_Line  = TC_Final + K={K_GAP}")
        print(f"    EDGE (game)  = TC_Line − Market_Total  (positive = market overvalues OVER)")
        print(f"{'═'*80}\n")

    # ── serialization ────────────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return {
            "matchup":       f"{self.away_code} @ {self.home_code}",
            "sport":         self.sport,
            "market_total":  self.market_total,
            "market_spread": self.market_spread,
            "tc_final":      self.get_tc_final(),
            "tc_line":       self.get_tc_line(),
            "signal":        self.get_signal(),
            "edge":          self.get_edge(),
            "kelly_pct":     self.get_kelly_pct() * 100,
            "bankroll":      self.bankroll,
            "away_totals":   self.away.totals(),
            "home_totals":   self.home.totals(),
            "away_players": [{**{"name": p.name, "pos": p.pos, "ht": p.ht, "status": p.status},
                              **p.proj()} for p in self.away.active()],
            "home_players": [{**{"name": p.name, "pos": p.pos, "ht": p.ht, "status": p.status},
                              **p.proj()} for p in self.home.active()],
            "formulas": {
                "player_tc":   f"stat × {CONS_PTS} (ACTIVE) | × {CONS_PTS*Q_MULT} (Q) | × {OUT_MULT} (OUT)",
                "player_t":    f"floor(TC × {LINE_FACTOR})",
                "tc_final":    f"raw_PTS × VAR_FACTOR + K_GAP({K_GAP})",
                "var_factors": f"HIGH={VAR_HIGH} ≥10 | MID={VAR_MID} 4-9 | LOW={VAR_LOW} <4",
                "edge_sign":   "EDGE = Market_Line − TC_Target (positive = value)",
            },
        }


# ── BACKTEST ENGINE ──────────────────────────────────────────────────────────
class BacktestEngine:
    """Run historical games through the TC model and record P&L."""

    def __init__(self, bankroll: float = 1000, kelly_frac: float = KELLY_FRAC):
        self.bankroll   = bankroll
        self.kelly_frac = kelly_frac
        self.ledger: List[Dict] = []

    def run(self, games: List[Dict]) -> Dict[str, Any]:
        """
        games = [{date, matchup, tc_line, market, actual, sport, ...}, ...]
        Each game must have tc_line or market+tc_final to compute edge.
        """
        for g in games:
            sport = g.get("sport", "NBA")
            away_c, home_c = g["matchup"].split(" @ ")

            tc_line = g.get("tc_line")
            market  = g.get("market", g.get("market_total"))
            actual  = g.get("actual")
            bet     = g.get("bet", "OVER")   # default
            stake   = g.get("stake", 10.0)

            if tc_line is None and market is not None:
                # reconstruct from raw data
                tc_line = round((g.get("away_tc", 0) + g.get("home_tc", 0)) * 0.82 + K_GAP, 1)

            game = Game(away_c, home_c, sport=sport,
                        market_total=market,
                        market_spread=g.get("spread"))

            result = game.record_result(actual, bet) if actual else {"signal": game.get_signal()}
            edge   = game.get_edge()

            # P&L
            if actual and bet:
                win = (bet == "OVER" and actual > tc_line) or \
                      (bet == "UNDER" and actual < tc_line)
                pnl = stake * (1.0) if win else -stake
                self.bankroll += pnl
                result.update({
                    "date": g.get("date"), "stake": stake, "pnl": pnl,
                    "bankroll": round(self.bankroll, 2),
                    "away_tc": g.get("away_tc"), "home_tc": g.get("home_tc"),
                })
                self.ledger.append(result)

        return self.summary()

    def summary(self) -> Dict[str, Any]:
        if not self.ledger:
            return {"games": 0, "wins": 0, "losses": 0, "win_rate": 0,
                    "bankroll": self.bankroll, "ledger": []}
        wins = sum(1 for r in self.ledger if r.get("result") == "WIN")
        losses = len(self.ledger) - wins
        return {
            "games":     len(self.ledger),
            "wins":      wins,
            "losses":    losses,
            "win_rate":  round(wins / len(self.ledger), 4),
            "bankroll":  round(self.bankroll, 2),
            "ledger":    self.ledger,
        }


# ── HELPER ───────────────────────────────────────────────────────────────────
def _p(name, pos, ht, pts, reb, ast, tpm, status="ACTIVE"):
    return (name, pos, ht, pts, reb, ast, tpm, status)


# ── ROSTER DATA ───────────────────────────────────────────────────────────────
NBA_TEAMS = {
    "NYK": "New York Knicks",      "PHI": "Philadelphia 76ers",
    "BOS": "Boston Celtics",        "CLE": "Cleveland Cavaliers",
    "OKC": "Oklahoma City Thunder", "MIN": "Minnesota Timberwolves",
    "DEN": "Denver Nuggets",         "DET": "Detroit Pistons",
    "SAS": "San Antonio Spurs",     "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",       "LAL": "Los Angeles Lakers",
    "GSW": "Golden State Warriors", "LAC": "LA Clippers",
    "DAL": "Dallas Mavericks",      "PHX": "Phoenix Suns",
    "IND": "Indiana Pacers",        "HOU": "Houston Rockets",
    "ATL": "Atlanta Hawks",         "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",         "BKN": "Brooklyn Nets",
    "NOP": "New Orleans Pelicans",  "SAC": "Sacramento Kings",
    "POR": "Portland Trail Blazers","UTA": "Utah Jazz",
    "TOR": "Toronto Raptors",       "WAS": "Washington Wizards",
    "ORL": "Orlando Magic",
}

NBA_ROSTERS = {
    "PHI": [
        _p("Tyrese Maxey",      "G","6-5", 24.5, 4.5, 5.5, 2.5),
        _p("Paul George",       "F","6-8", 20.0, 5.5, 4.0, 2.8,"Q"),
        _p("Joel Embiid",       "C","7-0", 28.0,11.0, 5.5, 1.8,"OUT"),
        _p("Ochai Agbaji",      "G","6-5",  9.0, 3.5, 2.5, 1.5),
        _p("Kelly Oubre Jr.",   "F","6-7", 14.5, 5.0, 1.5, 1.2),
        _p("Jared McCain",      "G","6-3", 14.5, 3.5, 2.5, 1.5),
        _p("Justin Edwards",    "F","6-8",  8.5, 3.5, 1.5, 1.2),
        _p("Jeff Dowtin Jr.",   "G","6-4",  8.0, 2.5, 4.0, 0.8),
        _p("Gregory Jackson",  "F","6-9",  7.0, 4.0, 1.0, 1.0),
    ],
    "NYK": [
        _p("Mikal Bridges",     "F","6-6", 21.0, 4.5, 3.5, 2.8),
        _p("Josh Hart",         "G","6-4", 15.5, 4.5, 5.0, 2.0),
        _p("Karl-Anthony Towns","C","7-0", 25.0,12.5, 3.5, 2.2),
        _p("Jalen Brunson",     "G","6-2", 24.5, 3.5, 6.5, 2.2,"Q"),
        _p("Miles McBride",     "G","6-2", 10.5, 2.5, 3.0, 2.0),
        _p("OG Anunoby",        "F","6-7", 17.5, 5.0, 2.0, 2.5),
        _p("Cameron Payne",     "G","6-4",  7.5, 2.0, 3.5, 1.2),
        _p("Jacob Topp",        "F","6-8",  6.5, 3.5, 1.0, 0.8),
        _p("Jericho Sims",      "C","6-10", 5.5, 5.0, 0.5, 0.3),
    ],
    "BOS": [
        _p("Jayson Tatum",      "F","6-8", 28.5, 7.5, 5.0, 2.9),
        _p("Jaylen Brown",       "G","6-6", 24.0, 6.0, 4.0, 2.5),
        _p("Derrick White",      "G","6-4", 15.5, 4.0, 4.5, 2.2),
        _p("Kristaps Porzingis","F","7-2", 20.0, 7.0, 2.5, 2.8,"OUT"),
        _p("Jrue Holiday",       "G","6-4", 14.5, 5.0, 6.0, 2.0),
        _p("Sam Hauser",         "F","6-5",  8.5, 3.5, 1.5, 1.8),
        _p("Luke Kornet",        "C","7-0",  6.5, 4.5, 1.0, 0.5),
        _p("Payton Pritchard",   "G","6-1",  9.5, 2.5, 3.0, 2.0),
        _p("Baylor Scheierman",  "G","6-5",  7.0, 2.5, 1.5, 1.5),
        _p("Al Horford",         "F","6-9", 11.0, 5.5, 3.5, 1.8),
    ],
    "CLE": [
        _p("Donovan Mitchell",  "G","6-1", 24.5, 5.0, 4.5, 3.0),
        _p("Darius Garland",    "G","6-1", 20.0, 3.5, 6.0, 2.5),
        _p("Evan Mobley",       "F","6-11",18.0, 9.0, 3.5, 1.2),
        _p("Jarrett Allen",      "C","6-9", 14.0, 8.0, 2.0, 0.5),
        _p("Max Strus",          "F","6-5", 12.5, 4.5, 3.5, 2.5),
        _p("Isaac Okoro",        "G","6-5", 10.0, 3.5, 3.0, 1.2),
        _p("Georges Niang",      "F","6-5",  9.0, 3.0, 1.5, 2.0),
        _p("Caris LeVert",       "G","6-5", 11.5, 3.5, 3.5, 1.8,"Q"),
        _p("Tristan Thompson",   "C","6-9",  6.0, 5.5, 1.0, 0.0),
        _p("Ty Jerome",         "G","6-5",  5.5, 2.0, 2.5, 1.0),
    ],
    "OKC": [
        _p("Shai Gilgeous-Alexander","G","6-6",27.5,5.5,6.5,2.2),
        _p("Jalen Williams",    "F","6-5", 19.0, 4.5, 4.5, 1.5),
        _p("Chet Holmgren",     "C","7-1", 16.5, 7.5, 2.5, 1.8),
        _p("Josh Giddey",       "G","6-8", 14.5, 7.5, 6.5, 1.5),
        _p("Lu Dort",           "G","6-4", 11.0, 3.5, 2.0, 2.5),
        _p("Isaiah Hartenstein","C","7-0", 11.5, 9.0, 2.5, 0.8),
        _p("Jared McCollum",    "G","6-3",  9.5, 3.0, 2.5, 1.5),
        _p("Alex Caruso",       "G","6-5",  8.0, 3.0, 2.5, 1.5),
        _p("Kenyan Duke",       "F","6-7",  7.0, 3.5, 1.5, 1.0),
        _p("Jaylin Williams",   "F","6-10", 6.0, 4.5, 1.0, 0.8),
    ],
    "MIN": [
        _p("Anthony Edwards",   "G","6-4", 26.5, 5.5, 5.0, 3.2),
        _p("Julius Randle",     "F","6-4", 18.5, 9.0, 4.5, 1.8),
        _p("Jaden McDaniels",   "F","6-9", 12.5, 4.5, 2.0, 1.8),
        _p("Nickeil Alexander-Walker","G","6-5",12.0,3.5,2.5,2.2),
        _p("Naz Reid",          "C","6-9", 13.5, 5.5, 2.0, 1.5),
        _p("Mike Conley",       "G","6-0", 11.5, 3.5, 5.5, 2.2),
        _p("Donte DiVincenzo",  "G","6-4", 10.5, 3.5, 2.5, 2.2),
        _p("Kyle Anderson",     "F","6-9",  8.5, 4.5, 3.5, 0.8),
    ],
    "DEN": [
        _p("Nikola Jokic",      "C","6-11",26.5,12.0,9.5,1.8),
        _p("Jamal Murray",      "G","6-4", 21.5, 4.5, 5.5, 2.5),
        _p("Michael Porter Jr.", "F","6-10",16.5,6.5,2.0,2.5),
        _p("Aaron Gordon",      "F","6-8", 14.0, 5.5, 2.5, 1.2),
        _p("Kentavious Caldwell-Pope","G","6-5",11.5,3.5,2.0,2.0),
        _p("Christian Braun",   "G","6-5",  8.5, 3.5, 1.5, 1.0),
        _p("Peyton Watson",     "F","6-8",  7.5, 3.0, 1.5, 0.8),
    ],
    "DET": [
        _p("Cade Cunningham",   "G","6-6", 22.0, 5.5, 7.5, 2.2),
        _p("Jaden Ivey",        "G","6-4", 17.5, 4.5, 4.0, 2.0),
        _p("Jalen Duren",        "C","6-10",13.5, 8.0, 2.0, 0.5),
        _p("Ausar Thompson",    "F","6-7", 12.5, 5.5, 3.5, 1.2),
        _p("Tim Hardaway Jr.",   "F","6-5", 14.0, 4.0, 2.5, 2.5),
        _p("Marcus Sasser",     "G","6-2", 10.5, 2.5, 3.0, 1.8),
        _p("Simone Fontecchio", "F","6-8",  8.5, 3.5, 1.5, 1.2),
        _p("Killian Hayes",     "G","6-5",  9.0, 3.0, 4.5, 1.2,"Q"),
    ],
    "GSW": [
        _p("Stephen Curry",     "G","6-2", 24.5, 4.5, 6.0, 3.5),
        _p("Jimmy Butler",      "F","6-7", 20.0, 5.5, 4.5, 1.5,"Q"),
        _p("Draymond Green",     "F","6-6", 11.5, 7.5, 6.5, 1.0),
        _p("Jonathan Kuminga",   "F","6-8", 16.5, 5.5, 2.5, 1.5),
        _p("Buddy Hield",       "G","6-4", 13.0, 4.5, 2.5, 3.0),
        _p("Andrew Wiggins",   "F","6-7", 12.0, 4.5, 2.0, 2.0),
        _p("Kevon Looney",     "C","6-9",  6.5, 6.5, 2.0, 0.3),
        _p("Gary Payton II",    "G","6-3",  7.0, 3.0, 1.5, 1.0),
        _p("Moses Moody",       "G","6-5",  8.0, 3.0, 1.5, 1.2),
        _p("Trayce Jackson-Davis","F","6-9", 7.0, 4.5, 1.0, 0.5),
    ],
    "LAC": [
        _p("Kawhi Leonard",    "F","6-7", 23.5, 6.0, 4.0, 2.5),
        _p("James Harden",     "G","6-5", 21.0, 5.0, 8.5, 2.8),
        _p("Ivica Zubac",       "C","7-0", 12.0, 9.5, 2.0, 0.0),
        _p("Norman Powell",    "G","6-3", 16.5, 3.5, 2.5, 2.2),
        _p("Terance Mann",     "G","6-5", 11.0, 4.5, 3.0, 1.5),
        _p("Amir Coffey",       "F","6-5",  9.0, 3.5, 2.0, 1.5),
        _p("Derrick Jones Jr.", "F","6-6", 10.5, 4.5, 1.5, 1.2),
        _p("Kris Dunn",        "G","6-4",  8.0, 3.5, 4.5, 0.8),
        _p("Nicolas Batum",    "F","6-8",  7.5, 4.0, 2.5, 1.2),
        _p("Ben Simmons",      "G","6-10", 8.5, 7.5, 6.5, 0.3,"Q"),
    ],
    "SAS": [
        _p("Victor Wembanyama", "C","7-4", 23.0,10.5, 4.0, 2.2),
        _p("Chris Paul",        "G","6-0", 10.0, 3.5, 6.5, 1.2),
        _p("Devin Vassell",    "G","6-5", 17.0, 4.0, 3.0, 2.5),
        _p("Keldon Johnson",   "F","6-5", 15.0, 5.0, 2.5, 2.2),
        _p("Jeremy Sochan",    "F","6-9", 11.0, 5.5, 3.0, 1.0),
        _p("Zach Collins",     "C","7-0", 10.0, 5.5, 2.0, 0.5),
        _p("Devonte Graham",    "G","6-1",  8.5, 2.0, 3.5, 1.8),
        _p("Doug McDermott",   "F","6-7",  7.5, 2.5, 1.0, 1.5),
        _p("Malaki Branham",   "G","6-5",  8.0, 2.0, 2.0, 1.0),
        _p("Sandro Mamukelashvili","F/C","6-10",9.5,5.0,1.5,0.8),
    ],
    "MIA": [
        _p("Jimmy Butler",     "F","6-7", 20.0, 5.5, 4.5, 1.5),
        _p("Tyler Herro",      "G","6-5", 21.0, 4.5, 4.0, 2.8),
        _p("Bam Adebayo",      "C","6-9", 18.5,10.0, 4.0, 0.5),
        _p("Nikola Jovic",     "F","6-10",13.0, 5.5, 3.0, 1.5),
        _p("Duncan Robinson",  "G","6-8", 11.5, 3.5, 2.5, 3.0),
        _p("Jaime Jaquez Jr.", "F","6-6", 12.0, 4.5, 3.0, 1.5),
        _p("Kevin Love",       "F","6-8",  8.5, 6.5, 2.0, 1.5),
        _p("Kyle Lowry",       "G","6-0",  7.5, 3.0, 5.0, 1.3),
        _p("Cody Zeller",     "C","6-10", 6.0, 5.0, 1.0, 0.3),
    ],
    "MIL": [
        _p("Giannis Antetokounmpo","F","6-11",27.5,11.5,5.5,1.2),
        _p("Damian Lillard",   "G","6-2", 24.5, 4.5, 7.0, 3.2),
        _p("Khris Middleton",   "F","6-7", 15.5, 5.5, 4.0, 2.2),
        _p("Brook Lopez",     "C","7-1", 12.5, 6.5, 1.5, 2.0),
        _p("Bobby Portis",     "F","6-10",11.5, 7.0, 1.5, 1.5),
        _p("Donte DiVincenzo", "G","6-4", 10.5, 3.5, 2.5, 2.2),
        _p("Pat Connaughton",  "G","6-5",  7.5, 4.0, 1.5, 1.5),
    ],
    "LAL": [
        _p("Luka Doncic",      "G","6-7", 28.5, 7.5, 8.5, 3.0),
        _p("LeBron James",     "F","6-9", 24.5, 7.5, 8.0, 2.5,"Q"),
        _p("Austin Reaves",    "G","6-5", 16.5, 4.5, 5.0, 2.0),
        _p("Rui Hachimura",    "F","6-8", 12.5, 5.0, 1.5, 1.2),
        _p("Jordan Reaves",   "G","6-5",  7.5, 3.0, 1.5, 1.2),
        _p("Gabe Vincent",     "G","6-4",  7.0, 2.0, 2.5, 1.0),
        _p("Dorian Finney-Smith","F","6-8",7.5,4.5,1.5,1.8),
        _p("Julius Randle",    "F","6-4", 18.5, 9.0, 4.5, 1.8),
    ],
    "HOU": [
        _p("Alperen Sengun",   "C","6-9", 19.5, 9.5, 4.5, 0.8),
        _p("Jalen Green",     "G","6-4", 21.0, 4.5, 3.5, 3.0),
        _p("Amen Thompson",    "F","6-8", 12.5, 6.5, 4.0, 1.2),
        _p("Fred VanVleet",   "G","6-0", 14.0, 3.5, 5.5, 2.5),
        _p("Jabari Smith Jr.",  "F","6-10",12.0, 6.5, 1.8, 1.5),
        _p("Tari Eason",       "F","6-8", 11.5, 5.5, 1.5, 1.2),
        _p("Cam Whitmore",    "G","6-5", 10.5, 3.5, 1.5, 1.0),
    ],
    "ATL": [
        _p("Trae Young",       "G","6-1", 25.5, 3.5, 9.5, 2.8),
        _p("Zach LaVine",     "G","6-5", 22.5, 4.5, 4.0, 3.2),
        _p("Jalen Johnson",   "F","6-9", 14.0, 6.5, 3.5, 1.2),
        _p("Domantas Sabonis", "C","6-10",14.0, 9.0, 5.5, 0.5),
        _p("De'Andre Hunter",  "F","6-8", 15.0, 4.5, 2.0, 2.2),
        _p("Onyeka Okongwu",  "C","6-10",10.5, 6.5, 1.5, 0.8),
        _p("Vit Krejci",       "G","6-7",  7.5, 3.5, 3.0, 1.2),
    ],
    "ORL": [
        _p("Paolo Banchero",  "F","6-10",23.5, 6.5, 4.0, 2.0),
        _p("Franz Wagner",    "F","6-10",19.5, 5.0, 3.0, 1.5),
        _p("Jalen Suggs",     "G","6-5", 16.5, 4.0, 4.5, 1.5),
        _p("Wendell Carter Jr.","C","6-6",14.5, 9.0, 2.5, 0.8),
        _p("Cole Anthony",    "G","6-2", 13.0, 4.5, 3.5, 1.2),
        _p("Goga Bitadze",    "C","6-11",10.5, 6.0, 2.0, 0.5),
        _p("Jonathan Isaac",  "F","6-10", 6.5, 4.0, 1.0, 0.5),
        _p("Caleb Houstan",   "F","6-8",  7.0, 3.0, 1.5, 0.8),
    ],
    "TOR": [
        _p("Scottie Barnes",   "F","6-8", 20.5, 6.5, 4.5, 1.5),
        _p("RJ Barrett",       "G","6-6", 19.5, 5.5, 3.5, 2.0),
        _p("Immanuel Quickley","G","6-2",14.5, 4.0, 4.5, 2.0),
        _p("Jakob Poeltl",    "C","7-0", 11.5, 8.5, 2.0, 0.0),
        _p("Ochai Agbaji",     "G","6-5",  9.0, 3.5, 2.5, 1.5),
        _p("Jamal Shead",     "G","6-2",  8.0, 3.0, 4.0, 1.0),
        _p("Jonathan Mogbo",  "F","6-8",  7.5, 5.5, 2.0, 0.5),
    ],
    "IND": [
        _p("Tyrese Haliburton","G","6-5", 21.0, 4.0, 8.5, 3.2),
        _p("Pascal Siakam",  "F","6-8", 20.0, 6.5, 4.5, 1.8),
        _p("Myles Turner",    "C","6-11",15.5, 8.0, 2.0, 1.2),
        _p("Bennedict Mathurin","G","6-5",17.5, 4.5, 2.5, 2.0),
        _p("Aaron Nesmith",  "F","6-5", 11.0, 4.0, 2.0, 2.0),
        _p("Obi Toppin",      "F","6-8", 11.5, 4.0, 2.0, 1.5),
        _p("Jalen Smith",    "F","6-10", 9.5, 5.5, 1.0, 1.0),
        _p("Andrew Nembhard","G","6-4",  9.0, 2.5, 4.0, 1.2),
    ],
}

for _c in ["CHI","BKN","NOP","SAC","POR","UTA","WAS","CHA"]:
    NBA_ROSTERS.setdefault(_c, [])

WNBA_TEAMS = {
    "NYL": "New York Liberty",  "POR": "Portland Fire",
    "MIN": "Minnesota Lynx",    "DAL": "Dallas Wings",
    "LVA": "Las Vegas Aces",   "IND": "Indiana Fever",
    "PHX": "Phoenix Mercury",   "SEA": "Seattle Storm",
    "CON": "Connecticut Sun",   "CHI": "Chicago Sky",
    "ATL": "Atlanta Dream",    "WAS": "Washington Mystics",
}

WNBA_ROSTERS = {
    "NYL": [
        _p("Breanna Stewart",      "F","6-4", 19.5, 8.5, 4.0, 2.4),
        _p("Sabrina Ionescu",      "G","5-11",17.5,5.5, 7.1, 3.2),
        _p("Jonquel Jones",        "C","6-6", 15.0, 9.0, 2.9, 1.5),
        _p("Courtney Vandersloot",  "G","5-8", 10.9, 4.0, 6.5, 1.8),
        _p("Betnijah Laney",       "F","6-0", 10.6, 3.0, 1.6, 1.0,"Q"),
        _p("Kayla Thornton",      "F","6-2",  6.5, 4.0, 0.9, 0.8),
        _p("Sonia",               "G","5-9",  6.0, 2.0, 1.5, 0.5),
        _p("Han Xu",              "C","6-11", 7.0, 4.0, 0.5, 0.3),
    ],
    "IND": [
        _p("Caitlin Clark",       "G","6-0", 18.5, 5.0, 8.0, 3.5),
        _p("Aliyah Boston",        "C","6-4", 14.0, 9.0, 2.5, 1.0),
        _p("Kelsey Mitchell",     "G","5-10",14.5, 3.0, 2.5, 2.0),
        _p("Grace Berger",        "G","6-0",  8.5, 2.5, 2.0, 0.8),
        _p("Lexie Hull",           "G","5-11", 6.5, 2.5, 1.5, 0.6),
        _p("Emma",                "F","6-2",  6.0, 4.0, 0.8, 0.5,"Q"),
        _p("Nina",                "F","6-3",  5.0, 3.5, 0.5, 0.3),
    ],
    "WAS": [
        _p("Elena Delle Donne",    "F","6-4", 18.0, 6.0, 3.0, 2.5),
        _p("Ariel Atkins",         "G","5-11",14.5, 4.0, 3.0, 1.5),
        _p("Natasha",             "C","6-5", 11.0, 7.5, 1.5, 0.5),
        _p("Natasha Cloud",       "G","5-11", 9.5, 3.5, 5.0, 1.2),
        _p("Shakira Austin",      "C","6-0",  8.5, 5.5, 1.5, 0.5,"Q"),
        _p("KeKe",                "F","6-4",  7.0, 4.0, 0.8, 0.5),
        _p("Jade",               "G","5-8",  5.5, 1.5, 1.5, 0.5),
    ],
    "LVA": [
        _p("A'ja Wilson",         "F","6-4", 22.5,10.0, 3.5, 1.5),
        _p("Chelsea Gray",         "G","5-11",14.5, 4.0, 5.0, 1.8),
        _p("Kia",                "C","6-5", 12.5, 7.5, 1.5, 0.5),
        _p("Jackie",             "G","5-10",11.0, 3.5, 4.0, 1.5),
        _p("Alysha",             "F","6-2",  8.5, 4.0, 1.0, 0.8,"Q"),
        _p("Kayla",              "G","5-9",  6.5, 1.5, 2.0, 0.8),
        _p("Sydney",              "F","6-3",  5.5, 3.0, 0.5, 0.3),
    ],
    "MIN": [
        _p("Napheesa Collier",    "F","6-0", 16.9, 5.5, 3.4, 1.8),
        _p("Kayla McCollough",   "G","5-11",14.1, 3.5, 2.0, 1.0,"Q"),
        _p("Alana",              "C","6-4", 11.5, 7.0, 1.5, 0.5),
        _p("Natasha",            "G","5-8", 11.0, 2.9, 5.5, 1.5),
        _p("Diamond",            "F","6-2",  8.5, 4.0, 1.0, 0.8),
        _p("Nele",               "F","6-3",  6.0, 3.0, 0.5, 0.3),
        _p("Olivia",             "G","5-7",  4.5, 1.0, 1.5, 0.4),
        _p("Nara",               "G","5-9",  3.5, 0.8, 0.8, 0.3),
    ],
    "DAL": [
        _p("Arielle",            "G","5-10",16.5, 4.5, 4.5, 2.0),
        _p("Moriah",             "G","6-0", 14.0, 4.0, 3.5, 1.3),
        _p("Caitlin",            "F","6-3", 12.5, 6.0, 1.5, 0.8),
        _p("Naomi",              "C","6-5", 10.5, 7.0, 1.0, 0.5,"Q"),
        _p("Satou",              "F","6-2",  9.0, 4.5, 1.5, 0.8),
        _p("Lindsay",            "G","5-9",  7.5, 2.0, 2.5, 0.9),
        _p("Jaiden",             "F","6-3",  5.5, 3.0, 0.5, 0.3),
        _p("Awak",               "G","5-8",  4.0, 1.0, 1.0, 0.3),
    ],
}

for _c in ["CON","SEA","PHX","CHI","ATL","POR"]:
    WNBA_ROSTERS.setdefault(_c, [])


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="NBA TC Engine v6.0 — Full-Stat Props + Backtest")
    p.add_argument("--sport",    choices=["NBA","WNBA"], default="NBA")
    p.add_argument("--game",     help="'AWAY @ HOME' e.g. 'SAS @ OKC'")
    p.add_argument("--total",    type=float, help="Market game total")
    p.add_argument("--spread",   type=float, help="Home spread (e.g. -4)")
    p.add_argument("--bankroll", type=float, default=1000)
    p.add_argument("--json",     action="store_true")
    p.add_argument("--list",     action="store_true")
    p.add_argument("--backtest", action="store_true")
    a = p.parse_args()

    if a.game:
        away, home = [x.strip().upper() for x in a.game.split("@")]
        g = Game(away, home, a.sport, a.total, a.spread, bankroll=a.bankroll)
        if a.json:
            print(json.dumps(g.to_dict(), indent=2))
        else:
            g.full_report()

    elif a.list:
        tm = NBA_TEAMS if a.sport == "NBA" else WNBA_TEAMS
        print(f"\n{a.sport} Teams ({len(tm)}):")
        for k in sorted(tm):
            t = NBA_ROSTERS.get(k, []) if a.sport == "NBA" else WNBA_ROSTERS.get(k, [])
            injuries = [p[0] for p in t if p[-1] in ("Q","OUT")]
            notes = f"  ❗ {', '.join(injuries)}" if injuries else ""
            print(f"  {k}: {tm[k]}{notes}")

    elif a.backtest:
        import csv, io, sys
        # read from stdin or file
        data = []
        reader = csv.DictReader(sys.stdin)
        for row in reader:
            data.append(row)
        engine = BacktestEngine(bankroll=a.bankroll)
        result = engine.run(data)
        print(json.dumps(result, indent=2))

    else:
        print("NBA TC Engine v6.0")
        print("Usage: --game 'AWAY @ HOME' [--total N] [--spread N] [--json]")
        print("       --list [--sport NBA|WNBA]")
        print("       --backtest  (pipe CSV to stdin)")