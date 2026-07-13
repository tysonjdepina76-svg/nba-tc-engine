"""
Table renderers for the TC dashboard.
"""

import streamlit as st
import pandas as pd


def render_picks_table(df: pd.DataFrame, title: str = "Picks"):
    if df is None or df.empty:
        st.info(f"No {title.lower()} to display.")
        return
    st.subheader(title)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_player_table(df: pd.DataFrame, sport: str, title: str = "Players"):
    if df is None or df.empty:
        st.info(f"No {title.lower()}.")
        return
    st.subheader(title)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    styled = df.style.format({c: "{:.1f}" for c in numeric_cols}, na_rep="-")
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_kv_table(rows: list, title: str = "Summary"):
    if not rows:
        return
    st.subheader(title)
    st.table(pd.DataFrame(rows))
