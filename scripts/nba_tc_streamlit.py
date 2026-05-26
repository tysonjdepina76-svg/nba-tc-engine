#!/usr/bin/env python3
"""
NBA TC Streamlit Dashboard — Live Roster / Player Prop Engine
=============================================================

Uses nba_tc_engine.py as the single source of truth.

Critical rule:
- TC Match applies ONLY to player props: PTS, REB, AST, 3PM.
- Game totals, spreads, moneylines, and team totals are not TC-match outputs.

Run:
    streamlit run nba_tc_streamlit.py --server.port 8502
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from nba_tc_engine import ESPN_TEAM_IDS, Game, fetch_team_roster, normalize_abbr

st.set_page_config(page_title="NBA TC Live Props", page_icon="🏀", layout="wide")

st.title("🏀 NBA TC Live Player Prop Engine")
st.caption("Live ESPN API rosters • TC Match applies only to PTS / REB / AST / 3PM player props")

with st.sidebar:
    st.header("Game")
    teams = sorted(ESPN_TEAM_IDS.keys())
    away = st.selectbox("Away", teams, index=teams.index("CLE") if "CLE" in teams else 0)
    home = st.selectbox("Home", teams, index=teams.index("NYK") if "NYK" in teams else 1)
    bankroll = st.number_input("Bankroll", min_value=100.0, max_value=100000.0, value=1000.0, step=100.0)
    force_refresh = st.button("Force refresh live rosters")
    st.divider()
    st.markdown("**TC Rules**")
    st.write("Props only: PTS, REB, AST, 3PM")
    st.write("Totals/spreads/ML are separate market context")

if force_refresh:
    fetch_team_roster(away, force_refresh=True)
    fetch_team_roster(home, force_refresh=True)
    st.success("Live rosters refreshed from ESPN API")

game = Game(away, home, bankroll=bankroll)
data = game.project()

st.subheader(data["matchup"])
st.info(data["game_total_note"])

c1, c2, c3 = st.columns(3)
c1.metric("Away players", len(data["away"]["players"]))
c2.metric("Home players", len(data["home"]["players"]))
c3.metric("Valid prop edges", len(data["valid_edges"]))


def roster_table(team_payload: dict):
    rows = []
    for p in team_payload["players"]:
        rows.append({
            "Role": p["role"],
            "Player": p["name"],
            "POS": p["pos"],
            "Status": p["status"],
            "TC_PTS": p["TC_PTS"],
            "T_PTS": p["T_PTS"],
            "TC_REB": p["TC_REB"],
            "T_REB": p["T_REB"],
            "TC_AST": p["TC_AST"],
            "T_AST": p["T_AST"],
            "TC_3PM": p["TC_3PM"],
            "T_3PM": p["T_3PM"],
        })
    return rows

left, right = st.columns(2)
with left:
    st.markdown(f"### {data['away']['code']} — {data['away']['name']}")
    st.dataframe(roster_table(data["away"]), use_container_width=True, hide_index=True)
with right:
    st.markdown(f"### {data['home']['code']} — {data['home']['name']}")
    st.dataframe(roster_table(data["home"]), use_container_width=True, hide_index=True)

st.markdown("### Valid Prop Edges")
edges = []
for e in data["valid_edges"]:
    edges.append({
        "Player": e["player"],
        "Team": e["team"],
        "Role": e["role"],
        "Stat": e["stat"],
        "TC": e["TC"],
        "T": e["T"],
        "Line": e["market_line"],
        "Edge": e["edge"],
    })
st.dataframe(edges, use_container_width=True, hide_index=True)

with st.expander("Raw JSON"):
    st.json(data)
