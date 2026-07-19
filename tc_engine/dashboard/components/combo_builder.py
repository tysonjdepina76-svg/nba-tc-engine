"""Dashboard Component — Combo Builder.

Builds parlay combinations from top +EV picks across sports,
computes combined edge, and displays qualifying combos."""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path


PICKS_DB = Path("/home/workspace/Projects/data/picks.db")


def load_picks_for_sport(sport: str, limit: int = 30) -> pd.DataFrame:
    conn = sqlite3.connect(str(PICKS_DB))
    league = sport.upper() if sport == "wc" else sport
    df = pd.read_sql_query(f"""
        SELECT player, team, league, stat, tc_projection, market_line, edge, direction, matchup
        FROM picks
        WHERE league = '{league}'
        ORDER BY ABS(edge) DESC
        LIMIT {limit}
    """, conn)
    conn.close()
    return df


def build_combos(df: pd.DataFrame, min_edge: float = 5.0, max_legs: int = 4) -> list:
    high = df[df["edge"].abs() >= min_edge]
    if len(high) < 2:
        return []

    combos = []
    for n_legs in [2, 3, 4]:
        if n_legs > len(high):
            continue
        for i in range(len(high) - n_legs + 1):
            legs = high.iloc[i : i + n_legs]
            combined_edge = legs["edge"].abs().mean()
            if combined_edge >= min_edge:
                combos.append({
                    "legs": n_legs,
                    "combined_edge": round(combined_edge, 1),
                    "picks": [
                        {
                            "player": row["player"],
                            "stat": row["stat"],
                            "edge": row["edge"],
                            "direction": row["direction"],
                            "team": row["team"],
                        }
                        for _, row in legs.iterrows()
                    ],
                })
    return combos


def render():
    st.header("Combo Builder")

    st.markdown("Build multi-leg parlays from top +EV picks. Higher combined edge = better expected value.")

    col1, col2, col3 = st.columns(3)
    with col1:
        sport = st.selectbox("League", ["WNBA", "MLB", "WC"], key="combo_sport")
    with col2:
        min_edge = st.slider("Min Edge %", 3.0, 10.0, 5.0, 0.5, key="combo_edge")
    with col3:
        max_legs = st.selectbox("Max Legs", [2, 3, 4], index=1, key="combo_legs")

    df = load_picks_for_sport(sport)
    if df.empty:
        st.info(f"No picks available for {sport}.")
        return

    st.subheader(f"Top Picks — {sport}")
    st.dataframe(df[["player", "stat", "edge", "direction", "team"]].head(20),
                 use_container_width=True, hide_index=True)

    combos = build_combos(df, min_edge, max_legs)
    if not combos:
        st.warning(f"No qualifying combos with edge ≥ {min_edge}%")
        return

    st.subheader(f"Qualifying Combos ({len(combos)})")
    for i, combo in enumerate(combos[:10]):
        with st.expander(f"#{i+1} {combo['legs']}-Leg | Combined Edge: {combo['combined_edge']}%"):
            for j, pick in enumerate(combo["picks"]):
                edge_color = "green" if pick["edge"] > 0 else "red"
                st.markdown(
                    f"**Leg {j+1}:** {pick['player']} ({pick['team']}) — "
                    f"{pick['stat']} {pick['direction']} — "
                    f":{edge_color}[{pick['edge']:+.1f}%]"
                )
