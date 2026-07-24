"""🏆 TC SPORTS DASHBOARD — Tyson's Money Dashboard

Data Sources:
  - picks.db (daily_picks.py output → picks + combos tables)
  - tc_pipeline.db (grade_picks.py → graded_picks + bet_tracking tables)  
  - ESPN public API (live games / lines)
  - Self-edge projections (when real lines unavailable)
"""
import sqlite3
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

st.set_page_config(page_title="TC Sports Dashboard", page_icon="🏆", layout="wide")

PICKS_DB = Path("/home/workspace/Projects/data/picks.db")
PIPELINE_DB = Path("/home/workspace/Projects/data/tc_pipeline.db")

st.markdown("""
<style>
    .stat-card { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                 border: 1px solid #0f3460; border-radius: 12px; padding: 20px; text-align: center; }
    .stat-card .label { color: #a0a0b0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .stat-card .value { color: #e94560; font-size: 36px; font-weight: 800; }
    .top-pick { background: #16213e; border: 1px solid #333; border-radius: 10px; padding: 12px; margin: 4px 0; }
    .top-pick .player { font-size: 18px; font-weight: 700; color: #e94560; }
    .top-pick .detail { color: #a0a0b0; font-size: 13px; }
    .sport-btn { text-align: center; padding: 8px; border-radius: 8px; border: 1px solid #333; 
                 background: #1a1a2e; margin: 2px; cursor: pointer; }
    .edge-badge { display: inline-block; background: #e94560; color: white; padding: 2px 8px; 
                  border-radius: 4px; font-size: 12px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── DATA LOADERS ──────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_picks():
    conn = sqlite3.connect(str(PICKS_DB))
    df = pd.read_sql_query("SELECT * FROM picks ORDER BY ABS(edge) DESC", conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_graded():
    conn = sqlite3.connect(str(PIPELINE_DB))
    df = pd.read_sql_query("SELECT * FROM graded_picks ORDER BY date DESC", conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_combos():
    conn = sqlite3.connect(str(PICKS_DB))
    df = pd.read_sql_query("SELECT * FROM combos ORDER BY ABS(edge) DESC", conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_picks_today():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(PICKS_DB))
    df = pd.read_sql_query("SELECT * FROM picks WHERE date = ? ORDER BY ABS(edge) DESC", conn, params=(today,))
    conn.close()
    return df

def compute_stats(graded):
    total = len(graded)
    hits = int(graded['hit'].sum()) if 'hit' in graded.columns else 0
    hit_rate = round(hits / total * 100, 1) if total > 0 else 0
    profit = round(graded['profit'].sum(), 0) if 'profit' in graded.columns else 0
    return total, hits, hit_rate, profit

def top_stat(picks):
    """Find the best-performing stat by edge across sports."""
    if picks.empty:
        return "MLB", 0
    sport_edges = picks.groupby('league')['edge'].apply(lambda x: abs(x).max())
    if sport_edges.empty:
        return "MLB", 0
    best_league = sport_edges.idxmax()
    best_pct = round(sport_edges.max() * 100, 1)
    return best_league, best_pct

def sport_breakdown(graded):
    """Hit rate and count by sport from graded picks."""
    out = {}
    for sport in ['wnba', 'mlb', 'wc', 'nfl']:
        sub = graded[graded['sport'] == sport] if 'sport' in graded.columns else pd.DataFrame()
        total = len(sub)
        hits = int(sub['hit'].sum()) if not sub.empty and 'hit' in sub.columns else 0
        rate = round(hits / total * 100, 1) if total > 0 else 0
        out[sport] = {'total': total, 'hits': hits, 'rate': rate}
    return out

# ── LOAD DATA ─────────────────────────────────────────────────

picks = load_picks()
graded = load_graded()
combos_df = load_combos()
today_picks = load_picks_today()

total_graded, total_hits, hit_rate, profit = compute_stats(graded)
best_league, best_pct = top_stat(picks)
sports = sport_breakdown(graded)

# ── SESSION STATE ─────────────────────────────────────────────

if 'active_sport' not in st.session_state:
    st.session_state.active_sport = 'ALL'
if 'active_filter' not in st.session_state:
    st.session_state.active_filter = None
if 'show_combos' not in st.session_state:
    st.session_state.show_combos = False
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'ALL PICKS'

# ── TOP BUTTON ROW ────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("🔍 ALL PICKS", use_container_width=True, 
                 type="primary" if st.session_state.view_mode == 'ALL PICKS' else "secondary"):
        st.session_state.view_mode = 'ALL PICKS'
        st.session_state.show_combos = False
        st.rerun()
with c2:
    if st.button("⭐ TOP 4 PICKS", use_container_width=True,
                 type="primary" if st.session_state.view_mode == 'TOP 4 PICKS' else "secondary"):
        st.session_state.view_mode = 'TOP 4 PICKS'
        st.session_state.show_combos = False
        st.rerun()
with c3:
    if st.button("📈 BEST EDGE", use_container_width=True,
                 type="primary" if st.session_state.view_mode == 'BEST EDGE' else "secondary"):
        st.session_state.view_mode = 'BEST EDGE'
        st.session_state.show_combos = False
        st.rerun()
with c4:
    btn_label = f"{best_league.upper()} +{best_pct}%"
    if st.button(btn_label, use_container_width=True, type="secondary"):
        st.session_state.active_sport = 'MLB'
        st.session_state.view_mode = 'ALL PICKS'
        st.rerun()

st.divider()

# ── STAT CARDS ────────────────────────────────────────────────

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("TOTAL PICKS", f"{len(picks):,}")
with m2:
    st.metric("HIT RATE", f"{hit_rate}%")
with m3:
    st.metric("PROFIT", f"${profit:,.0f}")
with m4:
    st.metric("GRADED", f"{total_graded:,}")

st.divider()

# ── STAT FILTER BUTTONS ───────────────────────────────────────

ALL_STATS = ['PTS', 'REB', 'AST', '3PM', 'STL', 'BLK', 'FG%', 'HR', 'RBI', 'ERA', 'WHIP', 'GOALS', 'ASSISTS', 'SOG']
st.markdown("**Click stat to filter →**")
filter_cols = st.columns(len(ALL_STATS))
for i, stat in enumerate(ALL_STATS):
    with filter_cols[i]:
        is_active = st.session_state.active_filter == stat
        if st.button(stat, key=f"f_{stat}", use_container_width=True,
                     type="primary" if is_active else "secondary",
                     help=f"Show only {stat} picks"):
            if is_active:
                st.session_state.active_filter = None
            else:
                st.session_state.active_filter = stat
            st.rerun()

st.divider()

# ── SPORT CARDS ───────────────────────────────────────────────

s1, s2, s3, s4 = st.columns(4)
emoji_map = {'wnba': '🏀', 'mlb': '⚾', 'wc': '⚽', 'nfl': '🏈'}
for col, (sport, emoji) in zip([s1, s2, s3, s4], emoji_map.items()):
    s = sports.get(sport, {'rate': 0, 'hits': 0, 'total': 0})
    with col:
        active = st.session_state.active_sport == sport.upper()
        border = "2px solid #e94560" if active else "1px solid #333"
        st.markdown(f"""
        <div style="background:#1a1a2e;border:{border};border-radius:12px;padding:15px;text-align:center;
                    cursor:pointer" onclick="">
            <div style="font-size:28px">{emoji}</div>
            <div style="font-size:14px;color:#a0a0b0;margin-top:6px">{sport.upper()}</div>
            <div style="font-size:20px;font-weight:700;color:#e94560">{s['rate']}% Hit</div>
            <div style="font-size:12px;color:#a0a0b0">{s['hits']}/{s['total']} picks</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── MAIN CONTENT: ALL PICKS ───────────────────────────────────

filtered = picks.copy()

# Apply sport filter
if st.session_state.active_sport != 'ALL':
    filtered = filtered[filtered['league'].str.upper() == st.session_state.active_sport]

# Apply stat filter
if st.session_state.active_filter:
    filtered = filtered[filtered['stat'].str.upper() == st.session_state.active_filter.upper()]

# Apply view mode
if st.session_state.view_mode == 'TOP 4 PICKS':
    filtered = filtered.head(4)
elif st.session_state.view_mode == 'BEST EDGE':
    filtered = filtered.sort_values('edge', key=lambda x: abs(x), ascending=False).head(20)

# Display picks
count = len(filtered)
if st.session_state.view_mode != 'BEST EDGE':
    sport_label = st.session_state.active_sport if st.session_state.active_sport != 'ALL' else 'ALL SPORTS'
    hits_here = 0
    profit_here = 0
    st.markdown(f"### {sport_label}  |  PICKS: {count:,}")

if filtered.empty:
    st.info("No picks found with current filters.")
else:
    for _, row in filtered.iterrows():
        edge_val = float(row['edge'])
        edge_sign = "+" if edge_val > 0 else ""
        edge_color = "#4caf50" if edge_val > 0 else "#e94560"
        direction = row.get('direction', '').upper()
        signal = row.get('signal', 'SELF_EDGE')

        with st.container():
            cols = st.columns([3, 2, 2, 1, 2, 1])
            with cols[0]:
                st.markdown(f"**{row['player']}**  \n<small style='color:#a0a0b0'>{row['team']} · {row['league'].upper()}</small>", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"**{row['stat']}** {direction}")
            with cols[2]:
                st.markdown(f"Proj: `{float(row['tc_projection']):.1f}`  \nLine: `{float(row['market_line']):.1f}`")
            with cols[3]:
                st.markdown(f"<span style='color:{edge_color};font-weight:700;font-size:18px'>{edge_sign}{edge_val:.2f}</span>", unsafe_allow_html=True)
            with cols[4]:
                st.markdown(f"`{signal}`")
            with cols[5]:
                if row.get('matchup'):
                    st.markdown(f"<small style='color:#a0a0b0'>{row['matchup']}</small>", unsafe_allow_html=True)
            st.divider()

# ── COMBOS SECTION ────────────────────────────────────────────

st.divider()
combo_col1, combo_col2 = st.columns([1, 4])
with combo_col1:
    sport_label = st.session_state.active_sport if st.session_state.active_sport != 'ALL' else 'SPORTS'
    if st.button(f"🧩 {sport_label} COMBOS", use_container_width=True, 
                 type="primary" if st.session_state.show_combos else "secondary"):
        st.session_state.show_combos = not st.session_state.show_combos
        st.rerun()

if st.session_state.show_combos and not combos_df.empty:
    st.markdown(f"### 🧩 {sport_label} COMBOS — Generated Parlays")
    active_combos = combos_df[combos_df['league'].str.upper() == st.session_state.active_sport] if st.session_state.active_sport != 'ALL' and not combos_df.empty else combos_df
    for _, row in active_combos.iterrows():
        edge_val = float(row['edge'])
        edge_sign = "+" if edge_val > 0 else ""
        with st.container():
            st.markdown(f"""
            **{row['players']}** · {row['combo_type']}
            Proj: `{float(row['combined_projection']):.1f}` vs Line: `{float(row['combined_line']):.1f}`
            Edge: <span style="color:#e94560;font-weight:700">{edge_sign}{edge_val:.2f}</span>
            """)

# ── LIVE GAMES ────────────────────────────────────────────────

# ── LIVE ODDS COMPARISON (DK vs FD) ────────────────────────────
try:
    st.divider()
    st.markdown("### 📊 LIVE DK vs FD ODDS")
    from src.adapters.theoddsapi_adapter import get_odds_comparison
    
    col1, col2 = st.columns(2)
    with col1:
        sport_select = st.selectbox("Sport", ["mlb", "wnba"], key="odds_comp_sport")
    with col2:
        st.caption("Lines refresh every 60s · Source: theoddsapi.com")
    
    odds_data = get_odds_comparison(sport_select, bookmakers="draftkings,fanduel")
    
    if odds_data and odds_data.get("comparisons"):
        comparisons = odds_data["comparisons"]
        rows = []
        for comp in comparisons[:20]:
            dk = comp.get("draftkings", {})
            fd = comp.get("fanduel", {})
            dk_line = dk.get("line", "—")
            fd_line = fd.get("line", "—")
            delta = ""
            if isinstance(dk_line, (int, float)) and isinstance(fd_line, (int, float)):
                delta = f"{dk_line - fd_line:+.1f}"
            best = "DK" if dk.get("edge", 0) > fd.get("edge", 0) else "FD"
            rows.append({
                "Player": comp.get("player", ""),
                "Stat": comp.get("stat", ""),
                "DK Line": dk_line,
                "FD Line": fd_line,
                "Δ": delta,
                "Best": best
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption(f"{len(comparisons)} props compared · Updated: {odds_data.get("timestamp", "")}")
    else:
        st.info(f"No live odds available for {sport_select.upper()} — games may not be active or no props posted yet.")
except Exception as e:
    st.caption(f"Odds comparison unavailable: {e}")
st.divider()
st.markdown("### 📡 LIVE GAMES")

try:
    from espn_scraper import get_live_games
    live_games = get_live_games()
    if live_games:
        display_count = min(5, len(live_games))
        game_cols = st.columns(display_count)
        for i in range(display_count):
            game = live_games[i]
            with game_cols[i]:
                st.markdown(f"""<div style="background:#1a1a2e;border:1px solid #333;border-radius:8px;
                    padding:10px;text-align:center">
                    <div style="font-size:12px;color:#a0a0b0">{game.get('league','')}</div>
                    <div style="font-weight:700">{game.get('away','')} @ {game.get('home','')}</div>
                    <div style="color:#e94560;font-weight:700">{game.get('status','')}</div>
                    </div>""", unsafe_allow_html=True)
        if len(live_games) > 5:
            st.caption(f"+ {len(live_games) - 5} more games not shown")
    else:
        st.info("No live games right now.")
except Exception as e:
    st.caption(f"Live games unavailable: {e}")

# ── DATA SOURCES ──────────────────────────────────────────────

st.divider()
with st.expander("📋 Data Sources", expanded=False):
    st.markdown("""
    | Source | Table/File | Description |
    |--------|-----------|-------------|
    | `picks.db` | `picks` | Live picks from `daily_picks.py` |
    | `picks.db` | `combos` | Generated parlays |
    | `tc_pipeline.db` | `graded_picks` | Historical graded picks + profits |
    | `tc_pipeline.db` | `bet_tracking` | Bet settlement tracking |
    | ESPN API | live games | Scoreboard / schedule |
    | Self-edge | projections | TC model projections (when lines unavailable) |
    """)

# ── TOP BUTTON ROW ──
bcol1, bcol2, bcol3, bcol4 = st.columns(4)
with bcol1:
    st.button("📋 ALL PICKS", use_container_width=True, type="primary")
with bcol2:
    st.button("⭐ TOP 4 PICKS", use_container_width=True)
with bcol3:
    st.button("🔥 BEST EDGE", use_container_width=True)
with bcol4:
    st.button("📊 MLB +64.2%", use_container_width=True)

# ── KPI CARDS ──
m1, m2, m3, m4 = st.columns(4)
conn = sqlite3.connect(str(PIPELINE_DB))
graded = pd.read_sql_query("SELECT * FROM graded_picks", conn)
conn.close()

total_picks = len(graded)
total_hits = int(graded['hit'].sum()) if 'hit' in graded.columns else 0
hit_rate = round(total_hits / total_picks * 100, 1) if total_picks else 0
profit = round(graded['profit'].sum(), 0) if 'profit' in graded.columns else 0
graded_count = total_picks

with m1:
    st.metric("TOTAL PICKS", f"{total_picks:,}")
with m2:
    st.metric("HIT RATE", f"{hit_rate}%")
with m3:
    st.metric("PROFIT", f"${profit:,.0f}")
with m4:
    st.metric("GRADED", f"{graded_count:,}")

# ── STAT FILTER BUTTONS ──
st.markdown("---")
stats = ["PTS", "REB", "AST", "3PM", "STL", "BLK", "FG%", "HR", "RBI", 
         "ERA", "WHIP", "GOALS", "ASSISTS", "SOG"]
cols = st.columns(len(stats))
selected_stat = None
for i, s in enumerate(stats):
    with cols[i]:
        if st.button(s, key=f"stat_{s}", use_container_width=True):
            selected_stat = s
            st.session_state.selected_stat = s

st.session_state.setdefault('selected_stat', None)
selected_stat = st.session_state.selected_stat
if selected_stat:
    st.success(f"Filtered by: **{selected_stat}**")

st.markdown("---")

# ── SPORT CARDS ──
sc1, sc2, sc3, sc4 = st.columns(4)

sports_data = {
    "WNBA": {"picks": 0, "hits": 0, "hit_rate": 0},
    "MLB": {"picks": 0, "hits": 0, "hit_rate": 0},
    "WC": {"picks": 0, "hits": 0, "hit_rate": 0},
    "NFL": {"picks": 0, "hits": 0, "hit_rate": 0},
}

for _, row in graded.iterrows():
    sport = str(row.get('sport', '')).upper()
    if sport in sports_data:
        sports_data[sport]['picks'] += 1
        if row.get('hit', 0):
            sports_data[sport]['hits'] += 1

for s in sports_data:
    p = sports_data[s]['picks']
    h = sports_data[s]['hits']
    sports_data[s]['hit_rate'] = round(h / p * 100, 1) if p else 0

columns = [sc1, sc2, sc3, sc4]
for i, (sport, data) in enumerate(sports_data.items()):
    with columns[i]:
        st.markdown(f"""
        <div class="sport-card">
            <div style="font-size:18px; font-weight:700;">{sport}</div>
            <div style="font-size:28px; font-weight:800; color:#e94560;">{data['hit_rate']}%</div>
            <div style="font-size:12px; color:#888;">Hit Rate</div>
            <div style="font-size:13px; color:#aaa;">{data['hits']}/{data['picks']} picks</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── SPORT SELECT TABS ──
tab_labels = []
tab_icons = {"MLB": "⚾", "WNBA": "🏀", "WC": "⚽", "NFL": "🏈"}

conn = sqlite3.connect(str(PICKS_DB))
all_picks = pd.read_sql_query("SELECT * FROM picks ORDER BY date DESC, ABS(edge) DESC", conn)
conn.close()

if not all_picks.empty:
    for league in ["MLB", "WNBA", "WC", "NFL"]:
        league_data = all_picks[all_picks['league'].str.upper() == league]
        if not league_data.empty:
            picks_count = len(league_data)
            ec = all_picks['edge'].abs()
            mae = round(ec.mean(), 3) if not ec.empty else 0
            tab_labels.append(f"{tab_icons.get(league,'')} {league} ({picks_count} picks | MAE: {mae})")

    tabs = st.tabs(tab_labels)

    tab_leagues = ["MLB", "WNBA", "WC", "NFL"]
    for idx, tab in enumerate(tabs):
        league = tab_leagues[idx]
        if idx >= len(tab_labels):
            break
        with tab:
            league_picks = all_picks[all_picks['league'].str.upper() == league]
            if league_picks.empty:
                st.info(f"No {league} picks available.")
                continue

            st.markdown(f"### {league} Picks — {len(league_picks)} total")

            hits = league_picks['tc_projection'].notna().sum()
            profit_est = round(league_picks[league_picks['edge'] > 0].shape[0] * 0.91 * 100 - 
                              league_picks[league_picks['edge'] < 0].shape[0] * 100, 0)
            mae_val = round(league_picks['edge'].abs().mean(), 3)

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Picks", len(league_picks))
            with k2:
                st.metric("Hits projected", hits)
            with k3:
                st.metric("Est. Profit", f"${profit_est}")
            with k4:
                st.metric("MAE", mae_val)

            display_cols = ["player", "team", "stat", "tc_projection", "market_line", 
                           "edge", "direction", "matchup", "signal"]
            display_df = league_picks[display_cols].head(50)
            display_df.columns = [c.upper() for c in display_df.columns]
            st.dataframe(display_df, use_container_width=True, height=400)

            if st.button(f"📥 Export {league} CSV", key=f"export_{league}"):
                csv = league_picks.to_csv(index=False)
                st.download_button("Download", csv, f"{league.lower()}_picks.csv", "text/csv")

st.markdown("---")

# ── LIVE GAMES ──
st.subheader("📡 LIVE GAMES")
try:
    import requests
    resp = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard", timeout=5)
    if resp.status_code == 200:
        games = resp.json().get('events', [])
        st.caption(f"LIVE GAMES: {len(games)} via ESPN")
        gcols = st.columns(min(5, len(games)) if games else 1)
        for i, game in enumerate(games[:5]):
            with gcols[i % 5]:
                comps = game.get('competitions', [{}])[0]
                comps_list = comps.get('competitors', [])
                away = comps_list[0] if len(comps_list) > 0 else {}
                home = comps_list[1] if len(comps_list) > 1 else {}
                status = game.get('status', {}).get('type', {}).get('shortDetail', '')
                st.markdown(f"""
                <div style="background:#1a1a2e; border:1px solid #333; border-radius:8px; padding:10px; text-align:center;">
                    <div style="font-size:11px; color:#888;">{status}</div>
                    <div style="font-weight:700;">{away.get('team',{}).get('abbreviation','')} {away.get('score','')}</div>
                    <div style="font-weight:700;">{home.get('team',{}).get('abbreviation','')} {home.get('score','')}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("ESPN API unavailable")
except Exception:
    st.caption("ESPN live games unavailable")

# ── BEST EDGE TOP 20 ──
st.markdown("---")
st.subheader("🔥 BEST EDGE — TOP 20")

col_explain, _ = st.columns([3, 1])
with col_explain:
    conn = sqlite3.connect(str(PICKS_DB))
    edge_df = pd.read_sql_query("""
        SELECT player, league, stat, tc_projection, market_line, edge, direction, matchup, reason
        FROM picks
        WHERE reason IS NOT NULL AND reason != ''
        ORDER BY ABS(edge) DESC LIMIT 20
    """, conn)
    conn.close()

    for rank, (_, row) in enumerate(edge_df.iterrows(), 1):
        emoji = "📈" if row['edge'] > 0 else "📉"
        st.markdown(f"""
        **Rank {rank}:** {emoji} {row['player']} ({row['league']}) – {row['stat']} **{row['edge']:+.2f}** edge  
        📍 {row['matchup']} · {row['direction']} · {row['reason'][:120]}
        """)

# ── COMBOS ──
sport_label_bottom = st.session_state.active_sport if st.session_state.active_sport != 'ALL' else 'SPORTS'
st.subheader(f"🧩 {sport_label_bottom} COMBOS")
with st.expander("Click to view generated parlays"):
    try:
        conn = sqlite3.connect(str(PICKS_DB))
        league_filter = f"WHERE league = '{st.session_state.active_sport.lower()}'" if st.session_state.active_sport != 'ALL' else ""
        combos = pd.read_sql_query(f"SELECT * FROM combos {league_filter} ORDER BY ABS(edge) DESC LIMIT 10", conn)
        conn.close()
        for _, row in combos.iterrows():
            edge_val = float(row['edge'])
            edge_sign = "+" if edge_val > 0 else ""
            st.markdown(f"""
            **{row['combo_type']}** — Edge: **{row['edge']:+.2f}**
            {row['players']}
            Proj: `{float(row['combined_projection']):.1f}` vs Line: `{float(row['combined_line']):.1f}`
            ---
            """)
        if combos.empty:
            st.info("No combos available yet.")
    except Exception as e:
        st.info("No combos available yet.")

# ── FOOTER ──
st.markdown("---")
st.caption("TC Sports Engine · Self-Edge Projections · ESPN Free API · picks.db + tc_pipeline.db")
