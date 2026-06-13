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
    # Sport-specific stat keys
    stat_keys = SPORT_STAT_KEYS.get(sport, {"pts":"ppg","reb":"rpg","ast":"apg","3pm":"tpm","stl":"spg","blk":"bpg"})
    pts_k, reb_k, ast_k, tpm_k, stl_k, blk_k = stat_keys["pts"], stat_keys["reb"], stat_keys["ast"], stat_keys["3pm"], stat_keys["stl"], stat_keys["blk"]
    tc_pts = round(player.get(pts_k, 0) * TC_FACTORS[u["pts"]] * mp, 1)
    tc_reb = round(player.get(reb_k, 0) * TC_FACTORS[u["reb"]] * mr, 1)
    tc_ast = round(player.get(ast_k, 0) * TC_FACTORS[u["ast"]] * ma, 1)
    tc_tpm = round(player.get(tpm_k, 0) * TC_FACTORS[u["3pm"]] * mt, 1)
    tc_line = round(tc_pts * LINE_FACTOR)
    edge = round(player.get(pts_k, 0) - tc_line, 1)
    return {"tc_pts": tc_pts, "tc_reb": tc_reb, "tc_ast": tc_ast, "tc_tpm": tc_tpm,
            "tc_line": tc_line, "edge": edge, "pts_k": pts_k, "reb_k": reb_k, "ast_k": ast_k, "tpm_k": tpm_k, "stl_k": stl_k, "blk_k": blk_k}


def status_icon(s):
    return "✅" if s == "ACTIVE" else "⚠️" if s in ("Q", "QUESTIONABLE") else "❌"


# ── Sport-aware units ─────────────────────────────────────────────
SPORT_UNITS: dict = {
    "NBA":    {"pts":"PTS","reb":"REB","ast":"AST","3pm":"3PM","stl":"STL","blk":"BLK","points_unit":"pts","total_unit":"pts","total_label":"Game Total","period_word":"quarters","period_emoji":"🏀","score_thresh":9.3},
    "WNBA":   {"pts":"PTS","reb":"REB","ast":"AST","3pm":"3PM","stl":"STL","blk":"BLK","points_unit":"pts","total_unit":"pts","total_label":"Game Total","period_word":"quarters","period_emoji":"🏀","score_thresh":14.0},
    "MLB":    {"pts":"R",  "reb":"H",  "ast":"RBI","3pm":"HR", "stl":"SB", "blk":"TB", "points_unit":"runs","total_unit":"runs","total_label":"Game Total (runs)","period_word":"innings","period_emoji":"⚾","score_thresh":4.5},
    "NHL":    {"pts":"G",  "reb":"A",  "ast":"SOG","3pm":"BLK","stl":"HITS","blk":"SV", "points_unit":"goals","total_unit":"goals","total_label":"Game Total (goals)","period_word":"periods","period_emoji":"🏒","score_thresh":3.0},
    "SOCCER": {"pts":"G",  "reb":"A",  "ast":"SOT","3pm":"SOG","stl":"TKL","blk":"SV", "points_unit":"goals","total_unit":"goals","total_label":"Match Total (goals)","period_word":"halves","period_emoji":"⚽","score_thresh":2.5},
}
u = SPORT_UNITS.get(sport, SPORT_UNITS["NBA"])
TC_FACTORS = {u["pts"]:0.85, u["reb"]:0.80, u["ast"]:0.75, u["3pm"]:0.70, u["stl"]:0.80, u["blk"]:0.75}

# ── Streamlit UI ─────────────────────────────────────────────────────────────
st.title(f"{u['period_emoji']} {sport} TC — Full Roster Projections")
st.markdown(f"""
**TC Rules:** TC applies ONLY to player props ({u['pts']}×0.85, {u['reb']}×0.80, {u['ast']}×0.75, {u['3pm']}×0.70, Q×0.55, OUT=0).  
**Team/{u['total_label'].lower()} are RAW projections only — no TC line, no TC edge.**  
**Game structure:** {sport} = {u['period_word']}. Stat units are sport-specific (NBA/WNBA=points/rebs/asts, MLB=runs/hits/RBI, NHL=goals/assists/shots, SOCCER=goals/assists/shots).
""")

st.divider()

# Game selector
col1, col2 = st.columns(2)
with col1:
    sport = st.selectbox("Sport", ["NBA", "WNBA", "NHL", "MLB", "SOCCER"], index=0)
with col2:
    if sport in ("NBA", "WNBA"):
        game_option = st.selectbox(
            "Game",
            ["SAS @ OKC (WCF G3)", "CLE @ NYK (ECF G3)", "Custom..."],
            index=0
        )
    elif sport == "NHL":
        game_option = st.selectbox(
            "Game",
            ["BOS @ NYR", "EDM @ FLA", "TOR @ TBL", "Custom..."],
            index=0
        )
    elif sport == "MLB":
        game_option = st.selectbox(
            "Game",
            ["NYY @ BOS", "LAD @ SF", "HOU @ SEA", "Custom..."],
            index=0
        )
    else:  # SOCCER
        game_option = st.selectbox(
            "Game",
            ["BRA @ ARG", "FRA @ ENG", "GER @ ESP", "Custom..."],
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

# ── Non-basketball sports: call /api/tc for DK lines + ESPN scoreboard ──
if sport in ("NHL", "MLB", "SOCCER"):
    st.subheader(f"🏒 {sport} {away_code} @ {home_code} — DK Live Lines + ESPN Scoreboard")
    try:
        import requests as _rq
        api_url = f"https://true.zo.space/api/tc?sport={sport}&away={away_code}&home={home_code}"
        r = _rq.get(api_url, timeout=20, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
        o = data.get("odds", {})
        cols = st.columns(4)
        with cols[0]:
            st.metric("DK Total", o.get("total") or "—")
        with cols[1]:
            st.metric("Away Spread", o.get("away_spread") if o.get("away_spread") is not None else "—")
        with cols[2]:
            st.metric("Home Spread", o.get("home_spread") if o.get("home_spread") is not None else "—")
        with cols[3]:
            st.metric("Source", "DK ✓" if "DraftKings" in str(o.get("ml_source","")) else "ESPN fallback")
        st.markdown(f"**ML:** {away_code} **{o.get('away_ml') or '—'}** / {home_code} **{o.get('home_ml') or '—'}**")
        st.caption(f"Scoreboard: {data.get('source','')} · Status: {data.get('signal','')}")
        with st.expander("Raw API response"):
            st.json(data)
    except Exception as e:
        st.error(f"API error: {e}")
    st.stop()

# Load rosters
away_roster = load_live_roster(away_code, sport)
home_roster = load_live_roster(home_code, sport)

if not away_roster or not home_roster:
    st.error(f"Missing roster for {away_code} or {home_code}")
    st.stop()

# ── RAW Game Totals (no TC) ─────────────────────────────────────────────────
sk = SPORT_STAT_KEYS[sport]
away_players = away_roster.get("starters", []) + away_roster.get("bench", [])
home_players = home_roster.get("starters", []) + home_roster.get("bench", [])

away_raw = sum(p.get(sk["pts"], 0) for p in away_players)
home_raw = sum(p.get(sk["pts"], 0) for p in home_players)
est_total = round((away_raw + home_raw) * 1.18)

st.subheader(f"{away_code} @ {home_code} — Raw {u['total_label']} (no TC)")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric(f"{away_code} RAW {u['pts']}", f"{away_raw:.1f}")
with col_b:
    st.metric(f"{home_code} RAW {u['pts']}", f"{home_raw:.1f}")
with col_c:
    st.metric(f"Est {u['total_label']}", f"~{est_total}", help=f"Raw combined × 1.18 {u['period_word']} adj")

# ── Team TC Player Prop Totals ─────────────────────
tc_keys = ["pts","reb","ast","3pm"]
away_tc = {k: sum(calc_tc(p)[f"tc_{k}"] for p in away_players) for k in tc_keys}
home_tc = {k: sum(calc_tc(p)[f"tc_{k}"] for p in home_players) for k in tc_keys}

st.subheader(f"TC Player Props — Team Totals ({sport} units)")
stat_lab = [u["pts"], u["reb"], u["ast"], u["3pm"]]
cols = st.columns(4)
for i, (k, lab) in enumerate(zip(tc_keys, stat_lab)):
    with cols[i]:
        st.metric(f"{away_code} TC {lab}", f"{away_tc[k]:.1f}")
        st.metric(f"{home_code} TC {lab}", f"{home_tc[k]:.1f}")

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
                    f"TC {u['pts']}": tc["tc_pts"],
                    f"TC {u['reb']}": tc["tc_reb"],
                    f"TC {u['ast']}": tc["tc_ast"],
                    f"TC {u['3pm']}": tc["tc_tpm"],
                    "TC LINE": tc["tc_line"],
                    "EDGE": f"{edge_sign}{tc['edge']:.1f}",
                    "Status": p.get("status", "ACTIVE"),
                    "Icon": status_icon(p.get("status", "ACTIVE")),
                })

            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)

            team_tc_pts = sum(tc_map[p["name"]]["tc_pts"] for p in filtered)
            team_raw_pts = sum(p.get(sk["pts"], 0) for p in filtered)
            st.caption(f"Team TC={team_tc_pts:.1f} {u['pts'].lower()} | RAW={team_raw_pts:.1f} {u['pts'].lower()}")


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
        st.warning(f"{icon} **{p['name']}** ({p.get('position','?')}) — {p.get('status','?')} | TC {u['pts']}: {calc_tc(p)['tc_pts']:.1f}")
else:
    st.success(f"✅ No injuries — all players ACTIVE")

# ── Prop Candidate Watchlist ─────────────────────────────────────────────────
st.divider()
st.subheader("🎯 Prop Candidate Watchlist (gap ≥ 3.0)")
candidates = []
for p in all_players:
    if p.get("status") == "OUT" or p.get(sk["pts"], 0) < 5:
        continue
    tc = calc_tc(p)
    if tc["edge"] >= 3.0:
        candidates.append({
            "Player": p["name"],
            "Team": away_code if p in away_players else home_code,
            "Role": "S" if p.get("role") == "STARTER" else "B",
            f"TC {u['pts']}": tc["tc_pts"],
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