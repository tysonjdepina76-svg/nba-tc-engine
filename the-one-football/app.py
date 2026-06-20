import streamlit as st
import numpy as np

st.set_page_config(page_title="THE ONE FOOTBALL", page_icon="🏈", layout="wide")

TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills",
    "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns",
    "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs",
    "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
    "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
    "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders"
]

POSITIONS = ["QB", "RB", "WR", "TE"]

QUICK_PLAYERS = {
    "QB": ["Dak Prescott", "Kyler Murray", "Patrick Mahomes", "Anthony Richardson", "Jordan Love"],
    "RB": ["Bijan Robinson", "Jonathan Taylor", "Zack Moss", "Tyler Allgeier"],
    "WR": ["Drake London", "Michael Pittman Jr.", "Alec Pierce", "Darnell Mooney"],
    "TE": ["Kyle Pitts", "Kylen Granson", "Jonnu Smith"]
}

STATS_BY_POSITION = {
    "QB": ["passing_yards", "passing_tds", "rushing_yards", "rushing_tds"],
    "RB": ["rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds", "receptions"],
    "WR": ["receiving_yards", "receiving_tds", "receptions"],
    "TE": ["receiving_yards", "receiving_tds", "receptions"]
}

LEAGUE_AVG = {
    "QB": {"passing_yards": 228, "passing_tds": 1.3, "rushing_yards": 18, "rushing_tds": 0.2},
    "RB": {"rushing_yards": 68, "rushing_tds": 0.45, "receiving_yards": 22, "receiving_tds": 0.1, "receptions": 2.8},
    "WR": {"receiving_yards": 51, "receiving_tds": 0.27, "receptions": 3.8},
    "TE": {"receiving_yards": 35, "receiving_tds": 0.18, "receptions": 2.9},
}

TEAM_TOTAL_DEFAULTS = {"good": 24.5, "average": 21.5, "poor": 18.5}

if 'games' not in st.session_state:
    st.session_state.games = []
if 'players' not in st.session_state:
    st.session_state.players = {}
if 'current_game' not in st.session_state:
    st.session_state.current_game = None
if 'results' not in st.session_state:
    st.session_state.results = []


def project_stat(position, stat_type, seasonal_avg, recent_avg, opp_def_rank,
                 home=True, team_total=22.0, injury_bonus=1.0, pace_factor=1.0):
    def_scale = {"elite": 0.90, "good": 0.95, "average": 1.0, "poor": 1.05, "dreadful": 1.10}
    defense_adj = def_scale.get(opp_def_rank.lower(), 1.0)
    home_adj = 1.06 if home else 1.0
    spread = 15 if "yards" in stat_type else (0.35 if "td" in stat_type else 1.2)
    weighted_avg = 0.41 * seasonal_avg + 0.36 * recent_avg + 0.20 * team_total + 0.03 * seasonal_avg
    proj = weighted_avg * defense_adj * home_adj * injury_bonus * pace_factor
    proj += np.random.normal(0, spread)
    proj = max(0, proj)
    return round(proj, 1)


def get_parlay_odds(legs):
    odds = {
        2: ("+264", 2.64), 3: ("+596", 5.96), 4: ("+1228", 11.28),
        5: ("+2435", 23.35), 6: ("+4700", 47.0), 8: ("+9500", 95.0),
        10: ("+25000", 250.0), 11: ("+35000", 350.0), 12: ("+40000", 400.0)
    }
    return odds.get(legs, ("+40000", 400.0))


st.title("🏈 THE ONE FOOTBALL — Projection Prop Builder")

tab1, tab2, tab3 = st.tabs(["Setup", "Players & Project", "Props & Results"])

with tab1:
    st.header("Game Setup")
    away = st.selectbox("Away", ["-- Select --"] + TEAMS, key="away")
    home = st.selectbox("Home", ["-- Select --"] + TEAMS, key="home")
    if st.button("Create Game"):
        if away != "-- Select --" and home != "-- Select --" and away != home:
            gt = away + " @ " + home
            if gt not in st.session_state.games:
                st.session_state.games.append(gt)
                st.session_state.current_game = gt
                st.session_state.players[gt] = []
                st.success("Game created!")
                st.rerun()
            else:
                st.error("Already exists")
        else:
            st.error("Pick two different teams")

    if st.session_state.games:
        sg = st.selectbox("Active Game", st.session_state.games)
        if st.button("Set Active"):
            st.session_state.current_game = sg
            st.success("Active: " + sg)
            st.rerun()

    if st.session_state.current_game:
        st.success("🎯 " + st.session_state.current_game)

with tab2:
    st.header("Add Player and Get Projections")
    if not st.session_state.current_game:
        st.warning("Set up a game first!")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            add_mode = st.radio("Quick or Manual?", ["Quick", "Manual"])
            if add_mode == "Quick":
                pos = st.selectbox("Pos", POSITIONS, key="qpos")
                name = st.selectbox("Player", QUICK_PLAYERS[pos], key="qname")
            else:
                pos = st.selectbox("Pos", POSITIONS, key="mpos")
                name = st.text_input("Player Name", key="mname")

            if st.button("Add & Show Projections"):
                if name:
                    for stat in STATS_BY_POSITION[pos]:
                        st.markdown(f"#### {name} — {stat.replace('_',' ').title()}")
                        stat_dflt = LEAGUE_AVG.get(pos, {}).get(stat, 40)
                        seas = st.number_input(f"Season Avg ({stat})", value=stat_dflt, key=f"sea_{stat}")
                        recent = st.number_input(f"Recent 3 Game Avg ({stat})", value=stat_dflt, key=f"rec_{stat}")
                        opp_def = st.selectbox("Defensive Rank", ["elite", "good", "average", "poor", "dreadful"], index=2, key=f"od_{stat}")
                        home_g = st.checkbox("Home", value=True, key=f"hm_{stat}")
                        tt_dflt = TEAM_TOTAL_DEFAULTS["average"]
                        team_total = st.number_input("Team Total", value=tt_dflt, key=f"tm_{stat}")
                        injury = st.slider("Injury/Boost", 0.95, 1.2, 1.0, 0.01, key=f"inj_{stat}")
                        pace = st.slider("Pace", 0.90, 1.10, 1.0, 0.01, key=f"pace_{stat}")
                        proj = project_stat(pos, stat, seas, recent, opp_def, home_g, team_total, injury, pace)
                        st.success(f"Projection: {proj}")
                        st.session_state.results.append({
                            'player': name, 'position': pos, 'stat': stat, 'projection': proj,
                            'details': dict(seasonal_avg=seas, recent_avg=recent, defense=opp_def, home=home_g,
                                             team_total=team_total, injury=injury, pace=pace)
                        })
                    st.rerun()
                else:
                    st.error("Enter player name")
        with col2:
            st.subheader("Current Players")
            if st.session_state.results:
                st.write(set([x['player'] for x in st.session_state.results]))
            else:
                st.info("Add a player above.")

with tab3:
    st.header("Props, Parlays, and Export")
    if not st.session_state.results:
        st.info("Add projections for props first.")
    else:
        st.write("Your Generated Props:")
        for rec in st.session_state.results:
            d = rec['details']
            st.write(f"{rec['player']} ({rec['position']}), {rec['stat'].replace('_',' ').title()}: {rec['projection']} ({d['defense']} D, {'Home' if d['home'] else 'Away'})")

        st.subheader("--- Parlay Builder ---")
        legs = st.slider("How many legs?", 2, min(12, len(st.session_state.results)), 4)
        parlay = st.session_state.results[:legs]
        slip = ""
        for i, leg in enumerate(parlay, 1):
            slip += f"{i}. {leg['player']} {leg['stat'].replace('_',' ').title()}: PROJ {leg['projection']}\n"
        st.code(slip)
        st.download_button(label="Export Your Parlay", data=slip, file_name="my_the_one_football_parlay.txt")

st.caption("🏈 THE ONE FOOTBALL — Plug-and-play, with projections, autofills, and full parlay support.")
