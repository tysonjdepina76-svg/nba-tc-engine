"""Train the Hybrid WNBA predictor on synthetic historical data and save it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/home/workspace/Projects")))

import numpy as np
import pandas as pd

from src.domain.entities import REGISTRY
from src.predictors import HybridWNBAPropPredictor


def build_synthetic_history(days: int = 60) -> pd.DataFrame:
    """Generate synthetic WNBA history for training."""
    np.random.seed(42)
    players = [
        "A'ja Wilson", "Breanna Stewart", "Aliyah Boston", "Satou Sabally",
        "Jewell Loyd", "Napheesa Collier", "Kelsey Mitchell", "Jackie Young",
        "Alyssa Thompson", "Caitlin Clark", "Angel Reese", "Diana Taurasi",
    ]
    rows = []
    for p in players:
        base = {
            "A'ja Wilson": 25.0, "Breanna Stewart": 22.0, "Aliyah Boston": 15.0,
            "Satou Sabally": 18.0, "Jewell Loyd": 19.0, "Napheesa Collier": 17.0,
            "Kelsey Mitchell": 17.5, "Jackie Young": 14.0, "Alyssa Thompson": 9.0,
            "Caitlin Clark": 16.0, "Angel Reese": 13.5, "Diana Taurasi": 16.5,
        }.get(p, 14.0)
        for _ in range(20):
            rows.append({
                "player": p,
                "minutes": max(15.0, 30 + np.random.normal(0, 4)),
                "usage_rate": max(10.0, 25 + np.random.normal(0, 5)),
                "is_home": int(np.random.choice([0, 1])),
                "rest_days": int(np.random.randint(1, 4)),
                "season_avg_pts": base + np.random.normal(0, 1),
                "season_avg_ast": 4 + np.random.normal(0, 0.5),
                "season_avg_fg3m": 1.5 + np.random.normal(0, 0.3),
                "recent_5_pts": base + np.random.normal(0, 2),
                "recent_5_ast": 4 + np.random.normal(0, 1),
                "recent_5_fg3m": 1.5 + np.random.normal(0, 0.5),
                "opp_drtg": 105 + np.random.normal(0, 3),
                "opp_3pa_allowed": 22 + np.random.normal(0, 2),
                "creation_rate": max(0.0, 0.15 + np.random.normal(0, 0.05)),
                "spotup_rate": max(0.0, 0.25 + np.random.normal(0, 0.05)),
                "vs_switching_def": int(np.random.choice([0, 1], p=[0.7, 0.3])),
                "target_pts": max(0.0, base + np.random.normal(0, 5)),
                "target_ast": max(0.0, 4 + np.random.normal(0, 2.5)),
                "target_fg3m": max(0.0, 1.5 + np.random.normal(0, 1.2)),
            })
    return pd.DataFrame(rows)


def main() -> None:
    predictor = REGISTRY.get_predictor()
    if predictor is None:
        print("❌ Hybrid predictor not initialized")
        return

    df = build_synthetic_history()
    predictor.train(df, targets=["pts", "ast", "fg3m"])
    predictor.save()
    print(f"✅ Trained on {len(df)} rows. Saved to models/hybrid_wnba/hybrid_wnba.pkl")
    print(f"   XGB models: {list(predictor.xgb_models.keys())}")
    print(f"   LGB models: {list(predictor.lgb_models.keys())}")
    print(f"   RF  models: {list(predictor.rf_models.keys())}")


if __name__ == "__main__":
    main()
