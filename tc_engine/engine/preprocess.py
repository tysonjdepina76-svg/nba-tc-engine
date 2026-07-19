"""Feature Engineering — Transform raw projections into ML-ready feature vectors.

Handles normalization, interaction features, and context-aware transforms
for the MLPredictor.
"""
from typing import Dict, Optional, List
import numpy as np


class FeatureEngineer:
    CORE_STATS = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "HR", "RBI", "H", "K"]
    INTERACTION_PAIRS = [("PTS", "AST"), ("REB", "AST"), ("PTS", "REB"),
                          ("HR", "RBI"), ("H", "K")]

    def __init__(self):
        self._feature_names: List[str] = []

    def transform(self, stats: Dict, history: Optional[Dict] = None) -> Dict:
        features: Dict[str, float] = {}
        history = history or {}

        for stat, value in stats.items():
            features[str(stat)] = float(value)

        for a, b in self.INTERACTION_PAIRS:
            if a in stats and b in stats:
                features[f"{a}_x_{b}"] = round(float(stats[a]) * float(stats[b]), 2)
            if a in stats:
                features[f"{a}_squared"] = round(float(stats[a]) ** 2, 2)

        last_5 = history.get("last_5_avg", 0)
        h2h = history.get("h2h_avg", 0)
        if last_5 and last_5 > 0 and stats:
            first_stat_val = float(list(stats.values())[0])
            features["recent_form_ratio"] = round(first_stat_val / last_5, 3)
        if h2h and h2h > 0 and stats:
            first_stat_val = float(list(stats.values())[0])
            features["h2h_ratio"] = round(first_stat_val / h2h, 3)
        features["rest_days"] = float(history.get("rest_days", 1))

        return features

    def get_feature_names(self) -> List[str]:
        sample = self.CORE_STATS[:3]
        sample_dict = {s: 10.0 for s in sample}
        sample_features = self.transform(sample_dict)
        return sorted(sample_features.keys())
