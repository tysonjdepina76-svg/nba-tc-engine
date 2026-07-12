#!/usr/bin/env python3
"""TC Dashboard — Unified 9-Tab Layout with 4 Combo Sub-Tabs"""

import streamlit as st
import pandas as pd
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# ─── PAGE CONFIG ───
st.set_page_config(
    page_title="SPORTS TC — TRIPLE CONSERVATIVE ENGINE",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 SPORTS TC — TRIPLE CONSERVATIVE ENGINE")

# ─── SIDEBAR ───
st.sidebar.header("📅 Controls")
date = st.sidebar.date_input("Date", datetime.now())
date_str = date.strftime("%Y-%m-%d")
sport_filter = st.sidebar.selectbox(
    "Sport",
    ["All", "MLB", "WNBA", "NBA", "NFL", "WORLD CUP", "NHL"]
)

st.sidebar.header("📊 System Status")

# ─── DATA LOADERS ───
@st.cache_data
def load_picks(date_str, sport_filter):
    """Load picks from Daily_Log."""
    picks_file = Path(f"/home/workspace/Daily_Log/{date_str}/picks.csv")
    if not picks_file.exists():
        return pd.DataFrame()

    df = pd.read_csv(picks_file)
    if sport_filter != "All" and 'league' in df.columns:
        df = df[df['league'] == sport_filter]
    return df

@st.cache_data
def load_graded(date_str, sport_filter):
    """Load graded picks from Daily_Log."""
    graded_file = Path(f"/home/workspace/Daily_Log/{date_str}/graded_picks.csv")
    if not graded_file.exists():
        return pd.DataFrame()

    df = pd.read_csv(graded_file)
    if sport_filter != "All" and 'sport' in df.columns:
        df = df[df['sport'] == sport_filter]
    return df

@st.cache_data
def load_combos(date_str, sport_filter="All"):
    """Load all per-game combos for the date. Each combos_*.json has
    {matchup, sport, legs, qualified, ...}. We merge into rows so the
    'Game by game' tab and the Combo Build sub-tabs work correctly."""
    combos_dir = Path(f"/home/workspace/Daily_Log/{date_str}")
    combo_files = list(combos_dir.glob("combos_*.json"))
    if not combo_files:
        log_root = Path("/home/workspace/Daily_Log")
        if log_root.exists():
            for d in sorted([x for x in log_root.iterdir() if x.is_dir()], reverse=True):
                combo_files = list(d.glob("combos_*.json"))
                if combo_files:
                    break
    if not combo_files:
        return pd.DataFrame()
    rows = []
    for cf in combo_files:
        try:
            with open(cf) as f:
                d = json.load(f)
        except Exception:
            continue
        matchup = d.get("matchup", cf.stem.replace("combos_", "").replace("_", "@"))
        sport = d.get("sport", "MLB")
        if sport_filter != "All" and sport != sport_filter:
            continue
        qualified = d.get("qualified", []) or d.get("legs", [])
        for q in qualified:
            row = {"matchup": matchup, "sport": sport, "file": cf.name, **q}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

@st.cache_data
def load_projections(date_str, sport):
    """Load projections for a specific sport."""
    proj_file = Path(f"/home/workspace/Daily_Log/{date_str}/{sport}_projections.json")
    if not proj_file.exists():
        return pd.DataFrame()

    with open(proj_file) as f:
        data = json.load(f)
    return pd.DataFrame(data.get("players", []))

@st.cache_data
def load_hit_rates():
    """Load hit-rate report."""
    hr_file = Path("/home/workspace/Projects/hit_rate_report.csv")
    if not hr_file.exists():
        return pd.DataFrame()
    return pd.read_csv(hr_file)

# ─── SIDEBAR STATUS ───
df_picks = load_picks(date_str, "All")
st.sidebar.metric("📋 Total Picks", len(df_picks))

df_graded = load_graded(date_str, "All")
if not df_graded.empty:
    hits = len(df_graded[df_graded['correct'] == True])
    st.sidebar.metric("✅ Graded", f"{hits}/{len(df_graded)}", f"{hits/len(df_graded)*100:.1f}%")

st.sidebar.success("🟢 TC Engine: Active")
st.sidebar.caption(f"Date: {date_str}")

if st.sidebar.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# ─── TABS ───
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📊 Live Picks",
    "📈 Accuracy",
    "💰 P&L",
    "🔗 DK Combos",
    "🔗 Live Combos",
    "🏆 Project Game",
    "🏆 Project Game 2",
    "⚾ MLB",
    "🌍 World Cup"
])

# ─── TAB 1: LIVE PICKS ───
with tab1:
    st.header("📊 Live Picks")

    df = load_picks(date_str, sport_filter)
    if df.empty:
        st.warning(f"No picks for {date_str}")
    else:
        st.metric("Total Picks", len(df))

        # Signal distribution
        if 'signal' in df.columns:
            col1, col2, col3 = st.columns(3)
            col1.metric("OVER", len(df[df['signal'] == 'OVER']))
            col2.metric("UNDER", len(df[df['signal'] == 'UNDER']))
            col3.metric("FLAT", len(df[df['signal'] == 'FLAT']))

        # Best picks filter
        hr_df = load_hit_rates()
        if not hr_df.empty and 'stat' in hr_df.columns:
            best_stats = hr_df[hr_df['accuracy'] >= 80]['stat'].tolist()
            if best_stats and 'stat' in df.columns:
                best_picks = df[df['stat'].isin(best_stats)]
                st.subheader("🎯 Best Picks (80%+ Accuracy)")
                st.dataframe(best_picks.head(20), use_container_width=True)

        st.dataframe(df, use_container_width=True)

# ─── TAB 2: ACCURACY ───
with tab2:
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

# ─── TAB 3: P&L ───
with tab3:
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

# ─── TAB 4: DK COMBOS ───
with tab4:
    st.header("🔗 DK Combos")
    st.info("DraftKings combo lines — coming soon (API integration in progress)")
    st.code("DK API endpoint: https://api.draftkings.com/combos/v1/{sport}")

# ─── TAB 5: LIVE COMBOS (Game by Game) ───
with tab5:
    st.header("🔗 Live Combos — Game by Game")
    combos_df = load_combos(date_str, sport_filter)
    if combos_df.empty:
        st.info(f"No combos for {date_str} — Odds API + SGO both blocked. Use TC self-edge projections as fallback.")
    else:
        games = combos_df["matchup"].unique().tolist()
        st.metric("Total Games w/ Combos", len(games))
        st.metric("Total Legs", len(combos_df))
        sel = st.selectbox("Game", ["All"] + games)
        view = combos_df if sel == "All" else combos_df[combos_df["matchup"] == sel]
        st.dataframe(view, use_container_width=True)

# ─── TAB 6: PROJECT GAME ───
with tab6:
    st.header("🏆 Project Game")

    sport = st.selectbox("Select Sport", ["MLB", "WNBA", "NBA", "NFL", "WORLD CUP", "NHL"], key="pg1")
    df = load_projections(date_str, sport)

    if df.empty:
        st.warning(f"No projections for {sport} on {date_str}")
    else:
        st.metric("Total Players", len(df))
        st.dataframe(df, use_container_width=True)

# ─── TAB 7: PROJECT GAME 2 ───
with tab7:
    st.header("🏆 Project Game 2 — Advanced View")

    sport = st.selectbox("Select Sport", ["MLB", "WNBA", "NBA", "NFL", "WORLD CUP", "NHL"], key="pg2")
    df = load_projections(date_str, sport)

    if df.empty:
        st.warning(f"No projections for {sport} on {date_str}")
    else:
        # Add edge calculation
        if 'tc_proj' in df.columns and 'dk_line' in df.columns:
            df['edge'] = (df['tc_proj'] - df['dk_line']) / df['dk_line'] * 100
            df['signal'] = df['edge'].apply(lambda x: "OVER" if x > 0 else "UNDER")
        st.dataframe(df, use_container_width=True)

# ─── TAB 8: MLB ───
with tab8:
    st.header("⚾ MLB — Player Props")

    df = load_projections(date_str, "MLB")
    if df.empty:
        st.warning(f"No MLB projections for {date_str}")
    else:
        st.metric("Total MLB Players", len(df))
        st.dataframe(df, use_container_width=True)

# ─── TAB 9: WORLD CUP ───
with tab9:
    st.header("🌍 World Cup — Player Props")

    df = load_projections(date_str, "WORLD CUP")
    if df.empty:
        st.warning(f"No World Cup projections for {date_str}")
    else:
        st.metric("Total WC Players", len(df))
        st.dataframe(df, use_container_width=True)

# ─── COMBO SUB-TABS ───
st.header("🔗 Combo Builds 1-4")
combo_tabs = st.tabs(["Combo Build 1", "Combo Build 2", "Combo Build 3", "Combo Build 4"])
for i, tab in enumerate(combo_tabs, 1):
    with tab:
        st.subheader(f"Combo Build {i}")
        combos_df = load_combos(date_str, sport_filter)
        if combos_df.empty:
            st.info("No combos available — book lines are offline. Try TC self-edge projections.")
        else:
            st.metric("Total Legs", len(combos_df))
            st.dataframe(combos_df, use_container_width=True)

# ─── FOOTER ───
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 TC Sports Analytics — Proprietary. All Rights Reserved.")
