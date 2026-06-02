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
    {"date":"05/12","away":"SAS","home":"MIN","away_score":126,"home_score":97,"actual":223,"dk":218.5,"tc_est":205.2,"edge":-13.3,"signal":"UNDER","result":"OVER","hit":False,"round":"Semifinals"},

    # ── WNBA BACKTEST ──
    {"date":"05/31","away":"LV","home":"GS","away_score":None,"home_score":None,"actual":None,"dk":None,"tc_est":315.8,"edge":0,"signal":"UNDER","result":"PENDING","hit":None,"round":"WNBA Regular","live":True,"sport":"WNBA"},
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
            return {"error": f"API {r.status_code}: {r.text[:200]}"}
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
        "About": "Sports TC Dashboard · NBA + WNBA + NCAAB + MLB + NHL | Powered by Zo Computer | TC applies to player props ONLY",
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
tab_proj, tab_live, tab_injury, tab_backtest, tab_parlay, tab_slate = st.tabs([
    "📊  Project Game",
    "📡  Live Stats",
    "🏥  Injury Report",
    "📈  Backtest",
    "💰  Parlay Builder",
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
                        f"{'🔴 OUT' if status=='OUT' else '🟡 Q' if status!='ACTIVE' else '🟢 ACTIVE'}"
                        f"- TC {sel_stat}: **{tc_v:.1f}**  |  Line: {line_v:.1f}  |  "
                        f"Edge: {edge_emoji(edge_v)} {edge_v:+.1f}"
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
# TAB 5 — PARLAY BUILDER (Top 8 Window + custom picker)
# ─────────────────────────────────────────────────────────────────────────────
with tab_parlay:
    st.markdown("### 💰 Parlay Builder")
    st.caption("Build multi-leg parlays using live projections and custom picks.")
    st.divider()

    # Leg 1: Pick a game
    leg1_sport = st.selectbox("Leg 1 Sport", SPORTS)
    leg1_away = st.selectbox("Leg 1 Away", TEAM_MAP.get(leg1_sport, NBA_TEAMS))
    leg1_home = st.selectbox("Leg 1 Home", TEAM_MAP.get(leg1_sport, NBA_TEAMS))

    leg1_proj = call_api(leg1_away, leg1_home, leg1_sport)
    leg1_tc = "—"
    leg1_edge = "—"
    leg1_signal = "—"
    if leg1_proj and "error" not in leg1_proj:
        a = leg1_proj.get("assessment", {}) or {}
        leg1_tc = a.get("tc_total") or leg1_proj.get("tc_combined") or "—"
        leg1_edge = leg1_proj.get("edge") or a.get("edge") or "—"
        leg1_signal = leg1_proj.get("signal") or a.get("signal") or "NO MARKET"

    st.markdown(f"**Leg 1:** {leg1_sport} — {leg1_away} @ {leg1_home}")
    st.metric("TC Total", fmt(leg1_tc))
    st.metric("Edge", f"{leg1_edge:+.1f}" if isinstance(leg1_edge, (int, float)) else fmt(leg1_edge))
    st.metric("Signal", leg1_signal)
    st.divider()

    # Leg 2: Pick a game
    leg2_sport = st.selectbox("Leg 2 Sport", SPORTS)
    leg2_away = st.selectbox("Leg 2 Away", TEAM_MAP.get(leg2_sport, NBA_TEAMS))
    leg2_home = st.selectbox("Leg 2 Home", TEAM_MAP.get(leg2_sport, NBA_TEAMS))

    leg2_proj = call_api(leg2_away, leg2_home, leg2_sport)
    leg2_tc = "—"
    leg2_edge = "—"
    leg2_signal = "—"
    if leg2_proj and "error" not in leg2_proj:
        a = leg2_proj.get("assessment", {}) or {}
        leg2_tc = a.get("tc_total") or leg2_proj.get("tc_combined") or "—"
        leg2_edge = leg2_proj.get("edge") or a.get("edge") or "—"
        leg2_signal = leg2_proj.get("signal") or a.get("signal") or "NO MARKET"

    st.markdown(f"**Leg 2:** {leg2_sport} — {leg2_away} @ {leg2_home}")
    st.metric("TC Total", fmt(leg2_tc))
    st.metric("Edge", f"{leg2_edge:+.1f}" if isinstance(leg2_edge, (int, float)) else fmt(leg2_edge))
    st.metric("Signal", leg2_signal)
    st.divider()

    # Leg 3: Pick a game
    leg3_sport = st.selectbox("Leg 3 Sport", SPORTS)
    leg3_away = st.selectbox("Leg 3 Away", TEAM_MAP.get(leg3_sport, NBA_TEAMS))
    leg3_home = st.selectbox("Leg 3 Home", TEAM_MAP.get(leg3_sport, NBA_TEAMS))

    leg3_proj = call_api(leg3_away, leg3_home, leg3_sport)
    leg3_tc = "—"
    leg3_edge = "—"
    leg3_signal = "—"
    if leg3_proj and "error" not in leg3_proj:
        a = leg3_proj.get("assessment", {}) or {}
        leg3_tc = a.get("tc_total") or leg3_proj.get("tc_combined") or "—"
        leg3_edge = leg3_proj.get("edge") or a.get("edge") or "—"
        leg3_signal = leg3_proj.get("signal") or a.get("signal") or "NO MARKET"

    st.markdown(f"**Leg 3:** {leg3_sport} — {leg3_away} @ {leg3_home}")
    st.metric("TC Total", fmt(leg3_tc))
    st.metric("Edge", f"{leg3_edge:+.1f}" if isinstance(leg3_edge, (int, float)) else fmt(leg3_edge))
    st.metric("Signal", leg3_signal)
    st.divider()

    # Parlay Summary
    st.markdown("### Parlay Summary")
    st.markdown(f"**Legs:** {leg1_sport} + {leg2_sport} + {leg3_sport}")
    st.markdown(f"**TC Totals:** {fmt(leg1_tc)} + {fmt(leg2_tc)} + {fmt(leg3_tc)}")
    st.markdown(f"**Edge:** {leg1_edge} + {leg2_edge} + {leg3_edge}")
    st.markdown(f"**Signals:** {leg1_signal} + {leg2_signal} + {leg3_signal}")
    st.divider()

    # Parlay Action
    st.markdown("### Parlay Action")
    st.caption("Click **Build Parlay** to lock in this multi-leg parlay.")
    if st.button("🔒 Build Parlay", use_container_width=True):
        st.session_state["parlay"] = {
            "legs": [
                {"sport": leg1_sport, "away": leg1_away, "home": leg1_home, "tc": leg1_tc, "edge": leg1_edge, "signal": leg1_signal},
                {"sport": leg2_sport, "away": leg2_away, "home": leg2_home, "tc": leg2_tc, "edge": leg2_edge, "signal": leg2_signal},
                {"sport": leg3_sport, "away": leg3_away, "home": leg3_home, "tc": leg3_tc, "edge": leg3_edge, "signal": leg3_signal},
            ],
            "total_tc": sum(float(leg.get("tc", "0")) for leg in st.session_state["parlay"]["legs"]),
            "total_edge": sum(float(leg.get("edge", "0")) for leg in st.session_state["parlay"]["legs"]),
            "signals": [leg.get("signal") for leg in st.session_state["parlay"]["legs"]],
        }
        st.success("✅ Parlay locked in!")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — SLATE (auto-populates from live projections)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_live_slate(sport: str) -> dict:
    """Fetch live slate for a single sport."""
    try:
        r = requests.get(
            f"{BASE_URL}/api/tc",
            params={"sport": sport, "mode": "live-stats"},
            timeout=30,
            headers={"Accept": "application/json"},
        )
        if r.ok:
            return r.json()
        return {"error": f"API {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _format_game_time(game: dict) -> str:
    """Format game time: use ESPN detail if available, else parse date."""
    detail = game.get("detail") or ""
    if detail and "at" in detail:
        # "Wed, June 3rd at 8:30 PM EDT" -> "Wed 8:30 PM EDT"
        try:
            parts = detail.split(" at ")
            day_part = parts[0].split(",")[0]  # "Wed"
            time_part = parts[1] if len(parts) > 1 else detail
            return f"{day_part} {time_part}"
        except Exception:
            return detail
    return game.get("date", "—")


def _build_slate_row(game: dict, sport: str) -> dict:
    """Build a single slate row with TC projection + DK total."""
    aw = game.get("away", {}) or {}
    hm = game.get("home", {}) or {}
    dk_total = game.get("dk_total") or game.get("total")

    # Auto-generate TC projection for this game
    tc_proj = call_api(aw.get("team", ""), hm.get("team", ""), sport, mode="project")
    tc_total = "—"
    tc_line = "—"
    edge = "—"
    signal = "—"
    if tc_proj and "error" not in tc_proj:
        a = tc_proj.get("assessment", {}) or {}
        tc_total = a.get("tc_total") or tc_proj.get("tc_combined") or "—"
        tc_line = a.get("tc_line") or tc_proj.get("tc_line") or "—"
        edge_raw = tc_proj.get("edge") or a.get("edge")
        if edge_raw is not None:
            try:
                edge_val = float(edge_raw)
                edge = f"{edge_val:+.1f}"
                # Compare to DK total
                if dk_total and dk_total != "—":
                    dk_f = float(dk_total)
                    if tc_total != "—":
                        try:
                            diff = float(tc_total) - dk_f
                            if diff > 2:
                                signal = "OVER"
                            elif diff < -2:
                                signal = "UNDER"
                            else:
                                signal = "PASS"
                        except (TypeError, ValueError):
                            pass
            except (TypeError, ValueError):
                pass

    return {
        "Sport": sport,
        "Time": _format_game_time(game),
        "Away": f"{aw.get('team','?')} {aw.get('score','') if game.get('completed') else ''}".strip(),
        "Home": f"{hm.get('team','?')} {hm.get('score','') if game.get('completed') else ''}".strip(),
        "Status": game.get("status", "—"),
        "DK Total": dk_total if dk_total else "—",
        "TC Total": tc_total,
        "TC Line": tc_line,
        "Edge": edge,
        "Signal": signal,
        "Matchup": game.get("matchup") or game.get("name", "—"),
    }


with tab_slate:
    st.markdown("### 📅 Live Slate — Auto-Populated")
    st.caption(
        "Pulls today's games from live ESPN data, auto-generates TC projections "
        "for each game, and computes edge vs DK total. Click **Refresh Slate** to "
        "reload all sports."
    )

    # Sport filter — default to both NBA + WNBA (active season)
    sport_choice = st.multiselect(
        "Filter by sport",
        SPORTS,
        default=["NBA", "WNBA"],
        key="slate_sport_filter",
    )

    if "slate_data" not in st.session_state:
        st.session_state["slate_data"] = None
    if "slate_filter" not in st.session_state:
        st.session_state["slate_filter"] = None

    col_refresh, col_nba, col_wnba = st.columns([2, 1, 1])
    with col_refresh:
        refresh_clicked = st.button("🔄  Refresh Slate", use_container_width=True, type="primary")
    with col_nba:
        nba_clicked = st.button("🏀  NBA Only", use_container_width=True)
    with col_wnba:
        wnba_clicked = st.button("⛹️  WNBA Only", use_container_width=True)

    if nba_clicked:
        sport_choice = ["NBA"]
        st.session_state["slate_filter"] = ["NBA"]
    if wnba_clicked:
        sport_choice = ["WNBA"]
        st.session_state["slate_filter"] = ["WNBA"]
    if st.session_state.get("slate_filter") and not refresh_clicked and not nba_clicked and not wnba_clicked:
        sport_choice = st.session_state["slate_filter"]

    if refresh_clicked or nba_clicked or wnba_clicked or st.session_state["slate_data"] is None:
        with st.spinner("Loading live slate from all sports…"):
            all_rows = []
            errors = []
            for sp in sport_choice:
                with st.spinner(f"Fetching {sp} slate…"):
                    slate = _fetch_live_slate(sp)
                if "error" in slate:
                    errors.append(f"**{sp}**: {slate['error']}")
                    continue
                games = slate.get("games", [])
                if not games:
                    errors.append(f"**{sp}**: No games scheduled today")
                    continue
                for g in games:
                    all_rows.append(_build_slate_row(g, sp))

            st.session_state["slate_data"] = {
                "rows": all_rows,
                "errors": errors,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    slate_data = st.session_state.get("slate_data")
    if slate_data:
        rows = slate_data.get("rows", [])
        errors = slate_data.get("errors", [])
        ts = slate_data.get("timestamp", "")
        st.caption(f"Last loaded: {ts}")

        if errors:
            with st.expander(f"⚠️ {len(errors)} sport(s) had no games", expanded=False):
                for e in errors:
                    st.caption(e)

        if not rows:
            st.warning(
                "No games found for the selected sports today. "
                "Try **WNBA Only** or **NBA Only**, or check back during the season."
            )
        else:
            st.success(f"**{len(rows)}** game(s) loaded · auto-projections complete")

            # Group by sport for clarity
            sports_loaded = sorted(set(r["Sport"] for r in rows))
            for sp in sports_loaded:
                sp_rows = [r for r in rows if r["Sport"] == sp]
                with st.expander(f"**{sp}** — {len(sp_rows)} game(s)", expanded=True):
                    st.dataframe(
                        sp_rows,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "DK Total": st.column_config.NumberColumn(format="%.1f"),
                            "TC Total": st.column_config.NumberColumn(format="%.1f"),
                            "TC Line": st.column_config.NumberColumn(format="%.1f"),
                        },
                    )

            # Combined view
            st.markdown("---")
            st.markdown("**All Sports Combined**")
            st.dataframe(rows, use_container_width=True, hide_index=True)

            # Top 8 Window widget
            st.markdown("---")
            st.markdown("**Top 8 Window**")
            st.dataframe(rows, use_container_width=True, hide_index=True)

            # Action: send a game to Project tab
            st.markdown("---")
            st.markdown("**Send to Project Tab**")
            game_options = [f"{r['Sport']}: {r['Matchup']}" for r in rows]
            if game_options:
                pick = st.selectbox("Pick a game", game_options, key="slate_pick")
                if st.button("📊  Load this game in Project tab", use_container_width=True):
                    picked_row = rows[game_options.index(pick)]
                    # Parse "NBA: NYK@SAS" -> sport=NBA, away=NYK, home=SAS
                    sp, matchup = pick.split(":", 1)
                    parts = matchup.strip().split("@")
                    if len(parts) == 2:
                        st.session_state["prefill_sport"] = sp.strip()
                        st.session_state["prefill_away"] = parts[0].strip()
                        st.session_state["prefill_home"] = parts[1].strip()
                        st.success(
                            f"✅ Loaded {sp.strip()} {parts[0].strip()} @ {parts[1].strip()} — "
                            f"go to **📊 Project Game** tab."
                        )

    st.markdown("---")
    st.markdown(
        "**How This Works:**"
        "1. Live ESPN data → today's games for each selected sport"
        "2. Auto TC projection → calls `/api/tc` for each game (PTS/REB/AST etc.)"
        "3. Edge = TC Total vs DK Total → OVER / UNDER / PASS signal"
        "4. Click any game → loads into Project tab for full prop breakdown"
        "5. All from one click — no manual entry needed"
    )

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Sports TC Dashboard  ·  Powered by Zo Computer  ·  "
    "stat × 0.85 · Q × 0.55 · OUT = 0 · Line = TC × 0.88 · Edge = TC − Line  ·  "
    "DK game totals stored independently — TC applies to player props only"
)