# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""Combo qualifier — self-edge based, no market dependency.

Generates 2-4 leg combos from Projection output using:
  - Min edge (self-edge: tc_projection vs 0.9x baseline)
  - Min confidence
  - Min correlation (same team, both offensive)
  - Min hit probability (product of leg confidences, correlation-adjusted)
  - Min/max leg count

Supports median line aggregation across DK/FD/ESPN when sources are present.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import statistics

from .entities import Projection
from .sport_config import get_config


# ─────────────────────────────────────────────────────────────────────────────
# Per-sport combo criteria (default values from spec)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_COMBO_CRITERIA: Dict[str, Dict] = {
    "NFL":    {"min_edge": 1.5, "min_confidence": 0.60, "min_correlation": 0.3, "min_hit_prob": 0.50, "max_legs": 4, "min_legs": 2},
    "NBA":    {"min_edge": 1.5, "min_confidence": 0.60, "min_correlation": 0.3, "min_hit_prob": 0.50, "max_legs": 4, "min_legs": 2},
    "WNBA":   {"min_edge": 1.5, "min_confidence": 0.60, "min_correlation": 0.3, "min_hit_prob": 0.50, "max_legs": 4, "min_legs": 2},
    "MLB":    {"min_edge": 1.5, "min_confidence": 0.55, "min_correlation": 0.2, "min_hit_prob": 0.45, "max_legs": 5, "min_legs": 2},
    "SOCCER": {"min_edge": 1.5, "min_confidence": 0.60, "min_correlation": 0.3, "min_hit_prob": 0.50, "max_legs": 4, "min_legs": 2},
    "NHL":    {"min_edge": 1.5, "min_confidence": 0.60, "min_correlation": 0.3, "min_hit_prob": 0.50, "max_legs": 4, "min_legs": 2},
    "BOXING": {"min_edge": 1.5, "min_confidence": 0.65, "min_correlation": 0.4, "min_hit_prob": 0.55, "max_legs": 3, "min_legs": 2},
    "MMA":    {"min_edge": 1.5, "min_confidence": 0.65, "min_correlation": 0.4, "min_hit_prob": 0.55, "max_legs": 3, "min_legs": 2},
}


# ─────────────────────────────────────────────────────────────────────────────
# Offensive stat classifier (for correlation filter)
# ─────────────────────────────────────────────────────────────────────────────

OFFENSIVE_STATS = {
    "PTS", "REB", "AST", "3PM", "STL", "BLK",  # NBA/WNBA
    "HITS", "RBI", "RUNS", "HR", "TB", "SB", "BB",  # MLB
    "G", "A", "SOT", "S", "COR",  # SOCCER
    "PASS_YDS", "PASS_TD", "RUSH_YDS", "RUSH_TD", "REC", "REC_YDS", "REC_TD", "REC_TGT",  # NFL
    "GOALS", "ASSISTS", "POINTS", "SHOTS", "SOG", "PPP",  # NHL
    "LANDED", "POWER_LANDED", "JABS_LANDED",  # BOXING
    "SIG_LANDED", "TD_LANDED",  # MMA
}


def is_offensive_stat(stat: str) -> bool:
    """Check if a stat is offensive (correlates with teammates positively)."""
    return stat.upper() in OFFENSIVE_STATS


# ─────────────────────────────────────────────────────────────────────────────
# Median line across sources
# ─────────────────────────────────────────────────────────────────────────────

def median_line(lines: List[Optional[float]]) -> Optional[float]:
    """Compute median of available lines. Returns None if no lines."""
    valid = [l for l in lines if l is not None and l > 0]
    if not valid:
        return None
    return statistics.median(valid)


# ─────────────────────────────────────────────────────────────────────────────
# Combo + Filter result dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Combo:
    sport: str
    game_id: str
    legs: List[Projection]
    avg_edge: float
    avg_confidence: float
    correlation: float
    hit_probability: float
    total_legs: int

    def to_dict(self) -> Dict:
        return {
            "sport": self.sport,
            "game_id": self.game_id,
            "legs": [l.to_dict() for l in self.legs],
            "avg_edge": round(self.avg_edge, 2),
            "avg_confidence": round(self.avg_confidence, 3),
            "correlation": round(self.correlation, 3),
            "hit_probability": round(self.hit_probability, 3),
            "total_legs": self.total_legs,
        }


@dataclass
class FilterReport:
    """Which projections were filtered out and why."""
    passed: List[Projection]
    filtered: List[Tuple[Projection, str]]  # (proj, reason)

    def to_dict(self) -> Dict:
        return {
            "passed_count": len(self.passed),
            "filtered_count": len(self.filtered),
            "filtered_reasons": [
                {"player": p.player, "team": p.team, "stat": p.stat, "reason": r}
                for p, r in self.filtered
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# ComboQualifier
# ─────────────────────────────────────────────────────────────────────────────

class ComboQualifier:
    def __init__(self, sport: str, criteria_override: Optional[Dict] = None):
        self.sport = sport.upper()
        self.criteria = {**DEFAULT_COMBO_CRITERIA.get(self.sport, DEFAULT_COMBO_CRITERIA["NFL"])}
        if criteria_override:
            self.criteria.update(criteria_override)

    def filter_projections(self, projections: List[Projection]) -> FilterReport:
        """Apply single-leg filters. Returns passed + filtered-with-reason."""
        passed = []
        filtered = []
        for p in projections:
            if not p.valid:
                filtered.append((p, "invalid projection"))
                continue
            if abs(p.edge) < self.criteria["min_edge"]:
                filtered.append((p, f"edge {p.edge:.2f} < {self.criteria['min_edge']}"))
                continue
            # Confidence gate: tc_projection's confidence is encoded as direction+edge magnitude
            conf = self._estimate_confidence(p)
            if conf < self.criteria["min_confidence"]:
                filtered.append((p, f"confidence {conf:.2f} < {self.criteria['min_confidence']}"))
                continue
            passed.append(p)
        return FilterReport(passed=passed, filtered=filtered)

    def _estimate_confidence(self, p: Projection) -> float:
        """Estimate confidence from edge magnitude + direction.

        No market lines available, so confidence is derived from how far
        the projection sits above (or below) its 0.9x baseline.
        """
        base = 0.5
        if abs(p.edge) >= 5.0:
            return min(0.95, base + 0.4)
        if abs(p.edge) >= 3.0:
            return min(0.85, base + 0.3)
        if abs(p.edge) >= 2.0:
            return min(0.75, base + 0.2)
        if abs(p.edge) >= 1.5:
            return min(0.65, base + 0.1)
        return base

    def _pair_correlation(self, p1: Projection, p2: Projection) -> float:
        """Estimate correlation between two props (0.0 - 1.0).

        Same team + both offensive → high correlation
        Same team + mixed → medium
        Different teams → 0 (uncorrelated, no combo)
        """
        if p1.team != p2.team:
            return 0.0
        off1 = is_offensive_stat(p1.stat)
        off2 = is_offensive_stat(p2.stat)
        if off1 and off2:
            # Same team, both offensive
            if p1.player == p2.player:
                return 0.9  # same player, different stats — very correlated
            return 0.5  # teammates, both producing
        if off1 or off2:
            return 0.3
        return 0.2

    def _hit_probability(self, legs: List[Projection], correlation: float) -> float:
        """Combined hit probability, correlation-adjusted.

        Base: product of individual confidences.
        Adjustment: positive correlation slightly raises joint hit (teammates
        both go off together, or both get shut down). Capped at 0.95.
        """
        probs = [self._estimate_confidence(l) for l in legs]
        base = 1.0
        for p in probs:
            base *= p
        # correlation bonus: positive correlation -> slight lift (limited to 1.25x)
        adj = 1.0 + (correlation * 0.25)
        return min(0.95, base * adj)

    def _build_combo(self, game_id: str, legs: List[Projection]) -> Optional[Combo]:
        if len(legs) < self.criteria["min_legs"] or len(legs) > self.criteria["max_legs"]:
            return None
        # Compute average correlation across all unique pairs
        pair_corrs = []
        for i in range(len(legs)):
            for j in range(i + 1, len(legs)):
                pair_corrs.append(self._pair_correlation(legs[i], legs[j]))
        if not pair_corrs:
            return None
        avg_corr = sum(pair_corrs) / len(pair_corrs)
        if avg_corr < self.criteria["min_correlation"]:
            return None
        avg_edge = sum(abs(l.edge) for l in legs) / len(legs)
        avg_conf = sum(self._estimate_confidence(l) for l in legs) / len(legs)
        hit_prob = self._hit_probability(legs, avg_corr)
        if hit_prob < self.criteria["min_hit_prob"]:
            return None
        return Combo(
            sport=self.sport,
            game_id=game_id,
            legs=legs,
            avg_edge=avg_edge,
            avg_confidence=avg_conf,
            correlation=avg_corr,
            hit_probability=hit_prob,
            total_legs=len(legs),
        )

    def qualify(self, projections: List[Projection]) -> Tuple[List[Combo], FilterReport]:
        """Top-level: filter + build combos.

        Returns (qualified_combos, filter_report).
        Combos sorted by hit_probability desc.
        """
        report = self.filter_projections(projections)
        passed = report.passed

        # Group by team within each game (game_id inferred from player matchup metadata
        # — fall back to team+stat bucket when game_id is missing)
        from collections import defaultdict
        buckets: Dict[Tuple[str, str], List[Projection]] = defaultdict(list)
        for p in passed:
            game_id = getattr(p, "game_id", None) or f"{p.team}-unknown"
            buckets[(game_id, p.team)].append(p)

        combos: List[Combo] = []
        # 2-leg combos: pair teammates
        for (game_id, team), props in buckets.items():
            for i in range(len(props)):
                for j in range(i + 1, len(props)):
                    c = self._build_combo(game_id, [props[i], props[j]])
                    if c:
                        combos.append(c)
            # 3-leg combos: top 3 by edge
            if len(props) >= 3 and self.criteria["max_legs"] >= 3:
                top3 = sorted(props, key=lambda x: abs(x.edge), reverse=True)[:3]
                c = self._build_combo(game_id, top3)
                if c:
                    combos.append(c)
            # 4-leg combos: top 4 by edge
            if len(props) >= 4 and self.criteria["max_legs"] >= 4:
                top4 = sorted(props, key=lambda x: abs(x.edge), reverse=True)[:4]
                c = self._build_combo(game_id, top4)
                if c:
                    combos.append(c)

        combos.sort(key=lambda c: c.hit_probability, reverse=True)
        return combos, report


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: aggregate lines from multiple sources
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_lines(sources: Dict[str, Optional[float]]) -> Dict:
    """Aggregate lines from multiple book sources.

    Returns:
      {
        "median": float | None,
        "mean": float | None,
        "sources": {dk: float, fd: float, espn: float},
        "agreement": float  # 0.0 - 1.0, how close sources are (1.0 = identical)
      }
    """
    valid = {k: v for k, v in sources.items() if v is not None and v > 0}
    if not valid:
        return {"median": None, "mean": None, "sources": sources, "agreement": 0.0}
    vals = list(valid.values())
    med = statistics.median(vals)
    mean = statistics.mean(vals)
    if len(vals) == 1:
        agreement = 1.0
    else:
        spread = max(vals) - min(vals)
        agreement = max(0.0, 1.0 - (spread / max(med, 0.1)))
    return {"median": med, "mean": mean, "sources": sources, "agreement": round(agreement, 3)}
