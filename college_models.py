#!/usr/bin/env python3
"""
NCAAB + NCAAF Models
Tyson Depina | Zo Computer

NCAAB: Adjusted Efficiency + Temporalized Massey + Four Factors
NCAAF: G-Elo + Net Rating + MOV

Usage:
  python3 college_models.py --sport NCAAB --home "KU" --away "UK"
  python3 college_models.py --sport NCAAF --home "BAMA" --away "UGA"
"""

import math
import json
from typing import Dict, Tuple, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# NCAAB — COLLEGE BASKETBALL
# ═══════════════════════════════════════════════════════════════════════════════

def pomeroy_ratings(adj_oe: float, adj_de: float, pace: float,
                    strength_of_schedule: float) -> Dict:
    """
    Pomeroy-style adjusted efficiency ratings.

    Args:
        adj_oe: Points scored per 100 possessions
        adj_de: Points allowed per 100 possessions
        pace: Possessions per game
        strength_of_schedule: Average opponent NET rating faced

    Returns:
        dict with NET, ratings, and recommendation
    """
    net_rating = adj_oe - adj_de

    # Four Factors weights (from March Madness study — 74.6% accuracy)
    # ADJOE=0.35, ADJDE=0.30, Power=0.20, 2PctAllowed=0.15
    power_rating = (
        0.35 * adj_oe +
        0.30 * (120 - adj_de) +   # invert so higher = better
        0.20 * net_rating +
        0.15 * (50)              # placeholder for 2PctAllowed
    )

    # Experience factor (fraction of minutes from returning players)
    # Placeholder — would need portal/coach data
    experience = 0.0  # range roughly -3 to +3

    return {
        "adj_oe": adj_oe,
        "adj_de": adj_de,
        "net_rating": net_rating,
        "power_rating": round(power_rating, 1),
        "pace": pace,
        "experience_factor": experience,
        "sos": strength_of_schedule,
    }


def massey_rating(teams: Dict[str, Dict]) -> Dict[str, float]:
    """
    Massey's method for ranking.

    Solves Mr = p where:
      M = D − A (D = diagonal games played, A = head-to-head results)
      p = cumulative point differential

    Augmented with λI regularization for small samples.

    Args:
        teams: dict of {team_abbr: {"games": [(opponent, margin)], "wins": n, "losses": n}}

    Returns:
        dict of {team_abbr: rating}
    """
    import numpy as np

    team_list = list(teams.keys())
    n = len(team_list)
    idx = {t: i for i, t in enumerate(team_list)}

    M = [[0.0] * n for _ in range(n)]
    p = [0.0] * n

    for team, data in teams.items():
        i = idx[team]
        games = data.get("games", [])
        M[i][i] = len(games)
        for opponent, margin in games:
            if opponent in idx:
                j = idx[opponent]
                M[i][j] -= 1
                p[i] += margin

    # Augment for singularity
    M[n-1] = [1.0] * n
    p[n-1] = 0.0

    # Solve with regularization
    lam = 0.01
    M_reg = [[M[i][j] + (lam if i == j else 0) for j in range(n)] for i in range(n)]
    try:
        ratings_arr = np.linalg.solve(M_reg, p)
    except np.linalg.LinAlgError:
        return {t: 0.0 for t in team_list}

    return {t: round(ratings_arr[idx[t]], 2) for t in team_list}


def ncaab_game_prediction(home_oe: float, home_de: float, home_pace: float,
                           away_oe: float, away_de: float, away_pace: float,
                           home_sos: float = 0, away_sos: float = 0,
                           home_court: float = 3.5) -> Dict:
    """
    NCAAB game prediction combining all models.

    Returns spread, total, and win probability.
    """
    import numpy as np

    # Adjusted efficiencies (from Pomeroy)
    home_net = home_oe - home_de
    away_net = away_oe - away_de

    # Massey-inspired composite
    # Higher pace = more possessions = more total points
    pace_factor = (home_pace + away_pace) / (97 + 97)  # 97 = avg college pace

    # Expected total using adjusted efficiencies
    # College: roughly OE + DE + 3 for neutral, +4 for home court
    exp_total = ((home_oe + away_oe) / 2 + (home_de + away_de) / 2) * (pace_factor + 0.05)
    exp_total = exp_total + home_court * 0.3  # slight home scoring boost

    # Expected spread
    net_diff = home_net - away_net
    exp_spread = net_diff + home_court

    # Win probability via sigmoid
    spread_factor = exp_spread / 7.5  # normalize to ~70% probability at 7.5 pt fav
    home_win_prob = 1 / (1 + math.exp(-spread_factor * 1.2))

    # Signal
    total_line = round(exp_total)
    total_edge = exp_total - total_line

    return {
        "home_win_prob": round(home_win_prob, 3),
        "away_win_prob": round(1 - home_win_prob, 3),
        "expected_total": round(exp_total, 1),
        "expected_spread": round(exp_spread, 1),
        "home_line": round(exp_spread, 1),
        "total_line": total_line,
        "total_edge": round(total_edge, 1),
        "signal": "OVER" if total_edge >= 2.0 else ("UNDER" if total_edge <= -2.0 else "PASS"),
        "home_court_advantage": home_court,
        "model_confidence": round(min(home_win_prob, 1-home_win_prob) * 2, 2),  # 0-1
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NCAAF — COLLEGE FOOTBALL
# ═══════════════════════════════════════════════════════════════════════════════

def g_elo_update(rating: float, actual_margin: float, expected: float,
                 k: float = 25.0) -> float:
    """
    G-Elo: Generalized Elo with Margin of Victory adjustment.

    Args:
        rating: Current Elo rating
        actual_margin: Actual point margin (positive = win)
        expected: Expected score from Elo formula
        k: K-factor (25 for FBS, 20 for FCS)

    Returns:
        New rating
    """
    # MOV multiplier (discretized log model)
    mov = abs(actual_margin)
    mov_mult = math.log(mov + 1) / 7.0
    mov_mult = min(mov_mult, 1.5)  # cap at 1.5x

    actual_score = 1.0 if actual_margin > 0 else (0.5 if actual_margin == 0 else 0.0)
    new_rating = rating + k * mov_mult * (actual_score - expected)
    return round(new_rating, 1)


def elo_win_prob(rating_a: float, rating_b: float) -> float:
    """Win probability for team A vs team B from Elo ratings."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def ncaaf_game_prediction(
    home_elo: float,
    away_elo: float,
    home_p5: bool = True,   # Power 5 conference
    away_p5: bool = True,
    home_fav: bool = True,  # home team is favorite
    line: float = 7.0       # current Vegas line
) -> Dict:
    """
    NCAAF game prediction using G-Elo + Net Rating + MOV.

    Args:
        home_elo: Home team Elo rating (avg FBS = 1500)
        away_elo: Away team Elo rating
        home_p5: Is home team Power 5?
        away_p5: Is away team Power 5?
        home_fav: Is home team the favorite?
        line: Current Vegas spread

    Returns:
        dict with win probabilities, spread, total, and edge
    """
    # G-Elo expected score
    expected_home = elo_win_prob(home_elo, away_elo)

    # Power 5 adjustment
    p5_bonus = 7.0  # roughly 7 Elo points = 1 point on spread
    if home_p5 and not away_p5:
        home_elo += p5_bonus
    elif away_p5 and not home_p5:
        away_elo += p5_bonus

    # Recompute after P5 adjustment
    expected_home_adj = elo_win_prob(home_elo, away_elo)

    # Home field advantage (FBS ~3.0 points, FCS ~2.5)
    home_field = 3.0 if home_p5 else 2.5
    expected_home_adj += home_field / 150  # small Elo adjustment

    # Spread from Elo
    elo_spread = (away_elo - home_elo) / 25.0  # 25 Elo = ~1 point
    elo_spread = elo_spread + home_field if elo_spread < 0 else elo_spread - home_field

    # Total: use historical average ( FBS total ~54)
    exp_total = 54.0

    # Edge vs current line
    spread_edge = elo_spread - line if home_fav else -(elo_spread - line)

    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "home_win_prob": round(expected_home_adj, 3),
        "away_win_prob": round(1 - expected_home_adj, 3),
        "elo_spread": round(elo_spread, 1),
        "home_fav": home_fav,
        "expected_total": exp_total,
        "spread_edge": round(spread_edge, 1),
        "total_edge": 0.0,  # Would need game-specific data
        "model_confidence": round(min(expected_home_adj, 1-expected_home_adj) * 2, 2),
        "p5_bonus_used": home_p5 or away_p5,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", choices=["NCAAB", "NCAAF"], required=True)
    parser.add_argument("--home")
    parser.add_argument("--away")
    args = parser.parse_args()

    if args.sport == "NCAAB":
        # Sample: Kansas vs Kentucky
        result = ncaab_game_prediction(
            home_oe=118.5, home_de=96.2, home_pace=71.5,
            away_oe=115.8, away_de=98.1, away_pace=69.2,
            home_sos=3.5, away_sos=2.8, home_court=3.5
        )
        print(f"\nNCAAB: KU vs UK")
        print(f"  KU Win Prob: {result['home_win_prob']:.1%}")
        print(f"  UK Win Prob: {result['away_win_prob']:.1%}")
        print(f"  Expected Total: {result['expected_total']}")
        print(f"  Signal: {result['signal']}")

    elif args.sport == "NCAAF":
        result = ncaaf_game_prediction(
            home_elo=1520, away_elo=1480,
            home_p5=True, away_p5=True,
            home_fav=True, line=7.0
        )
        print(f"\nNCAAF: BAMA vs UGA (example)")
        print(f"  Home Win Prob: {result['home_win_prob']:.1%}")
        print(f"  Away Win Prob: {result['away_win_prob']:.1%}")
        print(f"  Elo Spread: {result['elo_spread']}")
        print(f"  Spread Edge: {result['spread_edge']}")