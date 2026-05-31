#!/usr/bin/env python3
"""
NBA TC Engine — Streamlit GUI
Bridges nba_tc_engine.py (local Python) with /api/tc (live ESPN data).
"""
import streamlit as st
import requests
import json
import subprocess
import sys
import os
import math
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ENGINE_PATH = Path(__file__).parent / "nba_tc_engine.py"
API_BASE = "https://true.zo.space/api/tc"
LOCAL_API = "http://localhost:3099/api/tc"  # Zo Space local preview
STAT_KEYS = ["PTS", "REB", "AST", "3PM", "STL", "BLK"]
SPORT_KEYS = ["NBA", "WNBA"]

# ── TC Math (mirrors Python engine) ──────────────────────────────────────────
CONS = 0.85
Q_MULT = 0.55
LINE_FACTOR = 0.88

def tc_val(v, status="ACTIVE"):
    s = str(status).upper()
    if s in ("OUT", "DNP"):
        return 0.0
    mult = CONS * (Q_MULT if "Q" in s or "QUESTION" in s else 1.0)
    return round(float(v) * mult, 1)

def line_from_tc(v):
    return math.floor(float(v) * LINE_FACTOR)

def edge(tc_val, line_val):
    return round(float(line_val) - float(tc_val), 1)

def status_factor(status):
    s = str(status).upper()
    if s in ("OUT", "DNP"):
        return 0.0
    if "Q" in s or "QUESTION" in s or "DOUBTFUL" in s or "GTD" in s:
        return Q_MULT
    return 1.0

def fmt(n):
    try:
        return f"{float(n):.1f}"
    except (TypeError, ValueError):
        return "0.0"

# ── API Helpers ──────────────────────────────────────────────────────────────
def call_api(away, home, sport="NBA", use_local=False):
    base = LOCAL_API if use_local else API_BASE
    url = f"{base}?away={away}&home={home}&sport={sport}"
    try:
        r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        if r.ok:
            return r.json()
        return {"error": f"API {r.status_code}", "detail": r.text[:200]}
    except Exception as e:
        return {"error": str(e)}

def call_live_stats(sport="NBA", use_local=False):
    base = LOCAL_API if use_local else API_BASE
    url = f"{base}?sport={sport}&mode=live-stats"
    try:
        r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        if r.ok:
            return r.json()
        return {"error": f"API {r.status_code}", "games": []}
    except Exception as e:
        return {"error": str(e), "games": []}

def call_historical(sport, event_id, use_local=False):
    base = LOCAL_API if use_local else API_BASE
    url = f"{base}?sport={sport}&mode=historical&event={event_id}"
    try:
        r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        if r.ok:
            return r.json()
        return {"error": f"API {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ── Python Engine Bridge ─────────────────────────────────────────────────────
def run_local_engine(game_str, sport="NBA", total=None, spread=None):
    cmd = [sys.executable, str(ENGINE_PATH), "--game", game_str, "--sport", sport]
    if total is not None:
        cmd += ["--total", str(total)]
    if spread is not None:
        cmd += ["--spread", str(spread)]
    cmd.append("--json")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr or f"Exit {result.returncode}"}
    except Exception as e:
        return {"error": str(e)}

# ── UI Helpers ────────────────────────────────────────────────────────────────
def edge_color(e):
    try:
        e = float(e)
        if e > 2:
            return "green"
        elif e < -2:
            return "red"
        return "gray"
    except (TypeError, ValueError):
        return "gray"

def signal_color(s):
    s = str(s).upper()
    if s == "UNDER":
        return "red"
    if s == "OVER":
        return "green"
    if s == "PASS":
        return "yellow"
    return "gray"

def render_player_row(p, stat_keys):
    cols = st.columns([2, 1, 1, 1.5] + [1] * len(stat_keys) * 3)
    with cols[0]:
        name = p.get("name", "?")
        status = p.get("status", "ACTIVE")
        status_icon = "❌" if str(status).upper() in ("OUT", "DNP") else ("⚠️" if "Q" in str(status).upper() else "✅")
        st.markdown(f"**{status_icon} {name}**")
    with cols[1]:
        st.caption(p.get("pos", "-"))
    with cols[2]:
        st.caption(p.get("ht", "-"))
    with cols[3]:
        st.caption(f"`{p.get('status', 'ACTIVE')}`")
    col_idx = 4
    for stat in stat_keys:
        tc_key = f"tc_{stat.lower()}"
        tc_v = p.get(tc_key, 0)
        line_v = p.get(f"line_{stat.lower()}", 0)
        eg_v = p.get(f"edge_{stat.lower()}", 0)
        with cols[col_idx]:
            st.markdown(f"**{fmt(tc_v)}**")
        with cols[col_idx + 1]:
            st.caption(f"T:{fmt(line_v)}")
        with cols[col_idx + 2]:
            color = edge_color(eg_v)
            st.markdown(f"<span style='color:{color}'>{'+' if float(eg_v) >= 0 else ''}{fmt(eg_v)}</span>", unsafe_allow_html=True)
        col_idx += 3

def render_team_section(team_data, label, stat_keys):
    st.markdown(f"### {label}")
    sub = team_data.get("starters", {})
    bench_sub = team_data.get("bench", {})
    all_sub = team_data.get("all", {})
    totals = all_sub.get("totals", {}) if all_sub else {}

    # Totals row
    cols = st.columns([2] + [1] * len(stat_keys))
    with cols[0]:
        st.markdown("**Team Totals**")
    for i, stat in enumerate(stat_keys):
        with cols[i + 1]:
            tc_k = f"tc_{stat.lower()}"
            st.markdown(f"**{fmt(totals.get(tc_k, 0))}**")

    # Players
    players = all_sub.get("players", []) if all_sub else []
    injuries = team_data.get("injuries", [])
    if injuries:
        st.warning(" | ".join(injuries))

    for p in players:
        role = p.get("role", "")
        role_label = "🟢 START" if role == "START" else ("🔴 OUT" if role in ("OUT", "DNP") else "🟡 BENCH")
        with st.expander(f"{role_label}  **{p.get('name', '?')}** | {p.get('pos','-')} | TC_PTS={fmt(p.get('tc_pts',0))}", expanded=(role == "START")):
            row_cols = st.columns([1] + [1] * len(stat_keys) * 3)
            for i, stat in enumerate(stat_keys):
                tc_k = f"tc_{stat.lower()}"
                ln_k = f"line_{stat.lower()}"
                eg_k = f"edge_{stat.lower()}"
                tc_v = p.get(tc_k, 0)
                ln_v = p.get(ln_k, 0)
                eg_v = p.get(eg_k, 0)
                col_offset = i * 3
                with row_cols[col_offset]:
                    st.metric(f"TC {stat}", fmt(tc_v), fmt(eg_v), delta_color="normal" if float(eg_v) >= 0 else "inverse")
                with row_cols[col_offset + 1]:
                    st.caption(f"T: {fmt(ln_v)}")
                with row_cols[col_offset + 2]:
                    c = edge_color(eg_v)
                    st.markdown(f"<span style='color:{c}'>E: {'+' if float(eg_v) >= 0 else ''}{fmt(eg_v)}</span>", unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="NBA TC Engine", page_icon="🏀", layout="wide")
st.title("🏀 NBA TC Engine — Triple Conservative Betting System")

tabs = st.tabs(["📊 Project Game", "📡 Live Stats", "🔬 Local Engine", "📈 Backtest", "ℹ️ About"])

with tabs[0]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        sport = st.selectbox("Sport", SPORT_KEYS, index=0)
    with col2:
        away = st.text_input("Away Team Code", value="BOS").upper()
    with col3:
        home = st.text_input("Home Team Code", value="NYK").upper()

    use_local_api = st.checkbox("Use local Zo Space API (dev)", value=False)
    if st.button("🚀 Run TC Projection", use_container_width=True):
        with st.spinner("Calling TC API..."):
            result = call_api(away, home, sport, use_local=use_local_api)
        if "error" in result and "games" not in result:
            st.error(f"API Error: {result['error']}")
        else:
            st.success(f"Loaded: {result.get('matchup','?')} | {result.get('source','?')}")

            # Summary cards
            m = result.get("market_total") or result.get("market")
            tc_comb = result.get("tc_combined", 0)
            tc_line = result.get("tc_line", 0)
            signal = result.get("signal", "N/A")
            edge_val = result.get("edge", 0)
            ml_data = result.get("ml_spread_total", {})

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("TC Combined", fmt(tc_comb))
            c2.metric("TC Line", fmt(tc_line))
            c3.metric("Market Total", fmt(m) if m else "—")
            c4.metric("Edge", f"{'+' if float(edge_val) >= 0 else ''}{fmt(edge_val)}", delta_color="normal")
            c5.metric("Signal", signal, delta_color="normal")

            if ml_data:
                st.caption(f"ML: {ml_data.get('away_ml','?')} / {ml_data.get('home_ml','?')} | Spread pick: {ml_data.get('spread_pick','?')}")

            st.divider()

            # Roster tables
            st.markdown("### Rosters")
            if result.get("away"):
                render_team_section(result["away"], f"{result.get('away_team','AWAY')} (Away)", STAT_KEYS)
            if result.get("home"):
                render_team_section(result["home"], f"{result.get('home_team','HOME')} (Home)", STAT_KEYS)

            # Prop backtest table
            valid_props = result.get("valid_props", [])
            if valid_props:
                st.divider()
                st.markdown(f"### Valid Props ({len(valid_props)} picks, edge ≥ threshold)")
                prop_data = []
                for row in valid_props:
                    prop_data.append({
                        "Player": row.get("player", "?"),
                        "Team": row.get("team", "?"),
                        "Role": row.get("role", "?"),
                        "Stat": row.get("stat", "?"),
                        "Direction": row.get("direction", "?"),
                        "TC Proj": fmt(row.get("tc_projection", 0)),
                        "TC Target": fmt(row.get("tc_target", 0)),
                        "Edge": fmt(row.get("edge", 0)),
                        "Threshold": fmt(row.get("threshold", 0)),
                        "Status": row.get("status", "ACTIVE"),
                    })
                st.dataframe(prop_data, use_container_width=True, hide_index=True)

with tabs[1]:
    col1, col2 = st.columns([1, 1])
    with col1:
        sport_live = st.selectbox("Sport", SPORT_KEYS, index=0, key="live_sport")
    with col2:
        use_local = st.checkbox("Use local API (dev)", value=False, key="live_local")
    if st.button("📡 Fetch Live Stats", use_container_width=True):
        with st.spinner("Fetching ESPN live data..."):
            data = call_live_stats(sport_live, use_local=use_local)
        if "error" in data:
            st.error(data["error"])
        else:
            st.success(f"Live Stats — {len(data.get('games', []))} games")
            for g in data.get("games", []):
                completed = "✅" if g.get("completed") else "🔄"
                st.markdown(f"{completed} **{g.get('away',{}).get('team','?')} {g.get('away',{}).get('score','?')} @ {g.get('home',{}).get('team','?')} {g.get('home',{}).get('score','?')}** — {g.get('status','?')} {g.get('detail','')}")

                players = g.get("players", [])
                if players:
                    rows = [{"Player": p.get("name", "?"), "MIN": p.get("minutes", "?"), "PTS": fmt(p.get("actual", {}).get("pts", 0)), "REB": fmt(p.get("actual", {}).get("reb", 0)), "AST": fmt(p.get("actual", {}).get("ast", 0)), "3PM": fmt(p.get("actual", {}).get("tpm", 0))} for p in players[:15]]
                    st.dataframe(rows, use_container_width=True, hide_index=True)
                st.divider()

with tabs[2]:
    st.markdown("### Local Python Engine")
    st.caption(f"Runs `nba_tc_engine.py` directly from disk: `{ENGINE_PATH}`")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        eng_sport = st.selectbox("Sport", SPORT_KEYS, index=0, key="eng_sport")
    with c2:
        eng_game = st.text_input("Matchup", value="BOS @ NYK").upper()
    with c3:
        eng_total = st.number_input("Market Total", value=218.5, step=0.5, key="eng_total")
    if st.button("🔬 Run Local Engine", use_container_width=True):
        with st.spinner("Running Python engine..."):
            out = run_local_engine(eng_game, eng_sport, total=eng_total)
        if "error" in out:
            st.error(out["error"])
        else:
            st.json(out)

with tabs[3]:
    st.markdown("### Backtest (historical games via API)")
    c1, c2 = st.columns([1, 2])
    with c1:
        bt_sport = st.selectbox("Sport", SPORT_KEYS, index=0, key="bt_sport")
    with c2:
        event_id = st.text_input("ESPN Event ID", value="", placeholder="e.g. 401871160")
    if st.button("🔎 Load Historical Game"):
        if not event_id.strip():
            st.warning("Enter an ESPN event ID")
        else:
            with st.spinner("Loading historical boxscore..."):
                data = call_historical(bt_sport, event_id.strip())
            if "error" in data:
                st.error(data["error"])
            else:
                st.success(f"{data.get('matchup','?')} on {data.get('date','?')} | Actual total: {data.get('actual_total','?')}")
                if data.get("away"):
                    render_team_section(data["away"], f"{data.get('away_team','AWAY')} (Away)", STAT_KEYS)
                if data.get("home"):
                    render_team_section(data["home"], f"{data.get('home_team','HOME')} (Home)", STAT_KEYS)

with tabs[4]:
    st.markdown("## About the TC System")
    st.markdown("""**Triple Conservative (TC)** applies a `0.85×` multiplier to all player stats to produce conservative projections, then derives a betting line target using `floor(TC × 0.88)`.""")
    st.markdown("### Formula Reference")
    st.code("""# Player-level
TC = stat × 0.85 (ACTIVE)
TC = stat × 0.85 × 0.55 (QUESTIONABLE)
TC = 0 (OUT)

T  = floor(TC × 0.88)   # betting target

# Game-level
TC_final = raw_PTS × VAR_FACTOR + K_GAP(9.3)
VAR_FACTOR: HIGH=0.82 (spread≥10) | MID=0.79 (4-9) | LOW=0.76 (<4)

EDGE = market_line − TC_target
Signal: UNDER when TC_Line > market_total
""")
    st.markdown("### Architecture")
    st.markdown("""- **Python Engine** (`nba_tc_engine.py`) — offline batch, hardcoded rosters, backtest engine
- **Zo Space API** (`/api/tc`) — live ESPN data, TypeScript/Hono
- **Zo Space UI** (`/nba-tc`) — React web dashboard
- **Streamlit** (`nba_tc_streamlit.py`) — this app, bridges Python engine + live API""")