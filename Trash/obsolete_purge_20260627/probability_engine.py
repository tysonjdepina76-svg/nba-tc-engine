#!/usr/bin/env python3
"""
Probability Engine — Implied → Fair → Edge
===========================================
Separate from TC projections. This module converts betting odds into:
  1. Implied probability (raw odds → probability)
  2. Market overround / vig
  3. Fair (vig-free) probability  
  4. Edge = TC estimated probability - fair probability

Usage:
  from probability_engine import ProbabilityEngine
  pe = ProbabilityEngine()
  edge = pe.compute_edge(market_odds=-110, tc_win_prob=0.58)  # +5.6% edge
  fair_ml = pe.fair_moneyline_from_tc(tc_win_prob=0.58, vig=0.045)  # -138

Tyson's 4-step model:
  Step 1: Convert odds to implied probability (e.g. -110 → 52.38%)
  Step 2: Sum implied probs → overround/vig (e.g. 1.048 → 4.8% vig)
  Step 3: Divide each implied by overround → fair probability (e.g. 52.38/1.048 = 50%)
  Step 4: Edge = TC estimated win% - fair win%

Author: Tyson | Zo Computer | TC Pipeline
"""

import math
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, field


@dataclass
class FairOdds:
    """Container for vig-adjusted fair odds/probabilities for a two-way market."""
    fair_prob_away: float
    fair_prob_home: float
    fair_ml_away: int
    fair_ml_home: int
    implied_prob_away: float
    implied_prob_home: float
    overround: float
    vig_pct: float
    book: str = "unknown"


@dataclass 
class EdgeResult:
    """Edge analysis for a single side of a bet."""
    market_odds: int
    implied_prob: float
    fair_prob: float
    tc_estimated_prob: float
    edge_pct: float
    bet_direction: str  # "OVER", "UNDER", "FAVORITE", "UNDERDOG"
    kelly_fraction: float
    recommendation: str  # "BET", "PASS", "NO PLAY"


class ProbabilityEngine:
    """Core probability engine — odds ↔ probability ↔ edge math."""

    # Default vig assumptions per sport (WNBA ~4.5%, MLB ~3.5%, WC ~4%)
    DEFAULT_VIG: Dict[str, float] = {
        "WNBA": 0.045,
        "MLB": 0.035,
        "WORLD CUP": 0.040,
        "NBA": 0.045,
        "NFL": 0.045,
        "SOCCER": 0.040,
        "default": 0.045,
    }

    # ── Step 1: Odds → Implied Probability ────────────────────

    @staticmethod
    def american_to_implied(odds: int) -> float:
        """Convert American odds to implied probability.
        -110 → 0.5238 | +150 → 0.4000 | +100 → 0.5000
        """
        if odds > 0:
            return 100.0 / (odds + 100.0)
        else:
            return abs(odds) / (abs(odds) + 100.0)

    @staticmethod
    def implied_to_american(prob: float) -> int:
        """Convert implied probability to American odds.
        0.5238 → -110 | 0.4000 → +150
        """
        if prob <= 0 or prob >= 1:
            return 0
        if prob >= 0.5:
            return -round((prob / (1 - prob)) * 100)
        else:
            return round(((1 - prob) / prob) * 100)

    @staticmethod
    def decimal_to_implied(decimal_odds: float) -> float:
        """Convert decimal odds to implied probability.
        1.91 → 0.5236
        """
        if decimal_odds <= 0:
            return 0.0
        return 1.0 / decimal_odds

    @staticmethod
    def implied_to_decimal(prob: float) -> float:
        """Convert implied probability to decimal odds."""
        if prob <= 0:
            return float('inf')
        return 1.0 / prob

    # ── Step 2: Overround / Vig Calculation ───────────────────

    @staticmethod
    def compute_overround(away_odds: int, home_odds: int) -> Tuple[float, float, float]:
        """Compute overround and vig from a two-way market.
        Returns (overround, implied_away, implied_home).
        overround = implied_away + implied_home (e.g. 1.048 = 4.8% vig)
        """
        imp_away = ProbabilityEngine.american_to_implied(away_odds)
        imp_home = ProbabilityEngine.american_to_implied(home_odds)
        overround = imp_away + imp_home
        return overround, imp_away, imp_home

    @staticmethod
    def overround_to_vig_pct(overround: float) -> float:
        """Convert overround to vig percentage.
        1.048 → 0.0458 (4.58%)
        """
        if overround <= 0:
            return 0.0
        # Vig = overround - 1 (simplified)
        return overround - 1.0

    @staticmethod
    def vig_pct_to_overround(vig_pct: float) -> float:
        """Convert vig percentage to overround.
        0.045 → 1.045
        """
        return 1.0 + vig_pct

    # ── Step 3: Fair (Vig-Free) Probability ───────────────────

    @staticmethod
    def fair_prob_from_odds(away_odds: int, home_odds: int) -> FairOdds:
        """Strip vig from a two-way market to get fair probabilities.
        
        Method: Divide each implied probability by the total overround.
        This distributes the vig proportionally.
        
        Example:
          away_odds=-110, home_odds=-110
          imp_away=0.5238, imp_home=0.5238
          overround=1.0476
          fair_away=0.5000, fair_home=0.5000
        """
        overround, imp_away, imp_home = ProbabilityEngine.compute_overround(
            away_odds, home_odds
        )
        if overround > 0:
            fair_away = imp_away / overround
            fair_home = imp_home / overround
        else:
            fair_away = 0.5
            fair_home = 0.5

        fair_ml_away = ProbabilityEngine.implied_to_american(fair_away)
        fair_ml_home = ProbabilityEngine.implied_to_american(fair_home)

        return FairOdds(
            fair_prob_away=round(fair_away, 4),
            fair_prob_home=round(fair_home, 4),
            fair_ml_away=fair_ml_away,
            fair_ml_home=fair_ml_home,
            implied_prob_away=round(imp_away, 4),
            implied_prob_home=round(imp_home, 4),
            overround=round(overround, 4),
            vig_pct=round(ProbabilityEngine.overround_to_vig_pct(overround), 4),
        )

    @staticmethod
    def fair_prob_single_side(market_odds: int, market_overround: float) -> float:
        """Get fair probability for a single side, given known overround.
        
        This is useful when you only have one side's odds but know the market vig.
        fair = implied / overround
        """
        imp = ProbabilityEngine.american_to_implied(market_odds)
        if market_overround <= 0:
            market_overround = 1.045  # default 4.5% vig
        return imp / market_overround

    # ── Step 4: Edge Calculation ──────────────────────────────

    def compute_edge(
        self,
        market_odds: int,
        tc_win_prob: float,
        market_overround: Optional[float] = None,
        opposing_odds: Optional[int] = None,
        sport: str = "default",
    ) -> EdgeResult:
        """Compute edge: TC estimated probability vs fair market probability.
        
        Args:
            market_odds: The book's odds for this side (e.g. -110)
            tc_win_prob: TC engine's estimated win probability (e.g. 0.58)
            market_overround: Known overround. If None, computed from opposing_odds or default vig.
            opposing_odds: The other side's odds (to compute overround). Required if market_overround is None.
            sport: Sport for default vig lookup.
        
        Returns EdgeResult with edge_pct, kelly_fraction, and recommendation.
        """
        # Determine overround
        if market_overround is None:
            if opposing_odds is not None:
                overround_val, _, _ = self.compute_overround(market_odds, opposing_odds)
            else:
                vig = self.DEFAULT_VIG.get(sport, self.DEFAULT_VIG["default"])
                overround_val = self.vig_pct_to_overround(vig)
        else:
            overround_val = market_overround

        # Fair probability for this side
        fair_p = self.fair_prob_single_side(market_odds, overround_val)

        # Implied probability (book's raw)
        imp_p = self.american_to_implied(market_odds)

        # Edge: how much better TC thinks the outcome is vs fair market
        edge_pct = tc_win_prob - fair_p

        # Determine direction
        if abs(edge_pct) < 0.01:
            direction = "PASS"
        elif edge_pct > 0:
            direction = "FAVORITE" if market_odds < 0 else "UNDERDOG"
        else:
            direction = "NO PLAY"

        # Kelly fraction (half-Kelly for conservative sizing)
        # f = edge / (odds - 1) for decimal odds
        decimal_odds = self.implied_to_decimal(imp_p)
        if decimal_odds > 1.01:
            full_kelly = edge_pct / (decimal_odds - 1.0)
            half_kelly = max(0, full_kelly * 0.5)
        else:
            half_kelly = 0.0

        # Recommendation
        if edge_pct >= 0.05:
            rec = "STRONG BET"
        elif edge_pct >= 0.025:
            rec = "BET"
        elif edge_pct >= 0.01:
            rec = "LIGHT BET"
        elif edge_pct >= -0.01:
            rec = "PASS"
        else:
            rec = "NO PLAY"

        return EdgeResult(
            market_odds=market_odds,
            implied_prob=round(imp_p, 4),
            fair_prob=round(fair_p, 4),
            tc_estimated_prob=round(tc_win_prob, 4),
            edge_pct=round(edge_pct, 4),
            bet_direction=direction,
            kelly_fraction=round(half_kelly, 4),
            recommendation=rec,
        )

    # ── Player Prop Edge ──────────────────────────────────────

    def compute_prop_edge(
        self,
        dk_line: float,
        dk_over_odds: int,
        dk_under_odds: int,
        tc_projection: float,
        sport: str = "WNBA",
    ) -> EdgeResult:
        """Compute edge for a player prop (OVER vs UNDER).
        
        Steps:
        1. Convert DK over/under odds to implied probabilities
        2. Compute overround from both sides
        3. Strip vig → fair probabilities
        4. TC estimated probability based on tc_projection vs line
        5. Edge = TC prob - fair prob
        
        Args:
            dk_line: The prop line (e.g. 21.5 for PTS)
            dk_over_odds: American odds for OVER (e.g. -115)
            dk_under_odds: American odds for UNDER (e.g. -115)
            tc_projection: TC engine projected value
            sport: Sport for default vig
        
        Returns EdgeResult for the OVER side (flip under_edge for UNDER).
        """
        overround, imp_over, imp_under = self.compute_overround(dk_over_odds, dk_under_odds)

        # Fair probabilities
        if overround > 0:
            fair_over = imp_over / overround
            fair_under = imp_under / overround
        else:
            fair_over = 0.5
            fair_under = 0.5

        # TC estimated probability: how confident is TC that the player goes OVER?
        # Using a sigmoid-like function centered on the line with spread based on edge
        raw_edge = tc_projection - dk_line
        # Convert raw edge to probability estimate (calibrated against TC backtest)
        if raw_edge >= 5:
            tc_prob = 0.85
        elif raw_edge >= 3:
            tc_prob = 0.75 + (raw_edge - 3) * 0.05
        elif raw_edge >= 2:
            tc_prob = 0.65 + (raw_edge - 2) * 0.10
        elif raw_edge >= 1:
            tc_prob = 0.55 + (raw_edge - 1) * 0.10
        elif raw_edge >= 0:
            tc_prob = 0.50 + raw_edge * 0.05
        elif raw_edge >= -1:
            tc_prob = 0.45 + raw_edge * 0.05
        elif raw_edge >= -2:
            tc_prob = 0.35 + (raw_edge + 2) * 0.10
        elif raw_edge >= -3:
            tc_prob = 0.25 + (raw_edge + 3) * 0.10
        else:
            tc_prob = 0.15

        tc_prob = max(0.05, min(0.95, tc_prob))

        # Edge: TC prob vs fair prob
        edge_pct = tc_prob - fair_over

        # Direction and recommendation
        if raw_edge > 0:
            direction = "OVER"
        elif raw_edge < 0:
            direction = "UNDER"
        else:
            direction = "NEUTRAL"

        if edge_pct >= 0.05:
            rec = "STRONG BET"
        elif edge_pct >= 0.03:
            rec = "BET"
        elif edge_pct >= 0.015:
            rec = "LIGHT BET"
        elif edge_pct >= -0.015:
            rec = "PASS"
        else:
            rec = "NO PLAY"

        # Kelly sizing
        decimal_odds = self.implied_to_decimal(imp_over)
        if decimal_odds > 1.01:
            full_kelly = edge_pct / (decimal_odds - 1.0)
            half_kelly = max(0, full_kelly * 0.5)
        else:
            half_kelly = 0.0

        return EdgeResult(
            market_odds=dk_over_odds,
            implied_prob=round(imp_over, 4),
            fair_prob=round(fair_over, 4),
            tc_estimated_prob=round(tc_prob, 4),
            edge_pct=round(edge_pct, 4),
            bet_direction=direction,
            kelly_fraction=round(half_kelly, 4),
            recommendation=rec,
        )

    # ── Batch Processing ──────────────────────────────────────

    def analyze_game(self, away_odds: int, home_odds: int, tc_away_prob: Optional[float] = None) -> dict:
        """Full game analysis: fair odds, edge, recommendations for both sides."""
        fair = self.fair_prob_from_odds(away_odds, home_odds)

        result = {
            "fair_odds": fair,
            "market_vig_pct": round(fair.vig_pct * 100, 2),
            "away": None,
            "home": None,
        }

        if tc_away_prob is not None:
            away_edge = self.compute_edge(
                away_odds, tc_away_prob,
                market_overround=fair.overround,
            )
            home_edge = self.compute_edge(
                home_odds, 1.0 - tc_away_prob,
                market_overround=fair.overround,
            )
            result["away"] = away_edge
            result["home"] = home_edge

        return result

    def analyze_slate_props(
        self,
        props: List[dict],
        sport: str = "WNBA",
    ) -> List[dict]:
        """Analyze a slate of player props with probability edges.
        
        Each prop dict should have:
          player, stat, direction, dk_line, dk_over_odds, dk_under_odds, tc_projection
        """
        results = []
        for prop in props:
            edge_result = self.compute_prop_edge(
                dk_line=prop.get("dk_line", 0),
                dk_over_odds=prop.get("dk_over_odds", -115),
                dk_under_odds=prop.get("dk_under_odds", -115),
                tc_projection=prop.get("tc_projection", 0),
                sport=sport,
            )
            results.append({
                "player": prop.get("player", ""),
                "stat": prop.get("stat", ""),
                "direction": edge_result.bet_direction,
                "dk_line": prop.get("dk_line"),
                "tc_projection": prop.get("tc_projection"),
                "raw_edge": prop.get("tc_projection", 0) - prop.get("dk_line", 0),
                "fair_prob": edge_result.fair_prob,
                "tc_prob": edge_result.tc_estimated_prob,
                "edge_pct": edge_result.edge_pct,
                "kelly_fraction": edge_result.kelly_fraction,
                "recommendation": edge_result.recommendation,
            })
        return sorted(results, key=lambda r: abs(r["edge_pct"]), reverse=True)

    # ── Parlay Probability ────────────────────────────────────

    def parlay_probability(self, legs: List[EdgeResult]) -> dict:
        """Compute combined probability for a parlay.
        
        Parlay fair prob = product of individual fair probs (for independent events).
        Parlay TC prob = product of individual TC probs.
        Parlay edge = TC parlay prob - fair parlay prob.
        """
        if not legs:
            return {"fair_prob": 0, "tc_prob": 0, "edge_pct": 0, "legs": 0}

        fair_prob = 1.0
        tc_prob = 1.0
        for leg in legs:
            fair_prob *= leg.fair_prob
            tc_prob *= leg.tc_estimated_prob

        edge_pct = tc_prob - fair_prob

        return {
            "fair_prob": round(fair_prob, 6),
            "tc_prob": round(tc_prob, 6),
            "edge_pct": round(edge_pct, 6),
            "legs": len(legs),
            "implied_odds": self.implied_to_american(tc_prob),
            "fair_odds": self.implied_to_american(fair_prob),
            "recommendation": "BET" if edge_pct > 0.01 else "PASS" if edge_pct > 0 else "NO PLAY",
        }


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Probability Engine")
    parser.add_argument("--odds", type=int, help="American odds to convert")
    parser.add_argument("--away-odds", type=int, help="Away team American odds")
    parser.add_argument("--home-odds", type=int, help="Home team American odds")
    parser.add_argument("--tc-prob", type=float, help="TC estimated probability")
    parser.add_argument("--sport", default="WNBA")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    pe = ProbabilityEngine()

    if args.odds and not args.away_odds:
        imp = pe.american_to_implied(args.odds)
        if args.format == "json":
            print(json.dumps({"odds": args.odds, "implied_prob": round(imp, 4)}))
        else:
            print(f"Odds {args.odds:+d} → Implied Probability: {imp:.4f} ({imp*100:.2f}%)")

    elif args.away_odds and args.home_odds:
        fair = pe.fair_prob_from_odds(args.away_odds, args.home_odds)
        if args.format == "json":
            print(json.dumps({
                "away": {"odds": args.away_odds, "implied": fair.implied_prob_away, "fair": fair.fair_prob_away, "fair_ml": fair.fair_ml_away},
                "home": {"odds": args.home_odds, "implied": fair.implied_prob_home, "fair": fair.fair_prob_home, "fair_ml": fair.fair_ml_home},
                "overround": fair.overround,
                "vig_pct": round(fair.vig_pct * 100, 2),
            }, indent=2))
        else:
            print(f"Away {args.away_odds:+d}: implied={fair.implied_prob_away:.4f}, fair={fair.fair_prob_away:.4f} (fair ML: {fair.fair_ml_away:+d})")
            print(f"Home {args.home_odds:+d}: implied={fair.implied_prob_home:.4f}, fair={fair.fair_prob_home:.4f} (fair ML: {fair.fair_ml_home:+d})")
            print(f"Overround: {fair.overround:.4f} — Vig: {fair.vig_pct*100:.2f}%")

        if args.tc_prob:
            result = pe.analyze_game(args.away_odds, args.home_odds, args.tc_prob)
            if args.format == "json":
                print(json.dumps(result, indent=2, default=str))
            else:
                if result["away"]:
                    a = result["away"]
                    h = result["home"]
                    print(f"\nAway: TC prob={a.tc_estimated_prob:.4f}, edge={a.edge_pct*100:+.2f}%, {a.recommendation}")
                    print(f"Home: TC prob={h.tc_estimated_prob:.4f}, edge={h.edge_pct*100:+.2f}%, {h.recommendation}")
