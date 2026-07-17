import os
import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

DB_BASE = Path(__file__).parent / "data"
PICKS_DB = DB_BASE / "picks.db"
PIPELINE_DB = DB_BASE / "tc_pipeline.db"

st.set_page_config(page_title="TC Sports App", page_icon="🏆", layout="wide")

@st.cache_data(ttl=120)
def load_picks(limit=200):
    conn = sqlite3.connect(str(PICKS_DB))
    df = pd.read_sql_query(f"""
        SELECT player, team, league, stat, tc_projection, market_line, edge, direction, matchup, signal, reason
        FROM picks
        ORDER BY ABS(edge) DESC, date DESC
        LIMIT {limit}
    """, conn)
    conn.close()
    if not df.empty:
        df["edge_pct"] = df["edge"].round(1).astype(str) + "%"
    return df

@st.cache_data(ttl=300)
def load_graded():
    conn = sqlite3.connect(str(PIPELINE_DB))
    df = pd.read_sql_query("""
        SELECT sport, COUNT(*) as total,
               SUM(hit) as hits,
               ROUND(AVG(hit) * 100, 1) as hit_rate,
               ROUND(AVG(ABS(projection - actual)), 2) as mae
        FROM graded_picks
        GROUP BY sport
    """, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_bet_tracking():
    conn = sqlite3.connect(str(PIPELINE_DB))
    df = pd.read_sql_query("""
        SELECT sport, COUNT(*) as bets,
               SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
               ROUND(SUM(profit), 2) as total_profit
        FROM bet_tracking
        GROUP BY sport
    """, conn)
    conn.close()
    return df


def picks_tab():
    st.header("Live +EV Picks")
    df = load_picks()
    if df.empty:
        st.warning("No picks in DB. Run: python3 daily_picks.py --sport wnba")
        return

    c1, c2 = st.columns(2)
    c1.metric("Total Picks", len(df))
    if not df.empty:
        top_edge = df.iloc[0]
        c2.metric("Top Edge", f"{top_edge['player']} {top_edge['edge']:.1f}%")

    league_filter = st.selectbox("League", ["ALL"] + sorted(df["league"].dropna().unique().tolist()))
    if league_filter != "ALL":
        df = df[df["league"] == league_filter]

    display = df[["player", "team", "stat", "tc_projection", "market_line", "edge_pct", "direction", "matchup", "signal"]]
    st.dataframe(display, use_container_width=True, hide_index=True)


def investor_tab():
    st.header("Investor Dashboard")
    bt = load_bet_tracking()
    if bt.empty:
        st.info("Run pipeline/grade_picks.py to populate bet tracking.")
        return

    total_profit = bt["total_profit"].sum()
    total_bets = int(bt["bets"].sum())
    total_wins = int(bt["wins"].sum())
    win_rate = (total_wins / total_bets * 100) if total_bets else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total P&L", f"${total_profit:,.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Total Bets", f"{total_bets:,}")

    st.dataframe(bt, use_container_width=True, hide_index=True)

    try:
        import plotly.express as px
        fig = px.bar(bt, x="sport", y="total_profit", title="Profit by Sport", color="sport")
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        pass


def accuracy_tab():
    st.header("Projection Accuracy")
    graded = load_graded()
    if graded.empty:
        st.info("Run pipeline/grade_picks.py to grade picks.")
        return

    st.dataframe(graded, use_container_width=True, hide_index=True)

    try:
        import plotly.express as px
        fig = px.bar(graded, x="sport", y="hit_rate", title="Hit Rate % by Sport", color="sport")
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        pass


def edge_analysis_tab():
    st.header("Edge Analysis — Top 20 Explained")
    conn = sqlite3.connect(str(PICKS_DB))
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
        return

    for _, row in df.iterrows():
        emoji = "📈" if float(row["edge"]) > 0 else "📉"
        st.markdown(f"""
**{row['player']}** ({row['league']} — {row['stat']}) | Edge: **{row['edge']:.1f}%** {emoji}
{row.get('direction','')} | Matchup: {row.get('matchup','')}
> *{row.get('reason','')}*
---""")


def combo_tab():
    st.header("Combo Builder")
    league = st.selectbox("League", ["WNBA", "MLB", "WC"])
    try:
        from src.adapters.fantasy_combo_generator import FantasyComboGenerator
        gen = FantasyComboGenerator(min_legs=2, max_legs=4, min_edge=0.5)
        conn = sqlite3.connect(str(PICKS_DB))
        df = pd.read_sql_query(
            f"SELECT player, team, tc_projection AS projection, edge FROM picks WHERE league='{league}' AND edge > 0 ORDER BY edge DESC LIMIT 20",
            conn
        )
        conn.close()
        if df.empty:
            st.info(f"No picks for {league}.")
            return
        players = df.to_dict("records")
        combos = gen.generate_combos(league.lower(), players, max_combos=20)
        if combos:
            st.dataframe(pd.DataFrame(combos), use_container_width=True)
        else:
            st.info("No combos meet edge threshold.")
    except ImportError:
        st.error("FantasyComboGenerator module not found. Check src/adapters/")


def live_tab():
    st.header("Live Games")
    sport = st.selectbox("Sport", ["mlb", "wnba", "soccer"])
    try:
        from src.adapters.live_scraper import fetch_live_games
        games = fetch_live_games(sport)
        if games:
            for g in games:
                away = g.get("away", "?")
                home = g.get("home", "?")
                ascore = g.get("away_score", 0)
                hscore = g.get("home_score", 0)
                period = g.get("period", "?")
                st.metric(label=f"{away} @ {home}", value=f"{ascore} - {hscore}", delta=f"Q{period}")
        else:
            st.info(f"No live {sport.upper()} games running.")
    except ImportError:
        st.info("Live scraper not available. Check src/adapters/live_scraper.py")
    except Exception as e:
        st.error(f"Live feed error: {e}")


def main():
    st.title("TC Sports App")
    tabs = st.tabs([
        "Live +EV Picks",
        "Investor Dashboard",
        "Projection Accuracy",
        "Edge Analysis",
        "Combo Builder",
        "Live Games"
    ])
    with tabs[0]:
        picks_tab()
    with tabs[1]:
        investor_tab()
    with tabs[2]:
        accuracy_tab()
    with tabs[3]:
        edge_analysis_tab()
    with tabs[4]:
        combo_tab()
    with tabs[5]:
        live_tab()


if __name__ == "__main__":
    main()
