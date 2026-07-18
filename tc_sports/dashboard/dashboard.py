#!/usr/bin/env python3
"""TC Sports Dashboard — reads ALL alerts, no limits, all sports."""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import json
from datetime import datetime

PROCESSED_DIR = Path("/home/workspace/data/processed")
ALERTS_JSON = PROCESSED_DIR / "alerts.json"

st.set_page_config(page_title="TC Sports Intelligence", layout="wide")

st.title("🎯 TC Sports Intelligence")
st.caption(f"All +EV alerts – {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if not ALERTS_JSON.exists():
    st.error("❌ No alerts found. Run pipeline first.")
    st.stop()

try:
    with open(ALERTS_JSON, 'r') as f:
        raw = json.load(f)
except Exception as e:
    st.error(f"Failed to load: {e}")
    st.stop()

alerts = raw.get("alerts", [])
if not alerts:
    st.info("No +EV alerts at this time.")
    st.stop()

df = pd.DataFrame(alerts)
df["is_ev"] = df["edge"] > 0

st.sidebar.header("Filters")
sport_col = "league" if "league" in df.columns else "sport"
sport_filter = st.sidebar.selectbox(
    "Sport",
    ["All"] + sorted(df[sport_col].unique().tolist())
)

if sport_filter != "All":
    df = df[df[sport_col] == sport_filter]

col1, col2, col3 = st.columns(3)
col1.metric("Total Alerts", len(df))
col2.metric("Avg Edge", f"{df['edge'].mean():.2%}")
col3.metric("Avg Confidence", f"{df['confidence'].mean():.0f}%")

st.subheader("📋 All Alerts")

for _, row in df.iterrows():
    bg = "#0a3a1a" if row['is_ev'] else "#3a0a0a"
    border = "#66dd88" if row['is_ev'] else "#dd6666"
    line_val = row.get('market_line', row.get('line', 'N/A'))
    true_p = row.get('true_probability', row.get('true_prob', 0))
    st.markdown(f"""
    <div style="background:{bg}; border-left:4px solid {border};
                padding:0.8rem 1.2rem; border-radius:8px; margin-bottom:0.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <strong>{row['player']}</strong> ({row.get(sport_col, '')}) – {row['stat']}
                <span style="margin-left:15px; font-size:0.8rem; color:#aaa;">
                    Line: {line_val}
                </span>
            </div>
            <div>
                <span style="background:#1a2a3a; padding:2px 10px; border-radius:12px;">
                    Edge: <strong>{row['edge']:.2%}</strong>
                </span>
                <span style="margin-left:10px; color:#aaa;">True: {true_p:.1%}</span>
                <span style="margin-left:10px; color:#aaa;">Conf: {row.get('confidence', 0):.0f}%</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if len(df) > 1:
    st.subheader("📊 Edge Distribution")
    fig = px.histogram(df, x='edge', nbins=20, title=f"{len(df)} alerts – Edge spread")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Data sourced from pipeline – no mock.")
