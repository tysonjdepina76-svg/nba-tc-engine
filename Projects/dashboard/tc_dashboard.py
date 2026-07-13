"""
TC Sports App Dashboard - Enhanced with all features.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from config.columns import get_stat_columns
from config.teams import get_team_abbr
from sources.sports_registry import REGISTRY
from sources.utils.logging import setup_logging

logger = setup_logging()

st.set_page_config(page_title="TC Sports App", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #f0f2f6; }
    .stDataFrame { background-color: #1e1e2e; border-radius: 8px; padding: 8px; }
    .stButton button { background-color: #00A3FF; color: white; }
</style>
""", unsafe_allow_html=True)

def color_edge(val, good=0.06, bad=-0.04, inverse=False):
    if val is None or val == 0:
        return ""
    if inverse:
        if val < good: return "background-color: #90EE90"
        if val < 0: return "background-color: #F5F5A0"
        if val < bad: return "background-color: #FFCCCB"
        return "background-color: #FF6B6B"
    else:
        if val > good: return "background-color: #90EE90"
        if val > 0: return "background-color: #F5F5A0"
        if val > bad: return "background-color: #FFDAB9"
        return "background-color: #FF6B6B"

def render_lineup(lineup):
    if not lineup:
        return
    st.write("**Starting Lineup:**")
    df = pd.DataFrame(lineup)
    if "batting_order" in df.columns:
        df = df.sort_values("batting_order")
    st.dataframe(df[["batting_order", "name", "position"]], use_container_width=True)

def render_player_table(df: pd.DataFrame, sport: str, title: str = "Players"):
    if df.empty:
        st.info(f"No {title.lower()} available.")
        return
    config = get_stat_columns(sport)
    stat_keys = config.get("stats", [])
    aliases = config.get("aliases", {})
    display_cols = ["name", "team"] + [k for k in stat_keys if k in df.columns]
    df_display = df[display_cols].copy()
    if "edge" in df.columns or "Edge" in df.columns:
        edge_col = "edge" if "edge" in df.columns else "Edge"
        df_display["Edge"] = df[edge_col]
    df_display.rename(columns=aliases, inplace=True)
    if "Edge" in df_display.columns:
        styled = df_display.style.applymap(
            lambda x: color_edge(x, good=0.06, bad=-0.04),
            subset=["Edge"]
        )
    else:
        styled = df_display
    st.subheader(title)
    st.dataframe(styled, use_container_width=True)

@st.cache_data(ttl=60)
def load_cached_data(sport: str):
    from sources.line_fetcher import fetch_lines
    return fetch_lines(sport)

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def add_export_button(df, sport):
    if not df.empty:
        csv_data = convert_df_to_csv(df)
        st.download_button(
            label=f"Download {sport.upper()} Picks CSV",
            data=csv_data,
            file_name=f"{sport}_picks_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def safe_fetch(fetch_func, sport: str, fallback_data=None):
    try:
        data = fetch_func()
        if data and (data.get("players") or data.get("games")):
            return data
        st.info(f"No {sport} data available right now.")
        return fallback_data or {"players": []}
    except Exception as e:
        st.error(f"Error fetching {sport} data: {str(e)}")
        return fallback_data or {"players": []}

def render_mlb_live():
    from sources.mlb_live_summary import fetch_mlb_live_cached
    data = fetch_mlb_live_cached()
    if not data.get("games"):
        st.info("No live MLB games at the moment.")
        return
    for game in data["games"]:
        st.subheader(f"{game['away']} @ {game['home']} - {game['away_score']} - {game['home_score']} (Inning {game['inning']})")
        if game.get("away_pitcher"):
            st.write(f"**Pitchers:** {game['away_pitcher']} (away) vs {game['home_pitcher']} (home)")
        if game.get("lineup"):
            render_lineup(game["lineup"])
        if game.get("players"):
            render_player_table(pd.DataFrame(game["players"]), "mlb", "Batting Stats")

def render_wnba_live():
    from sources.wnba_live_summary import fetch_wnba_live_cached
    data = fetch_wnba_live_cached()
    if not data.get("games"):
        st.info("No live WNBA games at the moment.")
        return
    for game in data["games"]:
        st.subheader(f"{game['away']} @ {game['home']} - {game['away_score']} - {game['home_score']} (Q{game['period']})")
        if game.get("players"):
            render_player_table(pd.DataFrame(game["players"]), "wnba", "Player Stats")

def main():
    st.title("TC Sports App")
    sport = st.sidebar.selectbox("Sport", ["wnba", "mlb", "wc"])
    if sport == "wnba":
        render_wnba_live()
    elif sport == "mlb":
        render_mlb_live()
    else:
        from sources.soccer_live_summary import fetch_soccer_live_cached
        data = fetch_soccer_live_cached()
        if not data.get("games"):
            st.info("No live soccer games.")
        for game in data["games"]:
            st.subheader(f"{game['away']} @ {game['home']} - {game['away_score']} - {game['home_score']} ({game['minute']}')")
            if game.get("players"):
                render_player_table(pd.DataFrame(game["players"]), "soccer", "Player Stats")

if __name__ == "__main__":
    main()
