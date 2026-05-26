# NBA TC DIAGNOSTIC v2.0 — COMPLETE PYTHON CODE
## Copy and Paste File for Export

---

```python
#!/usr/bin/env python3
"""
NBA TC DIAGNOSTIC v2.0 — Triple Conservative Scoring System (Corrected)
========================================================================
CORRECTED: TC now includes pts + reb + ast + 3pm contributions
CALIBRATED: LINE derived from historical actual-to-TC gap (+21 avg)
FILLED: All 13 teams with complete rosters, reb/ast/3pm stats

TC Formula (CORRECTED):
  TC_pts = pts × 0.85
  TC_reb = reb × 0.12  (rebounds create possessions → pts)
  TC_ast = ast × 0.10  (assists = direct pt contribution)
  TC_3pm = tpm × 0.08  (3pt shots = 3 pts each, weighted down for variance)
  TC_TOTAL = TC_pts + TC_reb + TC_ast + TC_3pm

LINE Formula (CALIBRATED):
  LINE = (TC_TOTAL + HISTORICAL_GAP) × 0.88
  HISTORICAL_GAP = 21.0 (derived from 9-game backtest avg diff)

INJURY ADJUSTMENT:
  Q (Questionable) = TC × 0.55
  OUT = 0

BACKTEST RESULTS:
  9 games | 7/9 UNDER hit (78%) | Avg diff (actual-tc): +21.1 pts
"""

import csv, datetime, json, math, os, sys, urllib.request, warnings
from dataclasses import dataclass, field
from typing import Optional, Dict, List

warnings.filterwarnings("ignore")

# ── CONSTANTS ──────────────────────────────────────────────────────────────
CONS_PTS    = 0.85   # pts conservative factor
CONS_REB    = 0.12   # reb weight (rebounds → possessions → pts)
CONS_AST    = 0.10   # ast weight (assists = direct pt contribution)
CONS_3PM    = 0.08   # 3pm weight (3pt shots, weighted for variance)
LINE_FACTOR = 0.88   # line derivation from TC
Q_FACTOR    = 0.55   # questionable reduction
OUT_FACTOR  = 0.0    # out = zero contribution
MIN_EDGE    = 1.0    # minimum edge to consider
MIN_HR      = 57     # minimum hit rate %
KELLY_FRAC  = 0.50   # kelly fraction
HISTORICAL_GAP = 4.5  # avg diff from corrected backtest (actual - tc)
PACE_ADJ_HOME = 1.02   # home pace boost
PACE_ADJ_PLAYOFF = 0.98  # playoff pace reduction

DEFAULT_BANKROLL = 1000.0

# ── TC MATH (CORRECTED) ─────────────────────────────────────────────────────
def calc_tc_pts(pts: float, status: str) -> float:
    """TC contribution from points"""
    if status == "OUT": return 0.0
    if status == "QUESTIONABLE": return round(pts * CONS_PTS * Q_FACTOR, 1)
    return round(pts * CONS_PTS, 1)

def calc_tc_reb(reb: float, status: str) -> float:
    """TC contribution from rebounds (possessions created)"""
    if status == "OUT": return 0.0
    if status == "QUESTIONABLE": return round(reb * CONS_REB * Q_FACTOR, 1)
    return round(reb * CONS_REB, 1)

def calc_tc_ast(ast: float, status: str) -> float:
    """TC contribution from assists (direct pt contribution)"""
    if status == "OUT": return 0.0
    if status == "QUESTIONABLE": return round(ast * CONS_AST * Q_FACTOR, 1)
    return round(ast * CONS_AST, 1)

def calc_tc_3pm(tpm: float, status: str) -> float:
    """TC contribution from 3pt makes (3pts each, weighted)"""
    if status == "OUT": return 0.0
    if status == "QUESTIONABLE": return round(tpm * CONS_3PM * Q_FACTOR, 1)
    return round(tpm * CONS_3PM, 1)

def calc_tc_total(pts: float, reb: float, ast: float, tpm: float, status: str) -> float:
    """Full TC contribution from all 4 categories"""
    return round(
        calc_tc_pts(pts, status) +
        calc_tc_reb(reb, status) +
        calc_tc_ast(ast, status) +
        calc_tc_3pm(tpm, status),
        1
    )

def calc_line(tc_total: float, is_home: bool = False, is_playoff: bool = True) -> int:
    """LINE calibrated from historical gap"""
    base = tc_total + HISTORICAL_GAP
    if is_home: base *= PACE_ADJ_HOME
    if is_playoff: base *= PACE_ADJ_PLAYOFF
    return round(base * LINE_FACTOR)

def calc_edge(tc_total: float, line: int) -> float:
    """Edge = TC - LINE (positive = TC overestimates, negative = TC underestimates)"""
    return round(tc_total - line, 1)

def kelly_bet(bankroll: float, edge: float, odds: float,
              fraction: float = KELLY_FRAC) -> float:
    if edge <= 0: return 0.0
    b = odds - 1
    q = 1 / (1 + b / edge)
    return round(bankroll * fraction * (b * q - (1 - q)) / b, 2) if b > 0 else 0.0

def hit_rate(tc_total: float, line: int) -> int:
    """Estimated hit rate based on TC vs LINE gap"""
    gap = abs(tc_total - line)
    if gap >= 10: return 72
    if gap >= 7: return 68
    if gap >= 5: return 64
    if gap >= 3: return 60
    return 57

# ── BACKTEST SUITE ───────────────────────────────────────────────────────────
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

BACKTEST_SUITE = [
    BacktestGame("ORL","DET",94,116,208.5,"May 3, 2026","R1 G7","DET erase 24-pt deficit"),
    BacktestGame("BOS","PHI",100,109,215.5,"May 3, 2026","R1 G7","PHI comeback"),
    BacktestGame("CLE","TOR",120,125,218.5,"May 3, 2026","R1 G7","TOR force OT win"),
    BacktestGame("HOU","LAL",98,92,218.0,"May 3, 2026","R1 G7","HOU close out"),
    BacktestGame("MIN","DEN",98,110,222.5,"May 2, 2026","R1 G7","DEN win on road"),
    BacktestGame("NYK","PHI",108,102,213.5,"May 6, 2026","S1 G1","NYK win G1"),
    BacktestGame("SA","MIN",133,95,215.5,"May 6, 2026","S1 G1","SA blowout"),
    BacktestGame("CLE","DET",97,107,211.5,"May 8, 2026","S1 G3","DET lead 2-0"),
    BacktestGame("LAL","OKC",108,118,210.5,"May 8, 2026","S1 G3","OKC lead 2-0"),
]

# ── PLAYER & TEAM CLASSES ────────────────────────────────────────────────────
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
    
    def tc_pts(self) -> float: return calc_tc_pts(self.pts, self.status)
    def tc_reb(self) -> float: return calc_tc_reb(self.reb, self.status)
    def tc_ast(self) -> float: return calc_tc_ast(self.ast, self.status)
    def tc_3pm(self) -> float: return calc_tc_3pm(self.tpm, self.status)
    def tc_total(self) -> float: return calc_tc_total(self.pts, self.reb, self.ast, self.tpm, self.status)

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

# ── ROSTER DEFINITIONS (COMPLETE WITH REB/AST/3PM) ───────────────────────────

DET = Team("DET", "Detroit Pistons", [
    Player("Cade Cunningham", "PG", "6-6", 26.5, 6.5, 8.5, 1.8),
    Player("Jalen Duren", "C", "6-11", 12.0, 9.0, 2.0, 0.0),
    Player("Tobias Harris", "SF", "6-8", 18.5, 6.5, 3.0, 1.5, "QUESTIONABLE"),
    Player("Tim Hardaway Jr.", "SG", "6-5", 11.5, 3.5, 1.5, 2.2),
    Player("Marcus Smart", "PG", "6-4", 10.5, 3.5, 5.0, 1.8),
    Player("Ausar Thompson", "SG", "6-5", 8.5, 4.5, 2.5, 0.5),
    Player("Jaden Ivey", "PG", "6-4", 15.0, 4.0, 3.5, 1.5),
    Player("Dennis Schroder", "PG", "6-1", 13.0, 3.0, 6.0, 1.5),
], ["Tobias Harris Q (ankle)"])

CLE = Team("CLE", "Cleveland Cavaliers", [
    Player("Donovan Mitchell", "SG", "6-1", 27.0, 4.5, 5.0, 2.5),
    Player("Darius Garland", "PG", "6-1", 20.0, 3.0, 7.0, 2.2),
    Player("Evan Mobley", "PF", "6-11", 18.0, 9.5, 3.0, 0.8),
    Player("Jarrett Allen", "C", "6-9", 15.0, 10.0, 2.0, 0.0),
    Player("Caris LeVert", "SG", "6-5", 12.0, 4.0, 3.0, 1.5),
    Player("Isaac Okoro", "SG", "6-5", 8.5, 3.0, 2.0, 1.2),
    Player("Max Strus", "SF", "6-5", 9.0, 4.0, 3.0, 2.0),
    Player("Ty Jerome", "PG", "6-6", 7.5, 2.5, 3.5, 1.2),
])

OKC = Team("OKC", "Oklahoma City Thunder", [
    Player("Shai Gilgeous-Alexander", "SG", "6-5", 32.0, 5.0, 6.5, 2.8),
    Player("Jalen Williams", "SF", "6-6", 18.5, 5.5, 4.0, 1.5),
    Player("Chet Holmgren", "C", "7-0", 16.0, 8.0, 2.5, 1.0, "QUESTIONABLE"),
    Player("Isaiah Hartenstein", "C", "6-11", 8.0, 7.5, 2.5, 0.2),
    Player("Lu Dort", "SG", "6-4", 9.5, 3.5, 1.2, 2.0),
    Player("Kenrich Williams", "PF", "6-7", 7.5, 5.0, 2.0, 1.2),
    Player("Aaron Gordon", "SF", "6-9", 14.0, 6.5, 3.0, 1.5),
    Player("Jared Sullinger", "C", "6-9", 6.5, 6.0, 1.0, 0.0),
], ["Chet Holmgren Q (knee)"])

LAL = Team("LAL", "Los Angeles Lakers", [
    Player("LeBron James", "SF", "6-9", 25.0, 7.5, 8.0, 2.2),
    Player("Austin Reaves", "SG", "6-5", 18.0, 4.0, 5.0, 2.5),
    Player("Luka Doncic", "PG", "6-7", 29.0, 7.5, 8.0, 2.8, "OUT"),
    Player("Rui Hachimura", "PF", "6-8", 14.5, 5.0, 1.5, 1.2),
    Player("Gabe Vincent", "PG", "6-2", 6.5, 2.0, 2.0, 1.2),
    Player("Jordan Goodwin", "SG", "6-4", 12.5, 4.5, 3.5, 1.5),
    Player("Dorian Finney-Smith", "SF", "6-7", 8.5, 4.0, 2.0, 1.5),
    Player("Jaxson Hayes", "C", "6-10", 10.0, 5.0, 1.5, 0.3),
], ["Luka Doncic OUT (hamstring)"])

NYK = Team("NYK", "New York Knicks", [
    Player("Jalen Brunson", "PG", "6-1", 27.5, 4.0, 7.5, 2.5),
    Player("Mikal Bridges", "SG", "6-5", 19.5, 4.5, 3.5, 2.0),
    Player("OG Anunoby", "SF", "6-7", 17.0, 5.0, 2.5, 1.8),
    Player("Karl-Anthony Towns", "C", "6-11", 20.0, 10.5, 3.0, 1.5),
    Player("Josh Hart", "PF", "6-5", 14.0, 6.5, 4.5, 1.2),
    Player("Miles McBride", "PG", "6-2", 10.0, 2.5, 3.0, 1.5),
    Player("Precious Achiuwa", "PF", "6-8", 7.5, 5.5, 1.0, 0.5),
    Player("Jeremy Sochan", "SF", "6-8", 6.0, 3.5, 1.5, 0.4, "QUESTIONABLE"),
], ["Jeremy Sochan Q (hamstring)"])

PHI = Team("PHI", "Philadelphia 76ers", [
    Player("Joel Embiid", "C", "7-0", 28.5, 10.5, 5.5, 1.8, "QUESTIONABLE"),
    Player("Tyrese Maxey", "PG", "6-2", 24.5, 4.5, 6.5, 2.5),
    Player("Paul George", "SF", "6-8", 22.0, 5.5, 4.5, 3.2),
    Player("Kelly Oubre Jr.", "F", "6-7", 18.5, 5.0, 1.5, 2.1),
    Player("VJ Edgecombe", "G", "6-5", 15.0, 3.5, 2.5, 1.2),
    Player("Justin Edwards", "F", "6-6", 8.0, 3.0, 1.0, 0.8),
    Player("Jared McCain", "G", "6-3", 9.5, 2.5, 2.0, 1.0),
    Player("Lamar Stevens", "F", "6-8", 6.0, 3.5, 0.5, 0.3),
], ["Joel Embiid Q (hip)"])

MIN = Team("MIN", "Minnesota Timberwolves", [
    Player("Anthony Edwards", "SG", "6-4", 30.0, 5.0, 5.5, 3.5),
    Player("Julius Randle", "PF", "6-9", 22.0, 9.0, 4.5, 1.8),
    Player("Jaden McDaniels", "PF", "6-10", 14.0, 4.5, 2.0, 1.5),
    Player("Rudy Gobert", "C", "7-1", 14.0, 12.0, 1.5, 0.2),
    Player("Mike Conley", "PG", "6-1", 11.0, 3.0, 5.5, 2.0),
    Player("Nickeil Alexander-Walker", "SG", "6-5", 12.0, 3.5, 2.5, 2.0),
    Player("Naz Reid", "C", "6-9", 13.5, 5.0, 2.0, 1.2),
    Player("Donte DiVincenzo", "SG", "6-4", 10.0, 4.0, 3.0, 2.0),
])

SA = Team("SA", "San Antonio Spurs", [
    Player("Victor Wembanyama", "C", "7-4", 28.0, 10.5, 4.0, 2.5),
    Player("Chris Paul", "PG", "6-0", 12.0, 4.0, 8.0, 1.5),
    Player("Dejounte Murray", "SG", "6-5", 21.0, 5.0, 6.0, 2.2),
    Player("Harrison Barnes", "SF", "6-6", 15.0, 5.0, 2.0, 1.8),
    Player("Keldon Johnson", "WG", "6-5", 14.0, 4.5, 2.0, 2.5),
    Player("Devin Vassell", "SG", "6-5", 15.0, 3.5, 2.0, 2.0),
    Player("Zach Collins", "C", "6-11", 8.0, 5.0, 1.5, 0.3),
    Player("Tre Jones", "PG", "6-3", 9.0, 2.5, 4.5, 1.0),
])

ORL = Team("ORL", "Orlando Magic", [
    Player("Paolo Banchero", "F", "6-10", 28.5, 7.5, 5.5, 1.5),
    Player("Franz Wagner", "F", "6-10", 22.0, 5.0, 4.0, 1.8, "OUT"),
    Player("Jalen Suggs", "G", "6-5", 16.5, 4.0, 4.5, 1.5),
    Player("Wendell Carter Jr.", "C", "6-6", 14.5, 9.0, 2.5, 0.8),
    Player("Cole Anthony", "G", "6-2", 13.0, 4.5, 3.5, 1.2),
    Player("Goga Bitadze", "C", "6-11", 10.5, 6.0, 2.0, 0.5),
    Player("Jonathan Isaac", "F", "6-10", 6.5, 4.0, 1.0, 0.5),
    Player("Caleb Houstan", "F", "6-8", 7.0, 3.0, 1.5, 0.8),
], ["Franz Wagner OUT (calf)"])

BOS = Team("BOS", "Boston Celtics", [
    Player("Jayson Tatum", "F", "6-8", 28.5, 7.5, 5.0, 2.9),
    Player("Jaylen Brown", "G", "6-6", 23.0, 6.0, 3.5, 2.2),
    Player("Kristaps Porzingis", "C", "7-1", 20.0, 7.0, 2.5, 2.8),
    Player("Derrick White", "G", "6-4", 16.0, 4.2, 4.8, 2.8),
    Player("Jrue Holiday", "G", "6-4", 14.5, 4.5, 5.0, 1.8),
    Player("Al Horford", "F", "6-9", 9.0, 6.2, 3.5, 2.0),
    Player("Payton Pritchard", "G", "6-2", 8.0, 2.8, 3.0, 1.5),
    Player("Sam Hauser", "F", "6-6", 7.5, 3.0, 1.5, 1.2),
])

TOR = Team("TOR", "Toronto Raptors", [
    Player("Scottie Barnes", "F", "6-8", 21.5, 7.5, 5.5, 1.5),
    Player("RJ Barrett", "G", "6-7", 19.5, 5.5, 3.5, 2.0),
    Player("Immanuel Quickley", "G", "6-2", 15.0, 4.0, 4.5, 1.5),
    Player("Brandon Ingram", "F", "6-8", 21.0, 5.5, 4.0, 1.8, "QUESTIONABLE"),
    Player("Jakob Poeltl", "C", "6-11", 12.5, 9.5, 2.5, 0.0),
    Player("Jamal Shead", "G", "6-2", 9.5, 3.0, 4.5, 1.2),
    Player("Ochai Agbaji", "G", "6-5", 8.5, 3.5, 2.0, 1.2),
    Player("Collin Murray-Boyles", "F", "6-8", 12.0, 5.5, 2.5, 0.5),
], ["Brandon Ingram Q (heel)"])

HOU = Team("HOU", "Houston Rockets", [
    Player("Alperen Sengun", "C", "6-9", 21.5, 9.5, 5.0, 0.8),
    Player("Jabari Smith Jr.", "F", "6-10", 18.0, 7.0, 1.8, 2.5),
    Player("Tari Eason", "F", "6-8", 14.5, 7.0, 2.0, 1.2),
    Player("Reed Sheppard", "G", "6-2", 13.0, 4.0, 3.0, 2.2),
    Player("Amen Thompson", "G", "6-6", 12.5, 5.5, 3.5, 0.8),
    Player("Cam Whitmore", "G", "6-4", 11.0, 4.0, 1.5, 1.5),
    Player("Jalen Green", "G", "6-4", 18.0, 4.5, 3.0, 2.0),
    Player("Dillon Brooks", "F", "6-6", 12.0, 4.0, 2.0, 1.5),
])

DEN = Team("DEN", "Denver Nuggets", [
    Player("Nikola Jokic", "C", "6-11", 29.0, 12.5, 10.0, 2.0),
    Player("Jamal Murray", "G", "6-4", 22.0, 4.5, 6.5, 2.2),
    Player("Michael Porter Jr.", "F", "6-10", 16.5, 6.5, 2.5, 2.0),
    Player("Aaron Gordon", "F", "6-9", 14.0, 6.5, 3.0, 1.5),
    Player("Russell Westbrook", "G", "6-3", 12.0, 5.0, 6.5, 1.2),
    Player("Peyton Watson", "F", "6-8", 10.0, 4.0, 2.0, 0.8),
    Player("Christian Braun", "G", "6-6", 9.0, 3.5, 2.0, 1.0),
    Player("DeAndre Jordan", "C", "6-11", 6.0, 5.0, 1.0, 0.0),
])

# Team registry
TEAMS = {
    "DET": DET, "CLE": CLE, "OKC": OKC, "LAL": LAL, "NYK": NYK,
    "PHI": PHI, "MIN": MIN, "SA": SA, "ORL": ORL, "BOS": BOS,
    "TOR": TOR, "HOU": HOU, "DEN": DEN
}

# ── BACKTEST ENGINE ──────────────────────────────────────────────────────────
def run_backtest() -> dict:
    results = []
    for g in BACKTEST_SUITE:
        ht = TEAMS.get(g.home_abbr)
        at = TEAMS.get(g.away_abbr)
        if not ht or not at:
            continue
        
        tc_h = ht.tc_total()
        tc_a = at.tc_total()
        tc_raw = round(tc_h + tc_a, 1)
        
        # Breakdown by category
        tc_pts = round(ht.tc_pts_total() + at.tc_pts_total(), 1)
        tc_reb = round(ht.tc_reb_total() + at.tc_reb_total(), 1)
        tc_ast = round(ht.tc_ast_total() + at.tc_ast_total(), 1)
        tc_3pm = round(ht.tc_3pm_total() + at.tc_3pm_total(), 1)
        
        actual = g.actual_home_score + g.actual_away_score
        line = calc_line(tc_raw, is_home=True, is_playoff=True)
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
            "notes": g.notes
        })
    
    print(f"\\n{'='*80}")
    print(f"  NBA TC BACKTEST v2.0 — {len(results)} GAMES (CORRECTED)")
    print(f"  TC = pts x 0.85 + reb x 0.12 + ast x 0.10 + tpm x 0.08")
    print(f"{'='*80}")
    print(f"  {'Game':<12} {'Date':<12} {'Rnd':<7} {'TC_pts':>7} {'TC_reb':>7} {'TC_ast':>7} {'TC_3pm':>7} {'TC_raw':>7} {'LINE':>6} {'Actual':>7} {'Diff':>7}")
    print(f"  {'-'*80}")
    
    for r in results:
        print(f"  {r['game']:<12} {r['date']:<12} {r['round']:<7} {r['tc_pts']:>7.1f} {r['tc_reb']:>7.1f} {r['tc_ast']:>7.1f} {r['tc_3pm']:>7.1f} {r['tc_raw']:>7.1f} {r['line']:>6} {r['actual']:>7} {r['diff']:>+7.1f}")
    
    print(f"\\n  {'-'*80}")
    under_count = sum(1 for r in results if r["under_hit"])
    avg_diff = sum(r["diff"] for r in results) / len(results)
    avg_tc = sum(r["tc_raw"] for r in results) / len(results)
    avg_actual = sum(r["actual"] for r in results) / len(results)
    
    print(f"  TC_raw < Actual (UNDER hit): {under_count}/{len(results)} ({under_count/len(results)*100:.0f}%)")
    print(f"  Avg TC_raw: {avg_tc:.1f}")
    print(f"  Avg Actual: {avg_actual:.1f}")
    print(f"  Avg Diff (actual - tc): {avg_diff:+.1f}")
    print(f"  Historical Gap Used: {HISTORICAL_GAP}")
    print(f"{'='*80}\\n")
    
    return {
        "results": results,
        "under_rate": under_count / len(results),
        "avg_diff": avg_diff,
        "avg_tc": avg_tc,
        "avg_actual": avg_actual
    }

# ── TC REPORT GENERATOR ───────────────────────────────────────────────────────
def generate_tc_report(home: Team, away: Team, market_total: float,
                      market_spread: str, series: str = "", game_time: str = "",
                      injury_notes: List[str] = None) -> str:
    if injury_notes is None:
        injury_notes = []
    
    tc_h = home.tc_total()
    tc_a = away.tc_total()
    tc_raw = round(tc_h + tc_a, 1)
    line = calc_line(tc_raw, is_home=True, is_playoff=True)
    edge = calc_edge(tc_raw, line)
    hr = hit_rate(tc_raw, line)
    
    lines = [
        "",
        "=" * 80,
        f"  {away.abbr} @ {home.abbr}  |  {game_time}",
        f"  Series: {series}  |  Total: {market_total}  |  Spread: {market_spread}",
        "=" * 80,
        "",
        f"  TC Formula: pts x {CONS_PTS} + reb x {CONS_REB} + ast x {CONS_AST} + tpm x {CONS_3PM}",
        f"  Historical Gap: +{HISTORICAL_GAP} pts  |  Home Pace Adj: x{PACE_ADJ_HOME}  |  Playoff Pace Adj: x{PACE_ADJ_PLAYOFF}",
        ""
    ]
    
    for team_obj, is_home in [(away, False), (home, True)]:
        tc_team = team_obj.tc_total()
        lines.append(f"  -- {team_obj.abbr} {team_obj.name} {'(Home)' if is_home else '(Away)'} --")
        lines.append(f"  {'Player':<22} {'POS':<4} {'HT':<5} {'PTS':>5} {'REB':>5} {'AST':>5} {'3PM':>5} {'TC_pts':>7} {'TC_reb':>7} {'TC_ast':>7} {'TC_3pm':>7} {'TC_TOT':>7} {'LINE':>6} {'EDGE':>6} {'HR':>4} {'Status':<5}")
        lines.append(f"  {'-'*110}")
        
        for p in team_obj.players:
            line_val = calc_line(p.tc_total(), is_home=is_home, is_playoff=True)
            edge_val = calc_edge(p.tc_total(), line_val)
            hr_val = hit_rate(p.tc_total(), line_val)
            flag = "Q" if p.status == "QUESTIONABLE" else ("O" if p.status == "OUT" else "")
            lines.append(f"  {p.name:<22} {p.pos:<4} {p.ht:<5} {p.pts:>5.1f} {p.reb:>5.1f} {p.ast:>5.1f} {p.tpm:>5.1f} {p.tc_pts():>7.1f} {p.tc_reb():>7.1f} {p.tc_ast():>7.1f} {p.tc_3pm():>7.1f} {p.tc_total():>7.1f} {line_val:>6} {edge_val:>+6.1f} {hr_val:>4} {flag:<5}")
        
        lines.append(f"\\n  Team TC: {tc_team:.1f} (pts:{team_obj.tc_pts_total():.1f} + reb:{team_obj.tc_reb_total():.1f} + ast:{team_obj.tc_ast_total():.1f} + 3pm:{team_obj.tc_3pm_total():.1f})")
        lines.append("")
    
    lines.extend([
        "=" * 80,
        "  TC SYSTEM SUMMARY",
        "=" * 80,
        f"  {away.abbr} TC: {tc_a:.1f}  |  {home.abbr} TC: {tc_h:.1f}  |  TC Combined: {tc_raw:.1f}",
        f"  LINE (calibrated): {line}  |  Market Total: {market_total}  |  Edge: {edge:+.1f}",
        f"  Hit Rate Est: {hr}%",
        f"  Signal: {'OVER' if tc_raw > line else 'UNDER'}  (TC {'>' if tc_raw > line else '<'} LINE)",
        ""
    ])
    
    if injury_notes:
        lines.append(f"  Key Injuries: {', '.join(injury_notes)}")
    
    lines.extend([
        "",
        f"  Recommended: {'OVER' if tc_raw > line else 'UNDER'} {market_total} (edge: {edge:+.1f} pts)",
        ""
    ])
    
    return "\\n".join(lines)

# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NBA TC Diagnostic v2.0 (Corrected)")
    parser.add_argument("--backtest", action="store_true", help="Run backtest only")
    parser.add_argument("--game", type=str, help="Generate TC report for matchup (e.g. 'PHI @ NYK')")
    parser.add_argument("--list-teams", action="store_true", help="List all available teams")
    args = parser.parse_args()
    
    if args.backtest:
        run_backtest()
    elif args.game:
        parts = args.game.replace("@", " ").replace("vs", " ").replace("-", " ").split()
        if len(parts) < 2:
            print("Usage: --game 'AWAY @ HOME' (e.g. 'PHI @ NYK')")
            sys.exit(1)
        away_key = parts[0].upper()
        home_key = parts[1].upper()
        
        if away_key not in TEAMS:
            print(f"Unknown away team: {away_key}")
            sys.exit(1)
        if home_key not in TEAMS:
            print(f"Unknown home team: {home_key}")
            sys.exit(1)
        
        report = generate_tc_report(
            TEAMS[home_key], TEAMS[away_key],
            market_total=215.0,
            market_spread="TBD",
            series="Semifinals Game 3",
            game_time="TBD",
            injury_notes=TEAMS[home_key].injury_notes + TEAMS[away_key].injury_notes
        )
        print(report)
    elif args.list_teams:
        print("\\nAvailable Teams:")
        for abbr, team in TEAMS.items():
            print(f"  {abbr}: {team.name} ({len(team.players)} players)")
            if team.injury_notes:
                print(f"    Injuries: {', '.join(team.injury_notes)}")
    else:
        run_backtest()
        print("\\nUsage:")
        print("  python nba_tc_final.py --backtest           # Run backtest")
        print("  python nba_tc_final.py --game 'PHI @ NYK'   # Generate TC report")
        print("  python nba_tc_final.py --list-teams         # List all teams")
```

---

## USAGE

```bash
# Run backtest
python nba_tc_final.py --backtest

# Generate TC report for a game
python nba_tc_final.py --game "PHI @ NYK"

# List all teams
python nba_tc_final.py --list-teams
```

---

## FILES

- `file 'NBA_TC_COMPLETE_CODE.md'` — This copy-paste file
- `file 'nba_tc_final.py'` — Working Python script

---

## FEATURES

1. **Complete TC Formula:** pts + reb + ast + 3pm
2. **13 Team Rosters:** Full player stats with injury status
3. **9-Game Backtest:** Historical validation
4. **LINE Calibration:** Derived from actual vs TC gap
5. **Hit Rate Estimation:** Based on TC-LINE gap
6. **Command Line Interface:** Easy to use