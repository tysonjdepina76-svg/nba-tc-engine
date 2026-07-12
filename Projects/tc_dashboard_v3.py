#!/usr/bin/env python3
"""TC Dashboard v3 — 10 Tabs: Live, Accuracy, P&L, Odds Board, Hybrid TC, Project Game, MLB, WNBA, NFL, Archive"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title="SPORTS TC — TRIPLE CONSERVATIVE ENGINE",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 SPORTS TC — TRIPLE CONSERVATIVE ENGINE")
st.caption(f"Live | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============= SIDEBAR =============
st.sidebar.header("📅 Controls")
date = st.sidebar.date_input("Date", datetime.now())
date_str = date.strftime("%Y-%m-%d")
sport_filter = st.sidebar.selectbox(
    "Sport",
    ["All", "MLB", "WNBA", "NBA", "NFL", "WORLD CUP", "NHL"]
)
min_edge = st.sidebar.slider("Min Edge %", 0, 50, 5) / 100

st.sidebar.header("📊 System Status")
st.sidebar.success("🟢 TC Engine: Active")
st.sidebar.caption(f"Date: {date_str}")

if st.sidebar.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# ============= DATA LOADERS =============
@st.cache_data
def load_picks(date_str, sport_filter):
    picks_file = Path(f"/home/workspace/Daily_Log/{date_str}/picks.csv")
    if not picks_file.exists():
        return pd.DataFrame()
    df = pd.read_csv(picks_file)
    if sport_filter != "All" and 'league' in df.columns:
        df = df[df['league'] == sport_filter]
    return df

@st.cache_data
def load_graded(date_str, sport_filter):
    graded_file = Path(f"/home/workspace/Daily_Log/{date_str}/graded_picks.csv")
    if not graded_file.exists():
        return pd.DataFrame()
    df = pd.read_csv(graded_file)
    if sport_filter != "All" and 'sport' in df.columns:
        df = df[df['sport'] == sport_filter]
    return df

@st.cache_data
def load_odds(date_str, sport):
    odds_file = Path(f"/home/workspace/Daily_Log/{date_str}/odds/{sport}_odds.csv")
    if not odds_file.exists():
        return pd.DataFrame()
    return pd.read_csv(odds_file)

@st.cache_data
def load_hybrid_picks(date_str, sport):
    picks_file = Path(f"/home/workspace/Daily_Log/{date_str}/{sport}_hybrid_picks.json")
    if not picks_file.exists():
        return pd.DataFrame()
    with open(picks_file) as f:
        data = json.load(f)
    return pd.DataFrame(data)

@st.cache_data
def load_projections(date_str, sport):
    proj_file = Path(f"/home/workspace/Daily_Log/{date_str}/{sport}_projections.json")
    if not proj_file.exists():
        return pd.DataFrame()
    with open(proj_file) as f:
        data = json.load(f)
    return pd.DataFrame(data.get("players", []))

@st.cache_data
def load_hit_rates():
    hr_file = Path("/home/workspace/Projects/hit_rate_report.csv")
    if not hr_file.exists():
        return pd.DataFrame()
    return pd.read_csv(hr_file)

@st.cache_data
def load_backtest():
    bt_file = Path("/home/workspace/Projects/backtest_results.csv")
    if not bt_file.exists():
        return pd.DataFrame()
    return pd.read_csv(bt_file)

# ============= SIDEBAR METRICS =============
df_picks = load_picks(date_str, "All")
st.sidebar.metric("📋 Total Picks", len(df_picks))

df_graded = load_graded(date_str, "All")
if not df_graded.empty:
    hits = len(df_graded[df_graded['correct'] == True])
    st.sidebar.metric("✅ Graded", f"{hits}/{len(df_graded)}", f"{hits/len(df_graded)*100:.1f}%")

# ============= TABS =============
tabs = st.tabs([
    "📊 Live Picks",
    "📈 Accuracy",
    "💰 P&L",
    "🔗 Odds Board",
    "🎯 Hybrid TC",
    "🏆 Project Game",
    "⚾ MLB",
    "🏀 WNBA",
    "🏈 NFL",
    "📁 Archive"
])

# ============= TAB 1: LIVE PICKS =============
with tabs[0]:
    st.header("📊 Live Picks")
    df = load_picks(date_str, sport_filter)
    if df.empty:
        st.warning(f"No picks for {date_str}")
    else:
        if 'edge' in df.columns:
            df = df[df['edge'] >= min_edge]
        st.metric("Total Picks", len(df))
        if 'signal' in df.columns:
            col1, col2, col3 = st.columns(3)
            col1.metric("OVER", len(df[df['signal'] == 'OVER']))
            col2.metric("UNDER", len(df[df['signal'] == 'UNDER']))
            col3.metric("FLAT", len(df[df['signal'] == 'FLAT']))
        hr_df = load_hit_rates()
        if not hr_df.empty and 'stat' in hr_df.columns:
            best_stats = hr_df[hr_df['accuracy'] >= 80]['stat'].tolist()
            if best_stats and 'stat' in df.columns:
                best_picks = df[df['stat'].isin(best_stats)]
                st.subheader("🎯 Best Picks (80%+ Accuracy)")
                st.dataframe(best_picks.head(20), use_container_width=True)
        st.dataframe(df, use_container_width=True)

# ============= TAB 2: ACCURACY =============
with tabs[1]:
    st.header("📈 Accuracy")
    hr_df = load_hit_rates()
    if hr_df.empty:
        st.warning("Run hit_rate_report.py first")
    else:
        st.dataframe(hr_df, use_container_width=True)
        if 'accuracy' in hr_df.columns:
            best = hr_df.loc[hr_df['accuracy'].idxmax()]
            worst = hr_df.loc[hr_df['accuracy'].idxmin()]
            col1, col2 = st.columns(2)
            col1.metric("🔥 Best Stat", best.get('stat', 'N/A'), f"{best.get('accuracy', 0):.1f}%")
            col2.metric("❄️ Worst Stat", worst.get('stat', 'N/A'), f"{worst.get('accuracy', 0):.1f}%")
    graded_df = load_graded(date_str, sport_filter)
    if not graded_df.empty:
        total = len(graded_df)
        hits = len(graded_df[graded_df['correct'] == True])
        st.metric(f"Graded Picks ({date_str})", f"{hits}/{total}", f"{hits/total*100:.1f}%")

# ============= TAB 3: P&L =============
with tabs[2]:
    st.header("💰 Profit & Loss")
    graded_df = load_graded(date_str, sport_filter)
    if graded_df.empty:
        st.info("No graded picks yet")
    else:
        graded_df['pnl'] = graded_df['correct'].apply(lambda x: 1 if x else -1)
        total_pnl = graded_df['pnl'].sum()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total P&L", f"+{total_pnl}u" if total_pnl >= 0 else f"{total_pnl}u")
        col2.metric("Wins", len(graded_df[graded_df['correct'] == True]))
        col3.metric("Losses", len(graded_df[graded_df['correct'] == False]))
        col4.metric("Win Rate", f"{len(graded_df[graded_df['correct'] == True])/len(graded_df)*100:.1f}%")
        if 'sport' in graded_df.columns:
            pnl_by_sport = graded_df.groupby('sport')['pnl'].sum().reset_index()
            fig = px.bar(pnl_by_sport, x='sport', y='pnl', title="P&L by Sport", color='sport')
            st.plotly_chart(fig, use_container_width=True)

# ============= TAB 4: ODDS BOARD =============
with tabs[3]:
    st.header("🔗 Odds Board — Multi-Book")
    sport_odds = st.selectbox("Select Sport for Odds", ["WNBA", "MLB", "NFL", "NBA", "NHL"])
    df_odds = load_odds(date_str, sport_odds.lower())
    if df_odds.empty:
        st.warning(f"No odds for {sport_odds} on {date_str}")
    else:
        st.metric("Total Odds Rows", len(df_odds))
        if 'book_title' in df_odds.columns and 'market' in df_odds.columns:
            pivot_df = df_odds.pivot_table(
                index=['game_id', 'market'],
                columns='book_title',
                values='price',
                aggfunc='first'
            )
            st.dataframe(pivot_df, use_container_width=True)
        else:
            st.dataframe(df_odds, use_container_width=True)

# ============= TAB 5: HYBRID TC =============
with tabs[4]:
    st.header("🎯 Hybrid TC Picks — v1 vs v2 vs Hybrid vs Ensemble")
    sport_hybrid = st.selectbox("Select Sport", ["WNBA", "MLB"], key="hybrid")
    df_hybrid = load_hybrid_picks(date_str, sport_hybrid)
    if df_hybrid.empty:
        st.warning(f"No hybrid picks for {sport_hybrid} on {date_str}")
    else:
        st.dataframe(df_hybrid, use_container_width=True)
        if 'edge' in df_hybrid.columns:
            fig = px.histogram(df_hybrid, x='edge', color='direction', title="Edge Distribution by Direction")
            st.plotly_chart(fig, use_container_width=True)

# ============= TAB 6: PROJECT GAME =============
with tabs[5]:
    st.header("🏆 Project Game")
    sport_pg = st.selectbox("Select Sport", ["MLB", "WNBA", "NBA", "NFL", "WORLD CUP", "NHL"], key="pg")
    df_pg = load_projections(date_str, sport_pg)
    if df_pg.empty:
        st.warning(f"No projections for {sport_pg} on {date_str}")
    else:
        st.metric("Total Players", len(df_pg))
        st.dataframe(df_pg, use_container_width=True)

# ============= TAB 7: MLB =============
with tabs[6]:
    st.header("⚾ MLB — Player Props")
    df_mlb = load_projections(date_str, "MLB")
    if df_mlb.empty:
        st.warning(f"No MLB projections for {date_str}")
    else:
        st.metric("Total MLB Players", len(df_mlb))
        st.dataframe(df_mlb, use_container_width=True)

# ============= TAB 8: WNBA =============
with tabs[7]:
    st.header("🏀 WNBA — Player Props")
    df_wnba = load_projections(date_str, "WNBA")
    if df_wnba.empty:
        st.warning(f"No WNBA projections for {date_str}")
    else:
        st.metric("Total WNBA Players", len(df_wnba))
        st.dataframe(df_wnba, use_container_width=True)

# ============= TAB 9: NFL =============
with tabs[8]:
    st.header("🏈 NFL — Player Props")
    df_nfl = load_projections(date_str, "NFL")
    if df_nfl.empty:
        st.warning(f"No NFL projections for {date_str}")
    else:
        st.metric("Total NFL Players", len(df_nfl))
        st.dataframe(df_nfl, use_container_width=True)

# ============= TAB 10: ARCHIVE =============
with tabs[9]:
    st.header("📁 Archive")
    archive_dir = Path(f"/home/workspace/Daily_Log/{date_str}")
    if archive_dir.exists():
        files = list(archive_dir.glob("*"))
        st.metric("Files Archived", len(files))
        for f in sorted(files):
            size = f.stat().st_size
            st.write(f"📄 {f.name} ({size:,} bytes)")
    else:
        st.info(f"No archive for {date_str}")
