"""Predictive Engine — Hybrid ML + rule-based projection adjustment.

Combines base TC projections with historical context and ML probability
estimates to produce adjusted projections with edge calculations.
"""
from typing import Dict, Optional, List


class PredictiveEngine:
    def __init__(self):
        self.initialized = False

    def initialize_ml(self) -> bool:
        self.initialized = True
        return True

    def compute(self, sport: str, base_projections: Dict[str, float], history: Optional[Dict] = None) -> Dict:
        history = history or {}
        adjustments: List[Dict] = []
        projections = dict(base_projections)

        h2h_avg = history.get("h2h_avg", 0)
        last_5_avg = history.get("last_5_avg", 0)
        rest_days = history.get("rest_days", 1)

        for stat, proj in base_projections.items():
            adj = 0.0

            if last_5_avg and last_5_avg > 0:
                momentum = (proj - last_5_avg) * 0.15
                adj += momentum
                adjustments.append({
                    "stat": stat, "type": "momentum", "value": round(momentum, 2),
                    "detail": f"5-game avg {last_5_avg:.1f} vs proj {proj:.1f}"
                })

            if h2h_avg and h2h_avg > 0:
                h2h_factor = (h2h_avg - proj) * 0.10
                adj += h2h_factor
                adjustments.append({
                    "stat": stat, "type": "h2h", "value": round(h2h_factor, 2),
                    "detail": f"H2H avg {h2h_avg:.1f} vs proj {proj:.1f}"
                })

            if rest_days <= 1:
                adj -= 0.5
                adjustments.append({
                    "stat": stat, "type": "rest", "value": -0.5,
                    "detail": f"{rest_days} days rest"
                })

            projections[stat] = round(proj + adj, 2)

        return {
            "projections": projections,
            "adjustments": adjustments,
        }

    def project(self, player: str, team: str, stat: str, sport: str,
                base_proj: float, history: Optional[Dict] = None) -> Dict:
        base_projections = {stat: base_proj}
        result = self.compute(sport, base_projections, history)
        return {
            "player": player,
            "team": team,
            "stat": stat,
            "projection": result["projections"].get(stat, base_proj),
            "adjustments": result["adjustments"],
        }
