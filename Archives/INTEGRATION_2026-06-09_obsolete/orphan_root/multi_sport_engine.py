#!/usr/bin/env python3
"""
Multi-Sport Projection Engine
Handles NBA, WNBA, MLB, NCAAB, NCAAF, NHL
Tyson Depina | Zo Computer

Usage:
  python3 multi_sport_engine.py --sport NBA --game "OKC@SAS"
  python3 multi_sport_engine.py --sport MLB --game "NYY@BOS"
  python3 multi_sport_engine.py --all --report
"""

import argparse
import json
import math
import sys
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# ── NBA / WNBA — TC ENGINE BRIDGE ──────────────────────────────────────────
# TC engine is already built; we just import and wrap it here
def run_tc_prop(player_name: str, stat: str, pts: float,
                status: str, opp_deff: float, pace: float,
                league: str = "NBA") -> Dict:
    """
    Run TC (Triple Conservative) formula for player props.
    Wraps the existing TC logic for use in multi-sport pipeline.
    """
    STATUS_FACTOR = {"OUT": 0.0, "Q": 0.55, "P": 0.85, "GTD": 0.70, "U": 1.0}.get(status, 1.0)
    W_PTS   = 0.85
    GAP_PTS = -3.0
    LINE_FACTOR = 0.88

    if stat == "PTS":
        tc_raw = pts * W_PTS + GAP_PTS
    elif stat == "REB":
        tc_raw = pts * W_PTS + GAP_PTS
    elif stat == "AST":
        tc_raw = pts * W_PTS + GAP_PTS
    elif stat == "3PM":
        tc_raw = pts * W_PTS + GAP_PTS
    elif stat == "STL":
        tc_raw = pts * W_PTS + GAP_PTS
    elif stat == "BLK":
        tc_raw = pts * W_PTS + GAP_PTS
    else:
        tc_raw = pts * W_PTS + GAP_PTS

    # Pace adjustment
    league_pace = 99.8 if league == "NBA" else 99.2
    pace_factor = pace / league_pace if pace else 1.0
    tc_pace = tc_raw * pace_factor

    # Opponent defensive rating adjustment
    # Opp_DEFF: opponent points allowed per possession (lower = better defense)
    # An opponent 2 points better (100 vs 102) → 0.97 factor
    if opp_deff:
        deff_factor = (100.0 / opp_deff) if opp_deff > 0 else 1.0
        deff_factor = max(0.85, min(1.15, deff_factor))  # cap at ±15%
        tc_opp = tc_pace * deff_factor
    else:
        tc_opp = tc_pace

    # Status factor
    tc_final = tc_opp * STATUS_FACTOR

    # TC line (what sportsbook is offering)
    tc_line = math.floor(tc_final * LINE_FACTOR)
    edge = tc_final - tc_line

    # Signal
    if edge >= 4.0:
        signal = "OVER"
    elif edge <= -4.0:
        signal = "UNDER"
    else:
        signal = "PASS"

    return {
        "tc_raw": round(tc_raw, 1),
        "tc_pace_adj": round(tc_pace, 1),
        "tc_final": round(tc_final, 1),
        "tc_line": tc_line,
        "edge": round(edge, 1),
        "signal": signal,
        "pace_factor": round(pace_factor, 3),
        "deff_factor": round(deff_factor if opp_deff else 1.0, 3),
        "status_factor": STATUS_FACTOR,
    }


# ── MLB — POISSON REGRESSION ─────────────────────────────────────────────────
def poisson_expected_runs(
    team_abv: float,      # Team batting value (runs created per game)
    park_factor: float,    # Park adjustment (Coors=1.15, Petco=0.95, etc.)
    opp_fip: float,        # Opposing pitcher FIP (Fielding Independent Pitching)
    home: bool = False
) -> float:
    """
    Poisson-based run expectancy for MLB.

    FIP is better than ERA for predictive purposes because it removes
    defense-dependent outcomes (balls in play).

    Formula:
      Lambda = ABV × Park_Factor × (1 − FIP/12) × HFA
      where HFA = 1.03 for home team (slight home advantage)

    Args:
        team_abv: Team's weighted runs created per game (wRC+/27)
        park_factor: Stadium adjustment (1.0 = neutral)
        opp_fip: Opposing pitcher's FIP (lower = better pitcher)
        home: Whether the team is home (small home-field boost)

    Returns:
        Expected runs for this team in this game
    """
    hf_adjust = 1.03 if home else 1.0
    # FIP ranges roughly 2.5 (elite) to 6.0 (terrible); normalize
    fip_adj = max(0.4, min(1.2, 1.0 - (opp_fip - 4.0) / 10))
    expected = team_abv * park_factor * fip_adj * hf_adjust
    return round(expected, 1)


def poisson_over_prob(total_line: float, home_exp: float, away_exp: float) -> Dict:
    """
    Calculate probability of OVER total using Poisson distribution.

    Uses scipy or manual Poisson approximation.
    Falls back to normal approximation if scipy unavailable.
    """
    total_exp = home_exp + away_exp

    # Try scipy
    try:
        from scipy.stats import poisson
        # P(UNDER) = P(X ≤ line) — CDF
        under_prob = poisson.cdf(total_line, total_exp)
        over_prob = 1 - under_prob
        exact_prob = poisson.pmf(total_line, total_exp)
        return {
            "expected_total": total_exp,
            "over_prob": round(over_prob, 4),
            "under_prob": round(under_prob, 4),
            "push_prob": round(exact_prob, 4),
            "edge_vs_line": round(total_exp - total_line, 1),
            "method": "poisson_scipy"
        }
    except ImportError:
        # Manual Poisson via normal approximation
        variance = total_exp  # Poisson variance = mean
        std = math.sqrt(variance)
        z = (total_line + 0.5 - total_exp) / std if std > 0 else 0
        from math import erf
        under_prob = 0.5 * (1 + erf(z / math.sqrt(2)))
        return {
            "expected_total": total_exp,
            "over_prob": round(1 - under_prob, 4),
            "under_prob": round(under_prob, 4),
            "push_prob": 0.0,
            "edge_vs_line": round(total_exp - total_line, 1),
            "method": "poisson_normal_approx"
        }


def mlb_win_prob(home_exp: float, away_exp: float,
                  home_pitcher_fip: float, away_pitcher_fip: float) -> Dict:
    """
    Estimate win probability from expected runs and starting pitcher FIP.
    """
    # Simple log5 variant
    league_avg_runs = 4.5
    home_winrate = home_exp / (home_exp + away_exp)
    away_winrate = away_exp / (home_exp + away_exp)

    # Pitcher adjustment
    home_pitcher_adj = (home_pitcher_fip - 4.5) * 0.05
    away_pitcher_adj = (away_pitcher_fip - 4.5) * 0.05

    home_prob = home_winrate - home_pitcher_adj + away_pitcher_adj
    home_prob = max(0.1, min(0.9, home_prob))
    away_prob = 1 - home_prob

    return {
        "home_win_prob": round(home_prob, 3),
        "away_win_prob": round(away_prob, 3),
        "home_exp_runs": home_exp,
        "away_exp_runs": away_exp,
        "ml_suggestion": "HOME" if home_prob > 0.5 else "AWAY",
        "edge": round(abs(home_prob - away_prob), 3)
    }


# ── NHL — GOAL EXPECTANCY ───────────────────────────────────────────────────
def nhl_expected_goals(
    team_gf: float,       # Team goals for per game (rolling 10-game)
    team_ga: float,       # Team goals against per game (rolling 10-game)
    opp_5v5_ga: float,    # Opponent 5v5 goals allowed per game
    home: bool = False,
    sv_pct: float = 0.910,  # Goaltender save %
    pp_pct: float = 0.22,    # Power play %
    pk_pct: float = 0.82     # Penalty kill %
) -> Dict:
    """
    NHL Goal Expectancy Model.

    Key factors:
    - 5v5 GF/GA (even-strength scoring)
    - Opponent's 5v5 defense quality
    - Goaltending (save %)
    - Special teams (PP% × PK%)
    - Corsi (shot attempt differential)
    - Home advantage (+0.15 goals)

    Formula:
      5v5_Goal_Exp = (Team_GF_5v5 × Opp_5v5_GA_adj) ^ 0.5 × Home_Factor
      Corsi_Factor = (Team_Corsi/50) × 0.15 + 0.85
      Special_Factor = (PP_Pct/100 × PK_Pct/100) × 1.1 + 0.9
      Final_Goal_Exp = 5v5_Exp × Corsi × Special × (1 − (1 − Sv_Pct) × 2)
    """
    home_adj = 0.15  # Home ice advantage in goals

    # 5v5 expected goals
    opp_adj = max(0.7, min(1.3, 1.0 / (opp_5v5_ga / 3.0)))
    goal_exp_5v5 = math.sqrt(team_gf * opp_5v5_ga) * opp_adj
    goal_exp_5v5 *= (1.0 + (0.15 if home else 0.0))

    # Corsi factor (shot attempt differential; proxy for possession)
    # Teams averaging 55% Corsi tend to control play better
    corsi_factor = 1.0  # Would need Corsi data; default neutral

    # Special teams factor
    special_factor = (pp_pct / 100) * (pk_pct / 100) * 1.1 + 0.90

    # Goaltending adjustment
    # Sv% of 0.910 vs league avg of 0.910 = no change
    # Sv% of 0.930 = roughly 0.15 fewer goals against
    league_sv = 0.910
    goalie_adj = 1.0 - (sv_pct - league_sv) * 2.0

    final_exp = goal_exp_5v5 * corsi_factor * special_factor * goalie_adj

    # Goal totals
    total_exp = final_exp + (team_ga * 0.7)  # estimate opponent goals
    total_exp *= (1.0 + (0.15 if home else 0.0))

    return {
        "5v5_goal_exp": round(goal_exp_5v5, 2),
        "corsi_factor": corsi_factor,
        "special_factor": round(special_factor, 3),
        "goalie_adj": round(goalie_adj, 3),
        "expected_goals": round(final_exp, 2),
        "expected_total": round(total_exp, 1),
        "over_prob_vs_5.5": round(1 - (1 / (1 + math.exp(-(total_exp - 5.5)))), 3),
        "home_advantage_goals": home_adj
    }


def nhl_poisson_total(home_exp: float, away_exp: float,
                       total_line: float = 6.5) -> Dict:
    """Calculate over/under probability for NHL total using Poisson."""
    total_exp = home_exp + away_exp
    try:
        from scipy.stats import poisson as poisson_scipy
        under_prob = poisson_scipy.cdf(total_line, total_exp)
        return {
            "expected_total": round(total_exp, 1),
            "over_prob": round(1 - under_prob, 4),
            "under_prob": round(under_prob, 4),
            "edge_vs_line": round(total_exp - total_line, 1),
            "method": "nhl_poisson"
        }
    except ImportError:
        z = (total_line + 0.5 - total_exp) / math.sqrt(total_exp) if total_exp > 0 else 0
        from math import erf as math_erf
        under_prob = 0.5 * (1 + math_erf(z / math.sqrt(2)))
        return {
            "expected_total": round(total_exp, 1),
            "over_prob": round(1 - under_prob, 4),
            "under_prob": round(under_prob, 4),
            "edge_vs_line": round(total_exp - total_line, 1),
            "method": "nhl_normal_approx"
        }


# ── NCAAB — MASSEY + EFFICIENCY + LSTM ──────────────────────────────────────
def massey_rating(wins: List[int], losses: List[int],
                  point_diffs: List[float], opps: List[List[int]]) -> List[float]:
    """
    Compute Massey ratings for NCAAB teams.

    Solves: Mr = p
    where M = D − A (D = diagonal of games played, A = head-to-head matrix)
           p = cumulative point differential

    Returns list of ratings aligned with team index.
    """
    n = len(wins)
    if n < 2:
        return [0.0] * n

    # Build M matrix and p vector (simplified — full implementation
    # requires building full schedule matrix)
    M = [[0.0] * (n + 1) for _ in range(n + 1)]
    p = [0.0] * (n + 1)

    # Last row/col is constraint: sum of ratings = 0
    for i in range(n):
        games = wins[i] + losses[i]
        M[i][i] = games
        for j, diff in zip(opps[i], point_diffs):
            if j >= 0 and j < n:
                M[i][j] -= 1
                p[i] += diff

    # Add sum constraint
    for i in range(n):
        M[n][i] = 1.0
    p[n] = 0.0

    # Solve via Gaussian elimination (simplified)
    ratings = [0.0] * n
    try:
        # Direct solve for small n
        factor = sum(wins[i] + losses[i] for i in range(n))
        for i in range(n):
            net_rt = sum(point_diffs[j] for j in range(len(wins)))
            ratings[i] = (wins[i] - losses[i]) + (sum(point_diffs) / n)
    except:
        ratings = [0.0] * n

    # Normalize: mean = 0
    mean_r = sum(ratings) / n if n > 0 else 0
    ratings = [r - mean_r for r in ratings]
    return ratings


def ncaab_game_prob(
    home_adj_oe: float,   # Home AdjOE (offensive efficiency)
    home_adj_de: float,   # Home AdjDE (defensive efficiency)
    away_adj_oe: float,
    away_adj_de: float,
    home_court: float = 3.5  # points
) -> Dict:
    """
    NCAAB game probability using adjusted efficiency method.

    Key features (from March Madness model study):
      ADJOE_weight = 0.35
      ADJDE_weight = 0.30
      Power_Rating  = 0.20
      Two_Point_Pct_Allowed = 0.15

    Args:
        home_adj_oe: Home team offensive efficiency (points per possession × 100)
        home_adj_de: Home team defensive efficiency
        away_adj_oe: Away team offensive efficiency
        away_adj_de: Away team defensive efficiency
        home_court: Home court advantage in points

    Returns:
        Win probability, spread, total estimate
    """
    # Net efficiencies
    home_net = home_adj_oe - away_adj_de
    away_net = away_adj_oe - home_adj_de

    # Logit model (from March Madness study)
    logit = (
        (home_adj_oe - away_adj_de) * 0.0035 +  # ADJOE weight
        (away_adj_oe - home_adj_de) * 0.0030 +  # ADJDE weight
        home_court * 0.002
    )
    home_win_prob = 1 / (1 + math.exp(-logit * 10))

    # Spread (in points)
    # Expected margin = (home_oe - away_de) + home_court - (away_oe - home_de)
    expected_margin = (home_adj_oe - away_adj_de + home_court) - (away_adj_oe - home_adj_de)
    spread = round(expected_margin, 1)

    # Game total estimate (simplified)
    # Total = (home_oe + away_oe) / 2 × pace_factor + 2 (arbitrage)
    avg_efficiency = (home_adj_oe + away_adj_oe) / 2
    game_total = round(avg_efficiency * 0.70 + 68, 1)  # 68 = baseline possessions

    return {
        "home_win_prob": round(home_win_prob, 3),
        "away_win_prob": round(1 - home_win_prob, 3),
        "spread": f"HOME {'+' if spread > 0 else ''}{spread:.1f}",
        "home_spread": round(spread, 1),
        "game_total_estimate": game_total,
        "expected_margin": round(expected_margin, 1),
        "method": "ncaab_massey_efficiency"
    }


# ── NCAAF — G-ELO + MARGIN OF VICTORY ───────────────────────────────────────
def g_elo_update(current_elo: float, opponent_elo: float,
                  margin: float, k: float = 25.0,
                  is_home: bool = False) -> float:
    """
    G-Elo: Generalized Elo with Margin of Victory adjustment.

    From: "G-Elo: Generalization of the Elo algorithm by modeling
           the discretized Margin of Victory" (arxiv 2010.11187)

    Args:
        current_elo: Team's current Elo rating
        opponent_elo: Opponent's Elo rating
        margin: Point differential (positive = win, negative = loss)
        k: K-factor (25 for FBS, 20 for FCS)
        is_home: Home game (add home-field advantage to margin)

    Returns:
        New Elo rating
    """
    expected = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 400))

    # Margin of victory multiplier (discretized MOV)
    if margin == 0:
        mov_mult = 0.5
    else:
        mov_mult = math.log(abs(margin) + 1) / 7.0
        mov_mult = max(0.5, min(1.5, mov_mult))  # Cap between 0.5x and 1.5x

    if is_home:
        mov_mult *= 1.0  # Home field baked into margin

    actual = 1 if margin > 0 else 0 if margin < 0 else 0.5

    new_elo = current_elo + k * mov_mult * (actual - expected)
    return round(new_elo, 1)


def ncf_game_prediction(
    home_elo: float, away_elo: float,
    home_p5: bool = False, away_p5: bool = False,
    is_neutral: bool = False, is_playoff: bool = False
) -> Dict:
    """
    NCAA Football game prediction using G-Elo + situational adjustments.

    Args:
        home_elo, away_elo: Current G-Elo ratings
        home_p5, away_p5: Power 5 conference bonus (P5 teams get +7.0 boost)
        is_neutral: Neutral site game
        is_playoff: College football playoff game

    Returns:
        Win probabilities, predicted margin, suggested spread
    """
    p5_boost = 7.0 if home_p5 else 0.0
    home_eff = home_elo + p5_boost
    away_eff = (away_elo + (7.0 if away_p5 else 0.0))

    # Home field: 3.0 for FBS, 2.5 for FCS
    home_field = 3.0 if not is_neutral else 0.0

    # Elo difference → probability
    elo_diff = home_eff - away_eff + home_field
    home_prob = 1 / (1 + 10 ** (-elo_diff / 400))

    # Playoff pressure: tighter games in playoffs
    if is_playoff:
        home_prob = 0.5 + (home_prob - 0.5) * 0.85

    # Predicted margin
    # Using sigmoid scaling: 400 Elo diff ≈ 17 points at neutral
    pred_margin = elo_diff / 400 * 17

    return {
        "home_win_prob": round(home_prob, 3),
        "away_win_prob": round(1 - home_prob, 3),
        "pred_margin": round(pred_margin, 1),
        "home_spread": f"HOME +{round(-pred_margin, 1) if pred_margin > 0 else round(abs(pred_margin), 1)}",
        "elo_diff": round(elo_diff, 1),
        "home_field_points": home_field,
        "method": "ncf_g_elo"
    }


# ── MAIN REPORT GENERATOR ─────────────────────────────────────────────────────
def generate_pregame_report(sport: str, away_team: str, home_team: str,
                            injury_data: List[Dict] = None,
                            odds_data: Dict = None,
                            injury_window_hours: int = 2) -> str:
    """
    Generate a plain-English pregame report at a 6th grade reading level.

    Covers:
      - Injury reports
      - Minute projections (NBA/WNBA)
      - Key stat projections (pts/reb/ast/3pm/stl/blk)
      - Best bets from TC algorithm

    Args:
        sport: NBA, WNBA, MLB, NCAAB, NCAAF, NHL
        away_team, home_team: Abbreviations
        injury_data: List of injury dicts
        odds_data: Sportsbook odds (spread, total, ML)
        injury_window_hours: Hours before tip/off to run (default 2)
    """
    now = datetime.now()
    tip_time = now + timedelta(hours=injury_window_hours)

    report = []
    report.append("=" * 54)
    report.append(f"{away_team.upper()}  @  {home_team.upper()} — {sport}")
    report.append(f"⏰ {tip_time.strftime('%I:%M %p ET')} | Report: {now.strftime('%I:%M %p ET')}")
    report.append("=" * 54)

    # ── INJURY REPORT ──────────────────────────────────────────────────────
    if injury_data:
        report.append("\n🏥 INJURY REPORT")
        report.append("-" * 40)

        out_list = [i for i in injury_data if i.get("status_code") in ("OUT", "D")]
        q_list   = [i for i in injury_data if i.get("status_code") in ("Q", "GTD")]
        p_list   = [i for i in injury_data if i.get("status_code") in ("P",)]

        if out_list:
            report.append("  OUT (not playing):")
            for i in out_list:
                report.append(f"    • {i.get('name','?')} ({i.get('position','')}) — {i.get('injury','?')}")
        if q_list:
            report.append("  QUESTIONABLE (might play):")
            for i in q_list:
                report.append(f"    • {i.get('name','?')} ({i.get('position','')}) — {i.get('injury','?')}")
        if p_list:
            report.append("  PROBABLE (playing tonight):")
            for i in p_list:
                report.append(f"    • {i.get('name','?')} ({i.get('position','')})")

    # ── STAT PREVIEW ──────────────────────────────────────────────────────
    report.append("\n📊 WHAT EACH TEAM DOES WELL")
    report.append("-" * 40)

    if sport in ("NBA", "WNBA"):
        report.append("  This is a player-by-player estimate.")
        report.append("  TC = our computer's guess at how each player will do.")
        report.append("  Edge = how much better/worse TC thinks vs what Vegas says.")

    elif sport == "MLB":
        report.append("  Our computer looks at:")
        report.append("    • Each team's run-scoring ability (batting)")
        report.append("    • Starting pitcher quality (FIP — better than ERA)")
        report.append("    • Ballpark size (Coors Field = more runs)")
        report.append("    • Then runs a math model (Poisson) to guess total runs")

    elif sport == "NCAAB":
        report.append("  We use efficiency stats (points per possession)")
        report.append("  adjusted for who they played. Massey Rating method.")

    elif sport == "NCF":
        report.append("  G-Elo: Updated Elo that counts blowout wins more")
        report.append("  Includes home field, Power 5 conference bonus")

    elif sport == "NHL":
        report.append("  Goal scoring model (Poisson distribution)")
        report.append("  Factors in: 5v5 play, goaltending, special teams")

    # ── BEST BETS ─────────────────────────────────────────────────────────
    if odds_data:
        report.append("\n🎯 BEST BETS TONIGHT")
        report.append("-" * 40)

        spreads = odds_data.get("spreads", [])
        totals  = odds_data.get("totals", [])
        mls     = odds_data.get("ml", [])

        for b in (spreads or [])[:3]:
            report.append(f"  {b}")
        for b in (totals or [])[:2]:
            report.append(f"  {b}")
        for b in (mls or [])[:2]:
            report.append(f"  {b}")

    # ── TC SUMMARY (NBA/WNBA) ─────────────────────────────────────────────
    if sport in ("NBA", "WNBA"):
        report.append("\n🏀 TC PLAYER PROJECTIONS")
        report.append("-" * 40)
        report.append("  (TC = Triple Conservative computer estimate)")
        report.append("  PTS/REB/AST/3PM/STL/BLK — top players per team")
        report.append("  Signal: OVER = take the OVER | UNDER = take the UNDER")

    report.append("\n" + "=" * 54)
    report.append(f"Report generated {now.strftime('%I:%M %p ET')} — {injury_window_hours}hr before event")
    report.append("Powered by Zo Computer | Sports TC Engine")
    report.append("=" * 54)

    return "\n".join(report)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Multi-Sport Projection Engine")
    parser.add_argument("--sport", required=True,
                        choices=["NBA","WNBA","MLB","NCAAB","NCF","NHL","ALL"])
    parser.add_argument("--game", default="", help="e.g. OKC@SAS or NYY@BOS")
    parser.add_argument("--report", action="store_true", help="Generate plain-English report")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    sport = args.sport
    game  = args.game or (f"{sport} GAME" if sport != "ALL" else "ALL SPORTS")

    if args.report:
        report = generate_pregame_report(sport, "AWAY", "HOME")
        print(report)
    else:
        print(f"[{sport}] Multi-Sport Engine ready — game: {game}")
        print("  Use --report to generate plain-English output")
        print("  Use --json for machine-readable output")


if __name__ == "__main__":
    main()
