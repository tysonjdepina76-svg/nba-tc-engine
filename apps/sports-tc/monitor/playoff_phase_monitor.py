#!/usr/bin/env python3
"""
NBA Playoff Phase Monitor
Tracks every game from Play-In → Round 1 → Round 2 → Conference Finals → Finals
Stores: game metadata, TC projections, actual outcomes, edge analysis

Run: python3 playoff_phase_monitor.py
Output: monitor/playoff_tracker.json + monitor/backtest_master.csv
"""

import json, os, csv
from datetime import datetime
from pathlib import Path

BASE = "/home/workspace/sports-tc/monitor"
os.makedirs(BASE, exist_ok=True)

TRACKER_FILE = f"{BASE}/playoff_tracker.json"
CSV_FILE = f"{BASE}/backtest_master.csv"

# Play-In Games (Apr 15-18, 2026)
PLAYIN = [
    # West Play-In
    {"phase": "PLAY-IN", "date": "Apr 15, 2026", "game": "WEST#10@WEST#9", "away": "SAC", "home": "GSW", "result": None, "notes": ""},
    {"phase": "PLAY-IN", "date": "Apr 16, 2026", "game": "WEST#7@WEST#8", "away": "LAL", "home": "NOP", "result": None, "notes": ""},
    # East Play-In
    {"phase": "PLAY-IN", "date": "Apr 15, 2026", "game": "EAST#10@EAST#9", "away": "BKN", "home": "MIA", "result": None, "notes": ""},
    {"phase": "PLAY-IN", "date": "Apr 16, 2026", "game": "EAST#7@EAST#8", "away": "PHI", "home": "DET", "result": None, "notes": ""},
]

# First Round (Apr 19 - May 3, 2026)
ROUND1 = [
    # West
    {"phase": "ROUND1", "date": "Apr 19, 2026", "game": "OKC(1) vs PHX(8)", "away": "PHX", "home": "OKC", "game_num": 1, "series": "OKC vs PHX", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 20, 2026", "game": "OKC(1) vs PHX(8)", "away": "PHX", "home": "OKC", "game_num": 2, "series": "OKC vs PHX", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 22, 2026", "game": "OKC(1) vs PHX(8)", "away": "OKC", "home": "PHX", "game_num": 3, "series": "OKC vs PHX", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 24, 2026", "game": "OKC(1) vs PHX(8)", "away": "OKC", "home": "PHX", "game_num": 4, "series": "OKC vs PHX", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 19, 2026", "game": "SAS(2) vs POR(7)", "away": "POR", "home": "SAS", "game_num": 1, "series": "SAS vs POR", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 21, 2026", "game": "SAS(2) vs POR(7)", "away": "POR", "home": "SAS", "game_num": 2, "series": "SAS vs POR", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 23, 2026", "game": "SAS(2) vs POR(7)", "away": "SAS", "home": "POR", "game_num": 3, "series": "SAS vs POR", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 25, 2026", "game": "SAS(2) vs POR(7)", "away": "SAS", "home": "POR", "game_num": 4, "series": "SAS vs POR", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 27, 2026", "game": "SAS(2) vs POR(7)", "away": "POR", "home": "SAS", "game_num": 5, "series": "SAS vs POR", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 19, 2026", "game": "MIN(4) vs DEN(5)", "away": "DEN", "home": "MIN", "game_num": 1, "series": "MIN vs DEN", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 21, 2026", "game": "MIN(4) vs DEN(5)", "away": "DEN", "home": "MIN", "game_num": 2, "series": "MIN vs DEN", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 23, 2026", "game": "MIN(4) vs DEN(5)", "away": "MIN", "home": "DEN", "game_num": 3, "series": "MIN vs DEN", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 25, 2026", "game": "MIN(4) vs DEN(5)", "away": "MIN", "home": "DEN", "game_num": 4, "series": "MIN vs DEN", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 27, 2026", "game": "MIN(4) vs DEN(5)", "away": "DEN", "home": "MIN", "game_num": 5, "series": "MIN vs DEN", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 29, 2026", "game": "MIN(4) vs DEN(5)", "away": "DEN", "home": "MIN", "game_num": 6, "series": "MIN vs DEN", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "May 1, 2026", "game": "MIN(4) vs DEN(5)", "away": "MIN", "home": "DEN", "game_num": 7, "series": "MIN vs DEN", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 19, 2026", "game": "LAL(3) vs HOU(6)", "away": "HOU", "home": "LAL", "game_num": 1, "series": "LAL vs HOU", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 21, 2026", "game": "LAL(3) vs HOU(6)", "away": "HOU", "home": "LAL", "game_num": 2, "series": "LAL vs HOU", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 23, 2026", "game": "LAL(3) vs HOU(6)", "away": "LAL", "home": "HOU", "game_num": 3, "series": "LAL vs HOU", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 25, 2026", "game": "LAL(3) vs HOU(6)", "away": "LAL", "home": "HOU", "game_num": 4, "series": "LAL vs HOU", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 27, 2026", "game": "LAL(3) vs HOU(6)", "away": "HOU", "home": "LAL", "game_num": 5, "series": "LAL vs HOU", "round": "W1", "result": None},
    {"phase": "ROUND1", "date": "Apr 29, 2026", "game": "LAL(3) vs HOU(6)", "away": "HOU", "home": "LAL", "game_num": 6, "series": "LAL vs HOU", "round": "W1", "result": None},
    # East
    {"phase": "ROUND1", "date": "Apr 19, 2026", "game": "DET(1) vs ORL(8)", "away": "ORL", "home": "DET", "game_num": 1, "series": "DET vs ORL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 21, 2026", "game": "DET(1) vs ORL(8)", "away": "ORL", "home": "DET", "game_num": 2, "series": "DET vs ORL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 23, 2026", "game": "DET(1) vs ORL(8)", "away": "DET", "home": "ORL", "game_num": 3, "series": "DET vs ORL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 25, 2026", "game": "DET(1) vs ORL(8)", "away": "DET", "home": "ORL", "game_num": 4, "series": "DET vs ORL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 27, 2026", "game": "DET(1) vs ORL(8)", "away": "ORL", "home": "DET", "game_num": 5, "series": "DET vs ORL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 29, 2026", "game": "DET(1) vs ORL(8)", "away": "ORL", "home": "DET", "game_num": 6, "series": "DET vs ORL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "May 1, 2026", "game": "DET(1) vs ORL(8)", "away": "DET", "home": "ORL", "game_num": 7, "series": "DET vs ORL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 20, 2026", "game": "CLE(4) vs TOR(5)", "away": "TOR", "home": "CLE", "game_num": 1, "series": "CLE vs TOR", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 22, 2026", "game": "CLE(4) vs TOR(5)", "away": "TOR", "home": "CLE", "game_num": 2, "series": "CLE vs TOR", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 24, 2026", "game": "CLE(4) vs TOR(5)", "away": "CLE", "home": "TOR", "game_num": 3, "series": "CLE vs TOR", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 26, 2026", "game": "CLE(4) vs TOR(5)", "away": "CLE", "home": "TOR", "game_num": 4, "series": "CLE vs TOR", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 28, 2026", "game": "CLE(4) vs TOR(5)", "away": "TOR", "home": "CLE", "game_num": 5, "series": "CLE vs TOR", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 30, 2026", "game": "CLE(4) vs TOR(5)", "away": "TOR", "home": "CLE", "game_num": 6, "series": "CLE vs TOR", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "May 2, 2026", "game": "CLE(4) vs TOR(5)", "away": "CLE", "home": "TOR", "game_num": 7, "series": "CLE vs TOR", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 20, 2026", "game": "NYK(3) vs ATL(6)", "away": "ATL", "home": "NYK", "game_num": 1, "series": "NYK vs ATL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 22, 2026", "game": "NYK(3) vs ATL(6)", "away": "ATL", "home": "NYK", "game_num": 2, "series": "NYK vs ATL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 24, 2026", "game": "NYK(3) vs ATL(6)", "away": "NYK", "home": "ATL", "game_num": 3, "series": "NYK vs ATL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 26, 2026", "game": "NYK(3) vs ATL(6)", "away": "NYK", "home": "ATL", "game_num": 4, "series": "NYK vs ATL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 28, 2026", "game": "NYK(3) vs ATL(6)", "away": "ATL", "home": "NYK", "game_num": 5, "series": "NYK vs ATL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 30, 2026", "game": "NYK(3) vs ATL(6)", "away": "ATL", "home": "NYK", "game_num": 6, "series": "NYK vs ATL", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 20, 2026", "game": "BOS(2) vs PHI(7)", "away": "PHI", "home": "BOS", "game_num": 1, "series": "BOS vs PHI", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 22, 2026", "game": "BOS(2) vs PHI(7)", "away": "PHI", "home": "BOS", "game_num": 2, "series": "BOS vs PHI", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 24, 2026", "game": "BOS(2) vs PHI(7)", "away": "BOS", "home": "PHI", "game_num": 3, "series": "BOS vs PHI", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 26, 2026", "game": "BOS(2) vs PHI(7)", "away": "BOS", "home": "PHI", "game_num": 4, "series": "BOS vs PHI", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 28, 2026", "game": "BOS(2) vs PHI(7)", "away": "PHI", "home": "BOS", "game_num": 5, "series": "BOS vs PHI", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "Apr 30, 2026", "game": "BOS(2) vs PHI(7)", "away": "PHI", "home": "BOS", "game_num": 6, "series": "BOS vs PHI", "round": "E1", "result": None},
    {"phase": "ROUND1", "date": "May 3, 2026", "game": "BOS(2) vs PHI(7)", "away": "BOS", "home": "PHI", "game_num": 7, "series": "BOS vs PHI", "round": "E1", "result": None},
]

# Second Round / Conference Semifinals (May 5-14, 2026)
ROUND2 = [
    {"phase": "ROUND2", "date": "May 5, 2026", "game": "LAL(3) @ OKC(1)", "away": "LAL", "home": "OKC", "game_num": 1, "series": "OKC vs LAL", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 7, 2026", "game": "LAL(3) @ OKC(1)", "away": "LAL", "home": "OKC", "game_num": 2, "series": "OKC vs LAL", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 9, 2026", "game": "OKC(1) @ LAL(3)", "away": "OKC", "home": "LAL", "game_num": 3, "series": "OKC vs LAL", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 11, 2026", "game": "OKC(1) @ LAL(3)", "away": "OKC", "home": "LAL", "game_num": 4, "series": "OKC vs LAL", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 13, 2026", "game": "LAL(3) @ OKC(1)", "away": "LAL", "home": "OKC", "game_num": 5, "series": "OKC vs LAL", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 5, 2026", "game": "MIN(4) @ SAS(2)", "away": "MIN", "home": "SAS", "game_num": 1, "series": "SAS vs MIN", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 7, 2026", "game": "MIN(4) @ SAS(2)", "away": "MIN", "home": "SAS", "game_num": 2, "series": "SAS vs MIN", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 9, 2026", "game": "SAS(2) @ MIN(4)", "away": "SAS", "home": "MIN", "game_num": 3, "series": "SAS vs MIN", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 11, 2026", "game": "SAS(2) @ MIN(4)", "away": "SAS", "home": "MIN", "game_num": 4, "series": "SAS vs MIN", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 13, 2026", "game": "MIN(4) @ SAS(2)", "away": "MIN", "home": "SAS", "game_num": 5, "series": "SAS vs MIN", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 15, 2026", "game": "SAS(2) @ MIN(4)", "away": "SAS", "home": "MIN", "game_num": 6, "series": "SAS vs MIN", "round": "W2", "result": None},
    {"phase": "ROUND2", "date": "May 5, 2026", "game": "CLE(4) @ DET(1)", "away": "CLE", "home": "DET", "game_num": 1, "series": "DET vs CLE", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 7, 2026", "game": "CLE(4) @ DET(1)", "away": "CLE", "home": "DET", "game_num": 2, "series": "DET vs CLE", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 9, 2026", "game": "DET(1) @ CLE(4)", "away": "DET", "home": "CLE", "game_num": 3, "series": "DET vs CLE", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 11, 2026", "game": "DET(1) @ CLE(4)", "away": "DET", "home": "CLE", "game_num": 4, "series": "DET vs CLE", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 13, 2026", "game": "CLE(4) @ DET(1)", "away": "CLE", "home": "DET", "game_num": 5, "series": "DET vs CLE", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 5, 2026", "game": "NYK(3) @ BOS(2)", "away": "NYK", "home": "BOS", "game_num": 1, "series": "BOS vs NYK", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 7, 2026", "game": "NYK(3) @ BOS(2)", "away": "NYK", "home": "BOS", "game_num": 2, "series": "BOS vs NYK", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 9, 2026", "game": "BOS(2) @ NYK(3)", "away": "BOS", "home": "NYK", "game_num": 3, "series": "BOS vs NYK", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 11, 2026", "game": "BOS(2) @ NYK(3)", "away": "BOS", "home": "NYK", "game_num": 4, "series": "BOS vs NYK", "round": "E2", "result": None},
    {"phase": "ROUND2", "date": "May 13, 2026", "game": "NYK(3) @ BOS(2)", "away": "NYK", "home": "BOS", "game_num": 5, "series": "BOS vs NYK", "round": "E2", "result": None},
]

# Conference Finals (May 16-22, 2026) — CURRENT
CONF_FINALS = [
    # WCF
    {"phase": "CONF FINALS", "date": "May 18, 2026", "game": "SAS(2) @ OKC(1)", "away": "SAS", "home": "OKC", "game_num": 1, "series": "SA vs OKC", "round": "WCF", "result": None},
    {"phase": "CONF FINALS", "date": "May 20, 2026", "game": "SAS(2) @ OKC(1)", "away": "SAS", "home": "OKC", "game_num": 2, "series": "SA vs OKC", "round": "WCF", "result": None},
    {"phase": "CONF FINALS", "date": "May 22, 2026", "game": "OKC(1) @ SAS(2)", "away": "OKC", "home": "SAS", "game_num": 3, "series": "SA vs OKC", "round": "WCF", "result": None},
    # ECF
    {"phase": "CONF FINALS", "date": "May 19, 2026", "game": "CLE(4) @ NYK(3)", "away": "CLE", "home": "NYK", "game_num": 1, "series": "CLE vs NYK", "round": "ECF", "result": None},
    {"phase": "CONF FINALS", "date": "May 21, 2026", "game": "CLE(4) @ NYK(3)", "away": "CLE", "home": "NYK", "game_num": 2, "series": "CLE vs NYK", "round": "ECF", "result": None},
    {"phase": "CONF FINALS", "date": "May 23, 2026", "game": "NYK(3) @ CLE(4)", "away": "NYK", "home": "CLE", "game_num": 3, "series": "CLE vs NYK", "round": "ECF", "result": None},
]

FINALS = [
    {"phase": "FINALS", "date": "TBD", "game": "WCF Winner @ ECF Winner", "away": "TBD", "home": "TBD", "game_num": 1, "series": "NBA Finals", "round": "F", "result": None},
]

ALL_GAMES = PLAYIN + ROUND1 + ROUND2 + CONF_FINALS + FINALS

def load_existing_tracker():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {}

def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)

def get_phase_summary(games):
    summary = {}
    for g in games:
        phase = g["phase"]
        if phase not in summary:
            summary[phase] = {"total": 0, "with_results": 0, "games": []}
        summary[phase]["total"] += 1
        if g.get("actual_total"):
            summary[phase]["with_results"] += 1
        summary[phase]["games"].append(g)
    return summary

def print_summary():
    tracker = load_existing_tracker()
    summary = get_phase_summary(ALL_GAMES)
    print(f"\n{'='*70}")
    print("  NBA PLAYOFF PHASE MONITOR — 2026 Postseason")
    print(f"{'='*70}")
    print(f"\n  {'Phase':<20} {'Games':>6} {'Scored':>8} {'Pct':>6}")
    print(f"  {'-'*45}")
    for phase in ["PLAY-IN", "ROUND1", "ROUND2", "CONF FINALS", "FINALS"]:
        if phase in summary:
            s = summary[phase]
            pct = f"{s['with_results']/s['total']*100:.0f}%" if s['total'] > 0 else "0%"
            print(f"  {phase:<20} {s['total']:>6} {s['with_results']:>8} {pct:>6}")

if __name__ == "__main__":
    print_summary()
    print(f"\n  Tracker file: {TRACKER_FILE}")
    print(f"  Total games tracked: {len(ALL_GAMES)}")

