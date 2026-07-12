"""TC Sports Betting Dashboard — Streamlit (self-contained, no Odds API needed)."""
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from plotly import express as px

PROJECTS = Path("/home/workspace/Projects")
WORKSPACE = Path("/home/workspace")
for p in (str(PROJECTS), str(WORKSPACE)):
    if p not in sys.path:
        sys.path.insert(0, p)

st.set_page_config(page_title="TC Sports Dashboard", layout="wide")

DB_PATH = PROJECTS / "data" / "tc_history.db"
DAILY_LOG = WORKSPACE / "Daily_Log"


def load_picks() -> pd.DataFrame:
    files = sorted(WORKSPACE.glob("picks_*.csv"))
    if not files:
        return pd.DataFrame()
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df["source_file"] = f.name
            frames.append(df)
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_perf(days: int = 30) -> pd.DataFrame:
    try:
        from src.tracking.historical_tracker import HistoricalTracker
        tracker = HistoricalTracker(str(DB_PATH))
        perfs = []
        for sport in ("WNBA", "MLB", "WORLD_CUP", "NBA", "NFL", "NHL"):
            try:
                p = tracker.performance(sport=sport, days=days)
                if p.get("total_bets", 0) > 0 or p.get("pending_bets", 0) > 0:
                    p["sport"] = sport
                    perfs.append(p)
            except Exception:
                continue
        return pd.DataFrame(perfs) if perfs else pd.DataFrame()
    except Exception as e:
        st.error(f"Tracker error: {e}")
        return pd.DataFrame()


def todays_picks() -> pd.DataFrame:
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = DAILY_LOG / today
    if not today_dir.exists():
        return pd.DataFrame()
    rows = []
    for jf in sorted(today_dir.glob("proj_*.json")):
        try:
            data = pd.read_json(jf)
            if isinstance(data, pd.DataFrame) and not data.empty:
                data["source"] = jf.name
                rows.append(data)
        except Exception:
            continue
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main() -> None:
    st.title("🏀 TC Sports Betting Dashboard")
    st.caption(f"Live data — {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")

    with st.sidebar:
        st.header("Controls")
        days = st.slider("Performance window (days)", 1, 90, 30)
        st.divider()
        st.caption("Data sources")
        st.caption("• Daily_Log/YYYY-MM-DD/")
        st.caption("• picks_*.csv (workspace root)")
        st.caption("• data/tc_history.db")

    tab1, tab2, tab3 = st.tabs(["📊 Performance", "🎯 Today's Picks", "📁 Raw Logs"])

    with tab1:
        perf = load_perf(days=days)
        if perf.empty:
            st.info(f"No settled bets in the last {days} days. Run `python3 run.py --settle` after games complete.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Bets", int(perf["total_bets"].sum()))
            c2.metric("Hit Rate", f"{(perf['won'].sum() / max(perf['total_bets'].sum(), 1) * 100):.1f}%")
            c3.metric("Profit", f"${perf['profit'].sum():.2f}")
            c4.metric("ROI", f"{(perf['profit'].sum() / max(perf['total_stake'].sum(), 1) * 100):.1f}%")
            st.dataframe(perf[["sport", "total_bets", "won", "win_rate", "profit", "roi"]], use_container_width=True)
            if "sport" in perf.columns and "profit" in perf.columns:
                fig = px.bar(perf, x="sport", y="profit", color="sport", title=f"Profit by Sport — last {days} days")
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        picks = load_picks()
        today = todays_picks()
        st.subheader("Picks CSV (workspace)")
        if picks.empty:
            st.info("No picks_*.csv files yet.")
        else:
            # Normalize source column for backward compatibility
            if 'source' not in picks.columns:
                picks['source'] = "UNKNOWN"
            # Filter by source (DK / SGO / MOCK / SELF_EDGE)
            src_opts = sorted(picks['source'].dropna().unique().tolist())
            if src_opts:
                sel = st.multiselect("Filter by source", src_opts, default=src_opts, key="src_filter_picks")
                picks = picks[picks['source'].isin(sel)]
            st.dataframe(picks.tail(50), use_container_width=True)
        st.subheader("Today's projections")
        if today.empty:
            st.info("No projections saved for today yet.")
        else:
            if 'source' not in today.columns:
                today['source'] = "UNKNOWN"
            src_opts_t = sorted(today['source'].dropna().unique().tolist())
            if src_opts_t:
                sel_t = st.multiselect("Filter by source", src_opts_t, default=src_opts_t, key="src_filter_today")
                today = today[today['source'].isin(sel_t)]
            st.dataframe(today.tail(50), use_container_width=True)

    with tab3:
        st.subheader("Daily_Log tree (today)")
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = DAILY_LOG / today
        if today_dir.exists():
            for f in sorted(today_dir.iterdir()):
                st.caption(f"📄 {f.name} ({f.stat().st_size} bytes)")
        else:
            st.info(f"No logs for {today} yet.")
        if st.button("Refresh"):
            st.rerun()


if __name__ == "__main__":
    main()
