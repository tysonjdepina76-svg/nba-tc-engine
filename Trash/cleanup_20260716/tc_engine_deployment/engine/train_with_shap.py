import os
import sys
import json
import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "models"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def main():
    csv_path = DATA_DIR / "training_data.csv"
    if not csv_path.exists():
        print("No training data. Run export_training_data.py first.")
        return

    df = pd.read_csv(csv_path)
    graded = df.dropna(subset=["won"]).copy()
    if len(graded) < 50:
        print(f"Only {len(graded)} graded picks — need 50+. Skipping ML training.")
        return

    graded["won_int"] = graded["won"].astype(int)
    graded["direction_num"] = (graded["direction"] == "OVER").astype(int)
    graded["signal_num"] = graded["signal"].map({"STRONG": 3, "MODERATE": 2, "WEAK": 1}).fillna(1)

    feature_cols = ["edge", "line", "projection", "direction_num", "signal_num"]
    X = graded[feature_cols].values
    y = graded["won_int"].values

    tscv = TimeSeriesSplit(n_splits=5)
    accuracies = []

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        acc = accuracy_score(y_val, y_pred)
        accuracies.append(acc)
        print(f"  Fold {fold+1}: accuracy={acc:.3f}")

    final_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    final_model.fit(X, y)

    metrics = {
        "mean_accuracy": float(np.mean(accuracies)),
        "std_accuracy": float(np.std(accuracies)),
        "n_folds": len(accuracies),
        "n_samples": len(graded),
        "n_features": len(feature_cols),
        "features": feature_cols,
        "accuracy_per_fold": [float(a) for a in accuracies],
    }

    with open(MODEL_DIR / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    explainer = shap.TreeExplainer(final_model)
    shap_values = explainer.shap_values(X)

    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X, feature_names=feature_cols, show=False)
    plt.tight_layout()
    plt.savefig(MODEL_DIR / "shap_summary.png", dpi=120, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(8, 5))
    importance = final_model.feature_importances_
    idx = np.argsort(importance)
    plt.barh([feature_cols[i] for i in idx], importance[idx])
    plt.xlabel("Importance")
    plt.title("XGBoost Feature Importances")
    plt.tight_layout()
    plt.savefig(MODEL_DIR / "feature_importance.png", dpi=120)
    plt.close()

    import joblib
    joblib.dump(final_model, MODEL_DIR / "xgboost_model.pkl")

    print(f"\nTrained XGBoost: mean_acc={metrics['mean_accuracy']:.1%} ± {metrics['std_accuracy']:.1%}")
    print(f"Model saved to {MODEL_DIR}")

if __name__ == "__main__":
    main()
