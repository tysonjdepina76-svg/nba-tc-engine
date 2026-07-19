"""Dashboard Component — Live Picks.

Reads the picks database and displays the most recent high-edge picks
with signal badges, edge percentages, and sort/filter controls."""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path


PICKS_DB = Path("/home/workspace/Projects/data/picks.db")


def load_picks(limit: int = 200) -> pd.DataFrame:
    conn = sqlite3.connect(str(PICKS_DB))
    df = pd.read_sql_query(f"""
        SELECT player, team, league, stat, tc_projection, market_line, edge,
               direction, matchup, signal, reason, date
        FROM picks
        ORDER BY ABS(edge) DESC, date DESC
        LIMIT {limit}
    """, conn)
    conn.close()

    if not df.empty:
        df["edge_pct"] = df["edge"].round(1).astype(str) + "%"
        df["signal_icon"] = df["signal"].map({"STRONG": "🔴", "MODERATE": "🟡", "WEAK": "⚪"})

    return df


def render():
    st.header("Live +EV Picks")

    df = load_picks()
    if df.empty:
        st.warning("No picks in database. Run: python3 daily_picks.py --sport all")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Picks", len(df))
    high_edge = df[df["edge"].abs() >= 5]
    c2.metric("Strong Signals (≥5%)", len(high_edge))
    if not df.empty:
        top = df.iloc[0]
        c3.metric("Top Edge", f"{top['player']} {top['edge']:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        league_filter = st.selectbox("League", ["ALL"] + sorted(df["league"].dropna().unique().tolist()), key="live_league")
    with col2:
        signal_filter = st.selectbox("Signal", ["ALL", "STRONG", "MODERATE", "WEAK"], key="live_signal")

    if league_filter != "ALL":
        df = df[df["league"] == league_filter]
    if signal_filter != "ALL":
        df = df[df["signal"] == signal_filter]

    display_cols = ["signal_icon", "player", "team", "stat", "tc_projection", "market_line", "edge_pct", "direction", "matchup"]
    display = df[[c for c in display_cols if c in df.columns]]
    st.dataframe(display, use_container_width=True, hide_index=True, height=500)
