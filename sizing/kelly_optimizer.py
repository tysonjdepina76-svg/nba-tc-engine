import numpy as np
from typing import List, Dict, Optional

class KellyOptimizer:
    @staticmethod
    def simulate_growth(edges: List[float], fraction: float, bankroll: float = 1000) -> float:
        bankrolls = [bankroll]
        for edge in edges:
            if edge > 0:
                bankrolls.append(bankrolls[-1] * (1 + fraction * edge))
            else:
                bankrolls.append(bankrolls[-1] * (1 - fraction * abs(edge)))
        return bankrolls[-1]

    @staticmethod
    def optimize_kelly(edges: List[float], grid: Optional[List[float]] = None) -> Dict:
        if grid is None:
            grid = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        best_fraction = 0.25
        best_growth = 0
        for f in grid:
            growth = KellyOptimizer.simulate_growth(edges, f)
            if growth > best_growth:
                best_growth = growth
                best_fraction = f
        return {"recommended_kelly_fraction": best_fraction, "growth": best_growth}

    @staticmethod
    def monte_carlo(edges: List[float], n_sims: int = 1000) -> Dict:
        results = []
        for _ in range(n_sims):
            sample_edges = np.random.choice(edges, len(edges), replace=True)
            opt = KellyOptimizer.optimize_kelly(sample_edges.tolist())
            results.append(opt["recommended_kelly_fraction"])
        return {
            "mean": np.mean(results),
            "std": np.std(results),
            "p10": np.percentile(results, 10),
            "p90": np.percentile(results, 90)
        }
