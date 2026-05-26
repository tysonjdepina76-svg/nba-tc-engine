#!/usr/bin/env python3
"""
Sports TC Streamlit Dashboard
Full roster TC projections for NBA + WNBA Conference Finals.
TC applies ONLY to player props (PTS×0.85, REB×0.80, AST×0.75, TPM×0.70).
Team/game totals are RAW projections only.
"""

import json, os, sys, subprocess
import streamlit as st

st.set_page_config(page_title="Sports TC Dashboard", layout="wide")

# ── Paths ───────────────────────────────────────────────────────────────────
NBA_LIVE_DIR   = "/home/workspace/sports-tc/live_nba"
MONITOR_DIR    = "/home/workspace/sports-tc/monitor"
NBA_BACKTEST  = "/home/workspace/wnba_rosters/NBA_BACKTEST_ROSTERS.json"
WNBA_BACKTEST = "/home/workspace/wnba_rosters/WNBA_BACKTEST_ROSTERS.json"

TC_FACTORS  = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
Q_FACTOR    = 0.55
OUT_FACTOR = 0.0
LINE_FACTOR = 0.88

# ── Roster Loader ────────────────────────────────────────────────────────────
def load_live_roster(team_code, sport="NBA"):
    live_file = f"{NBA_LIVE_DIR}/conference_finals_live.json"
    if os.path.exists(live_file):
        with open(live_file) as f:
            data = json.load(f)
        teams_data = data.get("teams", {})
        if team_code in teams_data:
            raw = teams_data[team_code]
            if isinstance(raw, list):
                starters = [p for p in raw if p.get("role") == "STARTER"]
                bench = [p for p in raw if p.get("role") == "BENCH"]
                return {"starters": starters, "bench": bench}
            if isinstance(raw, dict):
                return raw

    bt_file = NBA_BACKTEST if sport == "NBA" else WNBA_BACKTEST
    if os.path.exists(bt_file):
        with open(bt_file) as f:
            bt = json.load(f)
        teams = bt.get("teams", {})
        if team_code in teams:
            t = teams[team_code]
            if isinstance(t, dict):
                return {"starters": t.get("starters", []), "bench": t.get("bench", [])}
            if isinstance(t, list):
                return {
                    "starters": [p for p in t if p.get("role") == "STARTER"],
                    "bench": [p for p in t if p.get("role") == "BENCH"]
                }
    return None


def calc_tc(player):
    s = player.get("status", "ACTIVE")
    if s == "OUT":
        mp = mr = ma = mt = OUT_FACTOR
    elif s == "Q":
        mp = mr = ma = mt = Q_FACTOR
    else:
        mp = mr = ma = mt = 1.0

    tc_pts = round(player.get("ppg", 0) * TC_FACTORS["pts"] * mp, 1)
    tc_reb = round(player.get("rpg", 0) * TC_FACTORS["reb"] * mr, 1)
    tc_ast = round(player.get("apg", 0) * TC_FACTORS["ast"] * ma, 1)
    tc_tpm = round(player.get("tpm", 0) * TC_FACTORS["tpm"] * mt, 1)
    tc_line = round(tc_pts * LINE_FACTOR)
    edge = round(player.get("ppg", 0) - tc_line, 1)
    return {"tc_pts": tc_pts, "tc_reb": tc_reb, "tc_ast": tc_ast, "tc_tpm": tc_tpm,
            "tc_line": tc_line, "edge": edge}


def status_icon(s):
    return "✅" if s == "ACTIVE" else "⚠️" if s in ("Q", "QUESTIONABLE") else "❌"


# ── Streamlit UI ─────────────────────────────────────────────────────────────
st.title("🏀 Sports TC — Full Roster Projections")
st.markdown("""
**TC Rules:** TC applies ONLY to player props (PTS×0.85, REB×0.80, AST×0.75, TPM×0.70, Q×0.55, OUT=0).  
**Team/game totals are RAW projections only — no TC line, no TC edge.**
""")

st.divider()

# Game selector
col1, col2 = st.columns(2)
with col1:
    sport = st.selectbox("Sport", ["NBA", "WNBA"], index=0)
with col2:
    game_option = st.selectbox(
        "Game",
        ["SAS @ OKC (WCF G3)", "CLE @ NYK (ECF G3)", "Custom..."],
        index=0
    )

custom_game = ""
if game_option == "Custom...":
    custom_game = st.text_input("Enter game (e.g. SAS @ OKC)", value="SAS @ OKC")
    game_choice = custom_game
else:
    game_choice = game_option.split(" (")[0]

parts = game_choice.upper().replace("@", " @ ").split(" @ ")
if len(parts) != 2:
    st.error("Use format: AWAY @ HOME")
    st.stop()

away_code, home_code = parts[0].strip(), parts[1].strip()

# Load rosters
away_roster = load_live_roster(away_code, sport)
home_roster = load_live_roster(home_code, sport)

if not away_roster or not home_roster:
    st.error(f"Missing roster for {away_code} or {home_code}")
    st.stop()

# ── RAW Game Totals (no TC) ─────────────────────────────────────────────────
away_players = away_roster.get("starters", []) + away_roster.get("bench", [])
home_players = home_roster.get("starters", []) + home_roster.get("bench", [])

away_raw_pts = sum(p.get("ppg", 0) for p in away_players)
home_raw_pts = sum(p.get("ppg", 0) for p in home_players)
est_total = round((away_raw_pts + home_raw_pts) * 1.18)

st.subheader(f"{away_code} @ {home_code} — Raw Game Totals (no TC)")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric(f"{away_code} RAW PTS", f"{away_raw_pts:.1f}")
with col_b:
    st.metric(f"{home_code} RAW PTS", f"{home_raw_pts:.1f}")
with col_c:
    st.metric("Est Game Total", f"~{est_total}", help="Raw combined × 1.18 playoff adj")

# ── Team TC Player Prop Totals ───────────────────────────────────────────────
away_tc = {k: sum(calc_tc(p)[f"tc_{k}"] for p in away_players) for k in ["pts","reb","ast","tpm"]}
home_tc = {k: sum(calc_tc(p)[f"tc_{k}"] for p in home_players) for k in ["pts","reb","ast","tpm"]}

st.subheader("TC Player Props — Team Totals")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(f"{away_code} TC PTS", f"{away_tc['pts']:.1f}")
    st.metric(f"{home_code} TC PTS", f"{home_tc['pts']:.1f}")
with col2:
    st.metric(f"{away_code} TC REB", f"{away_tc['reb']:.1f}")
    st.metric(f"{home_code} TC REB", f"{home_tc['reb']:.1f}")
with col3:
    st.metric(f"{away_code} TC AST", f"{away_tc['ast']:.1f}")
    st.metric(f"{home_code} TC AST", f"{home_tc['ast']:.1f}")
with col4:
    st.metric(f"{away_code} TC 3PM", f"{away_tc['tpm']:.1f}")
    st.metric(f"{home_code} TC 3PM", f"{home_tc['tpm']:.1f}")

st.divider()

# ── Full Roster Tables ───────────────────────────────────────────────────────
def render_roster_table(team_code, players, title=""):
    st.subheader(f"👥 {title or team_code} — Full Roster ({len(players)} players)")

    tc_map = {p["name"]: calc_tc(p) for p in players}

    # Tabs: Starters | Bench | All
    tabs = st.tabs(["Starters (5)", "Bench", "All Players"])
    for tab_idx, (label, filter_fn) in enumerate([
        ("Starters", lambda p: p.get("role") == "STARTER"),
        ("Bench", lambda p: p.get("role") == "BENCH"),
        ("All", lambda p: True),
    ]):
        with tabs[tab_idx]:
            filtered = [p for p in players if filter_fn(p)]
            rows = []
            for p in filtered:
                tc = tc_map[p["name"]]
                edge_sign = "+" if tc["edge"] >= 0 else ""
                rows.append({
                    "Role": "S" if p.get("role") == "STARTER" else "B",
                    "Player": p["name"],
                    "POS": p.get("position", "?"),
                    "TC PTS": tc["tc_pts"],
                    "TC REB": tc["tc_reb"],
                    "TC AST": tc["tc_ast"],
                    "TC 3PM": tc["tc_tpm"],
                    "TC LINE": tc["tc_line"],
                    "EDGE": f"{edge_sign}{tc['edge']:.1f}",
                    "Status": p.get("status", "ACTIVE"),
                    "Icon": status_icon(p.get("status", "ACTIVE")),
                })

            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)

            team_tc_pts = sum(tc_map[p["name"]]["tc_pts"] for p in filtered)
            team_raw_pts = sum(p.get("ppg", 0) for p in filtered)
            st.caption(f"Team TC={team_tc_pts:.1f} pts | RAW={team_raw_pts:.1f} pts")


render_roster_table(away_code, away_players, f"{away_code} (Away)")
render_roster_table(home_code, home_players, f"{home_code} (Home)")

# ── Injury Alert ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("⚕️ Injury Status")
all_players = away_players + home_players
injured = [p for p in all_players if p.get("status") != "ACTIVE"]
if injured:
    for p in injured:
        icon = status_icon(p.get("status", "ACTIVE"))
        st.warning(f"{icon} **{p['name']}** ({p.get('position','?')}) — {p.get('status','?')} | TC PTS: {calc_tc(p)['tc_pts']:.1f}")
else:
    st.success("✅ No injuries — all players ACTIVE")

# ── Prop Candidate Watchlist ─────────────────────────────────────────────────
st.divider()
st.subheader("🎯 Prop Candidate Watchlist (gap ≥ 3.0)")
candidates = []
for p in all_players:
    if p.get("status") == "OUT" or p.get("ppg", 0) < 5:
        continue
    tc = calc_tc(p)
    if tc["edge"] >= 3.0:
        candidates.append({
            "Player": p["name"],
            "Team": away_code if p in away_players else home_code,
            "Role": "S" if p.get("role") == "STARTER" else "B",
            "TC PTS": tc["tc_pts"],
            "TC LINE": tc["tc_line"],
            "EDGE": tc["edge"],
            "Status": p.get("status", "ACTIVE"),
        })

candidates.sort(key=lambda x: x["EDGE"], reverse=True)
if candidates:
    st.dataframe(candidates, use_container_width=True, hide_index=True)
else:
    st.info("No prop candidates meet the gap threshold (≥ 3.0)")

st.caption("⚠️ Use prop candidates as a watchlist only. Always check sportsbook lines before betting.")