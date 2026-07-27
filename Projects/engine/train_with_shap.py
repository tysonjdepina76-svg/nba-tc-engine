#!/usr/bin/env python3
"""
train_with_shap.py
Trains MLProbabilityPredictor on historical data, runs SHAP analysis,
logs metrics, and saves model to models/probability_model.joblib.

Usage:
    python engine/train_with_shap.py --data data/historical.csv --target result_binary
"""

import argparse
import os
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from engine.ml_predictor import MLProbabilityPredictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("train_with_shap")

def main():
    parser = argparse.ArgumentParser(description="Train tc_engine ML model with SHAP analysis")
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--target", type=str, default="result_binary")
    parser.add_argument("--model", type=str, default="models/probability_model.joblib")
    parser.add_argument("--top_features", type=int, default=15)
    args = parser.parse_args()

    logger.info("=== tc_engine Training + SHAP Analysis ===")

    data_path = Path(args.data)
    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        sys.exit(1)

    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df)} rows")

    if args.target not in df.columns:
        logger.error(f"Target column '{args.target}' not found in data. Columns: {list(df.columns)}")
        sys.exit(1)

    logger.info("Training MLProbabilityPredictor...")
    predictor = MLProbabilityPredictor()

    try:
        predictor.train(df, target_col=args.target)
    except Exception as e:
        logger.error(f"Training failed: {e}")
        sys.exit(1)

    logger.info("=== Top Feature Importances ===")
    try:
        importance_df = predictor.get_feature_importance(top_n=args.top_features)
        print(importance_df.to_string(index=False))
    except Exception as e:
        logger.warning(f"Feature importance failed: {e}")

    try:
        shap_values, X_sample = predictor.explain_global(max_samples=min(300, len(df)))
        if hasattr(shap_values, "shape"):
            mean_shap = abs(shap_values).mean(axis=0)
            shap_imp = pd.DataFrame({
                "feature": predictor.feature_columns,
                "mean_abs_shap": mean_shap
            }).sort_values("mean_abs_shap", ascending=False)
            print("\nTop features by mean |SHAP|:")
            print(shap_imp.head(10).to_string(index=False))
    except Exception as e:
        logger.warning(f"SHAP analysis failed: {e}")

    model_path = Path(args.model)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    predictor.save_model(str(model_path))
    logger.info(f"Model saved to: {model_path}")
    logger.info("=== Training Completed ===")

if __name__ == "__main__":
    main()
