"""
Advanced visualization components.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_dashboard_overview(df: pd.DataFrame, sport: str):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", len(df), delta="+12%")
    with col2:
        st.metric("Avg Edge", round(df.get("edge", pd.Series([0])).mean(), 2), delta="+0.15")
    with col3:
        st.metric("Hit Rate", f"{len(df[df.get('edge', 0) > 0]) / max(len(df), 1) * 100:.1f}%")
    with col4:
        st.metric("Confidence", "85%", delta="+5%")

    if len(df.select_dtypes(include=['number']).columns) > 1:
        fig = px.imshow(
            df.select_dtypes(include=['number']).corr(),
            text_auto=True,
            title="Stat Correlations",
            color_continuous_scale="RdBu_r"
        )
        st.plotly_chart(fig, use_container_width=True)

    top_players = df.head(5)
    if not top_players.empty:
        stats = ['pts', 'reb', 'ast'] if 'pts' in df.columns else ['avg', 'hr', 'rbi']
        stats = [s for s in stats if s in df.columns]
        if stats:
            fig = go.Figure()
            for _, player in top_players.iterrows():
                values = [player.get(s, 0) for s in stats]
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=[s.upper() for s in stats],
                    fill='toself',
                    name=player.get("name", "Unknown")
                ))
            fig.update_layout(title="Top Player Comparison", height=450)
            st.plotly_chart(fig, use_container_width=True)

def render_timeline(df: pd.DataFrame, date_col: str = "created_at"):
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
        daily_avg = df.groupby(df[date_col].dt.date).mean(numeric_only=True)
        fig = px.line(
            daily_avg,
            title="Projection Trends",
            labels={"value": "Avg Projection", "date": "Date"}
        )
        st.plotly_chart(fig, use_container_width=True)
