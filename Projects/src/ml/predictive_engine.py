"""
Predictive Engine - XGBoost + RandomForest + GradientBoosting ensemble
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictiveEngine:
    """ML-based prediction engine for betting value detection."""

    def __init__(self, model_path: str = "models/"):
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.is_trained = False

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and engineer features for ML models."""
        features = df.copy()

        numeric_cols = ['line', 'projection', 'edge', 'stake', 'odds', 'model_confidence']
        for col in numeric_cols:
            if col in features.columns:
                features[col] = pd.to_numeric(features[col], errors='coerce').fillna(0)

        if 'game_date' in features.columns:
            try:
                dates = pd.to_datetime(features['game_date'])
                features['hour'] = dates.dt.hour.fillna(0)
                features['day_of_week'] = dates.dt.dayofweek.fillna(0)
                features['month'] = dates.dt.month.fillna(0)
            except Exception:
                features['hour'] = 0
                features['day_of_week'] = 0
                features['month'] = 0

        features['edge_magnitude'] = abs(features['edge']) if 'edge' in features.columns else 0
        if 'line' in features.columns and 'projection' in features.columns:
            features['line_projection_ratio'] = features['line'] / (features['projection'] + 0.001)
        else:
            features['line_projection_ratio'] = 1

        if 'player' in features.columns and len(features) > 1:
            features['player_bet_count'] = features.groupby('player')['player'].transform('count')
            features['player_avg_edge'] = features.groupby('player')['edge'].transform('mean') if 'edge' in features.columns else 0
        else:
            features['player_bet_count'] = 1
            features['player_avg_edge'] = 0

        if 'stat' in features.columns and len(features) > 1:
            stat_means = features.groupby('stat')['edge'].transform('mean') if 'edge' in features.columns else 0
            stat_stds = features.groupby('stat')['edge'].transform('std') if 'edge' in features.columns else 1
            features['stat_z_score'] = (features['edge'] - stat_means) / (stat_stds + 0.001) if 'edge' in features.columns else 0
        else:
            features['stat_z_score'] = 0

        if 'game' in features.columns and len(features) > 1:
            features['game_bet_count'] = features.groupby('game')['game'].transform('count')
        else:
            features['game_bet_count'] = 1

        for lag in [1, 3, 5]:
            if 'edge' in features.columns and len(features) > lag:
                features[f'edge_lag_{lag}'] = features['edge'].shift(lag).fillna(0)
                features[f'line_lag_{lag}'] = features['line'].shift(lag).fillna(0) if 'line' in features.columns else 0
            else:
                features[f'edge_lag_{lag}'] = 0
                features[f'line_lag_{lag}'] = 0

        for window in [5, 10]:
            if 'edge' in features.columns and len(features) > window:
                features[f'edge_rolling_mean_{window}'] = features['edge'].rolling(window).mean().fillna(0)
                features[f'edge_rolling_std_{window}'] = features['edge'].rolling(window).std().fillna(0)
            else:
                features[f'edge_rolling_mean_{window}'] = 0
                features[f'edge_rolling_std_{window}'] = 0

        features = features.fillna(0)
        return features

    def train_models(self, training_data: pd.DataFrame):
        """Train multiple ML models on historical data."""
        if training_data.empty or len(training_data) < 50:
            logger.warning(f"Insufficient training data: {len(training_data)} samples (need 50+)")
            self.is_trained = False
            return

        logger.info(f"Training ML models on {len(training_data)} samples...")
        features_df = self.prepare_features(training_data)

        exclude_cols = ['game', 'player', 'stat', 'actual_result', 'game_date', 'actual_outcome']
        feature_cols = [col for col in features_df.columns
                       if col not in exclude_cols and pd.api.types.is_numeric_dtype(features_df[col])]
        if not feature_cols:
            self.is_trained = False
            return

        X = features_df[feature_cols].values
        y = features_df['profit'].values if 'profit' in features_df.columns else features_df['edge'].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        models = {
            'random_forest': RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_split=5, random_state=42, n_jobs=-1),
            'gradient_boost': GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42),
            'xgboost': xgb.XGBRegressor(n_estimators=100, learning_rate=0.03, max_depth=6, subsample=0.8, colsample_bytree=0.8, random_state=42)
        }

        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                predictions = model.predict(X_val)
                mae = mean_absolute_error(y_val, predictions)
                mse = mean_squared_error(y_val, predictions)
                r2 = r2_score(y_val, predictions)
                logger.info(f"{name} - MAE: {mae:.3f}, MSE: {mse:.3f}, R2: {r2:.3f}")
                self.models[name] = model
                self.scalers[name] = scaler
                if hasattr(model, 'feature_importances_'):
                    importance = model.feature_importances_
                    self.feature_importance[name] = dict(zip(feature_cols, importance))
                joblib.dump(model, self.model_path / f"{name}_model.pkl")
            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")

        self.is_trained = bool(self.models)

    def predict_value(self, bet_data: Dict) -> Dict:
        """Predict the true value of a potential bet."""
        if not self.is_trained or not self.models:
            edge = float(bet_data.get('edge', 0))
            return {
                'ensemble_prediction': edge,
                'model_predictions': {'fallback': edge},
                'confidence': 0.5,
                'is_value_bet': edge < -2.0,
                'bet_size_multiplier': 1.0
            }

        bet_df = pd.DataFrame([bet_data])
        features_df = self.prepare_features(bet_df)
        feature_cols = [col for col in features_df.columns
                       if col not in ['game', 'player', 'stat', 'actual_result', 'game_date', 'actual_outcome']
                       and pd.api.types.is_numeric_dtype(features_df[col])]
        X = features_df[feature_cols].values

        predictions = {}
        for name, model in self.models.items():
            try:
                scaler = self.scalers.get(name)
                if scaler:
                    X_scaled = scaler.transform(X)
                    predictions[name] = float(model.predict(X_scaled)[0])
                else:
                    predictions[name] = 0
            except Exception as e:
                logger.error(f"Prediction failed for {name}: {e}")
                predictions[name] = 0

        if not predictions:
            edge = float(bet_data.get('edge', 0))
            return {'ensemble_prediction': edge, 'model_predictions': {}, 'confidence': 0.5, 'is_value_bet': edge < -2.0, 'bet_size_multiplier': 1.0}

        ensemble = sum(predictions.values()) / len(predictions)
        confidence = min(abs(ensemble) / 10.0, 0.95)
        return {
            'ensemble_prediction': ensemble,
            'model_predictions': predictions,
            'confidence': confidence,
            'is_value_bet': ensemble < -2.0,
            'bet_size_multiplier': min(2.0, 1.0 + abs(ensemble) / 10.0)
        }
