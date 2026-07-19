"""TC Sports Dashboard — Streamlit App.

Enhanced multi-tab dashboard: Live Picks, Investor Dashboard, Projection Accuracy,
Edge Analysis, Combo Builder, Live Games, and Explainability (SHAP/PDP/ICE).
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from components.live_picks import render as render_live_picks
from components.performance import render as render_performance
from components.explainability import render as render_explainability
from components.combo_builder import render as render_combo_builder

st.set_page_config(page_title="TC Sports Engine", page_icon="🏆", layout="wide")

st.markdown("""
<style>
    .stMetric {border: 1px solid #333; border-radius: 8px; padding: 10px;}
    .stTabs [data-baseweb="tab-list"] {gap: 4px;}
    .stTabs [data-baseweb="tab"] {border-radius: 6px 6px 0 0; padding: 10px 20px;}
</style>
""", unsafe_allow_html=True)

st.title("🏆 TC Sports Engine")
st.caption("Triple Conservative (TC) — Live +EV picks, backtested performance, and explainable edge detection")

tabs = st.tabs([
    "📊 Live Picks",
    "💰 Investor Dashboard",
    "🔍 Edge Analysis",
    "🧩 Combo Builder",
    "🔬 Explainability",
    "📡 Live Games",
])

with tabs[0]:
    render_live_picks()

with tabs[1]:
    render_performance()

with tabs[2]:
    import sqlite3
    import pandas as pd
    from pathlib import Path

    st.header("Edge Analysis — Top 20 Explained")
    conn = sqlite3.connect(str(Path("/home/workspace/Projects/data/picks.db")))
    df = pd.read_sql_query("""
        SELECT player, league, stat, tc_projection, market_line, edge, direction, matchup, reason
        FROM picks
        WHERE reason IS NOT NULL AND reason != ''
        ORDER BY ABS(edge) DESC
        LIMIT 20
    """, conn)
    conn.close()

    if df.empty:
        st.info("No explained picks available.")
    else:
        for _, row in df.iterrows():
            emoji = "📈" if float(row["edge"]) > 0 else "📉"
            st.markdown(f"""
**{row['player']}** ({row['league']} — {row['stat']}) | Edge: **{row['edge']:.1f}%** {emoji}
> {row.get('direction','')} | vs {row.get('matchup','')}
> *{row.get('reason','')}*
---
""")

with tabs[3]:
    render_combo_builder()

with tabs[4]:
    render_explainability()

with tabs[5]:
    import json
    from datetime import datetime

    st.header("Live Games")
    today = datetime.now().strftime("%Y-%m-%d")
    dash_path = Path("/home/workspace/Daily_Log") / today / "live_dashboard.json"

    if dash_path.exists():
        with open(dash_path) as f:
            data = json.load(f)
        games = data.get("games", [])

        if not games:
            st.info("No live games right now.")
        else:
            sport_f = st.selectbox("Sport", ["ALL", "MLB", "WNBA", "WC"], key="live_sport_filter")
            if sport_f != "ALL":
                games = [g for g in games if g.get("sport", "").upper() == sport_f]

            for g in games:
                teams = g.get("teams", [])
                away = teams[0] if len(teams) > 0 else {}
                home = teams[1] if len(teams) > 1 else {}
                away_name = away.get("name", "?")
                home_name = home.get("name", "?")
                state = g.get("state", "pre")
                period = g.get("period", 0)
                clock = g.get("clock", "")
                state_emoji = {"pre": "⏳", "in": "🔴", "final": "✅"}.get(state, "⚪")
                status = f"Q{period}" if period else clock or state.upper()

                with st.expander(f"{state_emoji} {away_name} @ {home_name} ({status})"):
                    c1, c2 = st.columns(2)
                    for side, col in [(away, c1), (home, c2)]:
                        col.subheader(side.get("name", "?"))
                        players = side.get("players", [])
                        if players:
                            for p in players[:6]:
                                name = p.get("name", "?")
                                pts = p.get("PTS", p.get("H", ""))
                                reb = p.get("REB", p.get("RBI", ""))
                                ast = p.get("AST", p.get("HR", ""))
                                col.text(f"{name}: PTS {pts} | REB {reb} | AST {ast}")
                        else:
                            col.text("No player data")
    else:
        st.info("No live game data for today. Run: python generate_live_dashboard.py")

st.sidebar.header("TC Engine Status")
st.sidebar.markdown(f"""
- **Database**: picks.db ✅
- **Graded**: tc_pipeline.db ✅
- **API**: stagger/main.py ✅
- **Scheduler**: APScheduler ✅
- **Models**: ./models/ ✅
- **Plots**: ./plots/ ✅
""")
st.sidebar.caption("TC Engine v2.0 — Production Pipeline")
