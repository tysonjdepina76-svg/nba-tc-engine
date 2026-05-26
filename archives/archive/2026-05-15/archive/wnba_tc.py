#!/usr/bin/env python3
"""
WNBA TC ENGINE — Triple Conservative Scoring System
Adapted from your NBA TC template for WNBA use.

TC Formula:
  TC_pts = pts × 0.85
  TC_reb = reb × 0.12
  TC_ast = ast × 0.10
  TC_3pm = tpm × 0.08
  TC_TOTAL = sum of the four components

LINE Formula:
  LINE = (TC_TOTAL + HISTORICAL_GAP) × pace_adjustments × LINE_FACTOR

Injury:
  QUESTIONABLE → TC × 0.55
  OUT → 0

This file is intentionally clean:
  - Core math + Player/Team dataclasses
  - Minimal dummy backtest structure
  - WNBA team stubs for you to fill
  - CLI for backtest / single-game report
"""

import sys
import warnings
from dataclasses import dataclass, field
from typing import List, Dict

warnings.filterwarnings("ignore")

# ── CONSTANTS ──────────────────────────────────────────────────────────────
CONS_PTS = 0.85   # pts factor
CONS_REB = 0.12   # reb factor
CONS_AST = 0.10   # ast factor
CONS_3PM = 0.08   # 3PM factor
LINE_FACTOR = 0.88
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
MIN_EDGE = 1.0
MIN_HR = 57
KELLY_FRAC = 0.50

# You will want to re‑calibrate this for WNBA once you have data
HISTORICAL_GAP = 4.5

# Pace tweaks for playoffs / home court if you want them in W
PACE_ADJ_HOME = 1.02
PACE_ADJ_PLAYOFF = 0.98
DEFAULT_BANKROLL = 1000.0

# ── TC MATH ────────────────────────────────────────────────────────────────
def calc_tc_pts(pts: float, status: str) -> float:
    if status == "OUT":
        return 0.0
    if status == "QUESTIONABLE":
        return round(pts * CONS_PTS * Q_FACTOR, 1)
    return round(pts * CONS_PTS, 1)

def calc_tc_reb(reb: float, status: str) -> float:
    if status == "OUT":
        return 0.0
    if status == "QUESTIONABLE":
        return round(reb * CONS_REB * Q_FACTOR, 1)
    return round(reb * CONS_REB, 1)

def calc_tc_ast(ast: float, status: str) -> float:
    if status == "OUT":
        return 0.0
    if status == "QUESTIONABLE":
        return round(ast * CONS_AST * Q_FACTOR, 1)
    return round(ast * CONS_AST, 1)

def calc_tc_3pm(tpm: float, status: str) -> float:
    if status == "OUT":
        return 0.0
    if status == "QUESTIONABLE":
        return round(tpm * CONS_3PM * Q_FACTOR, 1)
    return round(tpm * CONS_3PM, 1)

def calc_tc_total(pts: float, reb: float, ast: float, tpm: float, status: str) -> float:
    return round(
        calc_tc_pts(pts, status)
        + calc_tc_reb(reb, status)
        + calc_tc_ast(ast, status)
        + calc_tc_3pm(tpm, status),
        1,
    )

def calc_line(tc_total: float, is_home: bool = False, is_playoff: bool = False) -> int:
    base = tc_total + HISTORICAL_GAP
    if is_home:
        base *= PACE_ADJ_HOME
    if is_playoff:
        base *= PACE_ADJ_PLAYOFF
    return round(base * LINE_FACTOR)

def calc_edge(tc_total: float, line: int) -> float:
    return round(tc_total - line, 1)

def kelly_bet(bankroll: float, edge: float, odds: float, fraction: float = KELLY_FRAC) -> float:
    if edge <= 0:
        return 0.0
    b = odds - 1
    q = 1 / (1 + b / edge)
    return round(bankroll * fraction * (b * q - (1 - q)) / b, 2) if b > 0 else 0.0

def hit_rate(tc_total: float, line: int) -> int:
    gap = abs(tc_total - line)
    if gap >= 10:
        return 72
    if gap >= 7:
        return 68
    if gap >= 5:
        return 64
    if gap >= 3:
        return 60
    return 57

# ── DOMAIN MODELS ──────────────────────────────────────────────────────────
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

    def tc_pts(self) -> float:
        return calc_tc_pts(self.pts, self.status)

    def tc_reb(self) -> float:
        return calc_tc_reb(self.reb, self.status)

    def tc_ast(self) -> float:
        return calc_tc_ast(self.ast, self.status)

    def tc_3pm(self) -> float:
        return calc_tc_3pm(self.tpm, self.status)

    def tc_total(self) -> float:
        return calc_tc_total(self.pts, self.reb, self.ast, self.tpm, self.status)

@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]
    injury_notes: List[str] = field(default_factory=list)

    def tc_pts_total(self) -> float:
        return round(sum(p.tc_pts() for p in self.players), 1)

    def tc_reb_total(self) -> float:
        return round(sum(p.tc_reb() for p in self.players), 1)

    def tc_ast_total(self) -> float:
        return round(sum(p.tc_ast() for p in self.players), 1)

    def tc_3pm_total(self) -> float:
        return round(sum(p.tc_3pm() for p in self.players), 1)

    def tc_total(self) -> float:
        return round(sum(p.tc_total() for p in self.players), 1)

# ── WNBA TEAM STUBS (FILL THESE OUT) ───────────────────────────────────────
# Example: Lynx and Wings with rough placeholder numbers.
# Swap these for your projection-based numbers, or map in from DK props.

LYNX = Team("MINL", "Minnesota Lynx", [
    Player("Napheesa Collier", "F", "6-1", 20.5, 9.0, 3.5, 1.1),
    Player("Kayla McBride", "G", "5-11", 15.2, 3.1, 2.5, 2.7),
    Player("Alanna Smith", "F", "6-4", 10.0, 5.5, 2.0, 1.2),
    Player("Courtney Williams", "G", "5-8", 11.5, 4.0, 4.5, 0.8),
    Player("Dorka Juhasz", "F", "6-5", 8.5, 7.2, 2.1, 0.6),
])

WINGS = Team("DALW", "Dallas Wings", [
    Player("Arike Ogunbowale", "G", "5-8", 23.5, 3.0, 4.0, 2.9),
    Player("Satou Sabally", "F", "6-4", 18.0, 7.5, 3.5, 1.6),
    Player("Natasha Howard", "F", "6-2", 14.2, 8.0, 2.2, 0.9),
    Player("Veronica Burton", "G", "5-9", 7.8, 2.5, 4.0, 1.0),
    Player("Teaira McCowan", "C", "6-7", 12.0, 9.5, 1.2, 0.0),
])

LIBERTY = Team("NYL", "New York Liberty", [
    Player("Breanna Stewart", "F", "6-4", 22.5, 9.1, 3.8, 1.8),
    Player("Sabrina Ionescu", "G", "5-11", 18.3, 5.5, 6.2, 3.1),
    Player("Jonquel Jones", "C", "6-6", 15.0, 8.8, 2.0, 1.2),
    Player("Betnijah Laney-Hamilton", "G", "6-0", 12.7, 4.0, 3.0, 1.6),
    Player("Courtney Vandersloot", "G", "5-9", 8.9, 3.0, 7.1, 1.1),
])

Aces = Team("LVA", "Las Vegas Aces", [
    Player("A'ja Wilson", "F", "6-4", 24.5, 10.5, 3.5, 1.2),
    Player("Chelsea Gray", "G", "5-11", 13.5, 3.5, 6.8, 1.5),
    Player("Kelsey Plum", "G", "5-8", 17.8, 2.5, 4.5, 2.8),
    Player("Jackie Young", "G", "5-11", 16.2, 4.0, 3.2, 2.2),
    Player("Kiah Stokes", "C", "6-3", 5.5, 7.8, 1.0, 0.2),
])

MERCURY = Team("PHX", "Phoenix Mercury", [
    Player("Diana Taurasi", "G", "6-0", 16.5, 3.5, 4.0, 2.5),
    Player("Brittney Griner", "C", "6-9", 19.0, 8.5, 1.8, 0.3),
    Player("Skylar Diggins-Smith", "G", "5-9", 15.5, 3.0, 5.5, 1.8),
    Player("Sophie Cunningham", "F", "6-1", 10.5, 4.0, 2.0, 1.5),
    Player("Brianna Turner", "F", "6-3", 7.0, 6.5, 1.5, 0.2),
])

STORM = Team("SEA", "Seattle Storm", [
    Player("Jewell Loyd", "G", "5-10", 19.5, 3.5, 3.8, 2.2),
    Player("Nneka Ogwumike", "F", "6-2", 17.5, 8.0, 2.5, 0.8),
    Player("Skylar Diggins", "G", "5-9", 14.0, 2.5, 6.0, 1.5),
    Player("Ezi Magbegor", "C", "6-4", 10.0, 6.0, 1.2, 0.5),
    Player("Sami Whitcomb", "G", "5-10", 8.5, 3.0, 2.5, 1.8),
])

WNBA_TEAMS: Dict[str, Team] = {
    "MINL": LYNX,
    "DALW": WINGS,
    "NYL": LIBERTY,
    "LVA": Aces,
    "PHX": MERCURY,
    "SEA": STORM,
}

# ── SIMPLE BACKTEST STRUCT (DUMMY PLACEHOLDER) ─────────────────────────────
@dataclass
class BacktestGame:
    home_abbr: str
    away_abbr: str
    actual_home_score: int
    actual_away_score: int
    market_total: float
    date: str
    round_label: str
    notes: str = ""

# You will replace this with real WNBA backtest once you log data.
BACKTEST_SUITE: List[BacktestGame] = [
    BacktestGame("DALW", "MINL", 89, 82, 170.5, "May 1, 2026", "RS", "Sample game"),
]

def run_backtest() -> dict:
    results = []
    for g in BACKTEST_SUITE:
        ht = WNBA_TEAMS.get(g.home_abbr)
        at = WNBA_TEAMS.get(g.away_abbr)
        if not ht or not at:
            continue
        tc_h = ht.tc_total()
        tc_a = at.tc_total()
        tc_raw = round(tc_h + tc_a, 1)
        tc_pts = round(ht.tc_pts_total() + at.tc_pts_total(), 1)
        tc_reb = round(ht.tc_reb_total() + at.tc_reb_total(), 1)
        tc_ast = round(ht.tc_ast_total() + at.tc_ast_total(), 1)
        tc_3pm = round(ht.tc_3pm_total() + at.tc_3pm_total(), 1)
        actual = g.actual_home_score + g.actual_away_score
        line = calc_line(tc_raw, is_home=True, is_playoff=False)
        diff = round(actual - tc_raw, 1)
        results.append({
            "game": f"{g.away_abbr}@{g.home_abbr}",
            "date": g.date,
            "round": g.round_label,
            "tc_pts": tc_pts,
            "tc_reb": tc_reb,
            "tc_ast": tc_ast,
            "tc_3pm": tc_3pm,
            "tc_raw": tc_raw,
            "line": line,
            "actual": actual,
            "diff": diff,
            "under_hit": tc_raw < actual,
            "notes": g.notes,
        })

    print(f"\n{'='*80}")
    print(f" WNBA TC BACKTEST — {len(results)} GAMES (DUMMY)")
    print(f" TC = pts×{CONS_PTS} + reb×{CONS_REB} + ast×{CONS_AST} + tpm×{CONS_3PM}")
    print(f"{'='*80}")
    print(f" {'Game':<12} {'Date':<12} {'Rnd':<7} {'TC_pts':>7} {'TC_reb':>7} "
          f"{'TC_ast':>7} {'TC_3pm':>7} {'TC_raw':>7} {'LINE':>6} {'Actual':>7} {'Diff':>7}")
    print(f" {'-'*80}")
    for r in results:
        print(f" {r['game']:<12} {r['date']:<12} {r['round']:<7} "
              f"{r['tc_pts']:>7.1f} {r['tc_reb']:>7.1f} {r['tc_ast']:>7.1f} {r['tc_3pm']:>7.1f} "
              f"{r['tc_raw']:>7.1f} {r['line']:>6} {r['actual']:>7} {r['diff']:>+7.1f}")

    under_count = sum(1 for r in results if r["under_hit"])
    avg_diff = sum(r["diff"] for r in results) / len(results)
    avg_tc = sum(r["tc_raw"] for r in results) / len(results)
    avg_actual = sum(r["actual"] for r in results) / len(results)

    print(f"\n TC_raw < Actual (UNDER hit): {under_count}/{len(results)} "
          f"({under_count/len(results)*100:.0f}%)")
    print(f" Avg TC_raw: {avg_tc:.1f}")
    print(f" Avg Actual: {avg_actual:.1f}")
    print(f" Avg Diff (actual - tc): {avg_diff:+.1f}")
    print(f" Historical Gap Used: {HISTORICAL_GAP}")
    print(f"{'='*80}\n")

    return {
        "results": results,
        "under_rate": under_count / len(results),
        "avg_diff": avg_diff,
        "avg_tc": avg_tc,
        "avg_actual": avg_actual,
    }

# ── REPORT GENERATOR ───────────────────────────────────────────────────────
def generate_tc_report(
    home: Team,
    away: Team,
    market_total: float,
    market_spread: str,
    series: str = "",
    game_time: str = "",
    injury_notes: List[str] = None,
    is_playoff: bool = False,
) -> str:
    if injury_notes is None:
        injury_notes = []

    tc_h = home.tc_total()
    tc_a = away.tc_total()
    tc_raw = round(tc_h + tc_a, 1)
    line = calc_line(tc_raw, is_home=True, is_playoff=is_playoff)
    edge = calc_edge(tc_raw, line)
    hr = hit_rate(tc_raw, line)

    lines = [
        "",
        "=" * 80,
        f" {away.abbr} @ {home.abbr} | {game_time}",
        f" Series: {series} | Total: {market_total} | Spread: {market_spread}",
        "=" * 80,
        "",
        f" TC Formula: pts x {CONS_PTS} + reb x {CONS_REB} + ast x {CONS_AST} + tpm x {CONS_3PM}",
        f" Historical Gap: +{HISTORICAL_GAP} pts | Home Pace Adj: x{PACE_ADJ_HOME} | "
        f"Playoff Pace Adj: x{PACE_ADJ_PLAYOFF}",
        "",
    ]

    for team_obj, is_home_flag in [(away, False), (home, True)]:
        tc_team = team_obj.tc_total()
        lines.append(f" -- {team_obj.abbr} {team_obj.name} "
                     f"{'(Home)' if is_home_flag else '(Away)'} --")
        lines.append(
            f" {'Player':<22} {'POS':<4} {'HT':<5} "
            f"{'PTS':>5} {'REB':>5} {'AST':>5} {'3PM':>5} "
            f"{'TC_pts':>7} {'TC_reb':>7} {'TC_ast':>7} {'TC_3pm':>7} {'TC_TOT':>7} "
            f"{'LINE':>6} {'EDGE':>6} {'HR':>4} {'Status':<7}"
        )
        lines.append(f" {'-'*110}")
        for p in team_obj.players:
            line_val = calc_line(p.tc_total(), is_home=is_home_flag, is_playoff=is_playoff)
            edge_val = calc_edge(p.tc_total(), line_val)
            hr_val = hit_rate(p.tc_total(), line_val)
            flag = "Q" if p.status == "QUESTIONABLE" else ("O" if p.status == "OUT" else "")
            lines.append(
                f" {p.name:<22} {p.pos:<4} {p.ht:<5} "
                f"{p.pts:>5.1f} {p.reb:>5.1f} {p.ast:>5.1f} {p.tpm:>5.1f} "
                f"{p.tc_pts():>7.1f} {p.tc_reb():>7.1f} {p.tc_ast():>7.1f} {p.tc_3pm():>7.1f} "
                f"{p.tc_total():>7.1f} {line_val:>6} {edge_val:>+6.1f} {hr_val:>4} {flag:<7}"
            )
        lines.append(
            f"\n Team TC: {tc_team:.1f} "
            f"(pts:{team_obj.tc_pts_total():.1f} + reb:{team_obj.tc_reb_total():.1f} "
            f"+ ast:{team_obj.tc_ast_total():.1f} + 3pm:{team_obj.tc_3pm_total():.1f})"
        )
        lines.append("")

    lines.extend([
        "=" * 80,
        " TC SYSTEM SUMMARY",
        "=" * 80,
        f" {away.abbr} TC: {tc_a:.1f} | {home.abbr} TC: {tc_h:.1f} | TC Combined: {tc_raw:.1f}",
        f" LINE (calibrated): {line} | Market Total: {market_total} | Edge: {edge:+.1f}",
        f" Hit Rate Est: {hr}%",
        f" Signal: {'OVER' if tc_raw > line else 'UNDER'} "
        f"(TC {'>' if tc_raw > line else '<'} LINE)",
        "",
    ])

    if injury_notes:
        lines.append(f" Key Injuries: {', '.join(injury_notes)}")

    lines.extend([
        "",
        f" Recommended: {'OVER' if tc_raw > line else 'UNDER'} "
        f"{market_total} (edge: {edge:+.1f} pts)",
        "",
    ])

    return "\n".join(lines)

# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WNBA TC Engine")
    parser.add_argument("--backtest", action="store_true", help="Run dummy WNBA backtest")
    parser.add_argument("--game", type=str, help="Generate TC report for matchup (e.g. 'MINL @ DALW')")
    parser.add_argument("--list-teams", action="store_true", help="List all WNBA teams")
    args = parser.parse_args()

    if args.backtest:
        run_backtest()

    elif args.game:
        parts = args.game.replace("@", " ").replace("vs", " ").replace("-", " ").split()
        if len(parts) < 2:
            print("Usage: --game 'AWAY @ HOME' (e.g. 'MINL @ DALW')")
            sys.exit(1)

        away_key = parts[0].upper()
        home_key = parts[1].upper()

        if away_key not in WNBA_TEAMS:
            print(f"Unknown away team: {away_key}")
            sys.exit(1)
        if home_key not in WNBA_TEAMS:
            print(f"Unknown home team: {home_key}")
            sys.exit(1)

        report = generate_tc_report(
            WNBA_TEAMS[home_key],
            WNBA_TEAMS[away_key],
            market_total=170.5,
            market_spread="TBD",
            series="Regular Season",
            game_time="TBD",
            injury_notes=WNBA_TEAMS[home_key].injury_notes
                         + WNBA_TEAMS[away_key].injury_notes,
            is_playoff=False,
        )
        print(report)

    elif args.list_teams:
        print("\nWNBA Teams in this TC file:")
        for abbr, team in WNBA_TEAMS.items():
            print(f" {abbr}: {team.name} ({len(team.players)} players)")
            if team.injury_notes:
                print(f"  Injuries: {', '.join(team.injury_notes)}")

    else:
        run_backtest()
        print("\nUsage:")
        print(" python wnba_tc.py --backtest           # Run dummy backtest")
        print(" python wnba_tc.py --game 'MINL @ DALW' # Generate TC report")
        print(" python wnba_tc.py --list-teams         # List WNBA teams")
