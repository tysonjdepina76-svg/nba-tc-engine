import os
import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.inspection import PartialDependenceDisplay
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "models"))

def main():
    csv_path = DATA_DIR / "training_data.csv"
    model_path = MODEL_DIR / "xgboost_model.pkl"

    if not csv_path.exists():
        print("No training data.")
        return
    if not model_path.exists():
        print("No trained model. Run train_with_shap.py first.")
        return

    import joblib
    model = joblib.load(model_path)

    df = pd.read_csv(csv_path)
    graded = df.dropna(subset=["won"]).copy()
    graded["direction_num"] = (graded["direction"] == "OVER").astype(int)
    graded["signal_num"] = graded["signal"].map({"STRONG": 3, "MODERATE": 2, "WEAK": 1}).fillna(1)

    feature_cols = ["edge", "line", "projection", "direction_num", "signal_num"]
    X = graded[feature_cols].values

    fig, ax = plt.subplots(figsize=(10, 6))
    PartialDependenceDisplay.from_estimator(
        model, X, features=[0, 1, 2],
        feature_names=feature_cols[:3],
        ax=ax,
    )
    plt.tight_layout()
    plt.savefig(MODEL_DIR / "partial_dependence.png", dpi=120, bbox_inches="tight")
    plt.close()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for i, feat in enumerate(["edge", "line", "projection"]):
        idx = feature_cols.index(feat)
        x_vals = X[:, idx]
        y_prob = model.predict_proba(X)[:, 1]
        axes[i].scatter(x_vals, y_prob, alpha=0.3, s=8)
        axes[i].set_xlabel(feat)
        axes[i].set_ylabel("P(win)")
        axes[i].set_title(f"{feat} vs Win Probability")
    plt.tight_layout()
    plt.savefig(MODEL_DIR / "ice_plots.png", dpi=120, bbox_inches="tight")
    plt.close()

    print(f"Explainability plots saved to {MODEL_DIR}")

if __name__ == "__main__":
    main()
