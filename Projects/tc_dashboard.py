#!/usr/bin/env python3
"""TC Live Dashboard — Reads real pipeline output from Daily_Log/ and displays it."""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="TC Picks Dashboard", page_icon="🏀", layout="wide")

LOG_DIR = Path("/home/workspace/Daily_Log")
OUTPUT_DIR = LOG_DIR / datetime.now().strftime("%Y-%m-%d")

def _find_latest_dir() -> Path:
    """Return the most recent Daily_Log subdir that has a non-empty picks.csv."""
    if (OUTPUT_DIR / "picks.csv").exists():
        try:
            df = pd.read_csv(OUTPUT_DIR / "picks.csv")
            if len(df) > 0:
                return OUTPUT_DIR
        except Exception:
            pass
    # Fall back to recent dirs
    dirs = sorted([d for d in LOG_DIR.iterdir() if d.is_dir() and (d / "picks.csv").exists()],
                  reverse=True)
    for d in dirs:
        try:
            df = pd.read_csv(d / "picks.csv")
            if len(df) > 0:
                return d
        except Exception:
            continue
    return OUTPUT_DIR

DATA_DIR = _find_latest_dir()

MIN_EDGE = 0.5

CSV_COLS = [
    "date", "league", "matchup", "team", "player", "role", "status",
    "stat", "direction", "market_line", "tc_projection", "tc_target",
    "edge", "threshold", "raw_average", "source", "actual", "result",
]

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 TC Picks")
    sport_filter = st.multiselect("Sport", ["NBA", "WNBA"], default=["NBA", "WNBA"])
    min_edge = st.slider("Min Edge", 0.0, 10.0, 0.5, 0.5)
    min_confidence = st.slider("Min Confidence", 0.0, 3.0, 0.0, 0.1)
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
    st.divider()
    st.caption(f"Data: {DATA_DIR}")

# ── Auto-refresh ─────────────────────────────────────────
if auto_refresh:
    st.experimental_rerun()
    time.sleep(60)

# ── Load data ────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_picks() -> pd.DataFrame:
    csv_path = DATA_DIR / "picks.csv"
    if not csv_path.exists():
        return pd.DataFrame(columns=CSV_COLS), [], []
    df = pd.read_csv(csv_path, header=None, names=CSV_COLS)
    # Drop header rows that may have been included as data
    df = df[df["date"] != "date"]
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ["dk_line", "tc_projection", "edge", "confidence"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data(ttl=60)
def load_combos() -> dict:
    result = {}
    for f in sorted(DATA_DIR.glob("combos_*.json")):
        try:
            data = json.loads(f.read_text())
            key = f"{data.get('away','')}@{data.get('home','')}"
            result[key] = data
        except Exception:
            continue
    return result

@st.cache_data(ttl=120)
def load_slate(sport: str) -> list:
    slate_path = DATA_DIR / f"slate_{sport}.json"
    if not slate_path.exists():
        return []
    return json.loads(slate_path.read_text())

picks = load_picks()
combos = load_combos()

# ── Header ───────────────────────────────────────────────
st.title("🏀 TC Picks Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%I:%M %p ET')} • {len(picks)} picks loaded")

# ── Sport tabs ───────────────────────────────────────────
tab_basket, tab_soccer = st.tabs(["🏀 Basketball", "⚽ Soccer"])

with tab_basket:
    # ── Game-level summary ───────────────────────────────────
    if not picks.empty and "sport" in picks.columns:
        filtered = picks[picks["sport"].isin(sport_filter)]
        games = filtered.groupby(["sport", "matchup"])

        st.subheader("📋 Game Summary")
        game_rows = []
        for (sport, matchup), grp in games:
            qualified = grp[grp["edge"] >= min_edge].copy() if "edge" in grp.columns else grp
            combo_key = matchup.replace(" ", "")
            combo = combos.get(combo_key, {})
            game_rows.append({
                "Sport": sport,
                "Matchup": matchup,
                "Picks": len(grp),
                "Qualified": len(qualified),
                "DK Total": combo.get("dk_game_total", "—"),
                "Combo Legs": combo.get("qualified_legs", combo.get("matched_legs", 0)),
            })

        if game_rows:
            df_games = pd.DataFrame(game_rows)
            st.dataframe(df_games, use_container_width=True, hide_index=True,
                         column_config={"Sport": st.column_config.TextColumn(width="small"),
                                        "Picks": st.column_config.NumberColumn(width="small"),
                                        "Qualified": st.column_config.NumberColumn(width="small")})

    # ── Top edges table ──────────────────────────────────────
    if not picks.empty and "edge" in picks.columns and "stat" in picks.columns:
        st.subheader("🔥 Top Qualified Props")
        filtered = picks[picks["edge"] >= min_edge].copy() if "edge" in picks.columns else picks
        if "confidence" in filtered.columns:
            filtered = filtered[filtered["confidence"] >= min_confidence]

        top = filtered.sort_values("edge", ascending=False).head(50)
        cols_display = [c for c in ["player", "team", "matchup", "role", "stat", "direction",
                                     "dk_line", "tc_projection", "edge", "confidence", "sport"]
                         if c in top.columns]
        if not top.empty:
            st.dataframe(
                top[cols_display].reset_index(drop=True),
                use_container_width=True, hide_index=True,
                column_config={
                    "edge": st.column_config.NumberColumn("Edge", format="%.1f"),
                    "dk_line": st.column_config.NumberColumn("DK Line", format="%.1f"),
                    "tc_projection": st.column_config.NumberColumn("TC Proj", format="%.1f"),
                    "confidence": st.column_config.NumberColumn("Conf", format="%.1f"),
                })

    # ── Combo section ────────────────────────────────────────
    if combos:
        st.subheader("🧩 Combo-Qualified Legs")
        for key, combo in sorted(combos.items()):
            legs = combo.get("qualified", combo.get("legs", []))
            if not legs:
                continue
            sport = combo.get("sport", "")
            if sport not in sport_filter:
                continue
            with st.expander(f"{combo.get('sport','')} {key}  —  {len(combo.get('qualified',legs))}/{len(combo.get('legs',legs))} legs  •  DK Total: {combo.get('dk_game_total','—')}"):
                leg_df = pd.DataFrame(legs)
                cols_show = [c for c in ["player", "stat", "direction", "dk_line", "tc_projection", "edge"]
                             if c in leg_df.columns]
                if not leg_df.empty:
                    st.dataframe(leg_df[cols_show], use_container_width=True, hide_index=True)

    # ── No data state ────────────────────────────────────────
    if picks.empty:
        st.warning("No picks data found for today. Run `python3 Projects/daily_picks.py NBA WNBA` first.")

# ── Soccer tab content ────────────────────────────────
with tab_soccer:
    st.subheader("⚽ Soccer Combos — Live & Cached")
    import json
    try:
        live_resp = requests.get("http://localhost:8516/combos", timeout=8)
        if live_resp.ok:
            live_data = live_resp.json()
            st.caption(f"Engine: {live_data.get('source','?')} • {live_data.get('count',0)} combos cached")
            for c in live_data.get("combos", [])[:8]:
                st.write(f"**{c.get('player','?')}** — {c.get('combo_type','?')} **{c.get('dk_line','?')}** ({c.get('dk_odds','?')})")
        else:
            st.caption("Engine not responding")
    except Exception as e:
        st.caption(f"Engine offline: {e}")

    st.divider()
    st.subheader("⚽ World Cup TC Projections — Today")
    wc_dir = Path("/home/workspace/Daily_Log/worldcup") / datetime.now().strftime("%Y%m%d")
    wc_proj_csv = Path("/home/workspace/Reports/wc_tc_projections_") / datetime.now().strftime("%Y%m%d")
    wc_proj_csv = Path("/home/workspace/Reports") / f"wc_tc_projections_{datetime.now().strftime('%Y%m%d')}.csv"
    if wc_proj_csv.exists():
        wc_df = pd.read_csv(wc_proj_csv)
        st.caption(f"Loaded {len(wc_df)} WC TC projections")
        st.dataframe(wc_df.head(20), use_container_width=True, hide_index=True,
                     column_config={"edge": st.column_config.NumberColumn("Edge", format="%.2f"),
                                    "tc_proj": st.column_config.NumberColumn("TC", format="%.2f")})
    else:
        st.caption("No WC TC projection file yet — running now...")
        with st.spinner("Running WC TC projections..."):
            import subprocess
            r = subprocess.run(["python3", str(Path("/home/workspace/Projects/wc_projections.py"))],
                             capture_output=True, text=True, timeout=60)
            st.code(r.stdout[-1500:] if r.stdout else r.stderr[-500:])

    # ── Footer ───────────────────────────────────────────────
    st.divider()
    st.caption("Sources: ESPN live roster API + SGO/Odds API DK lines + TC math engine")