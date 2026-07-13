"""
Chart renderers for the TC dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_bar(df: pd.DataFrame, x: str, y: str, title: str = "Bar Chart"):
    if df is None or df.empty or x not in df.columns or y not in df.columns:
        return
    fig = px.bar(df, x=x, y=y, title=title)
    st.plotly_chart(fig, use_container_width=True)


def render_scatter(df: pd.DataFrame, x: str, y: str, title: str = "Scatter", color: str = None):
    if df is None or df.empty or x not in df.columns or y not in df.columns:
        return
    fig = px.scatter(df, x=x, y=y, color=color, title=title)
    st.plotly_chart(fig, use_container_width=True)


def render_line(df: pd.DataFrame, x: str, y: str, title: str = "Trend"):
    if df is None or df.empty or x not in df.columns or y not in df.columns:
        return
    fig = px.line(df.sort_values(x), x=x, y=y, title=title, markers=True)
    st.plotly_chart(fig, use_container_width=True)


def render_pie(df: pd.DataFrame, names: str, values: str, title: str = "Distribution"):
    if df is None or df.empty or names not in df.columns or values not in df.columns:
        return
    fig = px.pie(df, names=names, values=values, title=title)
    st.plotly_chart(fig, use_container_width=True)
