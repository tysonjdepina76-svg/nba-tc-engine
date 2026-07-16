import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "picks.db"

st.set_page_config(page_title="TC Sports App", page_icon="🏆", layout="wide")

def get_team_logo(team_name, sport=None):
    if sport == "mlb":
        return "⚾ "
    elif sport == "wnba":
        return "🏀 "
    elif sport == "wc":
        return "⚽ "
    return ""

def picks_tab():
    st.subheader("📋 Live +EV Picks")
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("""
        SELECT player, team, sport, stat, projection, line, edge, direction, reason
        FROM picks
        ORDER BY edge DESC
        LIMIT 20
    """, conn)
    conn.close()
    if df.empty:
        st.warning("No picks. Run: python daily_picks.py --sport all")
    else:
        df['logo'] = df.apply(lambda row: get_team_logo(row['team'], row['sport']), axis=1)
        cols = ['logo'] + [c for c in df.columns if c != 'logo']
        df = df[cols]
        st.dataframe(df, use_container_width=True)

def edge_analysis_tab():
    st.header("🧠 Edge Analysis")
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("""
        SELECT player, sport, stat, projection, line, edge, direction, reason
        FROM picks
        WHERE reason IS NOT NULL
        ORDER BY edge DESC
        LIMIT 20
    """, conn)
    conn.close()
    if df.empty:
        st.info("No explained picks yet.")
    else:
        for _, row in df.iterrows():
            st.markdown(f"""
            **{row['player']}** ({row['sport']} {row['stat']}) – Edge: {row['edge']}  
            📝 *{row['reason']}*
            """)

def investor_tab():
    st.header("📈 Investor Dashboard")
    st.info("Investor data appears after grading picks (coming soon).")

def accuracy_tab():
    st.header("🎯 Projection Accuracy")
    st.info("Accuracy data appears after grading picks (coming soon).")

def live_tab():
    st.header("⚡ Live Games")
    st.info("Live scores will appear when ESPN scraper is active.")

def combo_tab():
    st.header("🔗 Combo Builder")
    st.info("Combos will appear after picks are generated.")

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
