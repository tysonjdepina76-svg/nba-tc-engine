import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_score, recall_score
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "models"))

def heuristic_predict(row):
    if row["signal"] == "STRONG" and abs(row["edge"]) > 0.10:
        return 1
    if row["signal"] == "MODERATE" and abs(row["edge"]) > 0.05:
        return 1
    return 1 if row["edge"] > 0 else 0

def main():
    csv_path = DATA_DIR / "training_data.csv"
    model_path = MODEL_DIR / "xgboost_model.pkl"

    if not csv_path.exists():
        print("No training data.")
        return

    df = pd.read_csv(csv_path)
    graded = df.dropna(subset=["won"]).copy()
    y_true = graded["won"].astype(int).values

    y_heuristic = np.array([heuristic_predict(r) for _, r in graded.iterrows()])
    h_acc = accuracy_score(y_true, y_heuristic)
    h_prec = precision_score(y_true, y_heuristic, zero_division=0)
    h_rec = recall_score(y_true, y_heuristic, zero_division=0)

    results = {
        "n_graded": len(graded),
        "heuristic": {"accuracy": float(h_acc), "precision": float(h_prec), "recall": float(h_rec)},
        "ml": None,
    }

    if model_path.exists():
        import joblib
        model = joblib.load(model_path)
        graded["direction_num"] = (graded["direction"] == "OVER").astype(int)
        graded["signal_num"] = graded["signal"].map({"STRONG": 3, "MODERATE": 2, "WEAK": 1}).fillna(1)
        X = graded[["edge", "line", "projection", "direction_num", "signal_num"]].values
        y_ml = model.predict(X)
        ml_acc = accuracy_score(y_true, y_ml)
        ml_prec = precision_score(y_true, y_ml, zero_division=0)
        ml_rec = recall_score(y_true, y_ml, zero_division=0)
        results["ml"] = {
            "accuracy": float(ml_acc),
            "precision": float(ml_prec),
            "recall": float(ml_rec),
        }

    print(f"\n{'Metric':<15} {'Heuristic':>10} {'ML (XGBoost)':>15}")
    print("-" * 42)
    for m in ["accuracy", "precision", "recall"]:
        h = results["heuristic"][m]
        ml_val = results["ml"][m] if results["ml"] else "N/A"
        h_str = f"{h:.1%}"
        ml_str = f"{ml_val:.1%}" if isinstance(ml_val, float) else str(ml_val)
        print(f"{m:<15} {h_str:>10} {ml_str:>15}")

    with open(MODEL_DIR / "backtest_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {MODEL_DIR / 'backtest_results.json'}")

if __name__ == "__main__":
    main()
