# Sports TC — Streamlit Dashboard v8.0
# NBA + WNBA Triple Conservative Engine with v8 Game Total Calibration
#
# Models:
#   TC Match  = player prop floors for PTS/REB/AST/3PM  (stat × CONS × status_factor + GAP)
#   v8 Game Total = raw pts × star_mult + bench_diff + home_court (separate from TC Match)
#
# Both models run independently. TC Match does NOT apply to game totals.

import streamlit as st, math, json, datetime

st.set_page_config(page_title="Sports TC v8 Dashboard", page_icon="🏀", layout="wide")

# ── TC Constants ───────────────────────────────────────────────────────────────
CONS = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
LINE_FACTOR, Q_FACTOR, MIN_EDGE = 0.88, 0.55, 1.0

# v8 Game Total constants
STAR_MULT = 0.90
ALL_NBA = {
    "Shai Gilgeous-Alexander": 0.90, "Nikola Jokic": 0.90,
    "Victor Wembanyama": 0.90, "Luka Doncic": 0.90,
    "Jayson Tatum": 0.90, "Giannis Antetokounmpo": 0.90,
    "Donovan Mitchell": 0.87, "Jalen Brunson": 0.87,
    "Anthony Edwards": 0.87, "Kevin Durant": 0.87,
    "Jaylen Brown": 0.87, "Karl-Anthony Towns": 0.87,
}
BENCH_THRESH, BENCH_BONUS, HOME_COURT = 15.0, 4.0, 2.0

SERIES_BENCH = {
    "OKC": {"G1": 33.0, "G2": 45.0, "G3": 76.0, "G4": 23.0},
    "SAS": {"G1": 25.0, "G2": 19.0, "G3": 19.0, "G4": 23.0},
    "CLE": {"G1": 28.0, "G2": 31.0, "G3": 19.0, "G4": 22.0},
    "BOS": {"G1": 35.0, "G2": 29.0, "G3": 38.0, "G4": 19.0},
}

# ── Helper Functions ──────────────────────────────────────────────────────────

def sf(status):
    u = str(status).upper()
    if "OUT" in u: return 0.0
    if any(x in u for x in ["Q", "QUESTION", "DOUBTFUL", "GTD"]): return Q_FACTOR
    return 1.0

def tc(stat, raw, status="ACTIVE"):
    return round(float(raw or 0) * CONS.get(stat, 0.85) * sf(status), 2)

def tl(val):
    return math.floor(float(val or 0) * LINE_FACTOR)

def edge(tc_val, line_val):
    return round(tc_val - line_val, 2)

def star_mult(name):
    return ALL_NBA.get(name, 1.0)

def raw_pts_for_total(pts, status="ACTIVE"):
    factor = sf(status)
    return round(float(pts) * factor * star_mult(name if 'name' in locals() else ""), 1)

def team_totals(players, half=1.0):
    active = [p for p in players if sf(p.get("status", "ACTIVE")) > 0]
    return {
        f"tc_{s}": round(sum(tc(s, p.get(s, 0), p.get("status", "ACTIVE")) for p in active) * half, 2)
        for s in ["pts", "reb", "ast", "tpm"]
    }

def calc_v8_total(players, is_home=False, bench_avg=None, opp_bench_avg=None, bench_data=None):
    """v8 game total calibration for a team."""
    adj = []
    total = 0.0
    for p in players:
        factor = sf(p.get("status", "ACTIVE"))
        mult = star_mult(p.get("name", ""))
        total += float(p.get("pts", 0)) * factor * mult

    if is_home:
        total += HOME_COURT
        adj.append(f"+{HOME_COURT} home_court")

    if bench_avg is not None and opp_bench_avg is not None:
        diff = bench_avg - opp_bench_avg
        if diff > BENCH_THRESH:
            total += BENCH_BONUS
            adj.append(f"+{BENCH_BONUS:.0f} bench_diff ({diff:.1f} PPG)")

    return {"adjusted": round(total, 1), "adjustments": adj}

def calc_bench_avg(team, bench_data):
    if team not in bench_data:
        return None
    vals = list(bench_data[team].values())
    return sum(vals) / len(vals) if vals else None

def grade(away_p, home_p, away_s, home_s, market=None, half=1.0):
    at, ht = team_totals(away_p, half), team_totals(home_p, half)
    tc_comb = round(at["tc_pts"] + ht["tc_pts"], 2)
    tc_line = tl(tc_comb)
    actual = int(away_s or 0) + int(home_s or 0)
    diff = actual - tc_comb
    edge_val = round(tc_line - float(market or tc_line), 2)
    signal = "OVER" if edge_val > MIN_EDGE else "UNDER" if edge_val < -MIN_EDGE else "PASS"
    result = "OVER" if actual > tc_line else "UNDER" if actual < tc_line else "PUSH"
    hit = signal != "PASS" and result == signal
    return {
        "tc_comb": tc_comb, "tc_line": tc_line, "market": market,
        "edge": edge_val, "signal": signal,
        "actual": actual, "result": result,
        "hit": "✅" if hit else "❌",
        "diff": round(diff, 2), "half": half < 1.0
    }

# ── TEAM ROSTERS ──────────────────────────────────────────────────────────────
TEAMS = {
    "DAL": {"name": "Dallas Wings", "players": [
        {"name": "Arielle Wiggins",   "pos": "F", "pts": 17.0, "reb": 6.0, "ast": 2.5, "tpm": 1.2, "status": "ACTIVE"},
        {"name": "Satou Sabally",     "pos": "F", "pts": 18.5, "reb": 7.5, "ast": 4.0, "tpm": 2.0, "status": "Q"},
        {"name": "Odyssey Sims",      "pos": "G", "pts": 15.0, "reb": 3.5, "ast": 6.0, "tpm": 1.5, "status": "ACTIVE"},
        {"name": "Teaira McCowan",    "pos": "C", "pts": 16.0, "reb":11.0, "ast": 1.5, "tpm": 0.0, "status": "ACTIVE"},
        {"name": "Natasha Howard",    "pos": "F", "pts": 14.0, "reb": 6.5, "ast": 2.0, "tpm": 1.0, "status": "OUT"},
        {"name": "Crystal Dangerfield","pos":"G","pts": 11.5, "reb": 2.5, "ast": 3.5, "tpm": 1.0, "status": "ACTIVE"},
        {"name": "Moriah Jefferson",  "pos": "G", "pts": 10.0, "reb": 2.0, "ast": 5.5, "tpm": 1.2, "status": "ACTIVE"},
        {"name": "Joyner Woods",      "pos": "G", "pts":  8.5, "reb": 2.5, "ast": 3.0, "tpm": 1.2, "status": "ACTIVE"},
    ]},
    "ATL": {"name": "Atlanta Dream", "players": [
        {"name": "Rhyne Howard",       "pos": "G", "pts": 15.5, "reb": 4.5, "ast": 3.5, "tpm": 2.0, "status": "ACTIVE"},
        {"name": "Allisha Gray",       "pos": "G", "pts": 14.2, "reb": 3.8, "ast": 2.9, "tpm": 1.9, "status": "ACTIVE"},
        {"name": "Elyesa Moro",        "pos": "F", "pts":  9.8, "reb": 5.2, "ast": 1.4, "tpm": 0.8, "status": "ACTIVE"},
        {"name": "Crystal Dangerfield","pos": "G", "pts":  8.5, "reb": 2.1, "ast": 2.8, "tpm": 1.5, "status": "ACTIVE"},
        {"name": "Nia Coffey",         "pos": "F", "pts":  7.2, "reb": 4.0, "ast": 1.2, "tpm": 0.9, "status": "ACTIVE"},
        {"name": "Taj",                "pos": "C", "pts":  5.1, "reb": 4.8, "ast": 0.5, "tpm": 0.2, "status": "ACTIVE"},
        {"name": "Iade",               "pos": "G", "pts":  4.0, "reb": 1.5, "ast": 1.2, "tpm": 0.6, "status": "ACTIVE"},
    ]},
    "NYK": {"name": "New York Knicks", "players": [
        {"name": "Jalen Brunson",       "pos": "PG", "pts": 26.0, "reb": 3.5, "ast": 6.5, "tpm": 2.5, "status": "ACTIVE"},
        {"name": "Karl-Anthony Towns",  "pos": "C",  "pts": 24.5, "reb":10.5, "ast": 3.0, "tpm": 2.0, "status": "ACTIVE"},
        {"name": "Mikal Bridges",        "pos": "SG", "pts": 19.0, "reb": 4.5, "ast": 3.5, "tpm": 2.2, "status": "ACTIVE"},
        {"name": "OG Anunoby",           "pos": "SF", "pts": 17.5, "reb": 5.0, "ast": 2.5, "tpm": 1.8, "status": "ACTIVE"},
        {"name": "Josh Hart",            "pos": "PF", "pts": 13.5, "reb": 6.5, "ast": 4.5, "tpm": 1.2, "status": "ACTIVE"},
        {"name": "Miles McBride",        "pos": "PG", "pts":  9.5, "reb": 2.5, "ast": 3.0, "tpm": 1.5, "status": "ACTIVE"},
    ]},
    "CLE": {"name": "Cleveland Cavaliers", "players": [
        {"name": "Donovan Mitchell",   "pos": "SG", "pts": 27.0, "reb": 4.5, "ast": 5.0, "tpm": 2.5, "status": "ACTIVE"},
        {"name": "Darius Garland",      "pos": "PG", "pts": 20.0, "reb": 3.0, "ast": 7.0, "tpm": 2.2, "status": "ACTIVE"},
        {"name": "Evan Mobley",        "pos": "PF", "pts": 18.0, "reb": 9.5, "ast": 3.0, "tpm": 0.8, "status": "ACTIVE"},
        {"name": "Jarrett Allen",      "pos": "C",  "pts": 15.0, "reb":10.0, "ast": 2.0, "tpm": 0.0, "status": "ACTIVE"},
        {"name": "Caris LeVert",       "pos": "SG", "pts": 12.0, "reb": 4.0, "ast": 3.0, "tpm": 1.5, "status": "ACTIVE"},
        {"name": "Max Strus",           "pos": "SF", "pts":  9.0, "reb": 4.0, "ast": 3.0, "tpm": 2.0, "status": "ACTIVE"},
    ]},
    "OKC": {"name": "Oklahoma City Thunder", "players": [
        {"name": "Shai Gilgeous-Alexander","pos":"SG","pts":32.0,"reb":5.0,"ast":6.5,"tpm":2.8,"status":"ACTIVE"},
        {"name": "Jalen Williams",         "pos":"SF","pts":18.5,"reb":5.5,"ast":4.0,"tpm":1.5,"status":"ACTIVE"},
        {"name": "Chet Holmgren",          "pos":"C", "pts":16.0,"reb":8.0,"ast":2.5,"tpm":1.0,"status":"ACTIVE"},
        {"name": "Isaiah Hartenstein",     "pos":"C", "pts": 8.0,"reb":7.5,"ast":2.5,"tpm":0.2,"status":"ACTIVE"},
        {"name": "Luguentz Dort",           "pos":"SG","pts": 9.5,"reb":3.5,"ast":1.2,"tpm":2.0,"status":"ACTIVE"},
        {"name": "Alex Caruso",             "pos":"G", "pts": 6.0,"reb":2.5,"ast":2.0,"tpm":1.2,"status":"ACTIVE"},
    ]},
    "SAS": {"name": "San Antonio Spurs", "players": [
        {"name": "Victor Wembanyama",  "pos": "C",  "pts": 28.0, "reb":10.5, "ast": 4.0, "tpm": 2.5, "status": "ACTIVE"},
        {"name": "De'Aaron Fox",       "pos": "G",  "pts": 24.5, "reb": 5.5, "ast": 6.5, "tpm": 1.8, "status": "ACTIVE"},
        {"name": "Stephon Castle",     "pos": "G",  "pts": 15.0, "reb": 4.5, "ast": 4.0, "tpm": 1.2, "status": "ACTIVE"},
        {"name": "Keldon Johnson",     "pos": "F",  "pts": 14.0, "reb": 4.5, "ast": 2.0, "tpm": 2.0, "status": "ACTIVE"},
        {"name": "Devin Vassell",      "pos": "SG", "pts": 12.0, "reb": 3.5, "ast": 2.5, "tpm": 2.2, "status": "ACTIVE"},
        {"name": "Harrison Barnes",    "pos": "F",  "pts": 13.5, "reb": 5.8, "ast": 2.2, "tpm": 1.4, "status": "ACTIVE"},
    ]},
    "MIN": {"name": "Minnesota Lynx", "players": [
        {"name": "Napheesa Collier",    "pos": "F", "pts": 20.0, "reb": 6.5, "ast": 3.5, "tpm": 1.8, "status": "ACTIVE"},
        {"name": "Alana Smith",          "pos": "G", "pts": 14.5, "reb": 3.5, "ast": 5.5, "tpm": 1.5, "status": "Q"},
        {"name": "Kayla McBride",        "pos": "G", "pts": 16.0, "reb": 4.0, "ast": 4.0, "tpm": 2.8, "status": "ACTIVE"},
        {"name": "Crystal Dangerfield",  "pos": "G", "pts": 12.0, "reb": 3.0, "ast": 3.5, "tpm": 1.2, "status": "ACTIVE"},
        {"name": "Natalie Achonwu",      "pos": "C", "pts":  9.5, "reb": 7.0, "ast": 2.0, "tpm": 0.5, "status": "ACTIVE"},
        {"name": "Olivia Olu",           "pos": "F", "pts":  7.0, "reb": 4.0, "ast": 1.5, "tpm": 1.0, "status": "ACTIVE"},
    ]},
}

# ── UI Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:#0d1117;padding:16px 24px;border-bottom:2px solid #00d4aa'>
  <h1 style='color:#e6edf3;margin:0'>🏀 Sports TC v8 Dashboard</h1>
  <p style='color:#7d8590;margin:4px 0 0'>
    Two independent models: <b style='color:#00d4aa'>TC Match</b> (player props) +
    <b style='color:#f0883e'>v8 Game Total</b> (raw pts + star mult + bench diff + home court)
  </p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["📊 Project Game", "📈 Backtest Results", "📡 Live Monitor", "📋 Slate"])

# ── TAB 1: PROJECT GAME ──────────────────────────────────────────────────────
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    sport = col1.selectbox("Sport", ["NBA", "WNBA"], index=0)
    team_a = col2.selectbox("Away", list(TEAMS.keys()), index=0)
    team_h = col3.selectbox("Home", list(TEAMS.keys()), index=3)
    market = st.number_input("Market Total", value=210.5, step=0.5)
    run = st.button("🚀 Run TC Projection", type="primary")

    if run:
        away_p = TEAMS.get(team_a, {}).get("players", [])
        home_p = TEAMS.get(team_h, {}).get("players", [])
        if not away_p or not home_p:
            st.error("Missing roster data.")
        else:
            # TC Match (player props)
            at, ht = team_totals(away_p), team_totals(home_p)
            tc_comb = round(at["tc_pts"] + ht["tc_pts"], 2)
            tc_line = tl(tc_comb)
            tc_edge = round(tc_line - market, 2)
            tc_signal = "OVER" if tc_edge > MIN_EDGE else "UNDER" if tc_edge < -MIN_EDGE else "PASS"

            # v8 Game Total
            away_bench_avg = calc_bench_avg(team_a, SERIES_BENCH)
            home_bench_avg = calc_bench_avg(team_h, SERIES_BENCH)
            h_adj = calc_v8_total(home_p, is_home=True, bench_avg=home_bench_avg, opp_bench_avg=away_bench_avg, bench_data=SERIES_BENCH)
            a_adj = calc_v8_total(away_p, is_home=False, bench_avg=away_bench_avg, opp_bench_avg=home_bench_avg, bench_data=SERIES_BENCH)
            v8_combined = round(h_adj["adjusted"] + a_adj["adjusted"], 1)
            v8_gap = round(v8_combined - market, 1)
            v8_lean = "UNDER" if v8_gap < -5 else "OVER" if v8_gap > 5 else "NO EDGE"

            # Display metrics row
            st.markdown(f"### {team_a} @ {team_h} — Projection")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("TC Combined", f"{tc_comb}")
            m2.metric("TC Line", f"{tc_line}")
            m3.metric("TC Edge", f"{tc_edge:+.2f}", delta=tc_signal)
            m4.metric("v8 Total", f"{v8_combined}", delta=f"{v8_gap:+.1f} vs market")
            m5.metric("v8 Lean", v8_lean)

            # v8 Adjustments detail
            with st.expander("🔧 v8 Game Total Adjustments", expanded=False):
                st.markdown(f"**{team_h} (Home):** {h_adj['adjusted']} raw → adjusted")
                for adj in h_adj["adjustments"]:
                    st.write(f"  • {adj}")
                st.markdown(f"**{team_a} (Away):** {a_adj['adjusted']} raw → adjusted")
                for adj in a_adj["adjustments"]:
                    st.write(f"  • {adj}")

            # Player tables
            for label, players, side in [(f"{team_a} (Away)", away_p, "away"), (f"{team_h} (Home)", home_p, "home")]:
                with st.expander(f"👥 {label} — Full Roster", expanded=True):
                    rows = []
                    for p in players:
                        tc_p = tc("pts", p["pts"], p["status"])
                        ln_p = tl(tc_p)
                        e = edge(tc_p, ln_p)
                        status_icon = "✅" if p["status"] == "ACTIVE" else ("⚠️" if p["status"] == "Q" else "❌")
                        rows.append({
                            "Player": p["name"], "POS": p["pos"],
                            "TC PTS": tc_p, "Line": ln_p, "Edge": f"{e:+.1f}",
                            "TC REB": tc("reb", p["reb"], p["status"]),
                            "TC AST": tc("ast", p["ast"], p["status"]),
                            "TC 3PM": tc("tpm", p["tpm"], p["status"]),
                            "Status": f"{status_icon} {p['status']}",
                        })
                    st.dataframe(rows, use_container_width=True, hide_index=True)

            # Prop candidates
            cands = []
            for p in away_p + home_p:
                if p["status"] != "ACTIVE" or float(p["pts"]) < 5:
                    continue
                tc_p = tc("pts", p["pts"], p["status"])
                ln_p = tl(tc_p)
                e = edge(tc_p, ln_p)
                if abs(e) >= 2.0:
                    cands.append({
                        "Player": p["name"],
                        "Team": team_a if p in away_p else team_h,
                        "TC PTS": tc_p, "Line": ln_p,
                        "Edge": f"{e:+.1f}",
                        "Direction": "OVER" if e > 0 else "UNDER"
                    })
            cands.sort(key=lambda x: float(x["Edge"].replace("+", "")), reverse=True)
            if cands:
                st.markdown("### 🎯 Prop Candidates (Edge ≥ 2.0)")
                st.dataframe(cands, use_container_width=True, hide_index=True)

# ── TAB 2: BACKTEST ────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("### 📈 Backtest Results — TC Match + v8 Game Total")
    st.caption("v8 direction = lean vs market total direction | TC edge = TC vs LINE | Both tracked independently")

    # Hardcoded backtest
    results = [
        {"game": "WNBA: DAL@ATL", "period": "FINAL", "actual": "69—86", "total": 155,
         "tc_comb": 131.75, "tc_line": 116, "market": 161.5, "tc_edge": -45.5,
         "tc_signal": "UNDER", "result": "OVER", "tc_hit": "❌",
         "v8_combined": 148.2, "v8_gap": -13.3, "v8_lean": "UNDER",
         "v8_hit": "❌", "note": "Both models lean UNDER; actual went OVER market"},
        {"game": "WNBA: TOR@MIN", "period": "FINAL", "actual": "72—100", "total": 172,
         "tc_comb": 146.2, "tc_line": 128, "market": 166.5, "tc_edge": -38.5,
         "tc_signal": "UNDER", "result": "OVER", "tc_hit": "❌",
         "v8_combined": 162.1, "v8_gap": -4.4, "v8_lean": "NO EDGE",
         "v8_hit": "❌", "note": "v8: no edge, market was high"},
        {"game": "NBA: SA@OKC", "period": "HALFTIME", "actual": "58—54", "total": 112,
         "tc_comb": 47.6, "tc_line": 41, "market": 218.5, "tc_edge": -177.5,
         "tc_signal": "UNDER", "result": "OVER", "tc_hit": "❌",
         "v8_combined": 158.8, "v8_gap": -59.7, "v8_lean": "UNDER",
         "v8_hit": "❌", "note": "SAS home 103, OKC away 82 — model correct direction"},
        {"game": "NBA: NY@CLE", "period": "HALFTIME", "actual": "50—44", "total": 94,
         "tc_comb": 48.45, "tc_line": 42, "market": 218.5, "tc_edge": -176.5,
         "tc_signal": "UNDER", "result": "OVER", "tc_hit": "❌",
         "v8_combined": 175.2, "v8_gap": -43.3, "v8_lean": "UNDER",
         "v8_hit": "❌", "note": "Half-time only; full game would be higher"},
    ]

    st.dataframe([
        {"Game": r["game"], "Period": r["period"], "Actual": r["actual"],
         "TC Comb": r["tc_comb"], "TC Line": r["tc_line"], "Market": r["market"],
         "TC Signal": r["tc_signal"], "TC Result": r["result"], "TC Hit": r["tc_hit"],
         "v8 Total": r["v8_combined"], "v8 Lean": r["v8_lean"], "v8 Hit": r["v8_hit"]}
        for r in results
    ], use_container_width=True, hide_index=True)

    tc_hits = sum(1 for r in results if r["tc_hit"] == "✅")
    v8_hits = sum(1 for r in results if r["v8_hit"] == "✅")
    st.caption(f"TC Match hit rate: {tc_hits}/{len(results)} | v8 Game Total hit rate: {v8_hits}/{len(results)}")
    st.info("💡 v8 Game Total is calibrated for direction lean, not exact prediction. TC Match tracks player prop accuracy independently.")

# ── TAB 3: LIVE MONITOR ──────────────────────────────────────────────────────
with tabs[2]:
    st.markdown("### 📡 Live Stats Monitor")
    st.info("Live ESPN scoreboard integration — connect to /api/tc?mode=live-stats for real-time data.")
    st.code("""GET /api/tc?away=DAL&home=ATL&sport=WNBA&market_total=161.5
GET /api/tc?mode=live-stats&sport=WNBA
GET /api/backtest? NBA  # run full backtest
GET /api/project  # POST with GameRequest body""", language="text")

# ── TAB 4: SLATE ──────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown("### 📋 Pregame Slate — Today's Games")
    slate = [
        {"game": "WNBA: DAL @ ATL", "time": "May 25, 2026", "market_total": 161.5,
         "tc_signal": "UNDER", "tc_edge": -45.5, "v8_lean": "UNDER", "v8_gap": -13.3, "status": "⏳ Upcoming"},
        {"game": "NBA: SAS @ OKC", "time": "May 25, 2026", "market_total": 218.5,
         "tc_signal": "UNDER", "tc_edge": -177.5, "v8_lean": "UNDER", "v8_gap": -59.7, "status": "⏳ Upcoming"},
        {"game": "WNBA: MIN @ CHI", "time": "May 25, 2026", "market_total": 163.5,
         "tc_signal": "UNDER", "tc_edge": -76.5, "v8_lean": "NO EDGE", "v8_gap": -3.2, "status": "⏳ Upcoming"},
        {"game": "NBA: NYK @ CLE", "time": "May 25, 2026", "market_total": 218.0,
         "tc_signal": "PASS", "tc_edge": 1.2, "v8_lean": "NO EDGE", "v8_gap": 2.5, "status": "⏳ Upcoming"},
    ]
    st.dataframe(slate, use_container_width=True, hide_index=True)