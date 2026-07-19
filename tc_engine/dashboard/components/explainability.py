"""Dashboard Component — Explainability.

Loads SHAP feature importance, Partial Dependence Plots (PDP),
and Individual Conditional Expectation (ICE) plots from the plots/ directory
and renders them in the dashboard."""
import streamlit as st
from pathlib import Path
import json


PLOTS_DIR = Path(__file__).parent.parent.parent / "plots"


def get_available_plots() -> list:
    if not PLOTS_DIR.exists():
        return []
    return sorted([f.name for f in PLOTS_DIR.glob("*.html")])


def load_feature_importance() -> dict:
    importance_file = PLOTS_DIR / "feature_importance.json"
    if importance_file.exists():
        with open(importance_file) as f:
            return json.load(f)
    return {}


def render():
    st.header("Model Explainability")

    st.markdown("""
    This tab shows how the TC prediction engine makes decisions.
    - **SHAP values** quantify each feature's contribution to predictions
    - **PDP plots** show how predictions change as a feature varies
    - **ICE plots** reveal individual-level variation in feature effects
    """)

    importance = load_feature_importance()
    if importance:
        st.subheader("Feature Importance")
        features = importance.get("features", [])
        values = importance.get("values", [])

        if features and values:
            try:
                import plotly.express as px
                import pandas as pd
                df = pd.DataFrame({"Feature": features, "Importance": values})
                df = df.sort_values("Importance", ascending=True)
                fig = px.bar(df, x="Importance", y="Feature", orientation="h",
                            title="SHAP Feature Importance", color="Importance")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.dataframe({"Feature": features[:20], "Importance": values[:20]})

    plots = get_available_plots()
    if plots:
        st.subheader("Generated Explainability Plots")
        for plot_name in plots:
            plot_path = PLOTS_DIR / plot_name
            with open(plot_path) as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=500, scrolling=True)
    else:
        st.info("No explainability plots generated yet. Run: python engine/generate_explainability_plots.py")

    st.subheader("SHAP Summary")
    shap_path = PLOTS_DIR / "shap_summary.html"
    if shap_path.exists():
        with open(shap_path) as f:
            st.components.v1.html(f.read(), height=600, scrolling=True)
    else:
        st.info("SHAP summary available after model training.")
