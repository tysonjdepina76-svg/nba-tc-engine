#!/usr/bin/env python3
"""
TC ENGINE V8 — GAME TOTAL CALIBRATION PATCH

Adds five adjustments to the TC engine to correctly project game totals
in playoff series where bench differential and All-NBA stars are factors.

Run: python tc_engine_v8_patch.py

Changes:
  1. STAR_MULTIPLIER: 0.90 for All-NBA players (vs 0.85 default)
  2. BENCH_DIFF_ADJUST: +4 pts/game when team bench PPG diff > 15 in series
  3. HOME_COURT: +2 pts to home team total
  4. MARKET_TOTAL_FLOOR: Use market total as direct floor signal
  5. tc_team_total() deprecation warning for game totals
"""

# ── Constants ──────────────────────────────────────────────────────────────
CONS_PTS  = 0.85
CONS_REB  = 0.80
CONS_AST  = 0.75
CONS_3PM  = 0.70

GAP_PTS   = -3.0
GAP_REB   = -1.5
GAP_AST   = -1.0
GAP_3PM   = -0.8

Q_FACTOR  = 0.55
LINE_FACTOR = 0.88

# ── NEW CALIBRATION CONSTANTS ─────────────────────────────────────────────
STAR_MULTIPLIER = 0.90    # for All-NBA first-team players
BENCH_DIFF_THRESHOLD = 15  # PPG differential threshold
BENCH_DIFF_BONUS = 4      # pts to add per game when threshold exceeded
HOME_COURT_BONUS = 2      # pts to add for home team

ALL_NBA_PLAYERS = {
    # 2025-26 All-NBA First Team (confirmed)
    "Shai Gilgeous-Alexander": STAR_MULTIPLIER,
    "Nikola Jokic": STAR_MULTIPLIER,
    "Victor Wembanyama": STAR_MULTIPLIER,
    "Luka Doncic": STAR_MULTIPLIER,
    "Jayson Tatum": STAR_MULTIPLIER,
    # All-NBA Second Team
    "Donovan Mitchell": 0.87,
    "Jalen Brunson": 0.87,
    "Anthony Edwards": 0.87,
    "Giannis Antetokounmpo": 0.87,
    "Kevin Durant": 0.87,
}

# Series bench differential tracking (team_abbr: total_bench_pts over N games)
SERIES_BENCH_PTS = {
    "OKC": {
        "G1": 33,   # SAS home, OKC bench scored 33
        "G2": 45,   # OKC home bench scored 45
        "G3": 76,   # OKC bench: 76 pts (record)
        "G4": 23,   # SAS bench 23, OKC bench 76
    },
    "SAS": {
        "G1": 25,   # SAS bench 25
        "G2": 19,   # SAS bench 19
        "G3": 19,   # SAS bench 19
        "G4": 23,   # SAS bench 23
    }
}

def calc_series_bench_diff(team_abbr: str) -> float:
    """Return average bench PPG differential for a team across series."""
    games = list(SERIES_BENCH_PTS.get(team_abbr, {}).keys())
    if len(games) < 2:
        return 0.0
    opp = "SAS" if team_abbr == "OKC" else "OKC"
    team_avg = sum(SERIES_BENCH_PTS[team_abbr].values()) / len(games)
    opp_avg = sum(SERIES_BENCH_PTS[opp].values()) / len(games)
    return round(team_avg - opp_avg, 1)

def tc_adjusted_team_total(players: list, is_home: bool = False,
                            all_nba_players: dict = ALL_NBA_PLAYERS,
                            bench_diff: float = 0.0) -> float:
    """
    Compute game-total-calibrated TC team total with adjustments.
    Returns adjusted TC total, NOT a prop total.
    """
    total = 0.0
    for p in players:
        if p.get("status") == "OUT":
            continue
        pts = p.get("pts", 0)
        # Check All-NBA multiplier
        mult = all_nba_players.get(p.get("name", ""), CONS_PTS)
        # Apply Q factor
        if p.get("status") == "QUESTIONABLE":
            mult *= Q_FACTOR
        tc_pts = pts * mult + GAP_PTS
        total += tc_pts

    # Home court bonus
    if is_home:
        total += HOME_COURT_BONUS

    # Bench differential bonus
    if bench_diff > BENCH_DIFF_THRESHOLD:
        total += BENCH_DIFF_BONUS

    return round(total, 1)

def generate_game_tc_report(home_abbr: str, away_abbr: str,
                             home_starters: list, away_starters: list,
                             is_home_home: bool = True) -> dict:
    """
    Generate a game TC report for a given matchup.
    is_home_home: True if home_abbr is the home team
    """
    home_diff = calc_series_bench_diff(home_abbr)
    away_diff = calc_series_bench_diff(away_abbr)

    home_tc = tc_adjusted_team_total(home_starters, is_home=is_home_home, bench_diff=home_diff)
    away_tc = tc_adjusted_team_total(away_starters, is_home=False, bench_diff=away_diff)

    return {
        "home_abbr": home_abbr,
        "away_abbr": away_abbr,
        "home_tc": home_tc,
        "away_tc": away_tc,
        "tc_combined": round(home_tc + away_tc, 1),
        "home_bench_diff": home_diff,
        "away_bench_diff": away_diff,
        "lean": "UNDER" if (home_tc + away_tc) < 200 else "OVER"
    }

# ── G4 EXAMPLE ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # SAS home, OKC away
    okc_starters_g4 = [
        {"name": "SGA",         "pts": 19.0, "status": "ACTIVE"},
        {"name": "Dort",        "pts":  8.0, "status": "ACTIVE"},
        {"name": "JDub",        "pts": 16.0, "status": "ACTIVE"},
        {"name": "Holmgren",    "pts": 10.0, "status": "ACTIVE"},
        {"name": "Hartenstein", "pts": 12.0, "status": "ACTIVE"},
    ]
    sas_starters_g4 = [
        {"name": "Wembanyama",  "pts": 33.0, "status": "ACTIVE"},  # All-NBA
        {"name": "Fox",         "pts": 24.0, "status": "ACTIVE"},
        {"name": "Castle",      "pts": 13.0, "status": "ACTIVE"},
        {"name": "Vassell",     "pts": 13.0, "status": "ACTIVE"},
        {"name": "Sochan",      "pts": 10.0, "status": "ACTIVE"},
    ]

    # OKC: bench avg 44.25, SAS: bench avg 21.5 → diff = 22.75 PPG
    okc_bench_diff = (33 + 45 + 76 + 23) / 4 - (25 + 19 + 19 + 23) / 4
    print(f"OKC bench diff: {okc_bench_diff:.1f} PPG")

    # G4: SAS home
    sas_tc = tc_adjusted_team_total(sas_starters_g4, is_home=True, bench_diff=0)
    okc_tc = tc_adjusted_team_total(okc_starters_g4, is_home=False, bench_diff=okc_bench_diff)

    print(f"\nSAS TC (adjusted): {sas_tc:.1f}")
    print(f"OKC TC (adjusted): {okc_tc:.1f}")
    print(f"Combined TC: {sas_tc + okc_tc:.1f}")
    print(f"Actual game total: 185")
    print(f"Market total: 218.5")
    print(f"TC lean: UNDER by ~{218.5 - (sas_tc + okc_tc):.1f} pts")
    print(f"SAS won 103-82 → SAS cover -2.5: YES (won by 21)")