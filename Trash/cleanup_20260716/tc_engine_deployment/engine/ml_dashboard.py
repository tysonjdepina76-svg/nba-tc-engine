import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="TC ML Dashboard", layout="wide")

st.title("TC Engine — ML Dashboard")
st.caption("Model performance, backtest comparison, and feature explainability")

MODEL_DIR = os.environ.get("MODEL_DIR", "/app/models")
DAILY_LOG = os.environ.get("DAILY_LOG", "/app/Daily_Log")

tab1, tab2, tab3 = st.tabs(["Backtest Comparison", "Feature Analysis", "Live Picks"])

with tab1:
    st.header("Heuristic vs ML-Gated Performance")

    metrics_path = os.path.join(MODEL_DIR, "training_metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            metrics = json.load(f)

        col1, col2, col3 = st.columns(3)
        col1.metric("Training Samples", metrics.get("n_samples", 0))
        col2.metric("CV Hit Rate", f"{metrics.get('cv_hit_rate', 0):.1%}")
        col3.metric("Heuristic Hit Rate", f"{metrics.get('heuristic_hit_rate', 0):.1%}")

        if metrics.get("cv_results"):
            st.subheader("Cross-Validation Results")
            cv_df = pd.DataFrame(metrics["cv_results"])
            st.dataframe(cv_df)

        if metrics.get("feature_importances"):
            st.subheader("Feature Importances")
            imp_df = pd.DataFrame(
                list(metrics["feature_importances"].items()),
                columns=["Feature", "Importance"],
            ).sort_values("Importance", ascending=False)
            st.bar_chart(imp_df.set_index("Feature"))
    else:
        st.info("No training metrics yet. Run train_with_shap.py")

with tab2:
    st.header("SHAP & Explainability")

    shap_path = os.path.join(MODEL_DIR, "shap_summary.png")
    pd_path = os.path.join(MODEL_DIR, "partial_dependence_edge.png")
    ice_path = os.path.join(MODEL_DIR, "ice_map.png")

    if os.path.exists(shap_path):
        st.image(shap_path, caption="SHAP Summary Plot")
    else:
        st.info("SHAP plot not generated yet")

    if os.path.exists(pd_path):
        st.image(pd_path, caption="Partial Dependence Plot")
    else:
        st.info("Partial dependence plot not generated yet")

    if os.path.exists(ice_path):
        st.image(ice_path, caption="ICE Map")
    else:
        st.info("ICE map not generated yet")

with tab3:
    st.header("Today's Picks")

    today = datetime.now().strftime("%Y-%m-%d")
    picks_path = os.path.join(DAILY_LOG, today, "picks.csv")

    if os.path.exists(picks_path):
        df = pd.read_csv(picks_path)
        st.metric("Total Picks", len(df))

        sport_filter = st.multiselect("Sport", df["sport"].dropna().unique())
        if sport_filter:
            df = df[df["sport"].isin(sport_filter)]

        st.dataframe(df, use_container_width=True)
    else:
        st.info("No picks generated today yet")
