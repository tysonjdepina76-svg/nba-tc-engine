"""Generate Explainability Plots — SHAP, PDP, and ICE.

Runs after model training to produce interpretability plots for
the top features. Outputs HTML files that the dashboard can embed.
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PLOTS_DIR = Path(__file__).parent.parent / "plots"
MODELS_DIR = Path(__file__).parent.parent / "models"


def generate_all(top_n: int = 8) -> dict:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {"timestamp": datetime.now().isoformat(), "plots": {}}

    output["plots"]["shap_summary"] = _generate_shap_summary(top_n)
    output["plots"]["pdp"] = _generate_pdp(top_n)
    output["plots"]["ice"] = _generate_ice(top_n)
    output["plots"]["feature_importance"] = _generate_feature_importance(top_n)

    manifest_path = PLOTS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(output, indent=2))

    return output


def _get_training_data() -> Optional[pd.DataFrame]:
    pipeline_db = Path(__file__).parent.parent.parent / "Projects" / "data" / "tc_pipeline.db"
    if not pipeline_db.exists():
        return None

    import sqlite3
    conn = sqlite3.connect(str(pipeline_db))
    df = pd.read_sql_query("""
        SELECT tc_projection, market_line, edge, projection as actual, sport, stat, direction, hit
        FROM graded_picks LIMIT 5000
    """, conn)
    conn.close()

    if df.empty:
        return None

    df["edge_abs"] = df["edge"].abs()
    df["projection_line_ratio"] = np.where(df["market_line"] != 0, df["tc_projection"] / df["market_line"].abs(), 0)
    df["projection_above_mean"] = df["tc_projection"] - df["tc_projection"].mean()
    df["line_below_mean"] = df["market_line"].mean() - df["market_line"]

    return df


def _generate_feature_importance(top_n: int) -> str:
    df = _get_training_data()
    filepath = PLOTS_DIR / "feature_importance.png"

    if df is None or df.empty:
        return str(filepath)

    features = ["tc_projection", "market_line", "edge_raw", "edge_abs",
                "projection_line_ratio", "projection_above_mean", "line_below_mean"]

    from sklearn.ensemble import RandomForestClassifier
    X = df[features].values
    X = np.nan_to_num(X, nan=0.0)
    y = df["hit"].values.astype(int)

    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    importances = rf.feature_importances_

    fig, ax = plt.subplots(figsize=(10, 6))
    sorted_idx = np.argsort(importances)[-top_n:]
    ax.barh([features[i] for i in sorted_idx], importances[sorted_idx])
    ax.set_xlabel("Importance")
    ax.set_title("Feature Importance (Random Forest)")
    plt.tight_layout()
    fig.savefig(filepath, dpi=100)
    plt.close(fig)

    return str(filepath)


def _generate_shap_summary(top_n: int) -> str:
    df = _get_training_data()
    filepath = PLOTS_DIR / "shap_summary.png"

    if df is None or df.empty:
        return str(filepath)

    features = ["tc_projection", "market_line", "edge_raw", "edge_abs",
                "projection_line_ratio", "projection_above_mean", "line_below_mean"]
    X = df[features].values
    X = np.nan_to_num(X, nan=0.0)
    y = df["hit"].values.astype(int)

    from sklearn.ensemble import RandomForestClassifier
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
    rf.fit(X[:1000], y[:1000])

    import shap
    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X[:200])

    if isinstance(shap_values, list):
        shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]

    fig, ax = plt.subplots(figsize=(10, 6))
    shap.summary_plot(shap_values, X[:200], feature_names=features, show=False, max_display=top_n)
    plt.tight_layout()
    fig.savefig(filepath, dpi=100, bbox_inches="tight")
    plt.close(fig)

    return str(filepath)


def _generate_pdp(top_n: int) -> str:
    df = _get_training_data()
    filepath = PLOTS_DIR / "pdp_plot.png"

    if df is None or df.empty:
        return str(filepath)

    features = ["tc_projection", "market_line", "edge_abs"]
    X = df[features].values
    X = np.nan_to_num(X, nan=0.0)
    y = df["hit"].values.astype(int)

    from sklearn.ensemble import RandomForestClassifier
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
    rf.fit(X[:1000], y[:1000])

    from sklearn.inspection import PartialDependenceDisplay
    fig, ax = plt.subplots(figsize=(12, 4 * len(features)))
    PartialDependenceDisplay.from_estimator(rf, X[:200], features=list(range(min(top_n, len(features)))),
                                            feature_names=features, ax=ax)
    plt.tight_layout()
    fig.savefig(filepath, dpi=100)
    plt.close(fig)

    return str(filepath)


def _generate_ice(top_n: int) -> str:
    df = _get_training_data()
    filepath = PLOTS_DIR / "ice_plot.png"

    if df is None or df.empty:
        return str(filepath)

    features = ["tc_projection", "market_line", "edge_abs"]
    X = df[features].values
    X = np.nan_to_num(X, nan=0.0)
    y = df["hit"].values.astype(int)

    from sklearn.ensemble import RandomForestClassifier
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
    rf.fit(X[:1000], y[:1000])

    from sklearn.inspection import PartialDependenceDisplay
    fig, ax = plt.subplots(figsize=(12, 4 * len(features)))
    PartialDependenceDisplay.from_estimator(rf, X[:100], features=list(range(min(top_n, len(features)))),
                                            feature_names=features, kind="individual", ax=ax)
    plt.tight_layout()
    fig.savefig(filepath, dpi=100)
    plt.close(fig)

    return str(filepath)


if __name__ == "__main__":
    results = generate_all()
    print(json.dumps(results, indent=2))
