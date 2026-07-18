#!/usr/bin/env python3
"""
Enhanced Streamlit dashboard with health status.
Run: streamlit run dashboard_enhanced.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime
from pathlib import Path
from config import OUTPUT_FILE, HEALTH_FILE

st.set_page_config(page_title="Live Sports + Health", layout="wide")

@st.cache_data(ttl=30)
def load_health():
    path = Path(HEALTH_FILE)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {"status": "UNKNOWN", "timestamp": datetime.now().isoformat()}

@st.cache_data(ttl=60)
def load_data():
    path = Path(OUTPUT_FILE)
    if not path.exists():
        return {
            "timestamp": datetime.now().isoformat(),
            "games": {"mlb": [], "wnba": []},
            "player_props": [],
            "summary": {"total_games": 0, "total_props": 0}
        }
    with open(path, "r") as f:
        return json.load(f)

st.sidebar.title("System Health")
health = load_health()
status = health.get("status", "UNKNOWN")
color = {"OK": "OK", "DEGRADED": "DEGRADED", "CRITICAL": "CRITICAL", "UNKNOWN": "UNKNOWN"}.get(status, "UNKNOWN")
st.sidebar.markdown(f"### Status: **{status}**")

if "checks" in health:
    st.sidebar.markdown("**Checks:**")
    for name, chk in health.get("checks", {}).items():
        icon = "PASS" if chk.get("status") == "PASS" else "FAIL"
        msg = chk.get("message", "")[:40]
        st.sidebar.text(f"{icon} {name}: {msg}")

last_health = health.get("timestamp")
if last_health:
    age = (datetime.now() - datetime.fromisoformat(last_health)).total_seconds()
    st.sidebar.metric("Health age", f"{int(age)}s ago")

st.title("Live Sports Data Dashboard")

data = load_data()
data_ts = data.get("timestamp")
if data_ts:
    age = (datetime.now() - datetime.fromisoformat(data_ts)).total_seconds()
    if age < 300:
        st.info(f"Data age: {int(age)}s")
    else:
        st.warning(f"Data stale ({int(age)}s)")

if st.button("Refresh All"):
    st.cache_data.clear()
    st.rerun()

summary = data.get("summary", {})
c1, c2, c3, c4 = st.columns(4)
c1.metric("Live Games", summary.get("total_games", 0))
c2.metric("Props", summary.get("total_props", 0))
c3.metric("MLB", summary.get("mlb_games", 0))
c4.metric("WNBA", summary.get("wnba_games", 0))

st.divider()

games = data.get("games", {})
mlb_df = pd.DataFrame(games.get("mlb", []))
if not mlb_df.empty:
    st.markdown("### MLB")
    cols = ["matchup", "away_score", "home_score", "status", "period", "clock"]
    available = [c for c in cols if c in mlb_df.columns]
    st.dataframe(mlb_df[available], use_container_width=True, hide_index=True)

wnba_df = pd.DataFrame(games.get("wnba", []))
if not wnba_df.empty:
    st.markdown("### WNBA")
    cols = ["matchup", "away_score", "home_score", "status", "period", "clock"]
    available = [c for c in cols if c in wnba_df.columns]
    st.dataframe(wnba_df[available], use_container_width=True, hide_index=True)

st.divider()

props = data.get("player_props", [])
if props:
    df = pd.DataFrame(props)
    col1, col2, col3 = st.columns(3)
    with col1:
        leagues = ["All"] + sorted(df["league"].unique().tolist())
        league_filter = st.selectbox("League", leagues)
    with col2:
        stats = ["All"] + sorted(df["stat"].unique().tolist())
        stat_filter = st.selectbox("Stat", stats)
    with col3:
        min_edge = st.slider("Min Edge %", 0, 50, 0, 5)

    filtered = df.copy()
    if league_filter != "All":
        filtered = filtered[filtered["league"] == league_filter]
    if stat_filter != "All":
        filtered = filtered[filtered["stat"] == stat_filter]
    filtered = filtered[filtered["edge"] >= (min_edge / 100)]
    filtered = filtered.sort_values("edge", ascending=False)

    if not filtered.empty:
        display = filtered[["player", "team", "stat", "projection", "line", "edge", "confidence", "matchup"]].copy()
        display["edge"] = (display["edge"] * 100).round(1).astype(str) + "%"
        display["confidence"] = display["confidence"].astype(str) + "%"
        display.columns = ["Player", "Team", "Stat", "Projection", "Line", "Edge", "Confidence", "Matchup"]
        st.dataframe(display, use_container_width=True, hide_index=True)

        if len(filtered) > 1:
            fig = px.histogram(filtered, x="edge", color="league", nbins=20,
                               title="Edge Distribution")
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No props extracted yet.")

st.caption("Health checks every 60s - Pipeline auto-runs via cron.")
