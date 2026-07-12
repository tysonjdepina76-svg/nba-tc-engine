"""
Sports TC Dashboard — Streamlit UI
Full integration with master_tc.py engine + live odds API
"""
import streamlit as st
import pandas as pd
import subprocess
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="Sports TC Dashboard",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Constants ──────────────────────────────────────────────────────────────
CONS = 0.85
Q_MULT = 0.55
LINE_FACTOR = 0.88
MIN_EDGE = 2.0

SPORT_OPTIONS = ["NBA", "WNBA"]

NBA_GAMES = [
    "PHI @ NYK", "BOS @ NYK", "OKC @ MIN", "CLE @ IND",
    "DEN @ LAC", "MIN @ SAS", "LAL @ GSW", "HOU @ DAL",
    "DET @ CLE", "ORL @ BOS", "SAS @ DEN", "PHX @ LAL",
    "MIL @ ATL", "CHA @ MIA", "CHI @ BKN", "NOP @ SAC",
]

WNBA_GAMES = [
    "NYL @ MIN", "LVA @ CON", "IND @ DAL", "CHI @ SEA",
    "PHX @ LAS", "ATL @ WAS", "NYL @ LVA", "CON @ CHI",
]

GAME_CACHE_TTL = 300  # 5 min

MARKET_TOTAL = {"NBA": 215.0, "WNBA": 165.0}

# ── Engine import ──────────────────────────────────────────────────────────
try:
    from master_tc import Game, CONS, Q_MULT, LINE_FACTOR, MIN_EDGE
    from master_tc import NBA_ROSTERS, WNBA_ROSTERS
    from master_tc import NBA_BACKTEST, WNBA_BACKTEST
    ENGINE_OK = True
except Exception as e:
    ENGINE_OK = False
    st.error(f"Engine load failed: {e}")

# ── Helpers ───────────────────────────────────────────────────────────────
def calc_tc_total(team_obj):
    t = team_obj.team_totals_all()
    return t["TC_TOTAL"]

def edge_label(edge):
    if edge > MIN_EDGE:
        return "OVER", "🟢"
    elif edge < -MIN_EDGE:
        return "UNDER", "🔴"
    return "NO EDGE", "⚪"

def format_status(status):
    if status == "ACTIVE":
        return "✅"
    elif status == "Q":
        return "⚠️ Q"
    else:
        return "❌ OUT"

# ── Sidebar ──────────────────────────────────────────────────────────────
st.sidebar.title("🏀 Sports TC")
st.sidebar.markdown("---")
st.sidebar.markdown("**Triple Conservative System**")
st.sidebar.markdown(f"`TC = stat × {CONS}`")
st.sidebar.markdown(f"`Q = × {Q_MULT} | OUT = 0`")
st.sidebar.markdown(f"`LINE = TC × {LINE_FACTOR}`")
st.sidebar.markdown("---")

sport = st.sidebar.selectbox("Sport", SPORT_OPTIONS, index=0)
game_list = NBA_GAMES if sport == "NBA" else WNBA_GAMES
game = st.sidebar.selectbox("Game", game_list)
show_injury = st.sidebar.checkbox("Show Injury Report", value=True)
show_roster = st.sidebar.checkbox("Full Roster Table", value=True)
dark_mode = st.sidebar.checkbox("Dark Mode", value=True)

st.sidebar.markdown("---")
st.sidebar.caption(f"Sports TC v4.0 | {datetime.now().strftime('%I:%M %p')}")

# ── Main Title ────────────────────────────────────────────────────────────
theme_bg = "#0e1117" if dark_mode else "#fafafa"
theme_fg = "#ffffff" if dark_mode else "#1a1a1a"

st.markdown(f"""
<div style="background:{theme_bg};padding:16px 24px;border-radius:12px;margin-bottom:20px">
  <h1 style="color:{theme_fg};margin:0">🏀 Sports TC Dashboard</h1>
  <p style="color:gray;margin:4px 0 0">{sport} — {game}</p>
</div>
""", unsafe_allow_html=True)

# ── Load game ─────────────────────────────────────────────────────────────
if ENGINE_OK:
    parts = game.replace(" @ ", " ").split()
    away, home = parts[0].upper(), parts[1].upper()
    g = Game(away, home, sport)
else:
    st.warning("Engine not loaded — running in parse-only mode")
    g = None

# ── Summary Cards ─────────────────────────────────────────────────────────
if g:
    at = g.away.team_totals_all()
    ht = g.home.team_totals_all()
    tc_combined = round(at["TC_TOTAL"] + ht["TC_TOTAL"], 1)
    line = round(tc_combined * LINE_FACTOR)
    edge = round(tc_combined - line, 1)
    signal, signal_icon = edge_label(edge)
    market_total = MARKET_TOTAL[sport]
    market_diff = round(tc_combined - market_total, 1)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("TC Combined", f"{tc_combined}", f"{market_diff:+.1f} vs market")
    col2.metric("TC Line", f"{line}", f"×{LINE_FACTOR}")
    col3.metric("Edge", f"{edge:+.1f}", signal)
    col4.metric("Signal", signal, f"{signal_icon} {signal}")
    col5.metric("Market Total", f"{market_total}", "baseline")

st.markdown("---")

# ── Tab Layout ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Projections",
    "📊 Backtest",
    "📰 Injury Report",
    "⚙️ Settings"
])

# ── Tab 1: Projections ────────────────────────────────────────────────────
with tab1:
    if g:
        for team_obj, label in [(g.away, away), (g.home, home)]:
            st.subheader(f"{label} — {team_obj.name}")

            if show_roster:
                rows = []
                for p in team_obj.roster():
                    proj = p.proj()
                    rows.append({
                        "Player": p.name,
                        "POS": p.pos,
                        "HT": p.ht,
                        "TC PTS": proj["TC_PTS"],
                        "TC REB": proj["TC_REB"],
                        "TC AST": proj["TC_AST"],
                        "TC 3PM": proj["TC_3PM"],
                        "TC TOTAL": p.tc_total(),
                        "Status": format_status(p.status),
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                start = team_obj.starters()
                for p in start:
                    proj = p.proj()
                    st.markdown(f"""
                    <div style="background:#1a1a2e;padding:8px 16px;border-radius:8px;margin:4px 0">
                      <strong>{p.name}</strong> ({p.pos}) — TC: {proj['TC_PTS']}pts {proj['TC_REB']}reb {proj['TC_AST']}ast {proj['TC_3PM']}3pm
                      <span style="float:right">{format_status(p.status)}</span>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")

        # Team totals table
        st.subheader("Team Totals")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**{away}**")
            st.write(f"TC PTS: `{at['TC_PTS']}`")
            st.write(f"TC REB: `{at['TC_REB']}`")
            st.write(f"TC AST: `{at['TC_AST']}`")
            st.write(f"TC 3PM: `{at['TC_3PM']}`")
            st.write(f"**TC TOTAL: `{at['TC_TOTAL']}`**")
        with col_b:
            st.markdown(f"**{home}**")
            st.write(f"TC PTS: `{ht['TC_PTS']}`")
            st.write(f"TC REB: `{ht['TC_REB']}`")
            st.write(f"TC AST: `{ht['TC_AST']}`")
            st.write(f"TC 3PM: `{ht['TC_3PM']}`")
            st.write(f"**TC TOTAL: `{ht['TC_TOTAL']}`**")

        # TC Line Derivation table
        st.markdown("---")
        st.subheader("TC Line Derivation")
        derivation_data = {
            "Metric": ["TC Combined", f"LINE (×{LINE_FACTOR})", "Edge", "Signal"],
            "Value": [tc_combined, line, f"{edge:+.1f}", signal],
            "Formula": [
                f"{away} TC + {home} TC",
                f"{tc_combined} × {LINE_FACTOR} = {line}",
                f"{tc_combined} − {line}",
                "OVER if edge > 2 | UNDER if edge < -2",
            ]
        }
        st.dataframe(pd.DataFrame(derivation_data), use_container_width=True, hide_index=True)

        # Market comparison
        with st.expander("📈 Market Comparison"):
            mkt = st.number_input("Market Total", value=float(market_total), step=0.5, key="mkt_total")
            diff = round(tc_combined - mkt, 1)
            pct = (diff / mkt) * 100
            result = "OVER" if diff > 0 else "UNDER"
            st.markdown(f"""
            | Metric | Value |
            |---|---|
            | TC Combined | {tc_combined} |
            | Market Total | {mkt} |
            | Diff | {diff:+.1f} ({pct:+.2f}%) |
            | Result | **{result}** |
            """)
    else:
        st.info("Configure engine to load projections")

# ── Tab 2: Backtest ──────────────────────────────────────────────────────
with tab2:
    st.subheader("TC Backtest Results")
    suite = NBA_BACKTEST if sport == "NBA" else WNBA_BACKTEST
    roster = NBA_ROSTERS if sport == "NBA" else WNBA_ROSTERS

    results = []
    for g_data in suite:
        away_p = roster.get(g_data["away"], [])
        home_p = roster.get(g_data["home"], [])
        tc_a = sum(p.tc(p.pts) for p in away_p if p.status != "OUT")
        tc_h = sum(p.tc(p.pts) for p in home_p if p.status != "OUT")
        tc = round(tc_a + tc_h, 1)
        line = round(tc * LINE_FACTOR)
        actual = g_data["actual_combined"]
        diff = round(tc - actual, 1)
        edge = round(tc - line, 1)
        hit = (diff > 0 and actual > tc) or (diff < 0 and actual < tc)
        pct = (diff / actual) * 100
        results.append({
            "Game": f"{g_data['away']}@{g_data['home']}",
            "Date": g_data["date"],
            "TC": tc,
            "LINE": line,
            "Actual": actual,
            "Diff": f"{diff:+.1f}",
            "Diff %": f"{pct:+.1f}%",
            "Result": "OVER" if diff > 0 else "UNDER",
            "Hit": "✅" if hit else "❌",
        })

    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Summary stats
    n = len(results)
    hits = sum(1 for r in results if r["Hit"] == "✅")
    avg_diff = sum(float(r["Diff"]) for r in results) / n
    col1, col2, col3 = st.columns(3)
    col1.metric("Hit Rate", f"{hits}/{n}", f"{hits/n*100:.0f}%")
    col2.metric("Avg Diff (TC-Actual)", f"{avg_diff:+.1f}", "TC bias")
    col3.metric("Backtest Period", f"{suite[0]['date']}", f"to {suite[-1]['date']}")

    st.markdown("---")
    st.subheader("TC Formula Audit")
    audit_data = {
        "Factor": ["CONS", "Q_MULT", "LINE_FACTOR", "MIN_EDGE"],
        "Value": [CONS, Q_MULT, LINE_FACTOR, MIN_EDGE],
        "Description": [
            "Conservative multiplier for ACTIVE players",
            "Questionable multiplier (TC-downgraded from 0.65)",
            "LINE = TC_combined × 0.88",
            "Minimum edge to qualify a pick",
        ]
    }
    st.dataframe(pd.DataFrame(audit_data), use_container_width=True, hide_index=True)

# ── Tab 3: Injury Report ─────────────────────────────────────────────────
with tab3:
    if g and show_injury:
        for team_obj, label in [(g.away, away), (g.home, home)]:
            injuries = [p for p in team_obj.players if p.status != "ACTIVE"]
            active = [p for p in team_obj.players if p.status == "ACTIVE"]
            st.subheader(f"{label} — {team_obj.name} ({len(active)} active)")

            if injuries:
                for p in injuries:
                    note = "❌ OUT" if p.status == "OUT" else "⚠️ QUESTIONABLE"
                    st.error(f"{p.name} ({p.pos}) — {note}")
            else:
                st.success(f"No injuries for {label}")

            rows = []
            for p in team_obj.roster():
                proj = p.proj()
                rows.append({
                    "Player": p.name,
                    "POS": p.pos,
                    "TC PTS": proj["TC_PTS"],
                    "Status": p.status,
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown("---")
    else:
        st.info("Toggle 'Show Injury Report' in sidebar")

# ── Tab 4: Settings ──────────────────────────────────────────────────────
with tab4:
    st.subheader("TC Settings")
    st.markdown(f"""
    | Parameter | Current | Description |
    |---|---|---|
    | CONS | {CONS} | Conservative multiplier |
    | Q_MULT | {Q_MULT} | Questionable multiplier |
    | LINE_FACTOR | {LINE_FACTOR} | LINE = TC × {LINE_FACTOR} |
    | MIN_EDGE | {MIN_EDGE} | Min edge for signal |
    """)
    st.info("Settings are read from master_tc.py. Edit the source to recalibrate.")

    st.markdown("---")
    st.subheader("Roster Status")
    if g:
        for team_obj, label in [(g.away, away), (g.home, home)]:
            active = [p for p in team_obj.players if p.status == "ACTIVE"]
            q = [p for p in team_obj.players if p.status == "Q"]
            out = [p for p in team_obj.players if p.status == "OUT"]
            st.markdown(f"**{label}**: {len(active)} active | {len(q)} Q | {len(out)} OUT")
    st.markdown("---")
    st.caption("Sports TC v4.0 | Powered by Zo Computer")