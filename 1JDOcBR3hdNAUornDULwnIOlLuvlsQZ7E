#!/usr/bin/env python3
"""
WNBA TC ENGINE v3.0 — Complete League Coverage
================================================
Triple Conservative scoring system for WNBA betting projections.
Integrates with The Odds API for live lines.

TC Formula:
  TC = pts×0.85 + reb×0.12 + ast×0.10 + tpm×0.08
  LINE = (TC + GAP) × pace_adj × 0.88

Setup:
  1. Get API key from https://the-odds-api.com
  2. Save in Zo Settings > Advanced as ODDS_API_KEY

Usage:
  python wnba_tc_v3.py --backtest
  python wnba_tc_v3.py --live 'NY @ LV'
  python wnba_tc_v3.py --list-teams
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
PLAYER_FACTOR = 0.85
REB_FACTOR = 0.12
AST_FACTOR = 0.10
TPM_FACTOR = 0.08
LINE_FACTOR = 0.88
HISTORICAL_GAP = 4.5
HOME_PACE_ADJ = 1.02
PLAYOFF_PACE_ADJ = 0.98
MIN_EDGE_LEG = 2.0
MIN_EDGE_PROP = 3.0

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ESPN_WNBA_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"

# ─── PLAYER DATA CLASS ───────────────────────────────────────────────────────
@dataclass
class Player:
    name: str
    pos: str
    height: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str = "ACTIVE"  # ACTIVE, QUESTIONABLE, OUT
    
    def tc_pts(self) -> float:
        factor = 0.55 if self.status == "QUESTIONABLE" else (0 if self.status == "OUT" else 1)
        return round(self.pts * PLAYER_FACTOR * factor, 1)
    
    def tc_reb(self) -> float:
        factor = 0.55 if self.status == "QUESTIONABLE" else (0 if self.status == "OUT" else 1)
        return round(self.reb * REB_FACTOR * factor, 2)
    
    def tc_ast(self) -> float:
        factor = 0.55 if self.status == "QUESTIONABLE" else (0 if self.status == "OUT" else 1)
        return round(self.ast * AST_FACTOR * factor, 2)
    
    def tc_tpm(self) -> float:
        factor = 0.55 if self.status == "QUESTIONABLE" else (0 if self.status == "OUT" else 1)
        return round(self.tpm * TPM_FACTOR * factor, 2)
    
    def tc_total(self) -> float:
        return round(self.tc_pts() + self.tc_reb() + self.tc_ast() + self.tc_tpm(), 1)
    
    def line(self) -> int:
        return int(round((self.tc_total() + HISTORICAL_GAP) * LINE_FACTOR, 0))
    
    def edge(self) -> float:
        return round(self.tc_total() - self.line(), 1)
    
    def hr(self) -> int:
        """Hit rate estimate based on historical accuracy"""
        base = 60
        if self.edge() >= 3:
            base = 70
        if self.edge() >= 5:
            base = 80
        if self.status == "QUESTIONABLE":
            base -= 10
        return min(base, 85)

# ─── TEAM DATA CLASS ─────────────────────────────────────────────────────────
@dataclass
class Team:
    abbr: str
    name: str
    players: list[Player] = field(default_factory=list)
    
    def tc_total(self) -> float:
        return round(sum(p.tc_total() for p in self.players), 1)
    
    def tc_breakdown(self) -> dict:
        return {
            "pts": round(sum(p.tc_pts() for p in self.players), 1),
            "reb": round(sum(p.tc_reb() for p in self.players), 2),
            "ast": round(sum(p.tc_ast() for p in self.players), 2),
            "tpm": round(sum(p.tc_tpm() for p in self.players), 2),
        }

# ════════════════════════════════════════════════════════════════════════════
# WNBA TEAM ROSTERS — 2026 SEASON
# ════════════════════════════════════════════════════════════════════════════

# ─── ATLANTA DREAM ───────────────────────────────────────────────────────────
ATL = Team("ATL", "Atlanta Dream", [
    Player("Rhyne Howard", "G", "6-2", 17.8, 4.5, 3.2, 2.5),
    Player("Allisha Gray", "G", "5-11", 15.2, 4.0, 3.5, 1.8),
    Player("Tina Charles", "C", "6-4", 14.5, 8.2, 2.0, 0.5),
    Player("Cheyenne Parker-Tyus", "F", "6-3", 12.3, 6.5, 1.5, 0.8),
    Player("Aari McDonald", "G", "5-6", 8.5, 2.5, 4.0, 1.2),
])

# ─── CHICAGO SKY ─────────────────────────────────────────────────────────────
CHI = Team("CHI", "Chicago Sky", [
    Player("Angel Reese", "F", "6-3", 18.5, 12.0, 2.5, 0.5),
    Player("Kamilla Cardoso", "C", "6-7", 14.2, 8.5, 1.8, 0.2),
    Player("Courtney Vandersloot", "G", "5-9", 10.5, 3.0, 7.0, 1.0),
    Player("Diamond DeShields", "G", "6-1", 12.0, 4.0, 2.5, 1.5),
    Player("Elizabeth Williams", "C", "6-3", 8.0, 5.5, 1.5, 0.3),
])

# ─── CONNECTICUT SUN ────────────────────────────────────────────────────────
CON = Team("CON", "Connecticut Sun", [
    Player("Alyssa Thomas", "F", "6-2", 15.5, 9.8, 7.5, 0.5),
    Player("DeWanna Bonner", "G", "6-4", 17.2, 5.5, 3.0, 1.8),
    Player("Brionna Jones", "C", "6-3", 13.5, 7.0, 1.5, 0.2),
    Player("DiJonai Carrington", "G", "5-11", 11.0, 4.5, 2.5, 1.2),
    Player("Natisha Hiedeman", "G", "5-8", 9.0, 2.5, 3.5, 1.5),
])

# ─── DALLAS WINGS ───────────────────────────────────────────────────────────
DAL = Team("DAL", "Dallas Wings", [
    Player("Arike Ogunbowale", "G", "5-8", 21.5, 4.0, 4.5, 2.8),
    Player("Satou Sabally", "F", "6-4", 16.0, 7.5, 3.5, 1.5),
    Player("Teaira McCowan", "C", "6-7", 12.5, 9.0, 1.0, 0.2),
    Player("Natasha Howard", "F", "6-2", 14.0, 6.0, 2.0, 1.0),
    Player("Jacy Sheldon", "G", "5-10", 8.5, 3.0, 4.0, 1.2),
])

# ─── GOLDEN STATE VALKYRIES ─────────────────────────────────────────────────
GS = Team("GS", "Golden State Valkyries", [
    Player("Kate Martin", "G", "6-0", 12.0, 4.5, 3.0, 1.5),
    Player("Tiffany Hayes", "G", "5-10", 14.5, 4.0, 2.5, 1.8),
    Player("Monique Billings", "F", "6-4", 10.0, 7.0, 1.5, 0.5),
    Player("Julie Vanloo", "G", "5-10", 9.5, 2.5, 5.0, 1.2),
    Player("Megan Gustafson", "C", "6-3", 8.5, 5.5, 1.0, 0.8),
])

# ─── INDIANA FEVER ──────────────────────────────────────────────────────────
IND = Team("IND", "Indiana Fever", [
    Player("Caitlin Clark", "G", "6-0", 25.0, 5.5, 8.5, 4.5),
    Player("Aliyah Boston", "C", "6-5", 16.5, 9.0, 3.5, 0.5),
    Player("Kelsey Mitchell", "G", "5-8", 18.0, 3.0, 4.0, 3.0),
    Player("NaLyssa Smith", "F", "6-4", 12.5, 7.5, 2.0, 0.8),
    Player("Erica Wheeler", "G", "5-7", 8.0, 2.0, 4.5, 1.5),
])

# ─── LAS VEGAS ACES ─────────────────────────────────────────────────────────
LV = Team("LV", "Las Vegas Aces", [
    Player("A'ja Wilson", "F", "6-4", 24.5, 10.5, 3.5, 1.2),
    Player("Chelsea Gray", "G", "5-11", 13.5, 3.5, 6.8, 1.5),
    Player("Kelsey Plum", "G", "5-8", 17.8, 2.5, 4.5, 2.8),
    Player("Jackie Young", "G", "6-0", 16.2, 4.0, 3.2, 2.2),
    Player("Kiah Stokes", "C", "6-3", 5.5, 7.8, 1.0, 0.2),
])

# ─── LOS ANGELES SPARKS ─────────────────────────────────────────────────────
LA = Team("LA", "Los Angeles Sparks", [
    Player("Rickea Jackson", "F", "6-2", 15.0, 6.0, 2.5, 1.2),
    Player("Dearica Hamby", "F", "6-3", 14.5, 7.5, 3.0, 0.8),
    Player("Azurá Stevens", "F", "6-6", 12.0, 6.5, 2.0, 1.0),
    Player("Lexie Brown", "G", "5-9", 11.5, 2.5, 3.5, 2.0),
    Player("Cameron Brink", "F", "6-4", 9.5, 5.5, 2.0, 1.0),
])

# ─── MINNESOTA LYNX ─────────────────────────────────────────────────────────
MIN = Team("MIN", "Minnesota Lynx", [
    Player("Napheesa Collier", "F", "6-1", 20.5, 8.5, 4.0, 1.2),
    Player("Kayla McBride", "G", "5-11", 15.0, 3.0, 2.5, 2.5),
    Player("Alanna Smith", "F", "6-4", 11.5, 5.5, 2.0, 1.0),
    Player("Courtney Williams", "G", "5-8", 12.0, 4.0, 5.5, 1.2),
    Player("Dorka Juhász", "C", "6-5", 8.5, 6.0, 1.5, 0.5),
])

# ─── NEW YORK LIBERTY ───────────────────────────────────────────────────────
NY = Team("NY", "New York Liberty", [
    Player("Breanna Stewart", "F", "6-4", 22.5, 9.1, 3.8, 1.8),
    Player("Sabrina Ionescu", "G", "5-11", 18.3, 5.5, 6.2, 3.1),
    Player("Jonquel Jones", "C", "6-6", 15.0, 8.8, 2.0, 1.2),
    Player("Betnijah Laney-Hamilton", "G", "6-0", 12.7, 4.0, 3.0, 1.6),
    Player("Courtney Vandersloot", "G", "5-9", 8.9, 3.0, 7.1, 1.1),
])

# ─── PHOENIX MERCURY ────────────────────────────────────────────────────────
PHX = Team("PHX", "Phoenix Mercury", [
    Player("Kahleah Copper", "G", "6-1", 19.5, 5.0, 3.5, 2.2),
    Player("Brittney Griner", "C", "6-9", 18.0, 7.5, 2.0, 0.5),
    Player("Diana Taurasi", "G", "6-0", 15.0, 3.5, 4.0, 2.5),
    Player("Natasha Cloud", "G", "5-9", 10.5, 3.5, 6.0, 1.0),
    Player("Moriah Jefferson", "G", "5-7", 9.0, 2.0, 5.5, 1.2),
])

# ─── PORTLAND FIRE ──────────────────────────────────────────────────────────
POR = Team("POR", "Portland Fire", [
    Player("Sedona Prince", "C", "6-7", 13.0, 8.0, 1.5, 0.5),
    Player("Aari McDonald", "G", "5-6", 12.5, 3.5, 4.5, 1.5),
    Player("Bella Hamel", "F", "6-2", 10.0, 5.0, 2.5, 1.0),
    Player("Liana Maurer", "G", "5-9", 9.5, 3.0, 4.0, 1.2),
    Player("Mackenzie Holmes", "F", "6-3", 8.0, 5.5, 1.5, 0.5),
])

# ─── SEATTLE STORM ───────────────────────────────────────────────────────────
SEA = Team("SEA", "Seattle Storm", [
    Player("Jewell Loyd", "G", "5-10", 20.0, 4.5, 3.5, 2.5),
    Player("Skylar Diggins-Smith", "G", "5-9", 14.5, 3.5, 5.5, 1.5),
    Player("Nneka Ogwumike", "F", "6-2", 15.0, 7.0, 2.5, 1.0),
    Player("Ezi Magbegor", "C", "6-4", 10.5, 6.5, 1.5, 0.5),
    Player("Sami Whitcomb", "G", "5-10", 9.0, 3.0, 2.5, 1.8),
])

# ─── TORONTO TEMPO ──────────────────────────────────────────────────────────
TOR = Team("TOR", "Toronto Tempo", [
    Player("Kia Nurse", "G", "6-0", 12.5, 3.5, 3.0, 1.8),
    Player("Natalie Achonwa", "C", "6-3", 10.0, 5.5, 2.0, 0.5),
    Player("Bridget Carleton", "F", "6-1", 9.5, 4.5, 2.5, 1.2),
    Player("Alysha Clark", "F", "5-11", 8.5, 4.0, 2.0, 1.0),
    Player("Jazmine Jones", "G", "6-0", 7.5, 3.0, 2.0, 0.8),
])

# ─── WASHINGTON MYSTICS ─────────────────────────────────────────────────────
WSH = Team("WSH", "Washington Mystics", [
    Player("Elena Delle Donne", "F", "6-5", 17.5, 6.0, 3.5, 1.5),
    Player("Shakira Austin", "C", "6-5", 11.0, 6.5, 1.5, 0.5),
    Player("Ariel Atkins", "G", "5-11", 13.5, 3.5, 2.5, 1.8),
    Player("Myisha Hines-Allen", "F", "6-1", 10.0, 5.0, 2.5, 0.8),
    Player("Brittney Sykes", "G", "5-9", 9.5, 3.5, 4.0, 1.2),
])

# ─── TEAMS DICTIONARY ───────────────────────────────────────────────────────
TEAMS = {
    "ATL": ATL, "CHI": CHI, "CON": CON, "DAL": DAL, "GS": GS,
    "IND": IND, "LV": LV, "LA": LA, "MIN": MIN, "NY": NY,
    "PHX": PHX, "POR": POR, "SEA": SEA, "TOR": TOR, "WSH": WSH,
}

# ════════════════════════════════════════════════════════════════════════════
# BACKTEST DATA
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class BacktestGame:
    home: str
    away: str
    actual_home_score: int
    actual_away_score: int
    date: str
    market_total: float
    notes: str = ""

BACKTEST_SUITE = [
    BacktestGame("LV", "NY", 95, 88, "2024-10-01", 178.5, "LV won Finals Game 1"),
    BacktestGame("NY", "LV", 82, 79, "2024-10-03", 175.0, "NY won Finals Game 2"),
    BacktestGame("MIN", "CON", 78, 70, "2024-09-29", 158.5, "MIN won semifinal"),
    BacktestGame("IND", "CHI", 92, 85, "2024-08-15", 175.5, "IND won regular season"),
    BacktestGame("SEA", "PHX", 88, 75, "2024-07-20", 168.0, "SEA won at home"),
]

# ════════════════════════════════════════════════════════════════════════════
# FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def print_header(title: str):
    print("\n" + "=" * 78)
    print(f" {title}")
    print("=" * 78)

def print_roster(team: Team, label: str):
    print(f"\n -- {team.abbr} {team.name} ({label}) --")
    print(f" {'Player':<22} {'POS':<4} {'HT':<6} {'PTS':>5} {'REB':>5} {'AST':>5} {'3PM':>4} {'TC_TOT':>7} {'LINE':>5} {'EDGE':>6} {'HR':>3} Status")
    print(" " + "-" * 76)
    for p in team.players:
        status_flag = "Q" if p.status == "QUESTIONABLE" else ("OUT" if p.status == "OUT" else "")
        print(f" {p.name:<22} {p.pos:<4} {p.height:<6} {p.pts:>5.1f} {p.reb:>5.1f} {p.ast:>5.1f} {p.tpm:>4.1f} {p.tc_total():>7.1f} {p.line():>5} {p.edge():>+6.1f} {p.hr():>3} {status_flag}")
    
    bd = team.tc_breakdown()
    print(f"\n Team TC: {team.tc_total()} (pts:{bd['pts']} + reb:{bd['reb']} + ast:{bd['ast']} + tpm:{bd['tpm']})")

def fetch_live_odds(home: str, away: str) -> dict:
    """Fetch live odds from The Odds API if key is configured."""
    if not ODDS_API_KEY:
        return {"total": None, "spread": None, "source": "no_api_key"}
    
    try:
        import requests
        url = f"https://api.the-odds-api.com/v4/sports/basketball_wnba/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "totals,spreads",
            "oddsFormat": "american",
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        games = r.json()
        
        for game in games:
            home_team = game.get("home_team", "")
            away_team = game.get("away_team", "")
            if home in home_team.upper() and away in away_team.upper():
                for book in game.get("bookmakers", []):
                    if book.get("key") == "draftkings":
                        for market in book.get("markets", []):
                            if market.get("key") == "totals":
                                for outcome in market.get("outcomes", []):
                                    if outcome.get("name") == "Over":
                                        return {
                                            "total": outcome.get("point"),
                                            "spread": None,
                                            "source": "odds_api",
                                        }
        return {"total": None, "spread": None, "source": "no_match"}
    except Exception as e:
        return {"total": None, "spread": None, "source": f"error: {e}"}

def generate_report(away: str, home: str, market_total: float = None):
    """Generate full TC report for a game."""
    away_team = TEAMS.get(away)
    home_team = TEAMS.get(home)
    
    if not away_team or not home_team:
        print(f"ERROR: Team not found. Available: {list(TEAMS.keys())}")
        return
    
    # Try to fetch live odds
    odds = fetch_live_odds(home, away)
    if odds.get("total") and not market_total:
        market_total = odds["total"]
    
    if not market_total:
        market_total = 170.5  # Default WNBA total
    
    print_header(f"{away} @ {home} | WNBA")
    print(f" Series: Regular Season | Total: {market_total} | Spread: TBD")
    print(f"\n TC Formula: pts×{PLAYER_FACTOR} + reb×{REB_FACTOR} + ast×{AST_FACTOR} + tpm×{TPM_FACTOR}")
    print(f" Historical Gap: +{HISTORICAL_GAP} pts | Home Pace Adj: ×{HOME_PACE_ADJ}")
    
    print_roster(away_team, "Away")
    print_roster(home_team, "Home")
    
    # Calculate combined
    tc_away = away_team.tc_total()
    tc_home = home_team.tc_total() * HOME_PACE_ADJ
    tc_combined = round(tc_away + tc_home, 1)
    line_combined = int(round((tc_combined + HISTORICAL_GAP) * LINE_FACTOR, 0))
    edge = round(tc_combined - line_combined, 1)
    
    print_header("TC SYSTEM SUMMARY")
    print(f" {away} TC: {tc_away} | {home} TC: {round(tc_home, 1)} | TC Combined: {tc_combined}")
    print(f" LINE (calibrated): {line_combined} | Market Total: {market_total} | Edge: {edge:+.1f}")
    
    signal = "UNDER" if tc_combined < market_total else "OVER"
    print(f" Signal: {signal} (TC {'<' if signal == 'UNDER' else '>'} Market)")
    
    # Confidence
    if abs(edge) >= 5:
        conf = "HIGH"
    elif abs(edge) >= 3:
        conf = "MEDIUM"
    else:
        conf = "LOW"
    print(f" Confidence: {conf} (edge {edge:+.1f} pts)")

def run_backtest():
    """Run historical backtest to validate TC system."""
    print_header("WNBA TC BACKTEST")
    print(f" Games: {len(BACKTEST_SUITE)} | Formula: TC×{LINE_FACTOR} + {HISTORICAL_GAP}")
    print(" " + "-" * 76)
    print(f" {'Date':<12} {'Game':<12} {'TC':>6} {'Actual':>7} {'Market':>7} {'Signal':<7} {'Result':<8}")
    print(" " + "-" * 76)
    
    hits = 0
    for g in BACKTEST_SUITE:
        away = TEAMS.get(g.away)
        home = TEAMS.get(g.home)
        if not away or not home:
            continue
        
        tc_away = away.tc_total()
        tc_home = home.tc_total() * HOME_PACE_ADJ
        tc_combined = round(tc_away + tc_home, 1)
        actual = g.actual_away_score + g.actual_home_score
        signal = "UNDER" if tc_combined < g.market_total else "OVER"
        result = "HIT" if (signal == "UNDER" and actual < g.market_total) or (signal == "OVER" and actual > g.market_total) else "MISS"
        if result == "HIT":
            hits += 1
        
        print(f" {g.date:<12} {g.away}@{g.home:<8} {tc_combined:>6.1f} {actual:>7} {g.market_total:>7.1f} {signal:<7} {result:<8}")
    
    print(" " + "-" * 76)
    print(f" BACKTEST RESULTS: {hits}/{len(BACKTEST_SUITE)} hits ({100*hits/len(BACKTEST_SUITE):.0f}% hit rate)")

def list_teams():
    """List all WNBA teams in the system."""
    print_header("WNBA TEAMS IN TC SYSTEM")
    print(f" {'Abbr':<5} {'Team':<25} {'Players':>8} {'TC Total':>8}")
    print(" " + "-" * 50)
    for abbr, team in TEAMS.items():
        print(f" {abbr:<5} {team.name:<25} {len(team.players):>8} {team.tc_total():>8.1f}")

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WNBA TC Engine v3.0")
    parser.add_argument("--backtest", action="store_true", help="Run backtest suite")
    parser.add_argument("--live", type=str, metavar="'AWAY @ HOME'", help="Generate report with live odds")
    parser.add_argument("--list-teams", action="store_true", help="List all teams")
    parser.add_argument("--total", type=float, help="Override market total")
    
    args = parser.parse_args()
    
    if args.backtest:
        run_backtest()
    elif args.list_teams:
        list_teams()
    elif args.live:
        parts = args.live.replace("@", " ").split()
        if len(parts) >= 2:
            away, home = parts[0].upper(), parts[-1].upper()
            generate_report(away, home, args.total)
        else:
            print("Usage: --live 'AWAY @ HOME' (e.g., 'NY @ LV')")
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python wnba_tc_v3.py --backtest")
        print("  python wnba_tc_v3.py --live 'NY @ LV'")
        print("  python wnba_tc_v3.py --live 'IND @ CHI' --total 175.5")
        print("  python wnba_tc_v3.py --list-teams")
