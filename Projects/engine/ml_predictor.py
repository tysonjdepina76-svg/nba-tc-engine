#!/usr/bin/env python3
"""
ml_predictor.py — TC Calibrated ML Probability Predictor.
RandomForest + SHAP + PDP + ICE for model explainability.
"""

import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss, roc_auc_score, brier_score_loss

logger = logging.getLogger("ml_predictor")

class MLProbabilityPredictor:
    def __init__(self, model_path: str = None):
        self.model = None
        self.feature_columns = [
            "proj_edge", "direction_encoded", "stat_avg", "stat_std",
            "recent_trend", "market_line", "opponent_rank",
        ]
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
    
    def train(self, df: pd.DataFrame, target_col: str = "result_binary"):
        features = [c for c in self.feature_columns if c in df.columns]
        if len(features) < 2:
            logger.error(f"Not enough features in data. Found: {features}")
            return False
        self.feature_columns = features
        
        X = df[features].fillna(0)
        y = df[target_col]
        
        if y.nunique() < 2:
            logger.warning("Only one class in target — can't train")
            return False
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y if y.value_counts().min() > 1 else None
        )
        
        base = RandomForestClassifier(
            n_estimators=300, max_depth=8, min_samples_leaf=5,
            random_state=42, n_jobs=-1
        )
        self.model = CalibratedClassifierCV(base, method="sigmoid", cv=5)
        self.model.fit(X_train, y_train)
        
        probs = self.model.predict_proba(X_test)[:, 1]
        logger.info(f"[ML] Log Loss: {log_loss(y_test, probs):.4f}")
        logger.info(f"[ML] ROC AUC: {roc_auc_score(y_test, probs):.4f}")
        logger.info(f"[ML] Brier: {brier_score_loss(y_test, probs):.4f}")
        return True
    
    def predict_probability(self, features: dict) -> float:
        if self.model is None:
            return 0.5
        X = pd.DataFrame([features]).reindex(columns=self.feature_columns, fill_value=0)
        return float(self.model.predict_proba(X)[0, 1])
    
    def get_feature_importance(self, top_n: int = 15) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model not trained")
        importances = np.mean([
            est.feature_importances_
            for est in self.model.calibrated_classifiers_
        ], axis=0)
        return pd.DataFrame({
            "feature": self.feature_columns,
            "importance": importances
        }).sort_values("importance", ascending=False).head(top_n)
    
    def explain_prediction(self, features: dict) -> dict:
        if self.model is None:
            return {"prediction": 0.5, "shap_values": {}}
        prob = self.predict_probability(features)
        explanation = {"prediction": prob, "shap_values": {}}
        try:
            import shap
            explainer = shap.TreeExplainer(self.model.calibrated_classifiers_[0])
            X = pd.DataFrame([features]).reindex(columns=self.feature_columns, fill_value=0)
            sv = explainer.shap_values(X)
            if isinstance(sv, list):
                sv = sv[1]
            for i, col in enumerate(self.feature_columns):
                explanation["shap_values"][col] = float(sv[0][i])
        except Exception:
            pass
        return explanation
    
    def explain_global(self, X=None, max_samples=300):
        if self.model is None:
            return None, None
        try:
            import shap
            if X is None:
                raise ValueError("Need feature data for global SHAP")
            X_sample = X[self.feature_columns].fillna(0).sample(min(max_samples, len(X)))
            explainer = shap.TreeExplainer(self.model.calibrated_classifiers_[0])
            shap_values = explainer.shap_values(X_sample)
            return shap_values, X_sample
        except Exception as e:
            logger.warning(f"SHAP global failed: {e}")
            return None, None
    
    def plot_partial_dependence(self, feature: str, X=None, grid_resolution=50):
        try:
            import plotly.graph_objects as go
            if X is None:
                return None
            vals = X[feature].dropna()
            grid = np.linspace(vals.quantile(0.02), vals.quantile(0.98), grid_resolution)
            means = []
            for v in grid:
                X_copy = X[self.feature_columns].fillna(0).copy()
                X_copy[feature] = v
                probs = self.model.predict_proba(X_copy)[:, 1]
                means.append(np.mean(probs))
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=grid, y=means, mode="lines", name="PDP"))
            fig.update_layout(title=f"Partial Dependence: {feature}", xaxis_title=feature, yaxis_title="Predicted Probability")
            return fig
        except Exception as e:
            logger.warning(f"PDP failed: {e}")
            return None
    
    def plot_ice(self, feature: str, X=None, grid_resolution=40, max_lines=50):
        try:
            import plotly.graph_objects as go
            if X is None:
                return None
            vals = X[feature].dropna()
            grid = np.linspace(vals.quantile(0.02), vals.quantile(0.98), grid_resolution)
            X_base = X[self.feature_columns].fillna(0).sample(min(max_lines, len(X)))
            fig = go.Figure()
            for _, row in X_base.iterrows():
                row_df = pd.DataFrame([row.values] * grid_resolution, columns=self.feature_columns)
                row_df[feature] = grid
                probs = self.model.predict_proba(row_df)[:, 1]
                fig.add_trace(go.Scatter(x=grid, y=probs, mode="lines", line=dict(width=0.3, color="gray"), showlegend=False))
            avg_means = []
            for v in grid:
                X_copy = X[self.feature_columns].fillna(0).copy()
                X_copy[feature] = v
                avg_means.append(np.mean(self.model.predict_proba(X_copy)[:, 1]))
            fig.add_trace(go.Scatter(x=grid, y=avg_means, mode="lines", line=dict(width=3, color="red"), name="Average (PDP)"))
            fig.update_layout(title=f"ICE Plot: {feature}", xaxis_title=feature, yaxis_title="Predicted Probability")
            return fig
        except Exception as e:
            logger.warning(f"ICE failed: {e}")
            return None
    
    def save_model(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "features": self.feature_columns}, path)
        logger.info(f"[ML] Model saved to {path}")
    
    def load_model(self, path: str):
        data = joblib.load(path)
        if isinstance(data, dict):
            self.model = data.get("model")
            self.feature_columns = data.get("features", self.feature_columns)
        else:
            self.model = data
        logger.info(f"[ML] Model loaded from {path}")
