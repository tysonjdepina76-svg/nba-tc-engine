#!/usr/bin/env python3
"""TC Sports Dashboard — Investor-grade picks viewer with signal + why columns."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os, sys, json
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/workspace")
CSV_PATH = WORKSPACE / "Daily_Log" / datetime.now().strftime("%Y-%m-%d") / "picks.csv"
FALLBACK_CSV = WORKSPACE / "sports_betting_dashboard" / "data" / "picks" / "today_picks.csv"
st.set_page_config(page_title="TC Sports App", page_icon="🏆", layout="wide")

SIGNAL_COLORS = {"STRONG": "#3fb950", "MODERATE": "#d29922", "WEAK": "#8b949e", "": "#484f58"}
SPORT_ICONS = {"WNBA": "🏀", "MLB": "⚾", "WC": "⚽", "WNBA_INTL": "🏀", "MLB_INTL": "⚾"}
LEAGUE_LABEL = {"WNBA": "WNBA", "MLB": "MLB", "WC": "World Cup", "WNBA_INTL": "WNBA", "MLB_INTL": "MLB"}

@st.cache_data(ttl=60)
def load_picks():
    paths = [CSV_PATH, FALLBACK_CSV]
    for p in paths:
        if os.path.exists(str(p)):
            try:
                df = pd.read_csv(p)
                if len(df) > 0:
                    return df
            except Exception:
                continue
    return pd.DataFrame()

def load_last_run():
    p = WORKSPACE / "Daily_Log" / "last_run.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}

def load_graded():
    p = WORKSPACE / "Projects" / "all_graded_picks.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_investor_metrics():
    g = load_graded()
    if g.empty:
        return {}
    g.columns = [c.strip().lower() for c in g.columns]
    result_col = next((c for c in g.columns if c in ("result", "hit", "win")), None)
    if not result_col:
        return {}
    g["_hit"] = g[result_col].astype(str).str.upper().isin(["WIN", "TRUE", "HIT", "1", "YES"])
    total = len(g)
    wins = g["_hit"].sum()
    wr = round(wins / total * 100, 1) if total else 0
    if "edge" in g.columns:
        g["_edge"] = pd.to_numeric(g["edge"], errors="coerce").abs()
        avg_edge = round(g["_edge"].mean(), 1)
    elif "edge_pct" in g.columns:
        g["_edge"] = pd.to_numeric(g["edge_pct"], errors="coerce").abs()
        avg_edge = round(g["_edge"].mean(), 1)
    else:
        avg_edge = 0
    roi = round((wr / 100) * avg_edge - ((100 - wr) / 100), 2) if total else 0
    return {"total_bets": total, "win_rate": wr, "avg_edge": avg_edge, "est_roi": roi}

def render_metric_row(m1, m2, m3, m4):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Graded", m1)
    c2.metric("Win Rate", f"{m2}%")
    c3.metric("Avg Edge", f"{m3}%")
    c4.metric("Est. ROI", f"{m4} Units", delta_color="normal")

def render_picks_table(df, sport_filter=None):
    if sport_filter and sport_filter != "All":
        df = df[df["league"].str.upper() == sport_filter.upper()]
    if df.empty:
        st.info(f"No picks for {sport_filter or 'any sport'}.")
        return df

    st.caption(f"**{len(df)} picks** — last updated {datetime.now().strftime('%H:%M:%S ET')}")

    style_cols = {}
    idx = df.index
    for col in ["signal", "league", "direction"]:
        if col in df.columns:
            style_cols[col] = idx

    styled = df.style
    if "signal" in df.columns:
        def _signal_cmap(v):
            return f"background-color: {SIGNAL_COLORS.get(str(v).upper().strip(), '#484f58')}; color: #fff; font-weight: 600"
        styled = styled.map(_signal_cmap, subset=["signal"])
    if "direction" in df.columns:
        def _dir_cmap(v):
            c = "#3fb950" if str(v).upper() == "OVER" else "#f85149" if str(v).upper() == "UNDER" else "#484f58"
            return f"background-color: {c}; color: #fff"
        styled = styled.map(_dir_cmap, subset=["direction"])
    if "edge" in df.columns:
        def _edge_bar(v):
            try:
                ev = float(v)
                if pd.isna(ev):
                    return ""
                bars = "█" * min(int(abs(ev) * 5), 20)
                return f"{ev:+.1f}% {bars}"
            except (ValueError, TypeError):
                return str(v)
        if "edge_display" not in df.columns:
            df["edge_display"] = df["edge"].apply(_edge_bar)

    st.dataframe(styled, use_container_width=True, height=600)
    return df

def main():
    st.title("🏆 TC Sports Dashboard")
    st.caption(f"🔄 Live | {datetime.now().strftime('%H:%M:%S ET')} | Simulator Edition")

    im = load_investor_metrics()
    if im:
        render_metric_row(im["total_bets"], im["win_rate"], im["avg_edge"], im["est_roi"])
    else:
        st.info("No graded picks yet — run `grade_picks.py` to populate investor metrics.")
    st.divider()

    df = load_picks()
    if df.empty:
        st.warning("No picks CSV found today. Run `daily_picks.py --sport wnba` to generate.")
        return

    leagues = sorted(df["league"].dropna().unique()) if "league" in df.columns else []
    league_labels = ["All"] + [LEAGUE_LABEL.get(l, l) for l in leagues]
    tabs = st.tabs(league_labels)

    display_cols = []
    for col in ["player", "team", "stat", "direction", "tc_projection", "market_line", "edge", "signal", "why", "reason", "league", "matchup", "game_time", "line_source", "alert_eligible"]:
        if col in df.columns:
            display_cols.append(col)

    for i, tab in enumerate(tabs):
        with tab:
            if i == 0:
                render_picks_table(df[display_cols])
            else:
                sport = leagues[i - 1]
                render_picks_table(df[display_cols], sport_filter=sport)

    st.divider()
    st.subheader("📊 Edge Distribution")
    if "edge" in df.columns:
        edges = pd.to_numeric(df["edge"], errors="coerce").dropna()
        if len(edges) > 0:
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=edges, nbinsx=40, marker_color="#d29922", name="Edge %"))
            fig.update_layout(height=300, xaxis_title="Edge %", yaxis_title="Count", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Signal Breakdown")
    if "signal" in df.columns:
        sig_counts = df["signal"].value_counts()
        cols = st.columns(len(sig_counts))
        for j, (sig, cnt) in enumerate(sig_counts.items()):
            color = SIGNAL_COLORS.get(str(sig).upper(), "#484f58")
            cols[j].metric(sig, cnt, delta_color="off")

    st.divider()
    lr = load_last_run()
    if lr:
        st.caption(f"Last pipeline run: {lr.get('timestamp', 'unknown')} | Sports: {lr.get('sports', [])} | Total picks: {lr.get('total_picks', 0)}")

    csv_out = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Picks CSV", csv_out, f"tc_picks_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")


if __name__ == "__main__":
    main()
