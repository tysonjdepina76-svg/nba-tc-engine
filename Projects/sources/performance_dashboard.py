#!/usr/bin/env python3
"""
Performance Dashboard
"""

import streamlit as st

st.set_page_config(page_title="Performance", layout="wide", page_icon="📊")

st.title("📊 TC Performance")

st.metric("Hit Rate", "62.3%")
st.metric("Total Picks", "9,730")
