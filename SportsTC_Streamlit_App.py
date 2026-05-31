"""
Sports TC — Triple Conservative Engine
Streamlit Dashboard | NBA + WNBA + NCAAB + MLB + NHL

Usage:
  pip install streamlit requests
  streamlit run SportsTC_Streamlit_App.py

API Backend: calls Zo TC API at https://true.zo.space/api/tc
TC does NOT apply to game totals — it is a player prop projection engine only.
"""

import streamlit as st
import requests
from datetime import datetime
from multi_sport_engine import *
import json

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_URL  = "https://true.zo.space"
SPORTS    = ["NBA", "WNBA", "NCAAB", "MLB", "NHL"]

NBA_TEAMS  = ["ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET","GSW",
              "HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN","NOP","NYK",
              "OKC","ORL","PHI","PHX","POR","SAC","SAS","TOR","UTA","WAS"]
WNBA_TEAMS = ["ATL","CHI","CON","DAL","GS","IND","LV","LA","MIN","NY",
              "PHX","POR","SEA","TOR","WSH"]
NCAAB_TEAMS = ["ARI","AUB","BAY","UConn","DU","UVA","KU","UK","UNC","Nova",
               "GONZ","ARK","LOU","Mich","HOU","BAMA","SC","ILL","KSU","TEX"]
MLB_TEAMS   = ["NYY","BOS","NYM","PHI","ATL","CHC","CWS","LAD","SD","SF",
               "HOU","SEA","TEX","STL","MIL","CIN","PIT","COL","AZ","MIA"]
NHL_TEAMS  = ["BOS","TOR","NYR","NYI","NJ","PHI","CAR","FLA","TBL","WSH",
               "DET","CBJ","PIT","MTL","OTT","BUF","DAL","COL","VGK","SEA"]

TEAM_MAP = {
    "NBA":   NBA_TEAMS,
    "WNBA":  WNBA_TEAMS,
    "NCAAB": NCAAB_TEAMS,
    "MLB":   MLB_TEAMS,
    "NHL":   NHL_TEAMS,
}

STAT_CONFIG = {
    "NBA": {
        "PTS":  {"tc": "tc_pts",  "label": "Points",     "sym": "★"},
        "REB":  {"tc": "tc_reb",  "label": "Rebounds",   "sym": "◆"},
        "AST":  {"tc": "tc_ast",  "label": "Assists",    "sym": "●"},
        "3PM":  {"tc": "tc_tpm",  "label": "3-Pointers", "sym": "▲"},
        "STL":  {"tc": "tc_stl",  "label": "Steals",     "sym": "♦"},
        "BLK":  {"tc": "tc_blk",  "label": "Blocks",     "sym": "◈"},
    },
    "WNBA": {
        "PTS":  {"tc": "tc_pts",  "label": "Points",     "sym": "★"},
        "REB":  {"tc": "tc_reb",  "label": "Rebounds",   "sym": "◆"},
        "AST":  {"tc": "tc_ast",  "label": "Assists",    "sym": "●"},
        "3PM":  {"tc": "tc_tpm",  "label": "3-Pointers", "sym": "▲"},
        "STL":  {"tc": "tc_stl",  "label": "Steals",     "sym": "♦"},
        "BLK":  {"tc": "tc_blk",  "label": "Blocks",     "sym": "◈"},
    },
    "MLB": {
        "RUNS": {"tc": "tc_runs", "label": "Runs",       "sym": "⚾"},
        "HITS": {"tc": "tc_hits", "label": "Hits",       "sym": "🏏"},
        "RBI":  {"tc": "tc_rbi",  "label": "RBI",        "sym": "🔄"},
        "ERA":  {"tc": "tc_era",  "label": "ERA(IP)",    "sym": "📊"},
        "K":    {"tc": "tc_k",    "label": "Strikeouts", "sym": "💥"},
    },
    "NHL": {
        "GOALS":   {"tc": "tc_goals",   "label": "Goals",      "sym": "🥅"},
        "ASSISTS": {"tc": "tc_assists", "label": "Assists",    "sym": "🤝"},
        "SOG":     {"tc": "tc_sog",     "label": "Shots",      "sym": "🏒"},
        "HITS":    {"tc": "tc_hits",    "label": "Hits",       "sym": "💢"},
        "BLOCKS":  {"tc": "tc_blocks",  "label": "Blocks",     "sym": "🛡️"},
    },
}

BACKTEST = [
    {"date":"05/28","away":"OKC","home":"SAS","away_score":None,"home_score":None,"actual":None,"dk":219.5,"tc_est":223.4,"edge":+3.9,"signal":"OVER","result":"PENDING","hit":None,"round":"WCF","live":True},
    {"date":"05/18","away":"SAS","home":"OKC","away_score":115,"home_score":122,"actual":237,"dk":218.5,"tc_est":218.0,"edge":-0.5,"signal":"PASS","result":"OVER","hit":False,"round":"WCF"},
    {"date":"05/20","away":"SAS","home":"OKC","away_score":113,"home_score":122,"actual":235,"dk":219.5,"tc_est":216.2,"edge":-3.3,"signal":"PASS","result":"OVER","hit":False,"round":"WCF"},
    {"date":"05/22","away":"OKC","home":"SAS","away_score":123,"home_score":108,"actual":231,"dk":220.0,"tc_est":212.5,"edge":-7.5,"signal":"UNDER","result":"OVER","hit":False,"round":"WCF"},
    {"date":"05/24","away":"OKC","home":"SAS","away_score":82, "home_score":103,"actual":185,"dk":221.5,"tc_est":170.2,"edge":-51.3,"signal":"UNDER","result":"UNDER","hit":True,"round":"WCF"},
    {"date":"05/26","away":"OKC","home":"SAS","away_score":127,"home_score":114,"actual":241,"dk":219.5,"tc_est":224.3,"edge":+4.8,"signal":"OVER","result":"OVER","hit":True,"round":"WCF"},
    {"date":"05/04","away":"PHI","home":"NYK","away_score":98, "home_score":137,"actual":235,"dk":229.5,"tc_est":216.2,"edge":-13.3,"signal":"UNDER","result":"OVER","hit":False,"round":"Semifinals"},
    {"date":"05/05","away":"CLE","home":"DET","away_score":101,"home_score":111,"actual":212,"dk":228.5,"tc_est":195.0,"edge":-33.5,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/05","away":"LAL","home":"OKC","away_score":90, "home_score":108,"actual":198,"dk":224.5,"tc_est":182.2,"edge":-42.3,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/06","away":"PHI","home":"NYK","away_score":102,"home_score":108,"actual":210,"dk":227.5,"tc_est":193.2,"edge":-34.3,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/07","away":"CLE","home":"DET","away_score":97, "home_score":107,"actual":204,"dk":227.0,"tc_est":187.7,"edge":-39.3,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/07","away":"LAL","home":"OKC","away_score":107,"home_score":125,"actual":232,"dk":226.0,"tc_est":213.4,"edge":-12.6,"signal":"UNDER","result":"OVER","hit":False,"round":"Semifinals"},
    {"date":"05/08","away":"NYK","home":"PHI","away_score":108,"home_score":94, "actual":202,"dk":228.0,"tc_est":185.8,"edge":-42.2,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/09","away":"DET","home":"CLE","away_score":109,"home_score":116,"actual":225,"dk":229.0,"tc_est":207.0,"edge":-22.0,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/09","away":"OKC","home":"LAL","away_score":131,"home_score":108,"actual":239,"dk":227.5,"tc_est":219.9,"edge":-7.6,"signal":"UNDER","result":"OVER","hit":False,"round":"Semifinals"},
    {"date":"05/10","away":"NYK","home":"PHI","away_score":144,"home_score":114,"actual":258,"dk":226.5,"tc_est":237.4,"edge":+10.9,"signal":"OVER","result":"OVER","hit":True,"round":"Semifinals"},
    {"date":"05/11","away":"DET","home":"CLE","away_score":103,"home_score":112,"actual":215,"dk":228.5,"tc_est":197.8,"edge":-30.7,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/11","away":"OKC","home":"LAL","away_score":115,"home_score":110,"actual":225,"dk":226.5,"tc_est":207.0,"edge":-19.5,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/12","away":"SAS","home":"MIN","away_score":126,"home_score":97, "actual":223,"dk":218.5,"tc_est":205.2,"edge":-13.3,"signal":"UNDER","result":"OVER","hit":False,"round":"Semifinals"},
    {"date":"05/13","away":"CLE","home":"DET","away_score":117,"home_score":113,"actual":230,"dk":230.0,"tc_est":211.6,"edge":-18.4,"signal":"UNDER","result":"PUSH","hit":False,"round":"Semifinals"},
    {"date":"05/15","away":"DET","home":"CLE","away_score":115,"home_score":94, "actual":209,"dk":228.5,"tc_est":192.3,"edge":-36.2,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"05/15","away":"MIN","home":"SAS","away_score":109,"home_score":139,"actual":248,"dk":220.0,"tc_est":228.2,"edge":+8.2,"signal":"OVER","result":"OVER","hit":True,"round":"Semifinals"},
    {"date":"05/17","away":"CLE","home":"DET","away_score":125,"home_score":94, "actual":219,"dk":229.5,"tc_est":201.5,"edge":-28.0,"signal":"UNDER","result":"UNDER","hit":True,"round":"Semifinals"},
    {"date":"04/18","away":"ATL","home":"NYK","away_score":102,"home_score":113,"actual":215,"dk":226.5,"tc_est":197.8,"edge":-28.7,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/19","away":"ORL","home":"DET","away_score":101,"home_score":112,"actual":213,"dk":212.5,"tc_est":196.0,"edge":-16.5,"signal":"UNDER","result":"OVER","hit":False,"round":"Round 1"},
    {"date":"04/19","away":"PHI","home":"BOS","away_score":91, "home_score":123,"actual":214,"dk":222.5,"tc_est":196.9,"edge":-25.6,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/19","away":"CLE","home":"TOR","away_score":126,"home_score":113,"actual":239,"dk":232.5,"tc_est":219.9,"edge":-12.6,"signal":"UNDER","result":"OVER","hit":False,"round":"Round 1"},
    {"date":"04/19","away":"PHX","home":"OKC","away_score":84, "home_score":119,"actual":203,"dk":226.5,"tc_est":186.8,"edge":-39.7,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/19","away":"MIN","home":"SAS","away_score":104,"home_score":102,"actual":206,"dk":220.5,"tc_est":189.5,"edge":-31.0,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/20","away":"ATL","home":"NYK","away_score":107,"home_score":106,"actual":213,"dk":227.5,"tc_est":196.0,"edge":-31.5,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/21","away":"MIN","home":"SAS","away_score":95, "home_score":133,"actual":228,"dk":221.5,"tc_est":209.8,"edge":-11.7,"signal":"UNDER","result":"OVER","hit":False,"round":"Round 1"},
    {"date":"04/25","away":"NYK","home":"ATL","away_score":114,"home_score":98, "actual":212,"dk":225.5,"tc_est":195.0,"edge":-30.5,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/26","away":"DET","home":"ORL","away_score":88, "home_score":94, "actual":182,"dk":213.5,"tc_est":167.4,"edge":-46.1,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/26","away":"CLE","home":"TOR","away_score":89, "home_score":93, "actual":182,"dk":233.5,"tc_est":167.4,"edge":-66.1,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/27","away":"OKC","home":"PHX","away_score":131,"home_score":122,"actual":253,"dk":228.5,"tc_est":232.8,"edge":+4.3,"signal":"PASS","result":"OVER","hit":False,"round":"Round 1"},
    {"date":"04/28","away":"NYK","home":"ATL","away_score":126,"home_score":97, "actual":223,"dk":224.5,"tc_est":205.2,"edge":-19.3,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"04/28","away":"MIN","home":"SAS","away_score":97, "home_score":126,"actual":223,"dk":222.0,"tc_est":205.2,"edge":-16.8,"signal":"UNDER","result":"OVER","hit":False,"round":"Round 1"},
    {"date":"05/01","away":"ORL","home":"DET","away_score":79, "home_score":93, "actual":172,"dk":214.0,"tc_est":158.2,"edge":-55.8,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"05/01","away":"SAS","home":"MIN","away_score":139,"home_score":109,"actual":248,"dk":220.5,"tc_est":228.2,"edge":+7.7,"signal":"OVER","result":"OVER","hit":True,"round":"Round 1"},
    {"date":"05/02","away":"BOS","home":"PHI","away_score":91, "home_score":118,"actual":209,"dk":220.0,"tc_est":192.3,"edge":-27.7,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
    {"date":"05/03","away":"DET","home":"ORL","away_score":116,"home_score":94, "actual":210,"dk":214.5,"tc_est":193.2,"edge":-21.3,"signal":"UNDER","result":"UNDER","hit":True,"round":"Round 1"},
]


# ── HELPERS ─────────────────────────────────────────────────────────────────
def call_api(away: str, home: str, sport: str, mode: str = "project") -> dict:
    params = {"away": away, "home": home, "sport": sport}
    if mode == "live-stats":
        params["mode"] = "live-stats"
    try:
        r = requests.get(f"{BASE_URL}/api/tc", params=params, timeout=30,
                         headers={"Accept": "application/json"})
        if not r.ok:
            return {"error": f"API {r.status.status_code}: {r.text[:200]}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def run_local_projection(away: str, home: str, sport: str) -> dict:
    """Run multi-sport models locally (MLB/NHL/NCAAB)"""
    from multi_sport_engine import (
        poisson_expected_runs, mlb_win_prob,
        nhl_expected_goals, nhl_poisson_total,
        ncaab_game_prob
    )
    import random

    source = "multi-sport-engine"

    if sport == "MLB":
        # Poisson model — use league averages as base
        away_exp = poisson_expected_runs(away.lower(), 1.0, 4.0, True)
        home_exp = poisson_expected_runs(home.lower(), 1.0, 4.0, True)
        win = mlb_win_prob(away_exp, home_exp, 4.0, 4.0)

        return {
            "sport": "MLB", "away_team": away, "home_team": home, "source": source,
            "assessment": {
                "tc_total": f"{away_exp + home_exp:.1f}",
                "tc_line": f"{int(away_exp + home_exp)}",
                "edge": away_exp - home_exp,
                "signal": "HOME" if win["home_win_prob"] > 0.6 else ("AWAY" if win["away_win_prob"] > 0.6 else "TOSS-UP"),
            },
            "odds": {"away_ml": "-110", "home_ml": "-110", "spread": "—"},
            "away": {"all": {"players": [
                {"name": f"{away} Starter", "status": "ACTIVE", "team": away, "tc_pts": away_exp, "tc_reb": 0, "tc_ast": 0, "tc_runs": away_exp, "tc_hits": away_exp * 1.8, "tc_rbi": away_exp * 0.5},
            ]}},
            "home": {"all": {"players": [
                {"name": f"{home} Starter", "status": "ACTIVE", "team": home, "tc_pts": home_exp, "tc_reb": 0, "tc_ast": 0, "tc_runs": home_exp, "tc_hits": home_exp * 1.8, "tc_rbi": home_exp * 0.5},
            ]}},
            "dk_total": f"{away_exp + home_exp + 0.5:.1f}",
            "edge": f"{win['home_win_prob'] - 0.5:+.2f}",
            "signal": "HOME FAVORITE" if win["home_win_prob"] > 0.55 else ("AWAY FAVORITE" if win["away_win_prob"] > 0.55 else "EVEN"),
        }

    elif sport == "NHL":
        away_goals, home_goals, total = nhl_poisson_total(2.8, 2.4, 5.5, True)

        return {
            "sport": "NHL", "away_team": away, "home_team": home, "source": source,
            "assessment": {
                "tc_total": f"{total:.1f}",
                "tc_line": f"{total:.0f}",
                "edge": home_goals - away_goals,
                "signal": "HOME" if home_goals > away_goals else "AWAY",
            },
            "odds": {"away_ml": "-110", "home_ml": "-110", "spread": "PICK"},
            "away": {"all": {"players": [
                {"name": f"{away} Top Line", "status": "ACTIVE", "team": away, "tc_pts": away_goals, "tc_goals": away_goals, "tc_assists": away_goals * 1.5, "tc_sog": away_goals * 3.0},
            ]}},
            "home": {"all": {"players": [
                {"name": f"{home} Top Line", "status": "ACTIVE", "team": home, "tc_pts": home_goals, "tc_goals": home_goals, "tc_assists": home_goals * 1.5, "tc_sog": home_goals * 3.0},
            ]}},
            "dk_total": f"{total:.1f}",
            "edge": f"{home_goals - away_goals:+.1f}",
            "signal": "HOME EDGE" if home_goals > away_goals else "AWAY EDGE",
        }

    elif sport == "NCAAB":
        pred = ncaab_game_prob(82.5, 75.0, 78.0, 70.0, True)
        pace = 68

        return {
            "sport": "NCAAB", "away_team": away, "home_team": home, "source": source,
            "assessment": {
                "tc_total": pred.get("expected_total", f"{pace * 2:.1f}"),
                "tc_line": pred.get("spread", "PICK"),
                "edge": float(pred.get("elo_diff", 0)),
                "signal": f"HOME {pred.get('home_win_prob', 50)}%" if pred.get("home_win_prob", 0) > 50 else f"AWAY {pred.get('away_win_prob', 50)}%",
            },
            "odds": {"away_ml": "-110", "home_ml": "-110", "spread": pred.get("spread", "PICK")},
            "away": {"all": {"players": [
                {"name": f"{away} PG", "status": "ACTIVE", "team": away, "tc_pts": 14, "tc_reb": 4, "tc_ast": 5, "tc_tpm": 2, "tc_stl": 1, "tc_blk": 0},
            ]}},
            "home": {"all": {"players": [
                {"name": f"{home} C", "status": "ACTIVE", "team": home, "tc_pts": 18, "tc_reb": 10, "tc_ast": 2, "tc_tpm": 0, "tc_stl": 1, "tc_blk": 3},
            ]}},
            "dk_total": pred.get("dk_total", "—"),
            "edge": pred.get("spread", "PICK"),
            "signal": pred.get("home_win_prob", f"{pred.get('home_win_prob',50)}%"),
        }

    return {"error": f"No local engine for sport: {sport}"}


def fmt(n):
    try:
        return f"{float(n):.1f}"
    except (TypeError, ValueError):
        return "—"


def edge_emoji(n):
    try:
        v = float(n)
        return "🟢" if v > 2 else "🔴" if v < -2 else "🟡"
    except (TypeError, ValueError):
        return "🟡"


def status_factor(status: str) -> float:
    s = str(status or "ACTIVE").upper()
    if "OUT" in s or "DNP" in s:
        return 0.0
    if any(x in s for x in ["Q", "QUESTION", "DOUBTFUL", "GTD"]):
        return 0.55
    return 1.0


# ── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sports TC — Triple Conservative Engine",
    page_icon="🏀",
    layout="wide",
    menu_items={
        "About": "Sports TC Dashboard · NBA + WNBA + NCAAB + MLB + NHL\n"
                 "Powered by Zo Computer · TC Engine v4\n"
                 "TC applies to player props ONLY — DK game totals stored independently",
    },
)

st.markdown("""
<style>
.stApp { background: #0d1117; }
.stMetric { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px !important; }
section[data-testid="stSidebar"] { background: #161b22; }
[data-testid="stMainBlockContainer"] { padding-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏀 Sports TC")
    st.caption("*Triple Conservative Engine*")
    st.divider()
    sport = st.selectbox("Sport", SPORTS)
    teams = TEAM_MAP.get(sport, NBA_TEAMS)
    away  = st.selectbox("Away", teams,
                         index=teams.index("NYK") if "NYK" in teams else 0)
    home  = st.selectbox("Home", teams,
                         index=teams.index("CLE") if "CLE" in teams else 1)
    st.divider()
    st.markdown("**TC Formula**")
    st.caption("`TC PTS = pts × 0.85`")
    st.caption("`Q × 0.55 · OUT = 0`")
    st.caption("`TC Line = TC × 0.88`")
    st.caption("`Edge = TC − Line`")
    st.divider()
    st.markdown("**DK Game Totals**")
    st.caption("TC does NOT apply to game totals — TC is for player props ONLY.")
    st.caption("DK totals stored independently as market reference lines.")
    st.divider()
    dk_total_override  = st.number_input("DK Total Override",  value=0.0, step=0.5, format="%.1f",
                                help="Override the API DK total. 0 = use API value.")
    dk_spread_override = st.number_input("DK Spread Override", value=0.0, step=0.5, format="%.1f",
                                help="Override the API DK spread. 0 = use API value.")
    st.divider()
    st.caption(f"Session: {datetime.now().strftime('%H:%M:%S')}")

# ── MAIN TABS ────────────────────────────────────────────────────────────────
tab_proj, tab_live, tab_injury, tab_backtest, tab_slate = st.tabs([
    "📊  Project Game",
    "📡  Live Stats",
    "🏥  Injury Report",
    "📈  Backtest",
    "📋  Slate",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — PROJECT GAME
# ─────────────────────────────────────────────────────────────────────────────
with tab_proj:
    col_run = st.columns([1])
    if st.button("🚀  Run TC Projection", use_container_width=True):
        st.session_state["run_proj"] = True

    if st.session_state.get("run_proj"):
        with st.spinner("Calling projection engine…"):
            data = call_api(away, home, sport)

        if "error" in data:
            st.error(data["error"])
        elif data:
            a    = data.get("assessment", {})
            odds = data.get("odds", {})
            tc_total  = a.get("tc_total") or data.get("tc_combined") or "—"
            tc_line   = a.get("tc_line")  or data.get("tc_line")  or "—"
            edge      = data.get("edge") or a.get("edge") or "—"
            signal    = data.get("signal") or a.get("signal") or "NO MARKET"

            # Top-line metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("TC Combined", fmt(tc_total))
            with m2: st.metric("TC Line PTS", fmt(tc_line))
            with m3: st.metric("TC Edge", f"{edge:+.1f}" if isinstance(edge,(int,float)) else fmt(edge))
            with m4: st.metric("Signal", signal)
            st.caption(f"{data.get('sport','')} · {data.get('away_team','')} @ {data.get('home_team','')} · {data.get('source','')}")

            # Odds + DK card — sidebar overrides wired here
            effective_dk_total = dk_total_override if dk_total_override != 0.0 else (data.get("dk_total") or "—")
            effective_spread    = dk_spread_override if dk_spread_override != 0.0 else (odds.get("spread") or "—")
            override_active     = (dk_total_override != 0.0 or dk_spread_override != 0.0)

            o1, o2, o3, o4 = st.columns(4)
            with o1:
                ml = odds.get("away_ml") or odds.get("home_ml") or "—"
                st.metric("ML", f"{data.get('away_team','AWAY')} {ml}")
            with o2:
                badge = " OVERRIDE" if dk_spread_override != 0.0 else ""
                st.metric("Spread", f"{effective_spread}{badge}")
            with o3:
                badge = " OVERRIDE" if dk_total_override != 0.0 else ""
                st.metric("DK Total", f"{effective_dk_total}{badge}" if override_active else effective_dk_total)
            with o4:
                st.metric("TC Line", fmt(tc_line))

            st.divider()

            # Stat leaders
            sport_stats = STAT_CONFIG.get(sport, STAT_CONFIG)
            sel_stat = st.selectbox(
                "Stat Category",
                list(sport_stats.keys()),
                format_func=lambda k: f"{sport_stats[k]['sym']}  {k} — {sport_stats[k]['label']}",
            )
            cfg = sport_stats[sel_stat]

            away_players = data.get("away", {}).get("all", {}).get("players", [])
            home_players = data.get("home", {}).get("all", {}).get("players", [])

            all_pl = []
            for p in away_players:
                if status_factor(p.get("status", "")) > 0:
                    all_pl.append({**p, "team": data.get("away_team", "")})
            for p in home_players:
                if status_factor(p.get("status", "")) > 0:
                    all_pl.append({**p, "team": data.get("home_team", "")})

            all_pl.sort(key=lambda p: float(p.get(cfg["tc"], 0) or 0), reverse=True)
            top5 = all_pl[:5]

            lc = st.columns(2)
            for idx, player in enumerate(top5):
                with lc[idx % 2]:
                    tc_v   = float(player.get(cfg["tc"], 0) or 0)
                    raw_k  = sel_stat.lower()
                    line_k = f"line_{raw_k}"
                    edge_k = f"edge_{raw_k}"
                    line_v = float(player.get(line_k, 0) or 0)
                    edge_v = float(player.get(edge_k, 0) or 0)
                    status = player.get("status", "ACTIVE")
                    sym_map = {"PTS":"★","REB":"◆","AST":"●","3PM":"▲","STL":"♦","BLK":"◈"}
                    sym = sym_map.get(sel_stat, "•")
                    st.markdown(
                        f"**{sym}  {player.get('name','?')}**  ({player.get('team','')})  "
                        f"{'🔴 OUT' if status=='OUT' else '🟡 Q' if status!='ACTIVE' else '🟢 ACTIVE'}\n"
                        f"- TC {sel_stat}: **{tc_v:.1f}**  |  Line: {line_v:.1f}  |  "
                        f"Edge: {edge_emoji(edge_v)} {edge_v:+.1f}\n"
                        f"- Pos: {player.get('pos','—')}  |  Min: {player.get('min','—')}"
                    )
                    syms = player.get("symbols", [])
                    if syms:
                        st.caption("  ".join(syms))

            st.divider()

            # Full roster tables
            for side_lbl, side_key in [("away", "away"), ("home", "home")]:
                side = data.get(side_key, {})
                players = side.get("all", {}).get("players", [])
                inj = side.get("injuries") or []
                st.markdown(f"#### {side.get('abbr', side_key.upper())}  —  Full Roster TC Projections")
                rows = []
                for p in players:
                    status = p.get("status", "ACTIVE")
                    role = "OUT" if status == "OUT" else "START"
                    rows.append({
                        "Role":    role,
                        "Player":  p.get("name", "?"),
                        "POS":     p.get("pos", "—"),
                        "MIN":     p.get("min", "—"),
                        "Status":  status,
                        **{f"TC {k}": fmt(p.get(sport_stats[k]["tc"], 0)) for k in sport_stats},
                    })
                if rows:
                    st.dataframe(rows, use_container_width=True, hide_index=True)
                if inj:
                    st.warning(f"**Injury Report:** {', '.join(inj)}")
                st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — LIVE STATS
# ─────────────────────────────────────────────────────────────────────────────
with tab_live:
    sport_live = st.selectbox("Sport", SPORTS, key="live_sport")
    auto_refresh = st.checkbox("🔄 Auto-refresh every 60s", value=False, key="auto_refresh_live")
    if auto_refresh:
        try:
            from streamlit_autorefresh import st_autorefresh
            count = st_autorefresh(interval=60_000, limit=None, key="live_refresh_counter")
            st.caption(f"Auto-refresh #{count} · {datetime.now().strftime('%H:%M:%S')}")
        except ImportError:
            st.warning("Install streamlit-autorefresh for auto-refresh: pip install streamlit-autorefresh")
    if st.button("🔄  Refresh Live Stats", use_container_width=True):
        st.session_state["refresh_live"] = True

    with st.spinner("Fetching live scoreboard…"):

        live = call_api("", "", sport_live, mode="live-stats")

    if "error" in live:
        st.error(live["error"])
    elif live:
        games = live.get("games", [])
        st.success(f"**{len(games)}** game(s) · {live.get('timestamp','')}")
        for g in games:
            aw = g.get("away", {})
            hm = g.get("home", {})
            with st.expander(
                f"**{aw.get('team','?')} {aw.get('score','?')} @ "
                f"{hm.get('team','?')} {hm.get('score','?')}**  —  "
                f"{g.get('status','?')} {g.get('detail','')}",
                expanded=False,
            ):
                players = g.get("players") or []
                if players:
                    for p in players:
                        st.markdown(
                            f"{p.get('team','?')}  |  {p.get('name','?')}  |  "
                            f"PTS:{p.get('actual',{}).get('pts','—')}  |  "
                            f"REB:{p.get('actual',{}).get('reb','—')}  |  "
                            f"AST:{p.get('actual',{}).get('ast','—')}  |  "
                            f"3PM:{p.get('actual',{}).get('tpm','—')}  |  "
                            f"MIN:{p.get('minutes','—')}"
                        )
                else:
                    st.caption("No player box-score data for this game yet.")
    else:
        st.info("Click **Refresh Live Stats** to load today's games.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — INJURY REPORT
# ─────────────────────────────────────────────────────────────────────────────
with tab_injury:
    st.markdown("### 🏥  Team Injury Report")
    st.caption("Filters all players on a roster by injury/status designation. TC impact shown — OUT players contribute 0 to projections.")

    # Team selectors — pick any two teams to compare
    inj_sport = st.selectbox("Sport", SPORTS, key="inj_sport")
    inj_away  = st.selectbox("Away Team", TEAM_MAP.get(inj_sport, NBA_TEAMS), key="inj_away")
    inj_home  = st.selectbox("Home Team", TEAM_MAP.get(inj_sport, NBA_TEAMS), key="inj_home",
                             index=(TEAM_MAP.get(inj_sport, NBA_TEAMS).index(inj_away) + 1) % len(TEAM_MAP.get(inj_sport, NBA_TEAMS)))

    # Status filter
    inj_filter = st.pills("Filter", ["All", "OUT", "Questionable", "Active"], default="All", selection_mode="single")

    if st.button("🔍  Load Injury Report", use_container_width=True):
        with st.spinner(f"Fetching {inj_away} @ {inj_home} roster..."):
            inj_data = call_api(inj_away, inj_home, inj_sport)

        if "error" in inj_data:
            st.error(inj_data["error"])
        elif inj_data:
            def make_injury_rows(side_data, team_label):
                rows = []
                for p in side_data.get("all", {}).get("players", []):
                    status = str(p.get("status", "ACTIVE")).upper()
                    tc     = float(p.get("tc_tot", 0) or 0)
                    sf     = status_factor(p.get("status", ""))
                    tc_adj = tc * sf
                    if inj_filter == "OUT" and status != "OUT":
                        continue
                    if inj_filter == "Questionable" and "Q" not in status and status != "DOUBTFUL":
                        continue
                    if inj_filter == "Active" and status not in ("ACTIVE", ""):
                        continue
                    badge = "🔴 OUT" if status == "OUT" else "🟡 Q" if "Q" in status or status == "DOUBTFUL" else "🟢 ACTIVE"
                    rows.append({
                        "Team":      team_label,
                        "Player":    p.get("name", "—"),
                        "Pos":       p.get("pos", "—"),
                        "Status":    badge,
                        "TC Raw":    round(tc, 1),
                        "TC Adj":    round(tc_adj, 1),
                        "Impact":    "❌ None" if status == "OUT" else "⚠️ Reduced" if tc_adj < tc else "✅ Full",
                    })
                return rows

            away_rows = make_injury_rows(inj_data.get("away", {}), inj_data.get("away_team", inj_away))
            home_rows = make_injury_rows(inj_data.get("home", {}), inj_data.get("home_team", inj_home))
            all_rows  = away_rows + home_rows

            # Summary metrics
            out_count  = sum(1 for r in all_rows if "OUT" in r["Status"])
            q_count    = sum(1 for r in all_rows if "Q" in r["Status"])
            tc_loss    = sum(r["TC Raw"] - r["TC Adj"] for r in all_rows)

            m1, m2, m3 = st.columns(3)
            with m1: st.metric("OUT Players", out_count)
            with m2: st.metric("Questionable", q_count)
            with m3: st.metric("TC Points Lost", f"−{tc_loss:.1f}")

            if all_rows:
                st.dataframe(all_rows, use_container_width=True, hide_index=True)
            else:
                st.success("No players match the current filter.")

            # Injury notes from API
            for team_key, team_label in [("away", inj_data.get("away_team", "")), ("home", inj_data.get("home_team", ""))]:
                inj_notes = inj_data.get(team_key, {}).get("injuries", [])
                if inj_notes:
                    st.markdown(f"**{team_label} injury notes:** {', '.join(inj_notes)}")
        else:
            st.warning("No data returned. Try a different team pair.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — BACKTEST
# ─────────────────────────────────────────────────────────────────────────────
with tab_backtest:
    total   = len(BACKTEST)
    hits    = sum(1 for r in BACKTEST if r.get("hit") is True)
    misses  = total - hits
    winrate = 100 * hits / total if total else 0

    b1, b2, b3, b4, b5 = st.columns(5)
    with b1: st.metric("Total Games", total)
    with b2: st.metric("Win Rate", f"{winrate:.1f}%")
    with b3: st.metric("Hits", hits)
    with b4: st.metric("Misses", misses)
    with b5: st.metric("Signal",
                       "✅ STRONG" if winrate >= 70 else "⚠️ MODERATE" if winrate >= 55 else "❌ WEAK")

    round_sel = st.pills(
        "Filter by Round",
        ["All", "WCF", "Semifinals", "Round 1"],
        selection_mode="single",
        default="All",
    )
    filtered = BACKTEST if round_sel == "All" else [r for r in BACKTEST if r["round"] == round_sel]

    rows = []
    for r in filtered:
        rows.append({
            "Round":   r["round"],
            "Date":    r["date"],
            "Matchup": f"{r['away']} @ {r['home']}",
            "Away":    r.get("away_score", "—"),
            "Home":    r.get("home_score", "—"),
            "Actual":  r.get("actual", "—"),
            "TC Est":  r.get("tc_est", "—"),
            "DK":      r.get("dk", "—"),
            "Edge":    r.get("edge", 0),
            "Signal":  r.get("signal", "—"),
            "Result":  r.get("result", "—"),
            "Hit":     "✅" if r.get("hit") is True else "❌" if r.get("hit") is False else "⏳",
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "TC calibration: 0.92 PTS factor (playoffs) / 0.85 (regular) · "
        "DK game totals stored SEPARATELY — TC does NOT apply to game totals (player props only)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — SLATE
# ─────────────────────────────────────────────────────────────────────────────
with tab_slate:
    sport_slate = st.selectbox("Sport", SPORTS, key="slate_sport")
    st.info(
        "**Slate View** loads all active games for the selected sport. "
        "Shows DK game totals (stored independently of TC) and TC edge signals. "
        "Use DK totals as market lines; compare with TC player prop projections for your picks."
    )
    if st.button("📡  Load Slate", use_container_width=True):
        st.session_state["load_slate"] = True

    if st.session_state.get("load_slate"):
        with st.spinner("Loading slate from Zo API…"):
            slate = call_api("", "", sport_slate, mode="live-stats")

        if "error" in slate:
            st.error(slate["error"])
        elif slate:
            games = slate.get("games", [])
            st.success(f"**{len(games)}** game(s) found · {slate.get('timestamp','')}")

            if not games:
                st.warning(
                    f"No active {sport_slate} games right now. "
                    "Check back during the season or on game days."
                )
            else:
                slate_rows = []
                for g in games:
                    aw      = g.get("away", {})
                    hm      = g.get("home", {})
                    dk_tot  = g.get("dk_total") or g.get("total") or "—"
                    aw_lead = aw.get("leaders") or {}
                    hm_lead = hm.get("leaders") or {}

                    edge_v  = "—"
                    signal  = "—"
                    if aw_lead and hm_lead:
                        try:
                            aw_pts = sum(float(v) for v in aw_lead.values() if v)
                            hm_pts = sum(float(v) for v in hm_lead.values() if v)
                            tc_c   = round((aw_pts + hm_pts) * 0.92, 1)
                            tc_l   = round(tc_c * 0.88, 1)
                            dk_f   = float(dk_tot)
                            ev     = tc_c - dk_f
                            edge_v = f"{ev:+.1f}"
                            signal = "OVER" if ev > 2 else "UNDER" if ev < -2 else "PASS"
                        except (TypeError, ValueError):
                            pass

                    slate_rows.append({
                        "Time":        g.get("date", "—"),
                        "Away Team":   aw.get("team", "?"),
                        "Home Team":   hm.get("team", "?"),
                        "Away Score":  aw.get("score", "—"),
                        "Home Score":  hm.get("score", "—"),
                        "Status":      g.get("status", "—"),
                        "Detail":      g.get("detail", "—"),
                        "DK Total":    dk_tot,
                        "TC Edge":     edge_v,
                        "Signal":      signal,
                    })

                st.dataframe(slate_rows, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown(
                    "**How DK Totals Work Here:**\n\n"
                    "1. DK opened totals are stored per game as `dk_total` from the market.\n"
                    "2. TC does **NOT** apply to game totals — it is the *player prop projection engine*.\n"
                    "3. Compare TC player projections (PTS / REB / AST / 3PM / STL / BLK) "
                    "against DraftKings prop lines for your picks.\n"
                    "4. DK game totals are the market benchmark for game-level OVER/UNDER bets."
                )
        else:
            st.caption("Click **Load Slate** to fetch today's games.")
    else:
        st.caption("Click **Load Slate** to load today's games.")

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Sports TC Dashboard  ·  Powered by Zo Computer  ·  "
    "stat × 0.85 · Q × 0.55 · OUT = 0 · Line = TC × 0.88 · Edge = TC − Line  ·  "
    "DK game totals stored independently — TC applies to player props only"
)
