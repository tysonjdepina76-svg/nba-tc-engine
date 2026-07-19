"""Dashboard Component — Performance (Investor Dashboard).

Shows P&L, win rate, bet tracking by sport, and profit charts."""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path


PIPELINE_DB = Path("/home/workspace/Projects/data/tc_pipeline.db")


def load_bet_tracking() -> pd.DataFrame:
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


def load_graded() -> pd.DataFrame:
    conn = sqlite3.connect(str(PIPELINE_DB))
    df = pd.read_sql_query("""
        SELECT sport, COUNT(*) as total,
               SUM(hit) as hits,
               ROUND(AVG(hit) * 100, 1) as hit_rate,
               ROUND(AVG(ABS(tc_projection - market_line)), 2) as mae
        FROM graded_picks
        GROUP BY sport
    """, conn)
    conn.close()
    return df


def render():
    st.header("Investor Dashboard")

    bt = load_bet_tracking()
    if bt.empty:
        st.info("Run grade_daily_picks.py to populate bet tracking.")
        return

    total_profit = bt["total_profit"].sum()
    total_bets = int(bt["bets"].sum())
    total_wins = int(bt["wins"].sum())
    win_rate = (total_wins / total_bets * 100) if total_bets else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total P&L", f"${total_profit:,.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Total Bets", f"{total_bets:,}")

    st.subheader("By Sport")
    st.dataframe(bt, use_container_width=True, hide_index=True)

    try:
        import plotly.express as px
        fig = px.bar(bt, x="sport", y="total_profit", title="Profit by Sport", color="sport")
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.write("Install plotly for charts: pip install plotly")

    graded = load_graded()
    if not graded.empty:
        st.subheader("Projection Accuracy")
        st.dataframe(graded, use_container_width=True, hide_index=True)
        try:
            import plotly.express as px
            fig = px.bar(graded, x="sport", y="hit_rate", title="Hit Rate % by Sport", color="sport")
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            pass
