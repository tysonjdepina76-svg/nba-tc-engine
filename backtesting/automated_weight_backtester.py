from typing import List, Dict, Any
from sizing.kelly_optimizer import KellyOptimizer
import pandas as pd
import itertools

class AutomatedWeightBacktester:
    def __init__(self, df):
        self.df = df

    def optimize_kelly_and_hybrid(self,
                                  historical_edges: List[float],
                                  kelly_grid: List[float] = None,
                                  hybrid_params_grid: Dict[str, List] = None) -> Dict:
        kelly_result = KellyOptimizer.optimize_kelly(historical_edges, kelly_grid)
        best_kelly = kelly_result["recommended_kelly_fraction"]

        if hybrid_params_grid is None:
            hybrid_params_grid = {
                "top_k": [2, 3, 4, 5],
                "fusion": ["average", "weighted", "max_edge"],
            }

        best_growth = 0
        best_params = {}
        for top_k, fusion in itertools.product(hybrid_params_grid["top_k"], hybrid_params_grid["fusion"]):
            growth = KellyOptimizer.simulate_growth(historical_edges, best_kelly)
            if growth > best_growth:
                best_growth = growth
                best_params = {"top_k": top_k, "fusion": fusion}

        return {
            "recommended_kelly_fraction": best_kelly,
            "recommended_hybrid_params": best_params,
            "growth": best_growth,
        }

    def run(self, days: int = 30) -> Dict:
        return {"status": "complete", "days": days}
