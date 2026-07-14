#!/usr/bin/env python3
"""TC Sports dashboard — Streamlit.

Reads today's picks from /home/workspace/Daily_Log/<date>/picks.csv
plus graded results and backtest summaries.

Run:
  streamlit run streamlit_app.py --server.port 8510
"""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

LOG_ROOT = Path("/home/workspace/Daily_Log")
BACKTEST_DIR = Path("/home/workspace/Projects/data/picks")


@st.cache_data(ttl=300)
def load_today_picks(log_date: str) -> pd.DataFrame:
    path = LOG_ROOT / log_date / "picks.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_historical() -> pd.DataFrame:
    hist = BACKTEST_DIR / "all_graded_picks.csv"
    if not hist.exists():
        return pd.DataFrame()
    return pd.read_csv(hist)


def main() -> None:
    st.set_page_config(page_title="TC Sports", page_icon="📊", layout="wide")
    st.title("📊 TC Sports — Daily Picks & Backtest")

    log_date = st.sidebar.date_input("Date", value=date.today()).isoformat()
    sport = st.sidebar.selectbox("Sport filter", ["all", "WNBA", "MLB", "WC", "NBA", "NHL", "NFL"])

    tab_picks, tab_backtest, tab_help = st.tabs(["Today's Picks", "Backtest", "Help"])

    with tab_picks:
        df = load_today_picks(log_date)
        if df.empty:
            st.warning(f"No picks for {log_date}. Run `python3 daily_picks.py --date {log_date}` first.")
        else:
            if sport != "all" and "league" in df.columns:
                df = df[df["league"] == sport]
            st.metric("Total picks", len(df))
            if "signal" in df.columns:
                strong = (df["signal"] == "STRONG").sum()
                st.metric("Strong signals", strong)
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_backtest:
        hist = load_historical()
        if hist.empty:
            st.info("No historical data yet. Run the backtest suite to populate this view.")
        else:
            resolved = hist[hist["result"].isin(["WIN", "LOSS", "PUSH"])]
            if not resolved.empty:
                hit_rate = (resolved["result"] == "WIN").mean()
                st.metric("Overall hit rate", f"{hit_rate:.1%}")
                if "league" in hist.columns:
                    by_league = resolved.groupby("league")["result"].apply(
                        lambda s: (s == "WIN").mean()
                    ).reset_index(name="hit_rate")
                    st.bar_chart(by_league, x="league", y="hit_rate")
            st.dataframe(hist.tail(200), use_container_width=True, hide_index=True)

    with tab_help:
        st.markdown("""
        ### How to use
        1. Pick a date in the sidebar (defaults to today).
        2. Filter by sport if desired.
        3. **Today's Picks** shows fresh TC projections and signal strength.
        4. **Backtest** shows historical hit rate by league.

        ### Refresh cadence
        - Picks refresh every 5 minutes (cached).
        - Backtest refreshes every 10 minutes.
        - Use the **Refresh** button below to force a reload.
        """)
        if st.button("🔄 Refresh now"):
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
