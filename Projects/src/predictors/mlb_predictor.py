# src/predictors/mlb_predictor.py
import random
from typing import Dict, List, Any

class MLBHybridPredictor:
    def __init__(self):
        self.weights = {
            "avg": 0.4, "hr": 0.6, "rbi": 0.5, "r": 0.5,
            "sb": 0.7, "ops": 0.4, "era": 0.5, "whip": 0.5, "so": 0.5
        }
    
    def predict(self, player: Dict, features: Dict) -> Dict:
        results = {}
        for stat, weight in self.weights.items():
            tc_pred = features.get(f"season_avg_{stat}", 0)
            opp_factor = 1.0 - (features.get("opp_drtg", 100) - 100) / 100 * 0.1
            recent = features.get(f"recent_5_{stat}", tc_pred)
            recent_factor = 0.7 + 0.3 * (recent / tc_pred if tc_pred > 0 else 1)
            hybrid = tc_pred * opp_factor * recent_factor * (0.8 + 0.2 * weight)
            results[stat] = {
                "projection": round(hybrid, 3),
                "tc_component": round(tc_pred, 3),
                "confidence": round(0.7 + 0.3 * (1 - abs(hybrid - tc_pred) / (tc_pred + 1)), 2)
            }
        return results

def predict_mlb_player(player: Dict, features: Dict) -> Dict:
    return MLBHybridPredictor().predict(player, features)
