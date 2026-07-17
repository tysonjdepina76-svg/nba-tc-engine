#!/usr/bin/env python3
"""TC Sports Dashboard — reads pipeline output only. No mock, no hidden logic."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

st.set_page_config(page_title="TC Sports", page_icon="🎯", layout="wide")

DATA_DIR = Path(os.environ.get("TC_DATA", "/home/workspace/data"))
ALERTS_JSON = Path(os.environ.get("TC_ALERTS", str(DATA_DIR / "processed/alerts.json")))
SUMMARY_JSON = DATA_DIR / "processed" / "pipeline_summary.json"


def load_alerts() -> Dict[str, Any]:
    if not ALERTS_JSON.exists():
        return {"generated": "never", "thresholds": {}, "alerts": [], "calibration_source": ""}
    with open(ALERTS_JSON) as f:
        return json.load(f)


def load_summary() -> Dict[str, Any]:
    if not SUMMARY_JSON.exists():
        return {}
    with open(SUMMARY_JSON) as f:
        d = json.load(f)
        return d.get("stats", {})


def alert_color(level: str) -> str:
    return {"STRONG": "#22c55e", "MODERATE": "#f59e0b", "WEAK": "#64748b"}.get(level, "#64748b")


st.title("🎯 TC Sports Dashboard")

data = load_alerts()
alerts = data.get("alerts", [])
generated = data.get("generated", "never")
summary = load_summary()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Alerts", summary.get("total_alerts", len(alerts)))
col2.metric("STRONG", summary.get("strong", sum(1 for a in alerts if a["alert_level"] == "STRONG")))
col3.metric("MODERATE", summary.get("moderate", sum(1 for a in alerts if a["alert_level"] == "MODERATE")))
col4.metric("Avg Edge", f"{summary.get('avg_edge', 0)*100:.1f}%")

st.caption(f"Last pipeline: {generated} | Calibration: {data.get('calibration_source', 'unknown')} | Edge threshold: {data.get('thresholds', {}).get('edge_minimum', '?')}")

if not alerts:
    st.warning("No alerts available. Run the pipeline first:\n```bash\ncd /home/workspace/tc_sports && source config.env && python pipeline/ev_pipeline.py\n```")
    st.stop()

tabs = st.tabs(["Alerts", "By League", "Top Picks"])

with tabs[0]:
    rows = []
    for a in alerts:
        rows.append({
            "Player": a["player"],
            "League": a["league"],
            "Matchup": a.get("matchup", ""),
            "Stat": a["stat"],
            "O/U": a["direction"],
            "TC Proj": a["tc_projection"],
            "Line": a["market_line"],
            "Edge": f"{a['edge']*100:.1f}%",
            "Prob": f"{a['true_probability']*100:.1f}%",
            "Level": a["alert_level"],
        })

    import pandas as pd
    df = pd.DataFrame(rows)

    def highlight_level(val):
        colors = {"STRONG": "background-color: #166534; color: #f0fdf4",
                  "MODERATE": "background-color: #78350f; color: #fef3c7"}
        return colors.get(val, "")

    st.dataframe(
        df.style.applymap(highlight_level, subset=["Level"]),
        use_container_width=True,
        height=600,
    )

with tabs[1]:
    leagues = sorted(set(a["league"] for a in alerts))
    for league in leagues:
        league_alerts = [a for a in alerts if a["league"] == league]
        st.subheader(f"{league} ({len(league_alerts)} alerts)")
        top = league_alerts[:10]
        for a in top:
            icon = {"STRONG": "🟢", "MODERATE": "🟡", "WEAK": "⚪"}.get(a["alert_level"], "⚪")
            st.markdown(
                f"{icon} **{a['player']}** {a['stat']} {a['direction']} "
                f"— TC:{a['tc_projection']} vs Line:{a['market_line']} "
                f"(edge: {a['edge']*100:.1f}%, prob: {a['true_probability']*100:.0f}%)"
            )

with tabs[2]:
    strong = [a for a in alerts if a["alert_level"] == "STRONG"]
    st.subheader(f"Top STRONG Picks ({len(strong)})")
    for a in strong:
        st.success(f"**{a['player']}** ({a['league']} {a['matchup']}) — {a['stat']} {a['direction']} "
                   f"TC:{a['tc_projection']} Line:{a['market_line']} → {a['true_probability']*100:.0f}% true prob")
        if a.get("why"):
            st.caption(a["why"])

st.divider()
st.caption("Pipeline reads real data only. No mock, no fallback. Configure thresholds in config.env.")
