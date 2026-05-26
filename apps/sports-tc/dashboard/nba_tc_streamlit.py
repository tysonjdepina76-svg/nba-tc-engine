"""
NBA TC Streamlit UI — v3 Triple Conservative Betting Dashboard
==============================================================
Run:  streamlit run nba_tc_streamlit.py
"""

import streamlit as st
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from nba_tc_engine_v3 import (
    TEAMS, project_game, run_backtest, BACKTEST_GAMES,
    LINE_FACTOR, MIN_EDGE, KELLY_DIV,
)

st.set_page_config(
    page_title="NBA TC Engine v3",
    page_icon="🏀",
    layout="wide",
)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    bankroll = st.number_input("Bankroll ($)", min_value=100.0, max_value=100000.0, value=1000.0, step=100.0)
    default_mkt = st.number_input("Default Market Total", min_value=180.0, max_value=280.0, value=218.5, step=0.5)
    default_spr = st.number_input("Default Market Spread", min_value=-25.0, max_value=25.0, value=-4.5, step=0.5)
    st.markdown("---")
    st.caption(f"LINE_FACTOR: `{LINE_FACTOR}`")
    st.caption(f"MIN_EDGE: `{MIN_EDGE}`")
    st.caption(f"KELLY_DIV: `{KELLY_DIV}`")
    st.markdown("---")
    st.caption("Method B: tc_combined vs market_total")
    st.caption("Backtest: **7-3 (70%)**")

# ── HEADER ──────────────────────────────────────────────────────────────────
st.title("🏀 NBA TC Engine v3")
st.markdown("**Triple Conservative Betting System** — *Method B: tc_combined vs market_total*")
st.markdown("---")

# ── LIVE PROJECTION ─────────────────────────────────────────────────────────
st.header("📊 Live Game Projection")

col1, col2, col3 = st.columns(3)
with col1:
    away_team = st.selectbox("Away", options=list(TEAMS.keys()), index=list(TEAMS.keys()).index("SA"))
with col2:
    home_team = st.selectbox("Home", options=list(TEAMS.keys()), index=list(TEAMS.keys()).index("MIN"))
with col3:
    series = st.text_input("Series / Game", value="SAS@MIN G7")

col4, col5 = st.columns(2)
with col4:
    mkt_total = st.number_input("Market Total", min_value=180.0, max_value=280.0, value=default_mkt, step=0.5)
with col5:
    mkt_spread = st.number_input("Market Spread", min_value=-25.0, max_value=25.0, value=default_spr, step=0.5)

if st.button("🚀 Generate Projection", type="primary"):
    proj = project_game(home_team, away_team, mkt_total, mkt_spread, series, "TBD", bankroll)

    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        st.metric("TC Combined", f"{proj['tc_combined']:.1f}")
    with m_col2:
        st.metric("TC Total Line", proj['tc_total_line'])
    with m_col3:
        st.metric("Market Total", proj['market_total'])
    with m_col4:
        edge = proj['edge_vs_market']
        st.metric("Edge vs Market", f"{edge:+.1f}", delta=edge)
    with m_col5:
        lean = proj['total_lean']
        color = "green" if lean == "OVER" else "red" if lean == "UNDER" else "gray"
        st.markdown(f"**Lean:** :{color}[`{lean}`]")

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.subheader(f"{proj['matchup'].split(' @ ')[0]} (Away)")
        away_key = proj['matchup'].split(' @ ')[0]
        at = proj['team_tc'][away_key]
        st.metric("TC Total", f"{at['tc']:.1f}")
        st.metric("TC Line", at['tc_line'])
    with t_col2:
        st.subheader(f"{proj['matchup'].split(' @ ')[1]} (Home)")
        home_key = proj['matchup'].split(' @ ')[1]
        ht = proj['team_tc'][home_key]
        st.metric("TC Total", f"{ht['tc']:.1f}")
        st.metric("TC Line", ht['tc_line'])

    st.markdown("---")

    if proj['picks']:
        st.subheader("🎯 TC Picks")
        for pick in proj['picks']:
            with st.container():
                if pick['type'] == 'total':
                    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
                    with c1:
                        st.metric("Pick", f"{pick['pick']} {pick['market_total']}")
                    with c2:
                        st.metric("TC Combined", pick['tc_combined'])
                    with c3:
                        st.metric("Edge", f"{pick['edge_vs_market']:+.1f}")
                    with c4:
                        conf = pick['confidence']
                        color = "green" if conf == "HIGH" else "orange" if conf == "MEDIUM" else "gray"
                        st.markdown(f"Conf: :{color}[`{conf}`]")
                    with c5:
                        st.metric("Stake", f"${pick['stake_usd']:.2f} ({pick['kelly_pct']:.2f}%)")
                    st.caption(pick['rationale'])
                elif pick['type'] == 'spread':
                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                    with c1:
                        st.metric("Spread Pick", f"{pick['pick']}")
                    with c2:
                        st.metric("TC Spread", f"{pick['tc_spread']:+.1f}")
                    with c3:
                        st.metric("Market Spread", f"{pick['market_spread']:+.1f}")
                    with c4:
                        st.metric("Edge", f"{pick['edge']:+.1f}")
                    st.caption(pick['rationale'])
                st.markdown("---")
    else:
        st.info("No lean — edge_vs_market within MIN_EDGE threshold")

    with st.expander("🏥 Injury Report"):
        for team_abbr, notes in proj['injuries'].items():
            if notes:
                st.write(f"**{team_abbr}:** {', '.join(notes)}")

# ── BACKTEST ────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("📈 Backtest Results")

if st.button("▶️ Run Backtest"):
    bt = run_backtest(verbose=False)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Games Tested", bt['games_tested'])
    with c2:
        st.metric("Record", bt['record'])
    with c3:
        st.metric("Hit Rate", f"{bt['hit_rate']}%")

    rows = []
    for r in bt['game_details']:
        rows.append({
            "Game": r['game'],
            "TC_c": r['tc_combined'],
            "TC_ln": r['tc_total_line'],
            "Mkt": r['market_total'],
            "Actual": r['actual'],
            "E(Mkt)": r['edge_vs_market'],
            "Lean": r['lean'],
            "Result": r['result'],
        })
    st.dataframe(rows, use_container_width=True)

# ── ROSTER VIEWER ──────────────────────────────────────────────────────────
st.markdown("---")
st.header("📋 Team Rosters")

t_col1, t_col2 = st.columns(2)
with t_col1:
    sel_team = st.selectbox("Select Team", options=list(TEAMS.keys()), index=list(TEAMS.keys()).index("SA"))
with t_col2:
    st.write("")

team = TEAMS[sel_team]
st.subheader(f"{team.abbr} — {team.name}")

rows = []
for p in sorted(team.players, key=lambda x: x.tc_pts(), reverse=True):
    rows.append({
        "Player": p.name,
        "POS": p.pos,
        "HT": p.ht,
        "TC pts": round(p.tc_pts(), 1),
        "TC line": p.tc_line(),
        "Status": p.status,
    })
st.dataframe(rows, use_container_width=True)

if team.injury_notes:
    st.warning(" | ".join(team.injury_notes))