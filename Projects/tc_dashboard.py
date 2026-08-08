#!/usr/bin/env python3
"""TC DASHBOARD — Tonight's Picks · Pitching Window · Graded Summary"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
import sqlite3
import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

ET = timezone(timedelta(hours=-4))


def et_now():
    return datetime.now(timezone.utc).astimezone(ET).replace(tzinfo=None)


st.set_page_config(page_title="TC Dashboard", page_icon="📊", layout="wide")
st.title("📊 TC Dashboard")
st.caption(f"Last updated: {et_now().strftime('%Y-%m-%d %H:%M:%S')} ET")

today_et = et_now()
today_str = today_et.strftime("%Y-%m-%d")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🎯 Picks by Matchup", "⚾ Pitching Window", "📊 Graded Summary", "🃏 Combos", "📅 Schedule"]
)


@st.cache_data(ttl=60)
def load_today_picks(date_str):
    picks = []
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/picks.db")
        df = pd.read_sql_query(
            "SELECT * FROM picks WHERE date = ? ORDER BY league, matchup, stat, player",
            conn, params=(date_str,),
        )
        conn.close()
        # Combos live ONLY under the combos tab. Strip derived combo stats
        # (WNBA PRA/PR/PA, MLB BATTING/PITCHING and any '+' joined stat) so
        # they never appear as regular picks in tabs 1/2.
        combo_stats = {"PRA", "PR", "PA", "P+R+A", "P+R", "P+A",
                       "BATTING", "PITCHING", "PITCH+BAT", "SO+K",
                       "H+RBI", "R+RBI", "H+R", "HR+RBI"}
        if not df.empty and "stat" in df.columns:
            df = df[~df["stat"].astype(str).str.upper().str.strip().isin(combo_stats)
                    & ~df["stat"].astype(str).str.contains("+", case=False, na=False)]
        picks = df.to_dict("records")
    except Exception as e:
        st.sidebar.error(f"DB error: {e}")
    return picks


@st.cache_data(ttl=120)
def load_pitching_slate(date_str):
    path = Path(f"/home/workspace/data/pitching/pitching_slate_{date_str}.json")
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            games = data
        else:
            games = list(data.get("games", {}).values())
        for g in games:
            g.setdefault("matchup", f"{g.get('away','')} @ {g.get('home','')}")
            g.setdefault("away_team", g.get("away", ""))
            g.setdefault("home_team", g.get("home", ""))
        return games
    return []


@st.cache_data(ttl=120)
def load_schedule(date_str):
    path = Path(f"/home/workspace/data/schedule_{date_str}.json")
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        return data
    return {"mlb": [], "wnba": [], "updated": "", "total_mlb": 0, "total_wnba": 0}


@st.cache_data(ttl=300)
def load_graded_summary():
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/picks.db")
        total = conn.execute("SELECT COUNT(*) FROM picks").fetchone()[0]
        graded = conn.execute(
            "SELECT COUNT(*) FROM picks WHERE hit IS NOT NULL AND hit != 0"
        ).fetchone()[0]
        wins = conn.execute("SELECT COUNT(*) FROM picks WHERE hit = 1").fetchone()[0]
        profit = conn.execute(
            "SELECT COALESCE(SUM(profit), 0) FROM picks WHERE hit IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        hit_rate = (wins / graded * 100) if graded > 0 else 0
        return {"total": total, "graded": graded, "wins": wins, "hit_rate": hit_rate, "profit": profit}
    except Exception:
        return {"total": 0, "graded": 0, "wins": 0, "hit_rate": 0, "profit": 0}


@st.cache_data(ttl=300)
def load_graded_by_date(league="mlb"):
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/picks.db")
        df = pd.read_sql_query(
            """SELECT date, COUNT(*) as total,
                      SUM(CASE WHEN hit=1 THEN 1 ELSE 0 END) as wins,
                      SUM(CASE WHEN hit IS NOT NULL AND hit!=0 THEN 1 ELSE 0 END) as graded,
                      ROUND(SUM(CASE WHEN hit=1 THEN 1 ELSE 0 END)*100.0/
                            NULLIF(SUM(CASE WHEN hit IS NOT NULL AND hit!=0 THEN 1 ELSE 0 END),0), 1) as hit_rate
               FROM picks WHERE league=? AND hit IS NOT NULL
               GROUP BY date ORDER BY date DESC LIMIT 30""",
            conn, params=(league,),
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def load_today_combos(date_str, league="ALL"):
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/picks.db")
        if league.lower() == "all":
            df = pd.read_sql_query(
                "SELECT * FROM combos WHERE date = ? ORDER BY ABS(edge) DESC",
                conn, params=(date_str,),
            )
        else:
            df = pd.read_sql_query(
                "SELECT * FROM combos WHERE date = ? AND league = ? ORDER BY ABS(edge) DESC",
                conn, params=(date_str, league.lower()),
            )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Combo load error: {e}")
        return pd.DataFrame()


picks = load_today_picks(today_str)
summary = load_graded_summary()
pitching = load_pitching_slate(today_str)

# ═══════════════════════════════════════════════════════════════
# TAB 1 — PICKS BY MATCHUP
# ═══════════════════════════════════════════════════════════════
with tab1:
    league_filter = st.selectbox("League", ["ALL", "MLB", "WNBA"], key="league_tab1")
    date_filter = st.date_input("Date", today_et, key="date_tab1")
    refresh_btn = st.button("🔄 Refresh", key="refresh_tab1")

    if refresh_btn:
        st.cache_data.clear()
        st.rerun()

    df_date = load_today_picks(date_filter.strftime("%Y-%m-%d")) if date_filter.strftime(
        "%Y-%m-%d"
    ) != today_str else picks

    if df_date:
        df = pd.DataFrame(df_date)
        if league_filter != "ALL":
            df = df[df["league"] == league_filter.lower()]
        if not df.empty and "stat" in df.columns and "league" in df.columns:
            wnba_combo = {"PRA", "PR", "PA", "P+R+A", "P+R", "P+A"}
            mlb_combo = {"BATTING", "PITCHING", "PITCH+BAT", "SO+K", "H+RBI", "R+RBI", "H+R", "HR+RBI"}
            stat_u = df["stat"].astype(str).str.upper()
            is_combo = stat_u.str.contains("+")
            is_combo |= (df["league"].astype(str).str.lower().eq("wnba") & stat_u.isin(wnba_combo))
            is_combo |= (df["league"].astype(str).str.lower().eq("mlb") & stat_u.isin(mlb_combo))
            df = df[~is_combo]
        df = df.sort_values(["league", "matchup", "stat", "player"])
    else:
        df = pd.DataFrame()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📅 Picks", len(df) if not df.empty else 0)
    with col2:
        leagues = df["league"].value_counts().to_dict() if not df.empty else {}
        st.metric("⚾ MLB", leagues.get("mlb", 0))
    with col3:
        st.metric("🏀 WNBA", leagues.get("wnba", 0))

    if not df.empty:
        display_cols = [
            "league", "matchup", "player", "stat", "line", "tc_projection",
            "direction", "edge", "signal", "value",
        ]
        display = df[[c for c in display_cols if c in df.columns]]
        st.dataframe(display, use_container_width=True, height=600)

        matchups = df["matchup"].unique()
        sel_m = st.selectbox("Drill into matchup", ["All"] + sorted(matchups))
        if sel_m != "All":
            matchup_df = df[df["matchup"] == sel_m]
            st.dataframe(
                matchup_df[[c for c in display_cols if c in matchup_df.columns]],
                use_container_width=True, height=400,
            )
    else:
        st.info("No picks found for this date.")

# ═══════════════════════════════════════════════════════════════
# TAB 2 — PITCHING WINDOW
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("⚾ Today's Starting Pitchers & Bullpen Matchup")

    if not pitching:
        st.warning("No pitching data for today. Run `python3 Projects/generate_pitching.py --date {}`".format(today_str))
    else:
        st.caption(f"{len(pitching)} games loaded from pitching_slate_{today_str}.json")

        # Summary bar
        c1, c2, c3, c4 = st.columns(4)
        starters_known = sum(1 for g in pitching if g.get("away_starter") or g.get("home_starter"))
        with c1:
            st.metric("Matchups", len(pitching))
        with c2:
            st.metric("Starters Known", starters_known)
        with c3:
            st.metric("Pitching Picks", "87" if Path(f"/home/workspace/data/pitching/pitching_picks_{today_str}.json").exists() else "—")
        with c4:
            st.metric("Stat Source", "statsapi / pybaseball / ESPN")

        st.divider()

        for g in pitching:
            m = g["matchup"]
            away = g.get("away_team", "?")
            home = g.get("home_team", "?")
            away_sp = g.get("away_starter", "TBD")
            home_sp = g.get("home_starter", "TBD")
            away_proj = g.get("away_starter_proj", {}) or {}
            home_proj = g.get("home_starter_proj", {}) or {}
            away_bp = g.get("away_bullpen", {}) or {}
            home_bp = g.get("home_bullpen", {}) or {}

            with st.expander(f"🏟️ {m}  —  {away_sp} vs {home_sp}", expanded=len(pitching) <= 1):
                colA, colH = st.columns(2)

                # Away side
                with colA:
                    st.markdown(f"#### 🧢 {away} — {away_sp}")
                    asp = away_proj.get("season", {}) or {}
                    apj = away_proj.get("projected", {}) or {}

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("ERA", asp.get("era", "—"))
                    m2.metric("WHIP", asp.get("whip", "—"))
                    m3.metric("K/9", asp.get("k_9", "—"))
                    m4.metric("BB/9", asp.get("bb_9", "—"))

                    st.caption("Projected Today")
                    p1, p2, p3 = st.columns(3)
                    p1.metric("IP", apj.get("ip", "—"))
                    p2.metric("SO", apj.get("so", "—"))
                    p3.metric("ER", apj.get("er", "—"))

                    st.caption(f"vs Opponent RPG: {away_proj.get('vs_team_rpg', '—')}")
                    st.caption("**Bullpen**")
                    b1, b2, b3 = st.columns(3)
                    b1.metric("BP ERA", away_bp.get("era", "—"))
                    b2.metric("BP WHIP", away_bp.get("whip", "—"))
                    b3.metric("Proj IP", away_bp.get("projected_ip", "—"))

                # Home side
                with colH:
                    st.markdown(f"#### 🧢 {home} — {home_sp}")
                    hsp = home_proj.get("season", {}) or {}
                    hpj = home_proj.get("projected", {}) or {}

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("ERA", hsp.get("era", "—"))
                    m2.metric("WHIP", hsp.get("whip", "—"))
                    m3.metric("K/9", hsp.get("k_9", "—"))
                    m4.metric("BB/9", hsp.get("bb_9", "—"))

                    st.caption("Projected Today")
                    p1, p2, p3 = st.columns(3)
                    p1.metric("IP", hpj.get("ip", "—"))
                    p2.metric("SO", hpj.get("so", "—"))
                    p3.metric("ER", hpj.get("er", "—"))

                    st.caption(f"vs Opponent RPG: {home_proj.get('vs_team_rpg', '—')}")
                    st.caption("**Bullpen**")
                    b1, b2, b3 = st.columns(3)
                    b1.metric("BP ERA", home_bp.get("era", "—"))
                    b2.metric("BP WHIP", home_bp.get("whip", "—"))
                    b3.metric("Proj IP", home_bp.get("projected_ip", "—"))

                st.divider()

# ═══════════════════════════════════════════════════════════════
# TAB 3 — GRADED SUMMARY
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📈 Graded Picks Summary")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Picks", summary["total"])
    c2.metric("Graded", summary["graded"])
    c3.metric("Wins", summary["wins"])
    c4.metric("Hit Rate", f"{summary['hit_rate']:.1f}%")

    st.divider()
    league_sel = st.selectbox("League", ["mlb", "wnba"], key="graded_league")
    graded_df = load_graded_by_date(league_sel)

    if not graded_df.empty:
        st.dataframe(graded_df, use_container_width=True)
        fig = px.bar(graded_df, x="date", y="hit_rate", title=f"{league_sel.upper()} Daily Hit Rate (last 30 days)",
                     labels={"date": "Date", "hit_rate": "Hit Rate %"},
                     text_auto=".1f")
        fig.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No graded data available yet.")

# ═══════════════════════════════════════════════════════════════
# TAB 4 — COMBOS
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔥 Today's Top Combos (Correlated Multi-Leg Parlays)")

    cdf = load_today_combos(today_str)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Combos", len(cdf) if not cdf.empty else 0)
    with c2:
        mlb_c = len(cdf[cdf["league"].str.lower()=="mlb"]) if not cdf.empty and "league" in cdf.columns else 0
        st.metric("⚾ MLB", mlb_c)
    with c3:
        wnba_c = len(cdf[cdf["league"].str.lower()=="wnba"]) if not cdf.empty and "league" in cdf.columns else 0
        st.metric("🏀 WNBA", wnba_c)

    if not cdf.empty:
        display = cdf[["league", "combo_type", "players", "edge", "direction", "matchup",
                        "combined_projection", "combined_line"]]
        st.dataframe(display, use_container_width=True, height=500, column_config={
            "edge": st.column_config.NumberColumn(format="%.2f%%"),
            "combined_projection": st.column_config.NumberColumn(format="%.1f"),
            "combined_line": st.column_config.NumberColumn(format="%.1f"),
        })
    else:
        st.info("No combos generated for today yet. Run the daily pipeline to generate them.")

with tab5:
    st.subheader("📅 August 1, 2026 — Game Schedule")

    schedule = load_schedule(today_str)

    # MLB
    st.markdown("### ⚾ MLB — {0} Games".format(len(schedule.get('mlb', []))))
    if schedule.get('mlb'):
        mlb_cols = st.columns(3)
        for i, g_idx in enumerate(range(len(schedule['mlb']))):
            g = schedule['mlb'][g_idx]
            with mlb_cols[i % 3]:
                matchup_display = g.get('matchup', '?')
                time_str = g.get('time', 'TBD')
                # Count picks for this game
                db_key = "{0}_at_{1}".format(g.get('home', '?'), g.get('away', '?'))  # HOME_at_AWAY
                try:
                    pick_count = conn.execute(
                        "SELECT COUNT(*) FROM picks WHERE date=? AND LOWER(league)='mlb' AND matchup=?",
                        (today_str, db_key)
                    ).fetchone()[0]
                except:
                    pick_count = 0
                st.markdown(
                    "**{matchup}**  \n🕐 {time}  \n📊 {count} picks".format(
                        matchup=matchup_display, time=time_str, count=pick_count
                    )
                )
    else:
        st.info("No MLB schedule loaded.")

    # WNBA
    st.markdown("### 🏀 WNBA — {0} Games".format(len(schedule.get('wnba', []))))

    # Also show any WNBA games from DB not in schedule
    conn = sqlite3.connect("/home/workspace/Projects/data/picks.db")
    wnba_db_games = conn.execute(
        "SELECT DISTINCT matchup FROM picks WHERE date=? AND LOWER(league)='wnba' ORDER BY matchup",
        (today_str,)
    ).fetchall()

    wnba_schedule_matchups = set()
    if schedule.get('wnba'):
        for g in schedule['wnba']:
            db_key = "{0}_at_{1}".format(g.get('home', '?'), g.get('away', '?'))
            wnba_schedule_matchups.add(db_key)

    # Show schedule games first
    if schedule.get('wnba'):
        wnba_cols = st.columns(3)
        for i, g in enumerate(schedule['wnba']):
            with wnba_cols[i % 3]:
                matchup_display = g.get('matchup', '?')
                time_str = g.get('time', 'TBD')
                db_key = "{0}_at_{1}".format(g.get('home', '?'), g.get('away', '?'))
                try:
                    pick_count = conn.execute(
                        "SELECT COUNT(*) FROM picks WHERE date=? AND LOWER(league)='wnba' AND matchup=?",
                        (today_str, db_key)
                    ).fetchone()[0]
                except:
                    pick_count = 0
                st.markdown(
                    "**{matchup}**  \n🕐 {time}  \n📊 {count} picks".format(
                        matchup=matchup_display, time=time_str, count=pick_count
                    )
                )

    # Then any DB-only WNBA games
    extra_wnba = [(mup[0],) for mup in wnba_db_games if mup[0] not in wnba_schedule_matchups]
    if extra_wnba:
        st.markdown("**Additional WNBA games (from projections, times TBD):**")
        extra_cols = st.columns(3)
        for i, (mup,) in enumerate(extra_wnba):
            with extra_cols[i % 3]:
                parts = mup.split('_at_')
                display = "{away} @ {home}".format(away=parts[1] if len(parts)>1 else '?', home=parts[0])
                try:
                    pick_count = conn.execute(
                        "SELECT COUNT(*) FROM picks WHERE date=? AND LOWER(league)='wnba' AND matchup=?",
                        (today_str, mup)
                    ).fetchone()[0]
                except:
                    pick_count = 0
                st.markdown(
                    "**{matchup}**  \n🕐 TBD  \n📊 {count} picks".format(
                        matchup=display, count=pick_count
                    )
                )
    conn.close()
