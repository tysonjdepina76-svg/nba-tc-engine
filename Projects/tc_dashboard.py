"""TC Sports App — Main Streamlit Dashboard."""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.domain.entities import SportConfig, REGISTRY
from src.adapters.odds_api_adapter import OddsAPIAdapter
from src.adapters.cache_adapter import CacheAdapter
from src.adapters.fantasy_combo_generator import FantasyComboGenerator

st.set_page_config(page_title="TC Sports App", page_icon="🏆", layout="wide", initial_sidebar_state="expanded")

cache = CacheAdapter()
odds_api = OddsAPIAdapter(cache=cache)


def color_edge(val, good=0.06, bad=-0.04, inverse=False):
    if val is None or val == 0:
        return ""
    if inverse:
        if val < good:
            return "background-color: #90EE90"
        if val < 0:
            return "background-color: #F5F5A0"
        if val < bad:
            return "background-color: #FFCCCB"
        return "background-color: #FF6B6B"
    else:
        if val > good:
            return "background-color: #90EE90"
        if val > 0:
            return "background-color: #F5F5A0"
        if val > bad:
            return "background-color: #FFDAB9"
        return "background-color: #FF6B6B"


def render_player_table(df: pd.DataFrame, sport: str, title: str = "Players"):
    if df.empty:
        st.info(f"No {title.lower()} available.")
        return
    config = REGISTRY.get(sport)
    if not config:
        st.error(f"Unknown sport: {sport}")
        return
    schema = config.schema or {}
    stat_keys = schema.get("stat_labels", [])
    aliases = schema.get("aliases", {})
    display_cols = ["name", "team"] + [k for k in stat_keys if k in df.columns]
    df_display = df[display_cols].copy()
    if "edge" in df.columns or "Edge" in df.columns:
        edge_col = "edge" if "edge" in df.columns else "Edge"
        df_display["Edge"] = df[edge_col]
    df_display.rename(columns=aliases, inplace=True)
    if "Edge" in df_display.columns:
        styled = df_display.style.applymap(lambda x: color_edge(x, good=0.06, bad=-0.04), subset=["Edge"])
    else:
        styled = df_display
    st.subheader(title)
    st.dataframe(styled, use_container_width=True)


def render_lineup(lineup: list):
    if not lineup:
        return
    st.write("**Starting Lineup:**")
    df = pd.DataFrame(lineup)
    if "batting_order" in df.columns:
        df = df.sort_values("batting_order")
    cols = ["batting_order", "name", "position"]
    display_cols = [c for c in cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)


def render_game_header(game: dict):
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        st.metric(game.get("away", "Away"), game.get("away_score", "-"))
    with col2:
        period = game.get("inning") or game.get("period") or game.get("minute", 0)
        label = "Inning" if "inning" in game else "Period"
        st.write(f"{label} {period}")
    with col3:
        st.metric(game.get("home", "Home"), game.get("home_score", "-"))
    if game.get("away_pitcher"):
        st.write(f"**Pitchers:** {game['away_pitcher']} (away) vs {game['home_pitcher']} (home)")


def render_edge_distribution(df: pd.DataFrame):
    if df.empty or "Edge" not in df.columns:
        return
    import plotly.express as px
    fig = px.histogram(df, x="Edge", title="Edge Distribution", labels={"Edge": "Edge Value", "count": "Number of Players"}, color_discrete_sequence=["#00A3FF"], nbins=20)
    fig.add_vline(x=0, line_dash="dash", line_color="red")
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)


def render_top_performers(df: pd.DataFrame, stat: str, n: int = 10):
    if df.empty or stat not in df.columns:
        return
    import plotly.express as px
    top = df.nlargest(n, stat)
    fig = px.bar(top, x="name", y=stat, title=f"Top {n} by {stat.upper()}", labels={"name": "Player", stat: stat.upper()}, color_discrete_sequence=["#FF6B6B"])
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)


def render_mlb_live():
    data = cache.get("mlb_live_summary")
    if not data:
        data = {
            "source": "sample",
            "games": [
                {"away": "NY Yankees", "home": "Boston Red Sox", "away_score": 3, "home_score": 2, "inning": 7, "away_pitcher": "Cole", "home_pitcher": "Sale", "lineup": [{"batting_order": 1, "name": "Judge", "position": "RF"}, {"batting_order": 2, "name": "Soto", "position": "LF"}], "players": [{"name": "Judge", "team": "NYY", "avg": 0.312, "hr": 1, "rbi": 2}]}
            ]
        }
    if not data.get("games"):
        st.info("No live MLB games at the moment.")
        return
    for game in data["games"]:
        with st.container():
            render_game_header(game)
            if game.get("lineup"):
                render_lineup(game["lineup"])
            if game.get("players"):
                df = pd.DataFrame(game["players"])
                render_player_table(df, "mlb", "Batting Stats")


def main():
    st.title("🏆 TC Sports App")
    with st.sidebar:
        st.header("Controls")
        sport = st.selectbox("Select Sport", ["mlb", "wnba", "wc"], format_func=lambda x: REGISTRY.get(x, SportConfig(name=x)).display_name if x else x.upper())
        view = st.radio("View", ["Projections", "Live", "Combos"])
        st.divider()
        st.caption(f"v2.0 • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    config = REGISTRY.get(sport)
    if not config or not config.enabled:
        st.warning(f"{sport.upper()} is currently {config.error_msg or 'disabled' if config else 'unknown'}")
        return
    st.header(f"{config.display_name}")
    with st.spinner(f"Loading {sport.upper()} data..."):
        cache_key = f"{sport}_{view.lower()}"
        data = cache.get(cache_key)
        if not data:
            if sport == "wnba":
                data = {
                    "players": [
                        {"name": "A'ja Wilson", "team": "LV", "pts": 25.7, "reb": 11.2, "ast": 3.8, "fg_pct": 0.512, "fg3": 0.8, "stl": 1.6, "blk": 2.0, "edge": 1.2},
                        {"name": "Aliyah Boston", "team": "IND", "pts": 17.0, "reb": 8.6, "ast": 2.4, "fg_pct": 0.498, "fg3": 0.4, "stl": 1.1, "blk": 1.2, "edge": 0.8},
                        {"name": "Breanna Stewart", "team": "NY", "pts": 22.3, "reb": 9.2, "ast": 4.1, "fg_pct": 0.487, "fg3": 1.2, "stl": 1.8, "blk": 1.5, "edge": 1.5},
                    ]
                }
            elif sport == "mlb":
                data = {
                    "players": [
                        {"name": "Shohei Ohtani", "team": "LAD", "avg": 0.312, "hr": 38, "rbi": 95, "r": 85, "sb": 12, "ops": 1.024, "era": 2.85, "whip": 1.02, "so": 180},
                        {"name": "Aaron Judge", "team": "NYY", "avg": 0.298, "hr": 42, "rbi": 100, "r": 90, "sb": 8, "ops": 0.986, "era": 0.0, "whip": 0.0, "so": 0},
                    ]
                }
            elif sport == "wc":
                data = {
                    "players": [
                        {"name": "Lionel Messi", "team": "ARG", "goals": 0.8, "assists": 0.4, "shots": 3.2, "shots_on_target": 1.8, "pass_pct": 85.0, "tackles": 1.2, "fouls": 0.8},
                    ]
                }
            cache.set(cache_key, data, ttl_seconds=300)
    if view == "Live":
        if sport == "mlb":
            render_mlb_live()
        else:
            st.info(f"Live view for {sport.upper()} coming soon.")
    elif view == "Combos":
        st.subheader("🎯 Combo Generator")
        generator = FantasyComboGenerator()
        combos = generator.generate_combos(sport, data.get("players", []))
        if combos:
            st.write(f"Generated {len(combos)} combos")
            for combo in combos[:10]:
                st.write(f"  • {combo}")
        else:
            st.info("No combos generated for this sport.")
    else:
        players = data.get("players", [])
        if not players:
            st.info(f"No projections available for {sport.upper()}.")
            return
        df = pd.DataFrame(players)
        render_player_table(df, sport, "Player Projections")
        st.subheader("📊 Analysis")
        col1, col2 = st.columns(2)
        with col1:
            render_edge_distribution(df)
        with col2:
            if "pts" in df.columns or "avg" in df.columns:
                stat = "pts" if "pts" in df.columns else "avg"
                render_top_performers(df, stat, 10)
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download CSV", data=csv_data, file_name=f"{sport}_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")


if __name__ == "__main__":
    main()
