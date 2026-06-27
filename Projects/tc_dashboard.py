#!/usr/bin/env python3

# TC \xe2\x80\x94 Triple Conservative \xe2\x80\x94 Trademark June 2026 \xe2\x80\x94 All rights reserved.
"""TC Live Dashboard \xe2\x80\x94 Reads real pipeline output from Daily_Log/ and displays it."""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="TC Picks Dashboard", page_icon="\xf0\x9f\x8f\x80", layout="wide")

ET = timezone(timedelta(hours=-4))  # EDT

LOG_DIR = Path("/home/workspace/Daily_Log")
OUTPUT_DIR = LOG_DIR / datetime.now(ET).strftime("%Y-%m-%d")

def _find_latest_dir() -> Path:
    if (OUTPUT_DIR / "picks.csv").exists():
        try:
            df = pd.read_csv(OUTPUT_DIR / "picks.csv")
            if len(df) > 0:
                return OUTPUT_DIR
        except Exception:
            pass
    dirs = sorted(
        [d for d in LOG_DIR.iterdir() if d.is_dir() and (d / "picks.csv").exists()],
        reverse=True,
    )
    for d in dirs:
        try:
            df = pd.read_csv(d / "picks.csv")
            if len(df) > 0:
                return d
        except Exception:
            continue
    return OUTPUT_DIR

DATA_DIR = _find_latest_dir()

CSV_COLS = [
    "date", "league", "matchup", "team", "player", "role", "status",
    "stat", "direction", "market_line", "tc_projection", "tc_target",
    "edge", "threshold", "raw_average", "source", "actual", "result",
]

# Column aliases: CSV column -> display column
COL_ALIAS = {
    "league": "sport",
    "market_line": "dk_line",
}

# \xe2\x94\x80\xe2\x94\x80 Sidebar \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80
with st.sidebar:
    st.title("\xf0\x9f\x8e\xaf TC Picks")
    sport_filter = st.multiselect(
        "Sport", ["NBA", "WNBA", "MLB", "WORLD CUP"],
        default=["WNBA", "MLB"],
    )
    min_edge = st.slider("Min Edge", 0.0, 10.0, 0.5, 0.5)

    # API Budget
    status_path = Path("/home/workspace/sports_betting_dashboard/data/account/status.json")
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text())
            calls = status.get("daily_calls", {})
            used = calls.get("used", 0)
            limit = calls.get("limit", 500)
            remaining = max(0, limit - used)
            pct = used / limit if limit > 0 else 0
        except Exception:
            used, limit, remaining, pct = 0, 500, 500, 0
    else:
        used, limit, remaining, pct = 0, 500, 500, 0
    st.divider()
    st.caption("\xf0\x9f\x93\xa1 API Budget")
    st.progress(min(pct, 1.0))
    st.caption(f"{used}/{limit} used \xc2\xb7 {remaining} remaining")

    auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
    st.divider()
    st.caption(f"Data: {DATA_DIR}")
    if st.button("🧊 Run Pipeline Health", use_container_width=True):
        with st.spinner("Running pipeline_master.py --quick..."):
            try:
                import subprocess
                r = subprocess.run(
                    ["python3", "/home/workspace/Projects/pipeline_master.py", "--quick", "--dry-run"],
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode == 0:
                    st.session_state["health_out"] = r.stdout
                    st.session_state["health_err"] = ""
                else:
                    st.session_state["health_out"] = r.stdout
                    st.session_state["health_err"] = r.stderr
            except Exception as e:
                st.session_state["health_err"] = str(e)

# \xe2\x94\x80\xe2\x94\x80 Load data \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80
@st.cache_data(ttl=60)
def load_picks() -> pd.DataFrame:
    csv_path = DATA_DIR / "picks.csv"
    if not csv_path.exists():
        return pd.DataFrame(columns=[c.lower() for c in CSV_COLS])
    raw = pd.read_csv(csv_path, header=None, names=CSV_COLS, dtype=str)
    # Strip header row if present
    raw = raw[raw["date"] != "date"]
    if raw.empty:
        return pd.DataFrame(columns=[c.lower() for c in CSV_COLS])
    # Detect header row
    first = str(raw.iloc[0, 0])[:10]
    if len(first) >= 7 and first[0:4].isdigit() and first[5:7].isdigit():
        df = raw.copy()
    else:
        df = raw.iloc[1:].reset_index(drop=True)
    df.columns = [c.strip().lower() for c in CSV_COLS]
    # Convert numeric columns (use CSV-native names)
    numeric_cols = ["market_line", "tc_projection", "edge", "tc_target", "threshold"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Add aliased columns so display code works with legacy names
    for csv_col, alias in COL_ALIAS.items():
        if csv_col in df.columns and alias not in df.columns:
            df[alias] = df[csv_col]
    # Compute confidence from edge (log-scale: edge=0.5 -> 0, edge=5 -> 2.0, edge=10 -> 2.5)
    if "edge" in df.columns:
        df["confidence"] = df["edge"].abs().apply(
            lambda x: round(1.5 + (x ** 0.45) if pd.notna(x) and x >= 0.5 else 0, 1)
        )
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


picks = load_picks()
combos = load_combos()

# \xe2\x94\x80\xe2\x94\x80 Header \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80
st.title("\xf0\x9f\x8f\x80 TC Picks Dashboard")
st.caption(
    f"Last updated: {datetime.now(ET).strftime('%I:%M %p ET')} \xe2\x80\xa2 "
    f"{len(picks)} picks loaded \xe2\x80\xa2 Data dir: {DATA_DIR.name}"
)

# \xe2\x94\x80\xe2\x94\x80 Auto-refresh (Streamlit 1.43+ pattern) \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80
if auto_refresh:
    time.sleep(60)
    st.rerun()

# ── Sport tabs ──
tab_basket, tab_baseball, tab_soccer = st.tabs(["🏀 Basketball", "⚾ Baseball", "⚽ Soccer"])

with tab_basket:
    sport_col = "sport" if "sport" in picks.columns else "league"
    # Only NBA/WNBA in this tab
    bk_filter = ["WNBA", "NBA"]
    filtered_bk = picks[picks[sport_col].isin(bk_filter)] if not picks.empty and sport_col in picks.columns else picks

    # ── Game-level summary ──
    if not filtered_bk.empty:
        games = filtered_bk.groupby([sport_col, "matchup"])
        st.subheader("📋 Game Summary")
        game_rows = []
        for (sport_label, matchup), grp in games:
            edge_col = "edge"
            qualified = (
                grp[grp[edge_col].abs() >= min_edge].copy()
                if edge_col in grp.columns
                else grp
            )
            combo_key = matchup.replace(" ", "")
            combo = combos.get(combo_key, {})
            game_rows.append({
                "Sport": sport_label,
                "Matchup": matchup,
                "Picks": len(grp),
                "Qualified": len(qualified),
                "DK Total": combo.get("dk_game_total", "—"),
                "Combo Legs": combo.get("qualified_legs", combo.get("matched_legs", 0)),
            })
        if game_rows:
            df_games = pd.DataFrame(game_rows)
            st.dataframe(
                df_games, use_container_width=True, hide_index=True,
                column_config={
                    "Sport": st.column_config.TextColumn(width="small"),
                    "Picks": st.column_config.NumberColumn(width="small"),
                    "Qualified": st.column_config.NumberColumn(width="small"),
                },
            )

    # ── Top edges table ──
    if not picks.empty and "edge" in picks.columns and "stat" in picks.columns:
        st.subheader("🔥 Top Qualified Props")
        top = picks.copy()
        if sport_col in top.columns:
            top = top[top[sport_col].isin(bk_filter)]
        top = top[top["edge"].abs() >= min_edge]
        if "confidence" in top.columns:
            top = top[top["confidence"] >= 0]
        top = top.sort_values("edge", key=abs, ascending=False).head(50)
        cols_display = [
            c for c in [
                "player", "team", "matchup", "role", "stat", "direction",
                "dk_line", "tc_projection", "edge", "confidence", "sport",
            ]
            if c in top.columns
        ]
        if not top.empty:
            st.dataframe(
                top[cols_display].reset_index(drop=True),
                use_container_width=True, hide_index=True,
                column_config={
                    "edge": st.column_config.NumberColumn("Edge", format="%.1f"),
                    "dk_line": st.column_config.NumberColumn("DK Line", format="%.1f"),
                    "tc_projection": st.column_config.NumberColumn("TC Proj", format="%.1f"),
                    "confidence": st.column_config.NumberColumn("Conf", format="%.1f"),
                },
            )

    # ── Combo section ──
    if combos:
        st.subheader("🧩 Combo-Qualified Legs")
        for key, combo in sorted(combos.items()):
            legs = combo.get("qualified", combo.get("legs", []))
            if not legs:
                continue
            combo_sport = combo.get("sport", "")
            if combo_sport not in bk_filter:
                continue
            with st.expander(
                f"{combo.get('sport','')} {key}  —  "
                f"{len(combo.get('qualified', legs))}/{len(combo.get('legs', legs))} legs  "
                f"•  DK Total: {combo.get('dk_game_total','—')}"
            ):
                leg_df = pd.DataFrame(legs)
                cols_show = [
                    c for c in [
                        "player", "stat", "direction", "dk_line", "tc_projection", "edge",
                    ]
                    if c in leg_df.columns
                ]
                if not leg_df.empty:
                    st.dataframe(leg_df[cols_show], use_container_width=True, hide_index=True)

    if picks.empty:
        st.warning(
            "No picks data found for today. "
            "Run `python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP'` first."
        )

# ═══════════════════ ⚾ BASEBALL TAB ═══════════════════
with tab_baseball:
    sport_col = "sport" if "sport" in picks.columns else "league"
    filtered_mlb = picks[picks[sport_col] == "MLB"] if not picks.empty and sport_col in picks.columns else pd.DataFrame()

    # ── Game-level summary ──
    if not filtered_mlb.empty:
        games_mlb = filtered_mlb.groupby("matchup")
        st.subheader("📋 Game Summary")
        game_rows = []
        for matchup, grp in games_mlb:
            qualified = grp[grp["edge"].abs() >= min_edge] if "edge" in grp.columns else grp
            game_rows.append({
                "Matchup": matchup,
                "Picks": len(grp),
                "Qualified": len(qualified),
                "DK Total": grp.iloc[0].get("dk_line", "—") if len(grp) > 0 and grp.iloc[0].get("role") == "GAME" else "—",
            })
        if game_rows:
            st.dataframe(
                pd.DataFrame(game_rows), use_container_width=True, hide_index=True,
                column_config={
                    "Picks": st.column_config.NumberColumn(width="small"),
                    "Qualified": st.column_config.NumberColumn(width="small"),
                },
            )

    # ── Top edges: split Batting vs Pitching ──
    if not filtered_mlb.empty and "edge" in filtered_mlb.columns and "stat" in filtered_mlb.columns:
        mlb_with_edge = filtered_mlb[filtered_mlb["edge"].abs() >= min_edge].copy()
        if "confidence" in mlb_with_edge.columns:
            mlb_with_edge = mlb_with_edge[mlb_with_edge["confidence"] >= 0]

        BATTING_STATS = {"hits", "runs", "rbi", "hr", "total_bases"}
        PITCHING_STATS = {"strikeouts", "hits_allowed", "earned_runs"}

        batting = mlb_with_edge[mlb_with_edge["stat"].isin(BATTING_STATS)]
        pitching = mlb_with_edge[mlb_with_edge["stat"].isin(PITCHING_STATS)]
        other_mlb = mlb_with_edge[~mlb_with_edge["stat"].isin(BATTING_STATS | PITCHING_STATS)]

        def _render_mlb_props(df, label):
            if df.empty:
                return
            st.subheader(f"🔥 Top Qualified Props — {label}")
            top = df.sort_values("edge", key=abs, ascending=False).head(30)
            cols_display = [
                c for c in [
                    "player", "team", "matchup", "stat", "direction",
                    "dk_line", "tc_projection", "edge", "confidence",
                ]
                if c in top.columns
            ]
            if not top.empty:
                st.dataframe(
                    top[cols_display].reset_index(drop=True),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "edge": st.column_config.NumberColumn("Edge", format="%.1f"),
                        "dk_line": st.column_config.NumberColumn("DK Line", format="%.1f"),
                        "tc_projection": st.column_config.NumberColumn("TC Proj", format="%.1f"),
                        "confidence": st.column_config.NumberColumn("Conf", format="%.1f"),
                    },
                )

        _render_mlb_props(batting, "Batting")
        _render_mlb_props(pitching, "Pitching")
        _render_mlb_props(other_mlb, "Other")

    if filtered_mlb.empty and not picks.empty:
        st.info("No MLB picks in today's data. Check back after the pipeline runs.")

    if picks.empty:
        st.warning("No picks data found. Run `python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP'` first.")

# ═══════════════════ ⚽ SOCCER TAB ═══════════════════
with tab_soccer:
    st.subheader("⚽ Soccer Combos — Live & Cached")
    try:
        live_resp = requests.get("http://localhost:8516/combos", timeout=8)
        if live_resp.ok:
            live_data = live_resp.json()
            st.caption(
                f"Engine: {live_data.get('source','?')} • "
                f"{live_data.get('count',0)} combos cached"
            )
            for c in live_data.get("combos", [])[:8]:
                st.write(
                    f"**{c.get('player','?')}** — {c.get('combo_type','?')} "
                    f"**{c.get('dk_line','?')}** ({c.get('dk_odds','?')})"
                )
        else:
            st.caption("Engine not responding")
    except Exception as e:
        st.caption(f"Engine offline: {e}")

    st.divider()
    st.subheader("⚽ World Cup TC Projections — Today")
    wc_proj_csv = (
        Path("/home/workspace/Reports")
        / f"wc_tc_projections_{datetime.now(ET).strftime('%Y%m%d')}.csv"
    )
    if wc_proj_csv.exists():
        wc_df = pd.read_csv(wc_proj_csv)
        st.caption(f"Loaded {len(wc_df)} WC TC projections")
        st.dataframe(
            wc_df.head(20), use_container_width=True, hide_index=True,
            column_config={
                "edge": st.column_config.NumberColumn("Edge", format="%.2f"),
                "tc_proj": st.column_config.NumberColumn("TC", format="%.2f"),
            },
        )
    else:
        st.caption("No WC TC projection file yet — running now...")
        with st.spinner("Running WC TC projections..."):
            import subprocess
            r = subprocess.run(
                ["python3", str(Path("/home/workspace/Projects/wc_projections.py"))],
                capture_output=True, text=True, timeout=60,
            )
            st.code(r.stdout[-1500:] if r.stdout else r.stderr[-500:])

    st.divider()
    st.caption("Sources: ESPN live roster API + SGO/Odds API DK lines + TC math engine")