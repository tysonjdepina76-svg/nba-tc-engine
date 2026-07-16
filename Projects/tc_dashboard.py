import streamlit as st
import sqlite3
import pandas as pd
import csv
import json
from pathlib import Path
from datetime import datetime

try:
    from fantasy_images import FantasyImages
    img_fetcher = FantasyImages()
except ImportError:
    img_fetcher = None

DB_PATH = Path(__file__).parent / "data" / "picks.db"
DAILY_LOG = Path("/home/workspace/Daily_Log")
HISTORICAL = Path("/home/workspace/sports_betting_dashboard/data/historical")

st.set_page_config(page_title="TC Sports App", page_icon="🏆", layout="wide")

def get_team_logo_html(team_name, league=None):
    if img_fetcher:
        try:
            url = img_fetcher.get_team_logo(team_name)
            if url:
                return f'<img src="{url}" width="30" style="border-radius:4px;vertical-align:middle;margin-right:6px;">'
        except:
            pass
    fallback = {"mlb": "⚾", "wnba": "🏀", "wc": "⚽", "MLB": "⚾", "WNBA": "🏀", "WC": "⚽"}
    return fallback.get(league, "")

def load_picks_from_db():
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("""
        SELECT player, team, league, stat, tc_projection as projection,
               market_line as line, edge, direction, reason, signal, matchup, period
        FROM picks ORDER BY edge DESC
    """, conn)
    conn.close()
    return df

def load_recent_picks_csv():
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = DAILY_LOG / today / "picks.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()

def load_graded_picks():
    today = datetime.now().strftime("%Y-%m-%d")
    gp = DAILY_LOG / today / "graded_picks.csv"
    if gp.exists():
        return pd.read_csv(gp)
    return pd.DataFrame()

def load_historical_backtest(sport):
    sport_map = {"WNBA": "wnba", "MLB": "mlb", "WC": "world_cup"}
    key = sport_map.get(sport, sport.lower())
    bt_files = list(HISTORICAL.glob(f"{key}_backtest*.csv"))
    if not bt_files:
        bt_files = list(HISTORICAL.glob(f"{key}_historical*.csv"))
    if bt_files:
        return pd.read_csv(bt_files[0])
    return pd.DataFrame()

def picks_tab():
    st.subheader("📋 Live +EV Picks — July 16, 2026")

    df = load_picks_from_db()
    if df.empty:
        st.warning("No picks. Run: python3 daily_picks.py --sport all")
        return

    sport_filter = st.selectbox("Sport", ["ALL", "WNBA", "MLB", "WC"], index=0)
    signal_filter = st.selectbox("Signal", ["ALL", "STRONG", "MODERATE", "WEAK", "PROJECTION ONLY", "HEADLINE"], index=0)

    if sport_filter != "ALL":
        df = df[df["league"] == sport_filter]

    if signal_filter == "HEADLINE":
        df = df[df["signal"].isna() | (df["signal"] == "")]
    elif signal_filter != "ALL":
        df = df[df["signal"] == signal_filter]

    headline = df[df["signal"].isna() | (df["signal"] == "")]
    proj = df[df["signal"] == "PROJECTION ONLY"]

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Headline Picks", len(headline))
    with col_b:
        st.metric("Projection Picks", len(proj))

    st.divider()
    st.caption(f"Showing {min(50, len(df))} of {len(df)} picks")

    for _, row in df.head(50).iterrows():
        logo_html = get_team_logo_html(row["team"], row["league"])
        signal = row.get("signal", "") or ""

        col1, col2, col3, col4 = st.columns([0.5, 4, 1.5, 1.5])
        with col1:
            st.markdown(logo_html, unsafe_allow_html=True)
        with col2:
            matchup_str = f" · {row['matchup']}" if pd.notna(row.get("matchup")) and row.get("matchup") else ""
            stat_str = f" · {row['stat']}" if pd.notna(row.get("stat")) and row.get("stat") else ""
            st.markdown(f"**{row['player']}** ({row['team']}){matchup_str}{stat_str}")

            why = row.get("reason", "")
            if pd.notna(why) and why:
                st.caption(f"💡 {why[:200]}")
        with col3:
            direction = row.get("direction", "OVER")
            color = "#3fb950" if str(direction).upper() == "OVER" else "#f85149"
            st.markdown(
                f"<span style='color:{color};font-weight:bold'>{direction}</span>"
                f"<br><span style='font-size:0.75em;opacity:0.7'>line {row.get('line',0):.1f} → proj {row.get('projection',0):.1f}</span>",
                unsafe_allow_html=True,
            )
        with col4:
            st.metric("Edge", f"{row['edge']:.1f}%")
            if signal:
                badge_colors = {
                    "STRONG": "#3fb950",
                    "MODERATE": "#d29922",
                    "WEAK": "#8b949e",
                    "PROJECTION ONLY": "#8b949e",
                }
                bg = badge_colors.get(signal, "#21262d")
                st.markdown(
                    f"<span style='background:{bg};color:white;padding:2px 6px;border-radius:4px;font-size:0.7em'>{signal}</span>",
                    unsafe_allow_html=True,
                )


def edge_analysis_tab():
    st.header("🧠 Edge Analysis")

    df = load_picks_from_db()
    if df.empty:
        st.info("No explained picks yet.")
        return

    sport = st.selectbox("Sport", ["ALL", "WNBA", "MLB", "WC"], key="edge_sport")
    if sport != "ALL":
        df = df[df["league"] == sport]

    headline = df[df["signal"].isna() | (df["signal"] == "")].head(20)
    st.subheader("🔥 Top Headline Picks")
    for _, row in headline.iterrows():
        logo_html = get_team_logo_html(row["team"], row["league"])
        stat_str = f" {row['stat']}" if pd.notna(row.get("stat")) and row.get("stat") else ""
        st.markdown(
            f"{logo_html} **{row['player']}** ({row['league']}{stat_str}) "
            f"— proj `{row['projection']:.1f}` vs line `{row.get('line',0):.1f}` → Edge: `{row['edge']:.1f}%`  \n"
            f"📝 *{row.get('reason','')}*",
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("📊 Edge Distribution")
    chart_data = df[df["edge"].notna()].copy()
    chart_data["edge_bucket"] = pd.cut(chart_data["edge"], bins=[-10, -5, -2, 0, 2, 5, 10, 20], labels=["<-5", "-5 to -2", "-2 to 0", "0-2", "2-5", "5-10", "10+"])
    st.bar_chart(chart_data["edge_bucket"].value_counts().sort_index())


def investor_tab():
    st.header("📈 Investor Dashboard")
    graded = load_graded_picks()

    if graded.empty:
        st.info("No graded picks yet today — games still in progress or backtest not yet run.")
        return

    total = len(graded)
    if "actual" in graded.columns and "result" in graded.columns:
        wins = len(graded[graded["result"] == "WIN"])
        hit_rate = (wins / total * 100) if total > 0 else 0
    else:
        wins = 0
        hit_rate = 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Picks", total)
    with col2:
        st.metric("Won", wins)
    with col3:
        st.metric("Hit Rate", f"{hit_rate:.1f}%")

    if "sport" in graded.columns:
        st.divider()
        st.subheader("By Sport")
        for sport_name in graded["sport"].dropna().unique():
            sdf = graded[graded["sport"] == sport_name]
            stot = len(sdf)
            if stot == 0:
                continue
            swin = len(sdf[sdf["result"] == "WIN"]) if "result" in sdf.columns else 0
            sr = (swin / stot * 100) if stot > 0 else 0
            st.markdown(f"**{sport_name}**: {stot} picks · {swin} wins · **{sr:.1f}%** hit  \n"
                        f"`{'█' * int(sr/5)}{'░' * (20 - int(sr/5))}`")


def accuracy_tab():
    st.header("🎯 Projection Accuracy")

    sport = st.selectbox("Sport", ["WNBA", "MLB", "WC"], key="acc_sport")
    hist = load_historical_backtest(sport)

    if hist.empty:
        st.info(f"No historical backtest data found for {sport}.")
        return

    st.metric("Backtest Rows", len(hist))

    cols = hist.columns.tolist()
    st.caption(f"Columns: {', '.join(cols[:12])}")

    if "edge" in hist.columns:
        st.subheader("Edge Distribution (Historical)")
        st.bar_chart(hist["edge"].describe())

    st.dataframe(hist.head(100), use_container_width=True, height=400)


def live_tab():
    st.header("⚡ Live Games — July 16, 2026")

    csv_df = load_recent_picks_csv()
    if csv_df.empty:
        st.info("No live slate data available.")
        return

    matchups = csv_df["matchup"].dropna().unique() if "matchup" in csv_df.columns else []

    if len(matchups) == 0:
        st.info("No matchups found in today's slate.")
        return

    for m in sorted(matchups)[:15]:
        with st.expander(f"🏟️ {m}"):
            game_df = csv_df[csv_df["matchup"] == m]
            st.caption(f"{len(game_df)} players projected")

            status = game_df["status"].iloc[0] if "status" in game_df.columns else "Scheduled"
            game_time = game_df["game_time"].iloc[0] if "game_time" in game_df.columns else ""
            st.markdown(f"**Status**: {status}  ·  **Game Time**: {game_time}")

            if "role" in game_df.columns:
                starters = game_df[game_df["role"] == "STARTER"]
                bench = game_df[game_df["role"] == "BENCH"]
                st.caption(f"Starters: {len(starters)} · Bench: {len(bench)}")

            st.dataframe(
                game_df[["player", "team", "stat", "projection", "dk_line", "edge", "direction", "role"]].head(12),
                use_container_width=True,
            )


def combo_tab():
    st.header("🔗 Combo Builder")
    st.info("Combos require real DK lines across multiple props. Currently: WNBA/WC self-edge only — no DK player props available. MLB using SportsDataIO DK lines.")

    df = load_picks_from_db()
    if df.empty:
        return

    headline_mlb = df[(df["league"] == "MLB") & ((df["signal"].isna()) | (df["signal"] == ""))]
    if not headline_mlb.empty:
        st.subheader("⚾ MLB Headline Picks (Combo Candidates)")
        for _, row in headline_mlb.iterrows():
            st.markdown(
                f"**{row['player']}** ({row['team']}) {row.get('stat','')} "
                f"— proj `{row['projection']:.1f}` vs line `{row.get('line',0):.1f}` → `{row['edge']:.1f}%` [{row.get('direction','OVER')}]",
            )
    else:
        st.info("No MLB headline picks today.")


def main():
    st.title("🏆 TC Sports App")
    st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %I:%M %p ET')} · "
               f"Source: picks.db ({len(load_picks_from_db())} picks) · "
               f"Dashboard: :8510 · API: :8000")

    tabs = st.tabs(["📋 Picks", "📈 Investor", "🎯 Accuracy", "⚡ Live", "🔗 Combos", "🧠 Edge Analysis"])
    with tabs[0]:
        picks_tab()
    with tabs[1]:
        investor_tab()
    with tabs[2]:
        accuracy_tab()
    with tabs[3]:
        live_tab()
    with tabs[4]:
        combo_tab()
    with tabs[5]:
        edge_analysis_tab()


if __name__ == "__main__":
    main()
