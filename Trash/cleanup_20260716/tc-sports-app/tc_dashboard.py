import streamlit as st
import pandas as pd
import requests
import sqlite3
import os
import sys
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.adapters.live_scraper import fetch_live_games
from fantasy_images import FantasyImages

st.set_page_config(page_title="TC Sports App", page_icon="🏆", layout="wide")

API = "http://localhost:8000"

@st.cache_data(ttl=30)
def load_picks():
    try:
        r = requests.get(f"{API}/api/picks/top", timeout=5)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=30)
def load_accuracy():
    try:
        r = requests.get(f"{API}/api/v1/accuracy", timeout=5)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=60)
def load_combos(sport):
    try:
        r = requests.get(f"{API}/api/v1/combos?sport={sport}", timeout=5)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=300)
def load_dashboard_stats():
    try:
        r = requests.get(f"{API}/api/stats/dashboard", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

@st.cache_data(ttl=300)
def load_recap():
    try:
        r = requests.get(f"{API}/api/stats/recap", timeout=5)
        return r.json() if r.status_code == 200 else []
    except:
        return []

def get_team_logo(team_name):
    img = FantasyImages()
    url = img.get_team_logo(team_name)
    return url

def health_widget():
    st.sidebar.subheader("🩺 System Health")
    checks = []
    try:
        r = requests.get(f"{API}/api/picks/top", timeout=2)
        checks.append(("API", r.status_code == 200))
    except:
        checks.append(("API", False))
    try:
        r = requests.get(f"{API}/api/v1/accuracy", timeout=2)
        checks.append(("Accuracy DB", r.status_code == 200))
    except:
        checks.append(("Accuracy DB", False))
    try:
        games = fetch_live_games("wnba")
        checks.append(("ESPN Live", len(games) > 0 if games else False))
    except:
        checks.append(("ESPN Live", False))
    try:
        db_path = os.path.expanduser("~/workspace/tc-sports-app/data/tc_pipeline.db")
        checks.append(("DB", os.path.exists(db_path)))
    except:
        checks.append(("DB", False))
    for name, ok in checks:
        st.sidebar.write(f"{'✅' if ok else '❌'} {name}")
    st.sidebar.metric("Dashboard", ":8510")
    st.sidebar.metric("API", ":8000")
    st.sidebar.caption(f"🕐 {datetime.now().strftime('%I:%M:%S %p ET')}")

def tab_picks():
    st.header("📋 Live +EV Picks")
    picks = load_picks()
    if picks:
        df = pd.DataFrame(picks)
        cols = st.columns([1, 1])
        sport_filter = cols[0].selectbox("Filter by Sport", ["All"] + sorted(df["sport"].unique().tolist()))
        edge_filter = cols[1].slider("Min Edge %", 0.0, 10.0, 0.0, 0.5)
        if sport_filter != "All":
            df = df[df["sport"] == sport_filter]
        df = df[df["edge"] >= edge_filter].sort_values("edge", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"edge": st.column_config.NumberColumn(format="+%.1f%%")})
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "tc_picks.csv", "text/csv")
    else:
        st.info("No picks yet. Run: python daily_picks.py --sport all")

def tab_investor():
    st.header("📈 Investor Dashboard")
    db_path = os.path.expanduser("~/workspace/tc-sports-app/data/tc_pipeline.db")
    if not os.path.exists(db_path):
        st.warning("No database. Run backtest first.")
        return
    conn = sqlite3.connect(db_path)
    df_wr = pd.read_sql_query("""
        SELECT sport, ROUND(AVG(hit)*100,1) AS win_rate, COUNT(*) AS picks
        FROM graded_picks GROUP BY sport
    """, conn)
    if not df_wr.empty:
        c1, c2 = st.columns(2)
        c1.subheader("Win Rate by Sport")
        c1.dataframe(df_wr, hide_index=True)
        fig = px.bar(df_wr, x="sport", y="win_rate", title="Win Rate %", color="sport")
        c2.plotly_chart(fig, use_container_width=True)
    df_trend = pd.read_sql_query("""
        SELECT DATE(timestamp) AS day,
               SUM(CASE WHEN hit=1 THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN hit=0 THEN 1 ELSE 0 END) AS losses,
               COUNT(*) AS total
        FROM graded_picks
        GROUP BY day ORDER BY day DESC LIMIT 30
    """, conn)
    if not df_trend.empty:
        df_trend = df_trend.sort_values("day")
        df_trend["profit"] = df_trend["wins"] - df_trend["losses"]
        df_trend["cum_profit"] = df_trend["profit"].cumsum()
        st.subheader("📊 30-Day Performance")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_trend["day"], y=df_trend["wins"], name="Wins", marker_color="#3fb950"))
        fig2.add_trace(go.Bar(x=df_trend["day"], y=df_trend["losses"], name="Losses", marker_color="#f85149"))
        fig2.add_trace(go.Scatter(x=df_trend["day"], y=df_trend["cum_profit"], name="Cumulative P&L",
                                   yaxis="y2", mode="lines+markers",
                                   line=dict(color="#d29922", width=3)))
        fig2.update_layout(barmode="group", xaxis_title="Date", yaxis_title="Picks",
                           yaxis2=dict(title="Net Units", overlaying="y", side="right"), height=400,
                           legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig2, use_container_width=True)
        returns = df_trend["profit"] / max(df_trend["total"].mean(), 1)
        if returns.std() > 0:
            sharpe = returns.mean() / returns.std() * (252 ** 0.5)
        else:
            sharpe = 0
        peak = df_trend["cum_profit"].cummax()
        drawdown = peak - df_trend["cum_profit"]
        max_dd = drawdown.max()
        calmar = (df_trend["cum_profit"].iloc[-1] / max_dd) if max_dd > 0 else 0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Win Rate", f"{df_wr['win_rate'].mean():.1f}%")
        c2.metric("Sharpe Ratio", f"{sharpe:.2f}")
        c3.metric("Max Drawdown", f"{max_dd:.0f} units")
        c4.metric("Calmar Ratio", f"{calmar:.2f}")
    conn.close()

def tab_accuracy():
    st.header("🎯 Projection Accuracy")
    data = load_accuracy()
    if data:
        df = pd.DataFrame(data)
        c1, c2 = st.columns(2)
        c1.dataframe(df, use_container_width=True, hide_index=True,
                      column_config={"mae": "MAE", "bias": "Bias", "n": "Samples", "hit_pct": st.column_config.NumberColumn("Hit %", format="%.1f%%")})
        if "mae" in df.columns and "sport" in df.columns:
            c2.bar_chart(df.set_index("sport")["mae"], use_container_width=True)
            if "hit_pct" in df.columns:
                st.subheader("Hit Rate by Sport")
                st.bar_chart(df.set_index("sport")["hit_pct"], use_container_width=True)
    else:
        st.info("No graded data yet. Run daily_picks + backtest first.")

def tab_live():
    st.header("⚡ Live Games & Odds")
    sport = st.selectbox("Sport", ["wnba", "mlb", "soccer"], key="live_sport")
    games = fetch_live_games(sport)
    if games:
        cols = st.columns(min(len(games), 2))
        for i, g in enumerate(games):
            with cols[i % 2]:
                st.metric(
                    f"{g['away']} @ {g['home']}",
                    f"{g['away_score']} - {g['home_score']}",
                    f"Period {g['period']} | {g.get('clock', 'LIVE')}"
                )
    else:
        st.info("No live games right now.")

def tab_combos():
    st.header("🔗 Combo Builder")
    sport = st.selectbox("Sport", ["mlb", "wnba", "wc"], key="combo_sport")
    min_legs = st.slider("Min Legs", 2, 4, 2)
    combos = load_combos(sport)
    if combos and not isinstance(combos, dict):
        df = pd.DataFrame(combos)
        df = df.sort_values("total_edge", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True,
                      column_config={"total_edge": st.column_config.NumberColumn("Total Edge", format="+%.1f")})
    else:
        st.info("No combos available. Run daily_picks first.")

def tab_analysis():
    st.header("🧠 Edge Analysis")
    picks = load_picks()
    if picks:
        df = pd.DataFrame(picks)
        df = df.sort_values("edge", ascending=False).head(20)
        for _, r in df.iterrows():
            edge = r.get("edge", 0)
            color = "#3fb950" if edge > 5 else "#d29922" if edge > 2 else "#f85149"
            logo_url = None
            if r.get("team"):
                logo_url = get_team_logo(r["team"])
            c1, c2 = st.columns([0.5, 9.5])
            with c1:
                if logo_url:
                    st.image(logo_url, width=40)
            with c2:
                st.markdown(f"**{r.get('player', '?')}** ({r.get('sport','?')}) — "
                           f"Edge: <span style='color:{color};font-weight:bold'>+{edge:.1f}%</span>",
                           unsafe_allow_html=True)
                if r.get("reason"):
                    st.caption(f"🧠 {r['reason']}")
                st.divider()
    else:
        st.info("Run daily_picks.py to generate picks with edge analysis.")

def main():
    st.sidebar.title("🏆 TC Sports")
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Basketball_Clipart.svg/512px-Basketball_Clipart.svg.png", width=60)
    health_widget()
    st.sidebar.divider()
    recap = load_recap()
    if recap and not isinstance(recap, dict):
        st.sidebar.subheader("📆 Yesterday")
        for r in recap:
            st.sidebar.metric(f"{r.get('sport','')} Win Rate", r.get("hit_rate", "N/A"))
    st.sidebar.divider()
    st.sidebar.caption("TC Pipeline · Tyson Depina")
    tabs = st.tabs(["📋 Picks", "📈 Investor", "🎯 Accuracy", "⚡ Live", "🔗 Combos", "🧠 Edge Analysis"])
    with tabs[0]: tab_picks()
    with tabs[1]: tab_investor()
    with tabs[2]: tab_accuracy()
    with tabs[3]: tab_live()
    with tabs[4]: tab_combos()
    with tabs[5]: tab_analysis()

if __name__ == "__main__":
    main()
