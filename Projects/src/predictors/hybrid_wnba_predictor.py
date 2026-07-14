"""
Hybrid WNBA Prop Predictor — Bayesian + XGBoost + LightGBM ensemble.
Combines TC math projections with ML models trained on historical game data.
"""
from __future__ import annotations

import os
import pickle
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from sklearn.ensemble import RandomForestRegressor
    HAS_SK = True
except ImportError:
    HAS_SK = False

FEATURES = [
    "minutes", "usage_rate", "is_home", "rest_days",
    "season_avg_pts", "season_avg_ast", "season_avg_fg3m",
    "recent_5_pts", "recent_5_ast", "recent_5_fg3m",
    "opp_drtg", "opp_3pa_allowed", "creation_rate", "spotup_rate",
    "vs_switching_def",
]

MODEL_DIR = Path("/home/workspace/Projects/models/hybrid_wnba")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PlayerFeatures:
    """Engineered features for a single player in a single game."""
    minutes: float = 30.0
    usage_rate: float = 25.0
    is_home: int = 1
    rest_days: int = 1
    season_avg_pts: float = 15.0
    season_avg_ast: float = 4.0
    season_avg_fg3m: float = 1.5
    recent_5_pts: float = 15.0
    recent_5_ast: float = 4.0
    recent_5_fg3m: float = 1.5
    opp_drtg: float = 105.0
    opp_3pa_allowed: float = 22.0
    creation_rate: float = 0.15
    spotup_rate: float = 0.25
    vs_switching_def: int = 0

    def to_dict(self) -> Dict[str, float]:
        return {
            "minutes": self.minutes,
            "usage_rate": self.usage_rate,
            "is_home": self.is_home,
            "rest_days": self.rest_days,
            "season_avg_pts": self.season_avg_pts,
            "season_avg_ast": self.season_avg_ast,
            "season_avg_fg3m": self.season_avg_fg3m,
            "recent_5_pts": self.recent_5_pts,
            "recent_5_ast": self.recent_5_ast,
            "recent_5_fg3m": self.recent_5_fg3m,
            "opp_drtg": self.opp_drtg,
            "opp_3pa_allowed": self.opp_3pa_allowed,
            "creation_rate": self.creation_rate,
            "spotup_rate": self.spotup_rate,
            "vs_switching_def": self.vs_switching_def,
        }


@dataclass
class PredictionResult:
    """Hybrid prediction output."""
    median: float
    p10: float
    p90: float
    confidence: float
    hybrid_weight_tc: float
    tc_math_component: float
    ml_component: float
    target: str


class HybridWNBAPropPredictor:
    """Ensemble predictor: TC math + XGBoost + LightGBM + RandomForest."""

    def __init__(self, tc_engine: Any = None, hybrid_weight_tc: float = 0.50):
        self.tc_engine = tc_engine
        self.hybrid_weight_tc = hybrid_weight_tc
        self.xgb_models: Dict[str, Any] = {}
        self.lgb_models: Dict[str, Any] = {}
        self.rf_models: Dict[str, Any] = {}
        self.trained = False

    def _feature_row(self, features: PlayerFeatures) -> np.ndarray:
        return np.array([features.to_dict()[f] for f in FEATURES], dtype=float).reshape(1, -1)

    def _tc_projection(self, features: PlayerFeatures, target: str) -> float:
        if self.tc_engine is not None:
            try:
                class _P:
                    def __init__(self, f, t): self.features, self.target = f, t
                return float(self.tc_engine.predict(_P(features, target), features, target=target))
            except Exception:
                pass
        base = {
            "pts": features.season_avg_pts,
            "reb": 6.0,
            "ast": features.season_avg_ast,
            "fg3m": features.season_avg_fg3m,
            "reb_ast": 10.0,
        }.get(target, 12.0)
        home_boost = 1.03 if features.is_home else 0.97
        return round(base * home_boost, 1)

    def train(self, df: pd.DataFrame, targets: List[str] = ("pts", "ast", "fg3m")) -> None:
        """Train XGB/LGB/RF on historical data. df must have FEATURES + target columns."""
        if df.empty or len(df) < 20:
            self.trained = False
            return

        feat_df = df[[c for c in FEATURES if c in df.columns]].fillna(0.0)
        if feat_df.shape[1] == 0:
            self.trained = False
            return

        for target in targets:
            target_col = f"target_{target}"
            if target_col not in df.columns:
                continue
            y = df[target_col].fillna(df[target_col].median()).values

            if HAS_XGB:
                try:
                    self.xgb_models[target] = xgb.XGBRegressor(
                        n_estimators=80, max_depth=4, learning_rate=0.08,
                        subsample=0.9, colsample_bytree=0.9, random_state=42,
                    ).fit(feat_df, y)
                except Exception:
                    pass

            if HAS_LGB:
                try:
                    self.lgb_models[target] = lgb.LGBMRegressor(
                        n_estimators=80, max_depth=4, learning_rate=0.08,
                        subsample=0.9, colsample_bytree=0.9, random_state=42, verbose=-1,
                    ).fit(feat_df, y)
                except Exception:
                    pass

            if HAS_SK:
                try:
                    self.rf_models[target] = RandomForestRegressor(
                        n_estimators=60, max_depth=6, random_state=42
                    ).fit(feat_df, y)
                except Exception:
                    pass

        self.trained = True

    def _ml_predict(self, target: str, row: np.ndarray) -> float:
        preds: List[float] = []
        if target in self.xgb_models:
            try:
                preds.append(float(self.xgb_models[target].predict(row)[0]))
            except Exception:
                pass
        if target in self.lgb_models:
            try:
                preds.append(float(self.lgb_models[target].predict(row)[0]))
            except Exception:
                pass
        if target in self.rf_models:
            try:
                preds.append(float(self.rf_models[target].predict(row)[0]))
            except Exception:
                pass
        if not preds:
            return 12.0
        return float(np.mean(preds))

    def predict(self, player: Any, features: PlayerFeatures, target: str = "pts") -> PredictionResult:
        """Return hybrid prediction with confidence band."""
        row = self._feature_row(features)
        tc = self._tc_projection(features, target)
        ml = self._ml_predict(target, row) if self.trained else tc
        median = self.hybrid_weight_tc * tc + (1 - self.hybrid_weight_tc) * ml

        # Synthetic uncertainty scales with std of components
        spread = abs(tc - ml)
        p10 = max(0.0, median - max(spread * 0.5 + 1.5, 2.0))
        p90 = median + max(spread * 0.5 + 1.5, 2.0)
        confidence = round(max(0.0, 1.0 - spread / max(median, 1.0) * 0.5), 2)

        return PredictionResult(
            median=round(median, 2),
            p10=round(p10, 2),
            p90=round(p90, 2),
            confidence=confidence,
            hybrid_weight_tc=self.hybrid_weight_tc,
            tc_math_component=round(tc, 2),
            ml_component=round(ml, 2),
            target=target,
        )

    def save(self) -> None:
        """Persist trained models to disk."""
        payload = {
            "xgb": self.xgb_models,
            "lgb": self.lgb_models,
            "rf": self.rf_models,
            "weight": self.hybrid_weight_tc,
        }
        with open(MODEL_DIR / "hybrid_wnba.pkl", "wb") as f:
            pickle.dump(payload, f)

    def load(self) -> bool:
        """Load trained models. Returns True on success."""
        path = MODEL_DIR / "hybrid_wnba.pkl"
        if not path.exists():
            return False
        try:
            with open(path, "rb") as f:
                payload = pickle.load(f)
            self.xgb_models = payload.get("xgb", {})
            self.lgb_models = payload.get("lgb", {})
            self.rf_models = payload.get("rf", {})
            self.hybrid_weight_tc = payload.get("weight", 0.50)
            self.trained = bool(self.xgb_models or self.lgb_models or self.rf_models)
            return self.trained
        except Exception:
            return False
