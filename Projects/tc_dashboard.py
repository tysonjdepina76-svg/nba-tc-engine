import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from pathlib import Path

DB_PICKS = Path(__file__).parent / "data" / "picks.db"
DB_PIPELINE = Path(__file__).parent / "data" / "tc_pipeline.db"

st.set_page_config(page_title="TC Sports App", page_icon="🏆", layout="wide")

def load_picks(limit=50):
    conn = sqlite3.connect(str(DB_PICKS))
    df = pd.read_sql_query(f"""
        SELECT player, team, sport, stat, projection, line, edge, direction, reason
        FROM picks
        ORDER BY edge DESC
        LIMIT {limit}
    """, conn)
    conn.close()
    return df

def load_bet_tracking():
    conn = sqlite3.connect(str(DB_PIPELINE))
    df = pd.read_sql_query("""
        SELECT sport, COUNT(*) as bets,
               SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
               SUM(profit) as total_profit
        FROM bet_tracking
        GROUP BY sport
    """, conn)
    conn.close()
    return df

def load_graded():
    conn = sqlite3.connect(str(DB_PIPELINE))
    df = pd.read_sql_query("""
        SELECT sport, COUNT(*) as total,
               SUM(hit) as hits,
               ROUND(AVG(hit), 2) as hit_rate,
               ROUND(AVG(ABS(projection - actual)), 2) as mae
        FROM graded_picks
        GROUP BY sport
    """, conn)
    conn.close()
    return df

def picks_tab():
    st.subheader("📋 Live +EV Picks")
    df = load_picks()
    if df.empty:
        st.warning("No picks. Run: python daily_picks.py --sport all")
    else:
        st.dataframe(df, use_container_width=True)

def investor_tab():
    st.header("📈 Investor Dashboard")
    df = load_bet_tracking()
    if df.empty:
        st.info("Run pipeline/grade_picks.py to populate bet tracking.")
    else:
        total_profit = df['total_profit'].sum()
        total_bets = df['bets'].sum()
        total_wins = df['wins'].sum()
        win_rate = total_wins / total_bets if total_bets else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Profit", f"${total_profit:.2f}")
        c2.metric("Win Rate", f"{win_rate*100:.1f}%")
        c3.metric("Total Bets", total_bets)
        st.dataframe(df)
        fig = px.bar(df, x='sport', y='total_profit', title='Profit by Sport')
        st.plotly_chart(fig)

def accuracy_tab():
    st.header("🎯 Projection Accuracy")
    df = load_graded()
    if df.empty:
        st.info("Run pipeline/grade_picks.py to grade picks.")
    else:
        st.dataframe(df)
        fig = px.bar(df, x='sport', y='hit_rate', title='Hit Rate by Sport')
        st.plotly_chart(fig)

def live_tab():
    st.header("⚡ Live Games")
    try:
        from src.adapters.live_scraper import fetch_live_games
        sport = st.selectbox("Select Sport", ["mlb", "wnba", "soccer"])
        games = fetch_live_games(sport)
        if games:
            for g in games:
                st.write(f"**{g['away']} @ {g['home']}** – {g['away_score']} - {g['home_score']} (Period {g['period']})")
        else:
            st.info("No live games currently.")
    except ImportError:
        st.info("Live scraper not available. Check src/adapters/live_scraper.py")

def combo_tab():
    st.header("🔗 Combo Builder")
    sport = st.selectbox("Sport for Combos", ["wnba", "mlb", "wc"])
    try:
        from src.adapters.fantasy_combo_generator import FantasyComboGenerator
        gen = FantasyComboGenerator(min_legs=2, max_legs=4, min_edge=0.5)
        conn = sqlite3.connect(str(DB_PICKS))
        df = pd.read_sql_query(f"SELECT player, team, projection, edge FROM picks WHERE sport='{sport}' ORDER BY edge DESC LIMIT 20", conn)
        conn.close()
        if df.empty:
            st.info("No picks available for combo generation.")
        else:
            players = df.to_dict('records')
            combos = gen.generate_combos(sport, players, max_combos=20)
            if combos:
                st.dataframe(pd.DataFrame(combos))
            else:
                st.info("No combos meet the edge threshold.")
    except ImportError:
        st.error("FantasyComboGenerator not available.")

def edge_analysis_tab():
    st.header("🧠 Edge Analysis")
    conn = sqlite3.connect(str(DB_PICKS))
    df = pd.read_sql_query("""
        SELECT player, sport, stat, projection, line, edge, direction, reason
        FROM picks
        WHERE reason IS NOT NULL
        ORDER BY edge DESC
        LIMIT 20
    """, conn)
    conn.close()
    if df.empty:
        st.info("No explained picks available.")
    else:
        for _, row in df.iterrows():
            st.markdown(f"""
            **{row['player']}** ({row['sport']} {row['stat']}) – Edge: {row['edge']}  
            📝 *{row['reason']}*
            """)

def main():
    st.title("🏆 TC Sports App")
    tabs = st.tabs(["📋 Picks", "📈 Investor", "🎯 Accuracy", "⚡ Live", "🔗 Combos", "🧠 Edge Analysis"])
    with tabs[0]: picks_tab()
    with tabs[1]: investor_tab()
    with tabs[2]: accuracy_tab()
    with tabs[3]: live_tab()
    with tabs[4]: combo_tab()
    with tabs[5]: edge_analysis_tab()

if __name__ == "__main__":
    main()
