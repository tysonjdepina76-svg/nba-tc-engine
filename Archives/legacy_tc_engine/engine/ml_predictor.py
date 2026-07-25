"""ML Predictor — Random Forest with probability calibration.

Trains on historical feature data and produces calibrated probability
estimates for TC picks.
"""
from typing import Dict, Optional
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
import pickle
from pathlib import Path


class MLPredictor:
    def __init__(self):
        self.model: Optional[CalibratedClassifierCV] = None
        self.scaler: Optional[StandardScaler] = None
        self._trained = False

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        base = RandomForestClassifier(
            n_estimators=100, max_depth=8, min_samples_split=10,
            random_state=42, n_jobs=-1
        )
        self.model = CalibratedClassifierCV(base, method="sigmoid", cv=5)
        self.model.fit(X_scaled, y)
        self._trained = True

        return {
            "n_samples": len(y),
            "n_features": X.shape[1],
            "class_balance": float(np.mean(y)),
            "trained": True,
        }

    def predict(self, features: Dict) -> Dict:
        if not self._trained or self.model is None:
            return {"probability": 0.5, "features": features, "calibrated": False,
                    "note": "Model not trained — returning neutral probability"}

        feature_values = np.array([[float(v) for v in features.values()]])
        if self.scaler:
            feature_values = self.scaler.transform(feature_values)

        proba = self.model.predict_proba(feature_values)[0]
        return {
            "probability": round(float(proba[1]), 4),
            "under_probability": round(float(proba[0]), 4),
            "features": features,
            "calibrated": True,
        }

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "scaler": self.scaler, "trained": self._trained}, f)

    @classmethod
    def load(cls, path: str) -> "MLPredictor":
        with open(path, "rb") as f:
            data = pickle.load(f)
        instance = cls()
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance._trained = data.get("trained", True)
        return instance
