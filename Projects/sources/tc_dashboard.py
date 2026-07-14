#!/usr/bin/env python3
"""
TC Dashboard
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="TC Sports", layout="wide", page_icon="⚾")

st.title("⚾ TC Sports Intelligence")

today = datetime.now().strftime("%Y-%m-%d")
picks_file = Path(f"/home/workspace/Daily_Log/{today}/picks.json")

if picks_file.exists():
    with open(picks_file) as f:
        data = json.load(f)
    picks = data.get("picks", [])
    st.metric("Total Picks", len(picks))
else:
    st.info("No picks for today")

st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
