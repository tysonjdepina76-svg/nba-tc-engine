#!/usr/bin/env python3
"""
OKC @ SAS — West Finals TC Dashboard
=====================================
Streamlit dashboard for OKC vs SAS TC projections.

Features:
  • DK Sportsbook lines panel  (spread · ML · game total)
  • Team/bench metric cards
  • TC projections table  (starters tab · bench tab)
  • TC stat-leader boxes — per-team PTS / REB / AST / 3PM leader overlay
  • Edge watchlist table
  • Works for every sport/team by swapping in the correct roster dict

TC Formula:
  TC  = PTS×0.85 + REB×0.12 + AST×0.10 + TPM×0.08
  GAP = 9.3  |  LINE = (TC + GAP) × 0.88  |  EDGE = TC − LINE

DK Lines (hardcoded from DraftKings WCF Game 5 5/26/26):
  SAS −2.5 (−150)  |  OKC +2.5 (+130)  |  Total 218.5
  Series:  OKC −160  |  SAS +135

Run:
    cd tc-workspace/scripts
    streamlit run okc_scs_series_dashboard.py --server.port 8505
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
st.set_page_config(
    page_title="OKC @ SAS — TC Projections",
    layout="wide",
    page_icon="🏀",
)

# ── TC Weights ────────────────────────────────────────────────────────────
W_PTS = 0.85
W_REB = 0.12
W_AST = 0.10
W_TPM = 0.08
LINE_FACTOR = 0.88
HISTORICAL_GAP = 9.3

def _sf(status: str) -> float:
    s = (status or "ACTIVE").upper()
    if s in ("OUT", "DNP"):
        return 0.0
    if any(q in s for q in ("Q", "QUESTION", "DOUBTFUL", "GTD")):
        return 0.55
    return 1.0

def compute_tc(pts, reb, ast, tpm, status="ACTIVE"):
    sf = _sf(status)
    tc_pts = round(pts  * W_PTS * sf, 1)
    tc_reb = round(reb  * W_REB * sf, 1)
    tc_ast = round(ast  * W_AST * sf, 1)
    tc_tpm = round(tpm  * W_TPM * sf, 1)
    tc_tot = round(tc_pts + tc_reb + tc_ast + tc_tpm, 1)
    line   = int(round((tc_tot + HISTORICAL_GAP) * LINE_FACTOR))
    edge   = round(tc_tot - line, 1)
    return tc_pts, tc_reb, tc_ast, tc_tpm, tc_tot, line, edge

# ── Roster Data — sourced from BBR 2026 WCF per-game series averages ─────────────────
# OKC Thunder — 5-game WCF series per-game averages (bball-reference.com)
OKC_PLAYERS = [
    ("Shai Gilgeous-Alexander","PG","6-6", 26.2, 3.0, 9.8, 1.2, "ACTIVE","STARTER"),
    ("Alex Caruso",           "SG","6-5", 17.0, 2.8, 1.6, 3.6, "ACTIVE","STARTER"),
    ("Chet Holmgren",          "C", "7-1", 12.2, 7.0, 1.2, 0.4, "ACTIVE","STARTER"),
    ("Cason Wallace",          "SG","6-5",  8.6, 2.8, 2.6, 1.4, "ACTIVE","STARTER"),
    ("Isaiah Hartenstein",     "C", "7-0",  8.2, 9.0, 0.2, 0.0, "ACTIVE","STARTER"),
    ("Jalen Williams",         "SF","6-7",  15.0,4.0, 1.5, 0.5, "ACTIVE","STARTER"),  # 2 games
    ("Jaylin Williams",        "PF","6-10", 6.0, 1.0, 0.4, 0.2, "ACTIVE","BENCH"),
    ("Luguentz Dort",           "SG","6-5",  4.4, 1.4, 0.4, 0.0, "ACTIVE","BENCH"),
    ("Ajay Mitchell",          "SG","6-5",  5.3, 2.7, 2.0, 0.0, "OUT",  "BENCH"),    # 3 games
    ("Isaiah Joe",             "SG","6-5",  2.8, 0.8, 0.6, 0.2, "ACTIVE","BENCH"),
    ("Aaron Wiggins",         "SG","6-5",  0.8, 0.0, 0.0, 0.0, "ACTIVE","BENCH"),
    ("Nikola Topić",            "PG","6-6",  0.7, 0.7, 0.0, 0.0, "ACTIVE","BENCH"),  # 3 games
]

# SAS Spurs — 5-game WCF series per-game averages (bball-reference.com)
# De'Aaron Fox played G1–G3 then injured (Game 4+5); Devin Vassell Q in series
SAS_PLAYERS = [
    ("Victor Wembanyama",    "PF","7-4", 28.2,11.8,3.6,1.8, "ACTIVE","STARTER"),
    ("Stephon Castle",       "PG","6-5", 18.6, 4.8,7.6,1.4, "ACTIVE","STARTER"),
    ("De'Aaron Fox",         "PG","6-4", 17.0, 4.0,5.7,0.7, "Q",     "STARTER"),  # 3 games
    ("Devin Vassell",        "SF","6-10",14.8, 5.4,2.4,3.2, "ACTIVE","STARTER"),
    ("Dylan Harper",         "SG","6-6",  10.8,5.4,3.2,0.6, "ACTIVE","STARTER"),  # 2 games
    ("Julian Champagnie",    "SF","6-8",  10.6, 6.2,1.6,2.0, "ACTIVE","STARTER"),
    ("Keldon Johnson",      "SG","6-6",  9.8, 2.8,0.6,1.4, "ACTIVE","STARTER"),
    ("Jeremy Sochan",        "PF","6-9",  10.8, 5.3,3.4,0.9, "ACTIVE","STARTER"),
    ("Zach Collins",          "C", "7-0",  7.6, 4.8,2.1,0.4, "ACTIVE","BENCH"),
    ("Tre Jones",            "PG","6-5",  8.2, 2.9,4.1,0.8, "ACTIVE","BENCH"),
    ("Malaki Branham",        "SG","6-4",  5.0, 2.5,2.3,1.5, "ACTIVE","BENCH"),   # 4 games
    ("Mamadou Ndiaye",       "PF","6-9",  3.0, 2.3,0.3,0.0, "ACTIVE","BENCH"),   # 3 games
    ("Cedi Osman",           "SF","6-8",  4.1, 1.9,1.5,1.1, "ACTIVE","BENCH"),    # 4 games
]

# ── DK Sportsbook Lines ───────────────────────────────────────────────────────
# Hardcoded from DraftKings WCF Game 5 (5/26/26) + Series odds
# Update DK_LINES dict manually for each game
DK_LINES = {
    "game_spread":      {"okc": "+2.5", "sas": "−2.5"},
    "game_spread_odds": {"okc": "+130",  "sas": "−150"},
    "game_ml":          {"okc": "+130",  "sas": "−150"},
    "game_total":       "218.5",
    "series_okc":       "−160",
    "series_sas":       "+135",
}

# ── Compute all TC rows ─────────────────────────────────────────────────────────
def compute_all(roster):
    rows = []
    for name, pos, ht, pts, reb, ast, tpm, status, role in roster:
        tc_pts, tc_reb, tc_ast, tc_tpm, tc_tot, line, edge = compute_tc(pts, reb, ast, tpm, status)
        sf = _sf(status)
        rows.append({
            "Player": name, "POS": pos, "HT": ht, "Role": role,
            "Status": status, "SF": sf,
            "PTS": pts, "REB": reb, "AST": ast, "3PM": tpm,
            "TC_PTS": tc_pts, "TC_REB": tc_reb, "TC_AST": tc_ast, "TC_3PM": tc_tpm,
            "TC_TOT": tc_tot, "LINE": line, "EDGE": edge,
        })
    return rows

okc_rows = compute_all(OKC_PLAYERS)
sas_rows = compute_all(SAS_PLAYERS)

okc_starters = [r for r in okc_rows if r["Role"] == "STARTER"]
okc_bench    = [r for r in okc_rows if r["Role"] == "BENCH"]
sas_starters = [r for r in sas_rows if r["Role"] == "STARTER"]
sas_bench    = [r for r in sas_rows if r["Role"] == "BENCH"]

okc_tc_total    = round(sum(r["TC_TOT"] for r in okc_rows), 1)
sas_tc_total    = round(sum(r["TC_TOT"] for r in sas_rows), 1)
okc_starters_tc = round(sum(r["TC_TOT"] for r in okc_starters), 1)
sas_starters_tc = round(sum(r["TC_TOT"] for r in sas_starters), 1)
okc_bench_tc    = round(sum(r["TC_TOT"] for r in okc_bench), 1)
sas_bench_tc    = round(sum(r["TC_TOT"] for r in sas_bench), 1)
tc_combined     = round(okc_tc_total + sas_tc_total, 1)
est_game_total  = int(round((tc_combined + HISTORICAL_GAP) * LINE_FACTOR))

# ── TC Stat Leaders ─────────────────────────────────────────────────────────────
def get_tc_leaders(rows):
    return {
        "TC_PTS_leader": max(rows, key=lambda r: r["TC_PTS"])["Player"],
        "TC_REB_leader": max(rows, key=lambda r: r["TC_REB"])["Player"],
        "TC_AST_leader": max(rows, key=lambda r: r["TC_AST"])["Player"],
        "TC_3PM_leader": max(rows, key=lambda r: r["TC_3PM"])["Player"],
        "raw_PTS_leader": max(rows, key=lambda r: r["PTS"])["Player"],
        "raw_REB_leader": max(rows, key=lambda r: r["REB"])["Player"],
        "raw_AST_leader": max(rows, key=lambda r: r["AST"])["Player"],
        "raw_3PM_leader": max(rows, key=lambda r: r["3PM"])["Player"],
    }

okc_leaders = get_tc_leaders(okc_rows)
sas_leaders = get_tc_leaders(sas_rows)

# ── Stat Leader Box HTML ───────────────────────────────────────────────────────
def stat_box(label, value, sub, color="#0d1b2a"):
    return f"""
    <div style="background:{color};border-radius:8px;padding:10px 14px;text-align:center;min-width:80px;flex:1;">
        <div style="font-size:0.65rem;color:#aaa;text-transform:uppercase;letter-spacing:1px;">{label}</div>
        <div style="font-size:1.0rem;font-weight:700;color:#e0e0e0;margin-top:2px;">{value}</div>
        <div style="font-size:0.6rem;color:#888;margin-top:1px;">{sub}</div>
    </div>"""

def team_stat_panel(leaders, tc_color):
    return "".join([
        stat_box("TC Pts ★", leaders["TC_PTS_leader"], "Points Leader", tc_color),
        stat_box("TC Reb ★", leaders["TC_REB_leader"], "Rebounds Leader", tc_color),
        stat_box("TC Ast ★", leaders["TC_AST_leader"], "Assists Leader", tc_color),
        stat_box("TC 3PM ★", leaders["TC_3PM_leader"], "3Pt Made Leader", tc_color),
    ])

okc_stat_panel = team_stat_panel(okc_leaders, "#1b3a4b")
sas_stat_panel = team_stat_panel(sas_leaders, "#3b1b1b")

# ── Streamlit UI ─────────────────────────────────────────────────────────────────
st.title("🏀 OKC @ SAS — TC Projections Dashboard")
st.caption(
    "TC = PTS×0.85 + REB×0.12 + AST×0.10 + TPM×0.08  |  "
    "GAP=9.3  |  LINE=(TC+GAP)×0.88  |  Source: BBR 2026 WCF series averages"
)

# ── DK Sportsbook Lines Panel ───────────────────────────────────────────────────
st.markdown("## 📊 DK Sportsbook Lines")
c = st.columns(5)

c[0].markdown(f"""
<div style="background:#1a1a2e;border:1.5px solid #4a90d9;border-radius:12px;padding:16px;text-align:center;">
    <div style="color:#aaa;font-size:0.7rem;text-transform:uppercase">🏀 OKC Thunder</div>
    <div style="color:#888;font-size:0.75rem;margin-top:6px;">Moneyline</div>
    <div style="font-size:1.8rem;font-weight:800;color:#e0e0e0;margin-top:2px;">{DK_LINES['game_ml']['okc']}</div>
    <div style="color:#aaa;font-size:0.7rem;margin-top:6px;">Spread {DK_LINES['game_spread']['okc']}</div>
    <div style="color:#4a90d9;font-size:0.9rem;font-weight:600;">{DK_LINES['game_spread_odds']['okc']}</div>
</div>""", unsafe_allow_html=True)

c[1].markdown(f"""
<div style="background:#0d1117;border:1.5px solid #aaa;border-radius:12px;padding:16px;text-align:center;">
    <div style="color:#888;font-size:0.7rem;text-transform:uppercase">Game Total</div>
    <div style="font-size:2.2rem;font-weight:800;color:#e0e0e0;margin-top:4px;">{DK_LINES['game_total']}</div>
    <div style="color:#888;font-size:0.7rem;margin-top:4px;">O/U {DK_LINES['game_total']}</div>
</div>""", unsafe_allow_html=True)

c[2].markdown(f"""
<div style="background:#1a1a2e;border:1.5px solid #d94a4a;border-radius:12px;padding:16px;text-align:center;">
    <div style="color:#aaa;font-size:0.7rem;text-transform:uppercase">🏀 SAS Spurs</div>
    <div style="color:#888;font-size:0.75rem;margin-top:6px;">Moneyline</div>
    <div style="font-size:1.8rem;font-weight:800;color:#e0e0e0;margin-top:2px;">{DK_LINES['game_ml']['sas']}</div>
    <div style="color:#aaa;font-size:0.7rem;margin-top:6px;">Spread {DK_LINES['game_spread']['sas']}</div>
    <div style="color:#d94a4a;font-size:0.9rem;font-weight:600;">{DK_LINES['game_spread_odds']['sas']}</div>
</div>""", unsafe_allow_html=True)

c[3].markdown(f"""
<div style="background:#0d1117;border:1.5px solid #aaa;border-radius:12px;padding:16px;text-align:center;">
    <div style="color:#888;font-size:0.7rem;text-transform:uppercase">Series Odds</div>
    <div style="font-size:0.8rem;color:#e0e0e0;margin-top:8px;">OKC {DK_LINES['series_okc']}</div>
    <div style="font-size:0.8rem;color:#e0e0e0;margin-top:2px;">SAS {DK_LINES['series_sas']}</div>
    <div style="color:#888;font-size:0.65rem;margin-top:8px;">Best of 7 — WCF</div>
</div>""", unsafe_allow_html=True)

c[4].markdown(f"""
<div style="background:#0d1117;border:1.5px solid #f0a500;border-radius:12px;padding:16px;text-align:center;">
    <div style="color:#888;font-size:0.7rem;text-transform:uppercase">TC Est. Total</div>
    <div style="font-size:2.2rem;font-weight:800;color:#f0a500;margin-top:4px;">{est_game_total}</div>
    <div style="color:#888;font-size:0.7rem;margin-top:4px;">TC Combined: {tc_combined}</div>
    <div style="color:#f0a500;font-size:0.7rem;margin-top:2px;">DK Total: {DK_LINES['game_total']}</div>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# ── TC Stat Leader Panel ───────────────────────────────────────────────────────
st.markdown("## ⭐ TC Stat Leaders — Per Team")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### OKC Thunder ★")
    st.markdown(f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>{okc_stat_panel}</div>",
                unsafe_allow_html=True)
with col_b:
    st.markdown("### SAS Spurs ★")
    st.markdown(f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>{sas_stat_panel}</div>",
                unsafe_allow_html=True)

st.markdown("---")

# ── Team Summary Metric Cards ───────────────────────────────────────────────────
st.markdown("## 📈 TC Team Summary")
m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
m1.metric("OKC TC Total",    f"{okc_tc_total:.1f}")
m2.metric("SAS TC Total",    f"{sas_tc_total:.1f}")
m3.metric("OKC Starters",   f"{okc_starters_tc:.1f}")
m4.metric("SAS Starters",   f"{sas_starters_tc:.1f}")
m5.metric("OKC Bench",      f"{okc_bench_tc:.1f}")
m6.metric("SAS Bench",      f"{sas_bench_tc:.1f}")
m7.metric("TC Combined",    f"{tc_combined:.1f}")
m8.metric("Est. Game Total", f"{est_game_total}")

st.markdown("---")

# ── TC Projection Tables ──────────────────────────────────────────────────────
st.markdown("## 🎯 TC Projections — Player Tables")
tab_okc_s, tab_okc_b, tab_sas_s, tab_sas_b = st.tabs(
    ["OKC Starters", "OKC Bench", "SAS Starters", "SAS Bench"]
)
COLS = ["Player","POS","HT","Status","TC_PTS","TC_REB","TC_AST","TC_3PM","TC_TOT","LINE","EDGE"]

def render_tab(rows):
    st.dataframe(
        [{c: r[c] for c in COLS} for r in rows],
        use_container_width=True,
        hide_index=True,
    )

with tab_okc_s: render_tab(okc_starters)
with tab_okc_b: render_tab(okc_bench)
with tab_sas_s: render_tab(sas_starters)
with tab_sas_b: render_tab(sas_bench)

st.markdown("---")

# ── Edge Watchlist ─────────────────────────────────────────────────────────────
st.markdown("## ⚠️ TC Edge Watchlist (EDGE ≥ 3.0  |  TC_TOT ≥ 8.0)")
all_rows = okc_rows + sas_rows
candidates = sorted(
    [r for r in all_rows if r["EDGE"] >= 3.0 and r["TC_TOT"] >= 8.0 and r["Status"] != "OUT"],
    key=lambda r: r["EDGE"],
    reverse=True,
)

# Build list of dicts first — then pass to st.dataframe
watchlist_rows = []
for r in candidates:
    watchlist_rows.append({
        "Player": r["Player"],
        "Team":   "OKC",
        "Role":   r["Role"],
        "TC_TOT": r["TC_TOT"],
        "LINE":   r["LINE"],
        "EDGE":   r["EDGE"],
        "Status": r["Status"],
    })

if watchlist_rows:
    st.dataframe(watchlist_rows, use_container_width=True, hide_index=True)
else:
    st.info("No props with EDGE ≥ 3.0 and TC_TOT ≥ 8.0 in current slate.")

st.caption("⚠️ Watchlist only — always verify live DK lines before betting.")
