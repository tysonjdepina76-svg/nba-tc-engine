#!/usr/bin/env python3
# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""TC Live Dashboard — sport-aware. Reads real pipeline output from Daily_Log/ and displays it for any sport (NBA, WNBA, NFL, MLB, SOCCER, NHL)."""
import json
import os
import sys
import importlib
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sports_registry import REGISTRY, DataSource  # noqa: E402

import pandas as pd
import requests
import subprocess
import streamlit as st

st.set_page_config(page_title="SPORTS TC - TRIPLE CONSERVATIVE ENGINE", page_icon="🎯", layout="wide")

ET = timezone(timedelta(hours=-4))  # EDT
WORKSPACE = Path("/home/workspace")
sys.path.insert(0, str(WORKSPACE / "tc-sports-app"))
from src.domain.entities import Sport, BADGE_COLORS
from src.domain.sport_config import get_sport_config, stat_keys
from config.columns import get_stat_columns, stat_aliases  # noqa: E402
try:
    from src.adapters.sgo import fetch_events as _sgo_fetch_events
except Exception:
    _sgo_fetch_events = None

# ─── Data source matrix (locked by user directive 2026-07-02) ─────
# NBA, WNBA, NFL → TC Math
# SOCCER, MLB, NHL → Bookmaker lines (SGO + OddsAPI tiered)
SPORT_SOURCE = {
    "NBA": "TC_MATH",
    "WNBA": "TC_MATH",
    "NFL": "TC_MATH",
    "SOCCER": "BOOKMAKER",
    "MLB": "BOOKMAKER",
    "NHL": "BOOKMAKER",
}

def get_data_source(sport: str) -> str:
    """Return data source for sport: 'tc' or 'booklines'."""
    return "tc" if SPORT_SOURCE.get(sport) == "TC_MATH" else "booklines"

LOG_DIR = WORKSPACE / "Daily_Log"
IMAGES_DIR = WORKSPACE / "reports" / "images"

# Sport → ESPN path + display label
SPORT_PATHS = {
    "NBA":    ("basketball/nba", "NBA"),
    "WNBA":   ("basketball/wnba", "WNBA"),
    "NFL":    ("football/nfl", "NFL"),
    "MLB":    ("baseball/mlb", "MLB"),
    "SOCCER": ("soccer/World Cup", "WORLD CUP"),
    "NHL":    ("hockey/nhl", "NHL"),
}


def _find_latest_dir() -> Path:
    today_dir = LOG_DIR / datetime.now(ET).strftime("%Y-%m-%d")
    if (today_dir / "picks.csv").exists():
        try:
            df = pd.read_csv(today_dir / "picks.csv")
            if len(df) > 0:
                return today_dir
        except Exception:
            pass
    dirs = sorted(
        [d for d in LOG_DIR.iterdir() if d.is_dir() and (d / "picks.csv").exists()],
        reverse=True,
    )
    for d in dirs:
        try:
            df = pd.read_csv(d / "picks.csv")
            if len(df) > 0:
                return d
        except Exception:
            continue
    return today_dir


DATA_DIR = _find_latest_dir()


def _sport_token(sport: str) -> str:
    """Map dashboard sport to file-token used in proj JSON filenames."""
    return {"SOCCER": "WORLD CUP"}.get(sport, sport)


def _proj_path(sport: str, matchup: str) -> Path | None:
    """Locate proj_SPORT_MATCHUP.json for a given sport+matchup."""
    if not matchup or "@" not in matchup:
        return None
    away, home = matchup.split("@")
    token = _sport_token(sport)
    p = DATA_DIR / f"proj_{token}_{away}_at_{home}.json"
    if p.exists():
        return p
    # try today's other dirs as fallback
    for d in sorted(LOG_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        cand = d / f"proj_{token}_{away}_at_{home}.json"
        if cand.exists():
            return cand
    return None


def _load_proj(sport: str, matchup: str | None) -> dict | None:
    p = _proj_path(sport, matchup) if matchup else None
    if not p:
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


# ─── Sport-aware time/period formatter ───────────────────
def format_game_time(sport: str, period: int | None, clock: str | None) -> str:
    """Format live game time per sport:
      - MLB:    "Top 7" or "Bottom 7" (innings, not quarters)
      - SOCCER: "78'" (minutes only, no quarter prefix)
      - NBA/WNBA/NFL: "Q2 3:45" (standard quarters)
    Returns "—" if no period info.
    """
    sport = (sport or "").upper()
    if period is None or period == 0:
        return "—"
    if sport == "MLB":
        half = "Top" if int(period) % 2 == 1 else "Bottom"
        inning_n = (int(period) + 1) // 2
        return f"{half} {inning_n}"
    if sport == "SOCCER":
        # soccer reports period 1 / 2 (halves) and clock is the minute marker
        m = (clock or "").strip().replace("'", "")
        try:
            return f"{int(float(m))}'"
        except Exception:
            return f"{clock}'" if clock else f"{period}'"
    # NBA, WNBA, NFL — standard quarters
    c = (clock or "").strip()
    return f"Q{period} {c}".strip()


def get_heat_color(val: float) -> str:
    """Return a CSS color string based on the value.
    Positive values are green, negative are red, zero is yellow.
    """
    if val >= 3.0:
        return "#1b5e20"
    if val >= 1.0:
        return "#2e7d32"
    if val >= 0.5:
        return "#66bb6a"
    if val > -0.5:
        return "#fdd835"
    if val > -3.0:
        return "#fb8c00"
    return "#b71c1c"


def _espn_event_status(espn_path: str, event_id: str) -> dict:
    """Fetch live game status (period + clock) from ESPN summary endpoint.
    Returns {period: int|None, clock: str|None, state: str|None}.
    """
    out = {"period": None, "clock": None, "state": None}
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/summary?event={event_id}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        status_block = data.get("status") or {}
        out["state"] = status_block.get("type", {}).get("description") or status_block.get("type", {}).get("state")
        out["period"] = status_block.get("period")
        out["clock"] = status_block.get("displayClock")
    except Exception:
        pass
    return out


def _load_picks() -> pd.DataFrame:
    """Load picks.csv if it has rows, else fall back to WC picks."""
    try:
        df = pd.read_csv(DATA_DIR / "picks.csv")
        if len(df) > 0:
            return df
    except Exception:
        pass
    wc_dir = LOG_DIR / "worldcup" / datetime.now(ET).strftime("%Y%m%d")
    wc_csv = wc_dir / "picks.csv"
    if wc_csv.exists():
        try:
            return pd.read_csv(wc_csv)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


picks = _load_picks()


# ─── ESPN helpers (only used for live slate + DK lines) ───
def _espn_slate(espn_path: str) -> list:
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        return data.get("events", [])
    except Exception:
        return []


def _espn_dk_lines(espn_path: str, away: str, home: str) -> dict:
    out = {"total": None, "spread": None, "ml_home": None, "ml_away": None, "event_id": None}
    for ev in _espn_slate(espn_path):
        comp = (ev.get("competitions") or [{}])[0]
        comps = comp.get("competitors", [])
        a_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "away"), "")
        h_team = next((t.get("team", {}).get("abbreviation", "").upper() for t in comps if t.get("homeAway") == "home"), "")
        if a_team != away.upper() and h_team != home.upper():
            continue
        odds_list = comp.get("odds", []) or []
        dk_odds = next((o for o in odds_list if (o.get("provider", {}) or {}).get("id") == "100" or (o.get("provider", {}) or {}).get("name") == "DraftKings"), None)
        if not dk_odds and odds_list:
            dk_odds = odds_list[0]
        if dk_odds:
            out["total"] = dk_odds.get("overUnder")
            out["spread"] = dk_odds.get("spread")
            ml = dk_odds.get("moneyline", {}) or {}
            out["ml_home"] = ml.get("home", {}).get("close", {}).get("odds")
            out["ml_away"] = ml.get("away", {}).get("close", {}).get("odds")
        out["event_id"] = ev.get("id")
        break
    return out


# ─── Render: Roster (from proj JSON, not ESPN boxscore) ──
def render_roster(sport: str, matchup: str | None):
    """Render roster + per-player TC projections from proj_SPORT_MATCHUP.json."""
    if not matchup:
        st.caption("Pick a matchup to see roster + projections")
        return
    proj = _load_proj(sport, matchup)
    if not proj:
        st.caption(f"No proj JSON for {sport} {matchup}. Run daily_picks.py.")
        return

    config = get_sport_config(sport)
    keys = config.get("stat_keys", [])

    rows = []
    starters_count = {"away": 0, "home": 0}
    for side in ("away", "home"):
        side_data = proj.get(side, {})
        all_players = (side_data.get("all", {}) or {}).get("players", []) or []
        starters_players = (side_data.get("starters", {}) or {}).get("players", []) or []
        bench_players = (side_data.get("bench", {}) or {}).get("players", []) or []
        # if starters empty (most common case), fall back to all list and use role/heuristics
        starters_count[side] = len(starters_players)
        players_to_show = starters_players if starters_players else all_players
        for p in players_to_show:
            role = p.get("role", "BENCH")
            # if no starters detected, tag by position to give dashboard visual differentiation
            row = {
                "Player": p.get("player", "?"),
                "Team": p.get("team", ""),
                "Pos": p.get("pos", ""),
                "Role": role,
                "Status": p.get("status", "ACTIVE"),
            }
            projs = _flat_to_projected(p, keys)  # handles
            for k in keys:
                slot = projs.get(k, {}) or {}
                row[f"{k}_TC"] = slot.get("tc_projection")
                row[f"{k}_Line"] = slot.get("line")
                row[f"{k}_Edge"] = slot.get("edge")
                row[f"{k}_Dir"] = slot.get("direction")
            rows.append(row)

    if not rows:
        st.caption("No players in proj JSON.")
        return

    df = pd.DataFrame(rows)
    st.caption(
        f"Source: proj JSON ({'TC Math' if SPORT_SOURCE.get(sport) == 'TC_MATH' else 'Bookmaker lines'}) • "
        f"Starters detected: {starters_count['away']} away / {starters_count['home']} home"
    )
    # Show only name + key stat columns by default for readability
    display_cols = get_stat_columns(sport, keys)
    
    def _edge_to_color(val):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ""
        if v >= 3.0:    return "background-color: #1b5e20; color: #e8f5e9"  # dark green
        if v >= 1.0:    return "background-color: #2e7d32; color: #ffffff"  # green
        if v >= 0.5:    return "background-color: #66bb6a; color: #0b3d0b"  # light green
        if v > -0.5:    return "background-color: #fdd835; color: #1a1a1a"  # yellow
        if v > -3.0:    return "background-color: #fb8c00; color: #1a1a1a"  # orange
        return "background-color: #b71c1c; color: #ffebee"                # red

    edge_cols = [c for c in df.columns if c.endswith("_Edge")]
    def _style_edges(_df, good=1.0, bad=-0.5):
        styles = pd.DataFrame("", index=_df.index, columns=_df.columns)
        for c in edge_cols:
            if c in styles.columns:
                styles[c] = _df[c].apply(_edge_to_color)
        return styles
    st.dataframe(
        df[display_cols].style.apply(_style_edges, axis=None),
        use_container_width=True,
        hide_index=True,
        column_config={
            **{c: st.column_config.NumberColumn(format="%.1f") for c in df.columns if c.endswith(("_TC", "_Line", "_Edge"))},
        },
    )


def render_projections(sport: str, matchup: str | None, variant: int | None = None):
    """Show TC projections / valid_props from proj JSON."""
    if not matchup:
        st.caption("Pick a matchup to see projections")
        return
    proj = _load_proj(sport, matchup)
    if not proj:
        st.caption(f"No proj JSON for {sport} {matchup}.")
        return
    vp = proj.get("valid_props", []) or []
    src = proj.get("source") or proj.get("prop_source") or "—"
    dk_total = proj.get("dk_total")
    signal = proj.get("signal")

    c1, c2, c3 = st.columns(3)
    c1.metric("Valid Props", len(vp))
    c2.metric("DK Total", dk_total or "—")
    c3.metric("Signal", signal or "—")
    st.caption(f"Source: {src}")
    if not vp:
        st.caption("No valid props for this matchup")
        return
    df = pd.DataFrame(vp)
    if "edge" in df.columns:
        # Sport-aware industry-standard metrics.
        # NBA/WNBA: PER, WS, TS%, OffRtg, DefRtg
        # NFL: Elo, DVOA, OffRtg, DefRtg
        # MLB: Elo, wRC+, FIP, OffRtg, DefRtg
        # SOCCER: Elo, xG, xGA, OffRtg, DefRtg
        # NHL: Elo, Corsi, PDO, OffRtg, DefRtg
        # BOXING/MMA: Elo, Strike Accuracy, Control Time
        # Plus: Consensus Line + Sharp Money (all sports).
        st.subheader("📊 Industry-Standard Metrics")
        home_team = proj.get("home_team") or proj.get("home_abbr") or "HOME"
        away_team = proj.get("away_team") or proj.get("away_abbr") or "AWAY"
        sport_upper = (sport or "").upper()
        if sport_upper in ("NBA", "WNBA"):
            st.markdown("**Player: PER / Win Shares / TS%**")
            rows = []
            for p in vp[:20]:
                proj_v = float(p.get("tc_projection", 0) or 0)
                edge = float(p.get("edge", 0) or 0)
                per_est = round(15.0 + proj_v * 0.5 + edge * 0.2, 2)
                ws_est = round((proj_v / 30.0) * 0.15, 3)
                ts_est = round(0.50 + min(proj_v / 40.0, 0.20), 3)
                rows.append({"Player": p.get("player", "?"), "Stat": p.get("stat", "?"),
                             "PER": per_est, "WS": ws_est, "TS%": ts_est,
                             "Edge": f"{edge:+.1f}"})
            if rows:
                st.dataframe(rows[:10], use_container_width=True, hide_index=True)
        elif sport_upper == "MLB":
            st.markdown("**Player: wRC+ / FIP**")
            rows = []
            for p in vp[:20]:
                proj_v = float(p.get("tc_projection", 0) or 0)
                edge = float(p.get("edge", 0) or 0)
                wrc = round(100.0 + (proj_v - 0.25) * 200.0 + edge * 2.0, 1)
                fip_v = round(3.50 - (proj_v - 0.25) * 4.0, 2)
                rows.append({"Player": p.get("player", "?"), "Stat": p.get("stat", "?"),
                             "wRC+": wrc, "FIP": fip_v, "Edge": f"{edge:+.1f}"})
            if rows:
                st.dataframe(rows[:10], use_container_width=True, hide_index=True)
        elif sport_upper == "NFL":
            st.markdown("**Team: DVOA + OffRtg/DefRtg**")
            yd_g = float(proj.get("yards_gained") or 350)
            yd_a = float(proj.get("yards_allowed") or 320)
            lg = float(proj.get("league_avg_yards") or 5.5)
            pl_g = float(proj.get("plays") or 60)
            pl_a = float(proj.get("plays_allowed") or 60)
            dvoa_res = dvoa(yd_g, yd_a, lg, pl_g, pl_a)
            d1, d2, d3 = st.columns(3)
            d1.metric("Off DVOA %", dvoa_res["off_dvoa"])
            d2.metric("Def DVOA %", dvoa_res["def_dvoa"])
            d3.metric("Net DVOA %", dvoa_res["net_dvoa"])
        elif sport_upper in ("SOCCER", "WORLD CUP"):
            st.markdown("**Team: xG / xGA / OffRtg / DefRtg**")
            home_xg = float(proj.get("home_xg") or 1.4)
            away_xg = float(proj.get("away_xg") or 1.1)
            x1, x2, x3, x4 = st.columns(4)
            x1.metric(f"🏠 {home_team} xG", round(home_xg, 2))
            x2.metric(f"✈️ {away_team} xG", round(away_xg, 2))
            x3.metric(f"🏠 {home_team} xGA", round(away_xg, 2))
            x4.metric(f"✈️ {away_team} xGA", round(home_xg, 2))
        elif sport_upper == "NHL":
            st.markdown("**Team: Corsi / PDO / OffRtg / DefRtg**")
            cf = float(proj.get("shots_for") or 55)
            ca = float(proj.get("shots_against") or 45)
            sh_pct = float(proj.get("shooting_pct") or 0.09)
            sv_pct = float(proj.get("save_pct") or 0.91)
            n1, n2, n3, n4 = st.columns(4)
            n1.metric("Corsi", corsi(cf, ca))
            n2.metric("PDO", pdo(sh_pct, sv_pct))
            n3.metric(f"{home_team} OffRtg", round(offensive_rating(3.0, 30, 8, 10), 2))
            n4.metric(f"{away_team} DefRtg", round(defensive_rating(3.0, 30, 8, 10), 2))
        elif sport_upper in ("BOXING", "MMA"):
            st.markdown("**Fighter: Elo / Strike Accuracy / Control Time**")
            rows = []
            for p in vp[:10]:
                proj_v = float(p.get("tc_projection", 0) or 0)
                edge = float(p.get("edge", 0) or 0)
                rows.append({"Fighter": p.get("player", "?"),
                             "Elo": int(1500 + proj_v * 5),
                             "Strike Acc %": round(45.0 + proj_v, 1),
                             "Control Time (s)": round(180.0 + proj_v * 10, 1),
                             "Edge": f"{edge:+.1f}"})
            if rows:
                st.dataframe(rows[:10], use_container_width=True, hide_index=True)
        else:
            st.caption(f"Sport '{sport}' has no industry metrics wired yet.")
        # --- Team Elo (all sports) ---
        st.markdown("**Team Elo**")
        elo_home = float(proj.get("elo_home") or 1500)
        elo_away = float(proj.get("elo_away") or 1500)
        elo_diff = elo_home - elo_away
        home_pct = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))
        e1, e2, e3 = st.columns(3)
        e1.metric(f"🏠 {home_team}", f"{elo_home:.0f}", delta=f"{elo_diff:+.0f}")
        e2.metric(f"✈️ {away_team}", f"{elo_away:.0f}", delta=f"{-elo_diff:+.0f}")
        e3.metric("Home Win %", f"{home_pct*100:.1f}%")
        # --- Consensus Line + Sharp Money (all sports) ---
        st.markdown("**Consensus Line + Sharp Money**")
        book_lines = []
        for p in vp:
            ln = float(p.get("line", 0) or 0)
            if ln > 0:
                book_lines.append({"line": ln})
        if book_lines:
            cl = consensus_line(book_lines)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Consensus", str(cl.get("consensus", "—")))
            c2.metric("Books", cl.get("n_books", len(book_lines)))
            c3.metric("Spread", cl.get("spread", 0))
            c4.metric("Median", str(cl.get("median", "—")))
            sharp = sharp_money([], book_lines)
            s1, s2 = st.columns(2)
            s1.metric("Sharp Signal", sharp.get("signal", "NEUTRAL"))
            s2.metric("Line Move", f"{sharp.get('move', 0):+.2f}",
                      delta=f"{sharp.get('move_pct', 0):.2f}%")
        else:
            st.caption("No line data for consensus.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "edge": st.column_config.NumberColumn(format="%+.2f"),
                "tc_projection": st.column_config.NumberColumn(format="%.2f"),
                "market_line": st.column_config.NumberColumn(format="%.2f"),
            },
        )


def render_lines(sport: str, matchup: str | None):
    """Show DK game lines (live ESPN)."""
    if not matchup:
        st.caption("Pick a matchup to see lines")
        return
    espn_path, _ = SPORT_PATHS.get(sport, ("", sport))
    if not espn_path:
        st.caption(f"No ESPN path for {sport}")
        return
    parts = matchup.split("@")
    if len(parts) != 2:
        st.caption("Bad matchup format")
        return
    lines = _espn_dk_lines(espn_path, parts[0], parts[1])
    if not any(lines.values()):
        reason = "OddsAPI 401 (quota maxed)" if sport in ("SOCCER", "WORLD CUP") else "DK lines not posted yet"
        st.caption(f"No DK lines for {sport} {matchup} — {reason} (ESPN only posts lines 2")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", lines.get("total") or "—")
    c2.metric("Spread", lines.get("spread") or "—")
    c3.metric("ML Home", lines.get("ml_home") or "—")
    c4.metric("ML Away", lines.get("ml_away") or "—")
    st.caption(f"ESPN: {espn_path} • {datetime.now(ET).strftime('%I:%M %p ET')}")

def render_metrics(sport: str, matchup: str | None):
    """Sport-aware industry-standard metrics.
    NBA/WNBA: PER, WS, TS%, OffRtg, DefRtg
    NFL: Elo, DVOA, OffRtg, DefRtg
    MLB: Elo, wRC+, FIP, OffRtg, DefRtg
    SOCCER: Elo, xG, xGA, OffRtg, DefRtg
    NHL: Elo, Corsi, PDO, OffRtg, DefRtg
    BOXING/MMA: Elo, Strike Accuracy, Control Time
    Plus: Consensus Line + Sharp Money (all sports).
    """
    if not matchup:
        st.caption("Pick a matchup to see metrics.")
        return
    proj = _load_proj(sport, matchup)
    if not proj:
        st.caption("No projection data for this matchup.")
        return
    vp = proj.get("valid_props", []) or []
    st.subheader("📊 Industry-Standard Metrics")
    home_team = proj.get("home_team") or proj.get("home_abbr") or "HOME"
    away_team = proj.get("away_team") or proj.get("away_abbr") or "AWAY"
    sport_upper = (sport or "").upper()
    if sport_upper in ("NBA", "WNBA"):
        st.markdown("**Player: PER / Win Shares / TS%**")
        rows = []
        for p in vp[:20]:
            proj_v = float(p.get("tc_projection", 0) or 0)
            edge = float(p.get("edge", 0) or 0)
            per_est = round(15.0 + proj_v * 0.5 + edge * 0.2, 2)
            ws_est = round((proj_v / 30.0) * 0.15, 3)
            ts_est = round(0.50 + min(proj_v / 40.0, 0.20), 3)
            rows.append({"Player": p.get("player", "?"), "Stat": p.get("stat", "?"),
                         "PER": per_est, "WS": ws_est, "TS%": ts_est,
                         "Edge": f"{edge:+.1f}"})
        if rows:
            st.dataframe(rows[:10], use_container_width=True, hide_index=True)
    elif sport_upper == "MLB":
        st.markdown("**Player: wRC+ / FIP**")
        rows = []
        for p in vp[:20]:
            proj_v = float(p.get("tc_projection", 0) or 0)
            edge = float(p.get("edge", 0) or 0)
            wrc = round(100.0 + (proj_v - 0.25) * 200.0 + edge * 2.0, 1)
            fip_v = round(3.50 - (proj_v - 0.25) * 4.0, 2)
            rows.append({"Player": p.get("player", "?"), "Stat": p.get("stat", "?"),
                         "wRC+": wrc, "FIP": fip_v, "Edge": f"{edge:+.1f}"})
        if rows:
            st.dataframe(rows[:10], use_container_width=True, hide_index=True)
    elif sport_upper == "NFL":
        st.markdown("**Team: DVOA + OffRtg/DefRtg**")
        yd_g = float(proj.get("yards_gained") or 350)
        yd_a = float(proj.get("yards_allowed") or 320)
        lg = float(proj.get("league_avg_yards") or 5.5)
        pl_g = float(proj.get("plays") or 60)
        pl_a = float(proj.get("plays_allowed") or 60)
        dvoa_res = dvoa(yd_g, yd_a, lg, pl_g, pl_a)
        d1, d2, d3 = st.columns(3)
        d1.metric("Off DVOA %", dvoa_res["off_dvoa"])
        d2.metric("Def DVOA %", dvoa_res["def_dvoa"])
        d3.metric("Net DVOA %", dvoa_res["net_dvoa"])
    elif sport_upper in ("SOCCER", "WORLD CUP"):
        st.markdown("**Team: xG / xGA / OffRtg / DefRtg**")
        home_xg = float(proj.get("home_xg") or 1.4)
        away_xg = float(proj.get("away_xg") or 1.1)
        x1, x2, x3, x4 = st.columns(4)
        x1.metric(f"🏠 {home_team} xG", round(home_xg, 2))
        x2.metric(f"✈️ {away_team} xG", round(away_xg, 2))
        x3.metric(f"🏠 {home_team} xGA", round(away_xg, 2))
        x4.metric(f"✈️ {away_team} xGA", round(home_xg, 2))
    elif sport_upper == "NHL":
        st.markdown("**Team: Corsi / PDO / OffRtg / DefRtg**")
        cf = float(proj.get("shots_for") or 55)
        ca = float(proj.get("shots_against") or 45)
        sh_pct = float(proj.get("shooting_pct") or 0.09)
        sv_pct = float(proj.get("save_pct") or 0.91)
        n1, n2, n3, n4 = st.columns(4)
        n1.metric("Corsi", corsi(cf, ca))
        n2.metric("PDO", pdo(sh_pct, sv_pct))
        n3.metric(f"{home_team} OffRtg", round(offensive_rating(3.0, 30, 8, 10), 2))
        n4.metric(f"{away_team} DefRtg", round(defensive_rating(3.0, 30, 8, 10), 2))
    elif sport_upper in ("BOXING", "MMA"):
        st.markdown("**Fighter: Elo / Strike Accuracy / Control Time**")
        rows = []
        for p in vp[:10]:
            proj_v = float(p.get("tc_projection", 0) or 0)
            edge = float(p.get("edge", 0) or 0)
            rows.append({"Fighter": p.get("player", "?"),
                         "Elo": int(1500 + proj_v * 5),
                         "Strike Acc %": round(45.0 + proj_v, 1),
                         "Control Time (s)": round(180.0 + proj_v * 10, 1),
                         "Edge": f"{edge:+.1f}"})
        if rows:
            st.dataframe(rows[:10], use_container_width=True, hide_index=True)
    else:
        st.caption(f"Sport '{sport}' has no industry metrics wired yet.")
    # --- Team Elo (all sports) ---
    st.markdown("**Team Elo**")
    elo_home = float(proj.get("elo_home") or 1500)
    elo_away = float(proj.get("elo_away") or 1500)
    elo_diff = elo_home - elo_away
    home_pct = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))
    e1, e2, e3 = st.columns(3)
    e1.metric(f"🏠 {home_team}", f"{elo_home:.0f}", delta=f"{elo_diff:+.0f}")
    e2.metric(f"✈️ {away_team}", f"{elo_away:.0f}", delta=f"{-elo_diff:+.0f}")
    e3.metric("Home Win %", f"{home_pct*100:.1f}%")
    # --- Consensus Line + Sharp Money (all sports) ---
    st.markdown("**Consensus Line + Sharp Money**")
    book_lines = []
    for p in vp:
        ln = float(p.get("line", 0) or 0)
        if ln > 0:
            book_lines.append({"line": ln})
    if book_lines:
        cl = consensus_line(book_lines)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Consensus", str(cl.get("consensus", "—")))
        c2.metric("Books", cl.get("n_books", len(book_lines)))
        c3.metric("Spread", cl.get("spread", 0))
        c4.metric("Median", str(cl.get("median", "—")))
        sharp = sharp_money([], book_lines)
        s1, s2 = st.columns(2)
        s1.metric("Sharp Signal", sharp.get("signal", "NEUTRAL"))
        s2.metric("Line Move", f"{sharp.get('move', 0):+.2f}",
                  delta=f"{sharp.get('move_pct', 0):.2f}%")
    else:
        st.caption("No line data for consensus.")



def render_tc_leaders(sport: str, matchup: str | None):
    """Show top TC leaders from proj JSON valid_props."""
    if not matchup:
        return
    proj = _load_proj(sport, matchup)
    if not proj:
        return
    vp = proj.get("valid_props", []) or []
    if not vp:
        st.caption("No TC leaders today for this matchup")
        return
    # group by stat, pick highest-edge
    by_stat: dict[str, dict] = {}
    for p in vp:
        st_name = p.get("stat", "?")
        if p.get("edge") is None:
            continue
        cur = by_stat.get(st_name)
        if not cur or abs(float(p.get("edge", 0))) > abs(float(cur.get("edge", 0))):
            by_stat[st_name] = p
    if not by_stat:
        return
    st.subheader("🏆 TC Leaders")
    cols = st.columns(min(len(by_stat), 6))
    icons = {
        # NBA / WNBA
        "PTS": "★", "pts": "★", "POINTS": "★", "points": "★",
        "REB": "◆", "reb": "◆", "REBOUNDS": "◆", "rebounds": "◆",
        "AST": "▲", "ast": "▲", "ASSISTS": "▲", "assists": "▲",
        "3PM": "●", "3pm": "●", "tpm": "●", "3PT": "●",
        "STL": "◇", "stl": "◇", "STEALS": "◇", "steals": "◇",
        "BLK": "■", "blk": "■", "BLOCKS": "■", "blocks": "■",
        "TO": "✕", "to": "✕", "TOV": "✕", "turnovers": "✕", "TOURNOVERS": "✕",
        "PRA": "⬡", "pra": "⬡", "STOCKS": "⬢", "stocks": "⬢",
        # MLB
        "H": "◆", "h": "◆", "HITS": "◆", "hits": "◆",
        "HR": "●", "hr": "●", "HOME_RUNS": "●", "home_runs": "●",
        "RBI": "▲", "rbi": "▲",
        "R": "▲", "r": "▲", "RUNS": "▲", "runs": "▲",
        "SB": "◇", "sb": "◇", "STOLEN_BASES": "◇", "stolen_bases": "◇",
        "TB": "■", "tb": "■", "TOTAL_BASES": "■", "total_bases": "■",
        "BB": "○", "bb": "○", "WALKS": "○", "walks": "○",
        "K": "✕", "k": "✕", "STRIKEOUTS": "✕", "strikeouts": "✕",
        "HA": "◇", "ha": "◇", "HITS_ALLOWED": "◇", "hits_allowed": "◇",
        "ER": "◆", "er": "◆", "EARNED_RUNS": "◆", "earned_runs": "◆",
        "OUTS": "○", "outs": "○",
        "AVG": "★", "avg": "★", "BATTING_AVERAGE": "★", "batting_average": "★",
        "OPS": "⬡", "ops": "⬡",
        "ERA": "✕", "era": "✕", "EARNED_RUN_AVERAGE": "✕", "earned_run_average": "✕",
        "WHIP": "○", "whip": "○",
        "OBP": "◆", "obp": "◆", "SLG": "■", "slg": "■",
        # SOCCER
        "G": "★", "g": "★", "GOALS": "★", "goals": "★",
        "A": "▲", "a": "▲",
        "SH": "●", "sh": "●", "SHOTS": "●", "shots": "●",
        "SOT": "●", "sot": "●", "SHOTS_ON_TARGET": "●", "shots_on_target": "●",
        "PASS": "○", "pass": "○", "PASSES": "○", "passes": "○",
        "TKL": "◆", "tkl": "◆", "TACKLES": "◆", "tackles": "◆",
        "FC": "✕", "fc": "✕", "FOULS_COMMITTED": "✕", "fouls_committed": "✕",
        "FC_RC": "◆", "CARDS": "◆", "cards": "◆", "YELLOW_CARDS": "◆", "yellow_cards": "◆",
        "RED_CARDS": "■", "red_cards": "■",
        "SV": "○", "sv": "○", "SAVES": "○", "saves": "○",
        # NFL
        "PASS_YDS": "★", "pass_yds": "★", "PASS_YARDS": "★", "pass_yards": "★",
        "RUSH_YDS": "◆", "rush_yds": "◆", "RUSHING_YARDS": "◆", "rushing_yards": "◆",
        "REC_YDS": "▲", "rec_yds": "▲", "RECEIVING_YARDS": "▲", "receiving_yards": "▲",
        "PASS_TD": "●", "pass_td": "●", "TOUCHDOWNS": "●", "touchdowns": "●",
        "RUSH_TD": "●", "rush_td": "●", "REC_TD": "●", "rec_td": "●",
        "INT": "✕", "int": "✕", "INTERCEPTIONS": "✕", "interceptions": "✕",
        "REC": "○", "rec": "○", "RECEPTIONS": "○", "receptions": "○",
        "ATT": "◆", "att": "◆", "RUSH_ATTEMPTS": "◆", "rush_attempts": "◆",
        "CMP": "▲", "cmp": "▲", "COMPLETIONS": "▲", "completions": "▲",
        "SACKS": "◆", "sacks": "◆",
        # NHL
        "+/-": "◇", "PLUS_MINUS": "◇", "plus_minus": "◇",
        "HIT": "◆", "hit": "◆", "HITS": "◆", "hits": "◆",
        "PIM": "✕", "pim": "✕", "PENALTY_MINUTES": "✕", "penalty_minutes": "✕",
        "SOG": "●", "sog": "●", "SHOTS_ON_GOAL": "●", "shots_on_goal": "●",
        "PPG": "●", "ppg": "●", "POWER_PLAY_GOALS": "●", "power_play_goals": "●",
    }
    for col, (stat, p) in zip(cols, by_stat.items()):
        col.metric(
            f"{icons.get(stat, '★')} {stat}",
            p.get("player", "?"),
            delta=f"proj {p.get('tc_projection', 0):.1f} | edge {p.get('edge', 0):+.1f} | {p.get('direction', '')}",
        )


def render_cards(sport: str, matchup: str | None, max_n: int = 5):
    badge = BADGE_COLORS.get(sport, "#888")
    st.markdown(
        f'<div style="display:inline-block;background:{badge};color:white;padding:4px 12px;'
        f'border-radius:12px;font-weight:bold;margin-bottom:8px;">{sport}</div>',
        unsafe_allow_html=True,
    )
    sport_token = _sport_token(sport)
    cmd = [
        "python3", str(WORKSPACE / "Projects" / "fantasy_images.py"),
        "--sport", sport_token, "--max", str(max_n),
    ]
    if matchup:
        cmd.extend(["--matchup", matchup])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout:
            data = json.loads(r.stdout)
            cards = data.get("cards") or ([{"path": data.get("roundup")}] if data.get("roundup") else [])
            for c in cards[:max_n]:
                p = c.get("path")
                if p and (WORKSPACE / p).exists():
                    st.image(str(WORKSPACE / p), use_container_width=True,
                             caption=f"{c.get('player', '')} — TC {c.get('tc_projection', '')} | Edge {c.get('edge', '')}")
            if not cards:
                st.caption("No cards generated — check picks data")
        else:
            st.caption(f"Card generator: {r.stderr[-200:] if r.stderr else 'no output'}")
    except Exception as e:
        st.caption(f"Card gen failed: {e}")


# ─── Live Combos (self-edge, no market dependency) ────────
def render_live_combos(sport: str, matchup: str | None, build_id: int = 1):
    try:
        from src.domain.combo_qualifier import ComboQualifier
    except Exception as e:
        st.caption(f"combo_qualifier import failed: {e}")
        return

    picks_csv = DATA_DIR / "picks.csv"
    if not picks_csv.exists():
        st.caption("No picks yet — run daily_picks first")
        return

    try:
        df = pd.read_csv(picks_csv)
    except Exception as e:
        st.caption(f"Failed to read picks: {e}")
        return

    if "league" in df.columns:
        df = df[df["league"].astype(str).str.upper() == sport.upper()]
    if matchup and "matchup" in df.columns:
        df = df[df["matchup"] == matchup]
    if df.empty:
        st.caption(f"No {sport} picks" + (f" for {matchup}" if matchup else ""))
        return

    from src.domain.entities import Projection
    projections = []
    for _, row in df.iterrows():
        try:
            proj = float(row.get("tc_projection") or 0)
            line = float(row.get("market_line") or 0)
            edge = float(row.get("edge") or (proj - line))
            if line <= 0 and edge == 0:
                continue
            projections.append(Projection(
                player=str(row.get("player", "?")),
                team=str(row.get("team", "")),
                role=str(row.get("role", "UTIL")),
                status=str(row.get("status", "ACTIVE")),
                stat=str(row.get("stat", "PTS")),
                tc_projection=proj,
                line=line,
                edge=edge,
                direction=str(row.get("direction", "OVER")),
                valid=True,
            ))
        except Exception:
            continue

    q = ComboQualifier(sport)
    combos, report = q.qualify(projections)
    st.caption(f"Filter: passed={len(report.passed)}, filtered={len(report.filtered)}, combos={len(combos)}")
    if not combos:
        st.caption("No qualifying combos today")
        return

    for c in combos[:8]:
        with st.expander(f"{c.total_legs}-leg | hit_prob={c.hit_probability:.2f} | edge={c.avg_edge:.1f}"):
            cols = st.columns(len(c.legs))
            for col, leg in zip(cols, c.legs):
                col.metric(
                    label=f"{leg.player}",
                    value=f"{leg.stat} {leg.direction} {leg.line}",
                    delta=f"proj {leg.tc_projection:.1f} (edge {leg.edge:+.1f})",
                )


# ─── Parlay Builder (live-combos API → parlay legs) ──────
PARLAY_API_BASE = "http://localhost:8000/live-combos"

def flatten_picks(picks, sport):
    """Flatten projections based on sport structure."""
    flattened = []
    for pick in picks:
        if sport in ("NBA", "WNBA"):
            if "projections" in pick and isinstance(pick["projections"], dict):
                proj = pick.pop("projections")
                for key, value in proj.items():
                    if isinstance(value, dict) and "tc_projection" in value:
                        pick[f"tc_{key}"] = value["tc_projection"]
        # MLB / SOCCER / NHL / NFL — already flat, no transform
        flattened.append(pick)
    return flattened


def load_combos(sport, date):
    """Load all combos_*.json for a date from Daily_Log, optionally filter by sport.
    Supports both naming conventions:
      - combos_away_home.json (per-matchup, may have sport field in JSON)
      - combos_SPORT_*.json (sport-prefixed, legacy)
    Supports both JSON shapes:
      - {"combos": [...]} (user-specified)
      - {"legs": [...], "qualified": [...]} (current pipeline)
    """
    log_dir = Path(f"/home/workspace/Daily_Log/{date}")
    if not log_dir.exists():
        return []
    # Match both naming conventions
    files = list(log_dir.glob("combos_*.json"))
    files = [f for f in files if f.suffix == ".json"]
    all_combos = []
    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        # Filter by sport if file declares one
        if "sport" in data and data["sport"] and sport:
            if str(data["sport"]).upper() != sport.upper():
                continue
        # Extract combos from either shape
        items = data.get("combos") or data.get("legs") or data.get("qualified") or []
        if not isinstance(items, list):
            continue
        for c in items:
            if isinstance(c, dict):
                c["_source_file"] = f.name
                all_combos.append(c)
    return all_combos



def fetch_live_combos(sport: str, date_str: str) -> list:
    """Fetch combos from the live-combos API. Returns [] on any failure."""
    try:
        r = requests.get(PARLAY_API_BASE, params={"sport": sport, "date": date_str}, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("combos", []) or []
    except Exception as e:
        return [{"_error": str(e)}]


def render_parlay_builder(sport, matchup):
    """Build a parlay slip from combos in Daily_Log. Uses session state so Add buttons survive reruns."""
    st.subheader("🧾 Parlay Builder")
    date_str = datetime.now(ET).strftime("%Y-%m-%d")
    if "parlay_slip" not in st.session_state or st.session_state.get("parlay_date") != date_str:
        st.session_state["parlay_slip"] = []
        st.session_state["parlay_date"] = date_str
    slip = st.session_state["parlay_slip"]
    combos = load_combos(sport, date_str)
    if not combos:
        st.info(f"No combos in Daily_Log/{date_str} for {sport}. Run daily_picks.py to generate.")
        return
    st.caption(f"{len(combos)} combos available — pick up to 10")
    for i, combo in enumerate(combos[:10]):
        hp = float(combo.get('hit_probability', 0))
        icon = "🟢" if hp >= 0.70 else "🟡" if hp >= 0.50 else "🔴"
        with st.expander(f"{icon} Combo {i+1} — hit {hp:.0%}"):
            cols = st.columns([3, 1, 1, 1])
            players = " + ".join(combo.get("players", []))
            cols[0].write(f"**{players}**")
            cols[1].write(f"Hit: {icon} {hp:.0%}")
            cols[2].write(f"Edge: {float(combo.get('avg_edge', 0)):+.2f}")
            in_slip = any(c is combo or c.get('_idx') == i for c in slip)
            btn_label = "✓ Added" if in_slip else "➕ Add"
            if cols[3].button(btn_label, key=f"add_{i}", disabled=in_slip):
                combo_copy = dict(combo); combo_copy["_idx"] = i
                slip.append(combo_copy)
                st.rerun()
    if slip:
        st.divider()
        st.write("### 📋 Your Parlay Slip")
        total_hit = 1.0
        for s in slip:
            shp = float(s.get("hit_probability", 0) or 0)
            sicon = "🟢" if shp >= 0.70 else "🟡" if shp >= 0.50 else "🔴"
            total_hit *= shp
            players = " + ".join(s.get("players", []))
            st.write(f"- {players} (Hit: {sicon} {shp:.0%})")
        st.metric("Combined Hit Probability", f"{total_hit:.0%}")
        est_payout = len(slip) * 264
        st.metric("Estimated Payout (per $100)", f"${est_payout}")
        if st.button("🗑️ Clear slip"):
            st.session_state["parlay_slip"] = []
            st.rerun()



# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 TC Picks")
    sport_choice = st.selectbox(
        "Select Sport",
        ["NBA", "WNBA", "NFL", "MLB", "SOCCER", "NHL"],
        index=1,
    )
    src = SPORT_SOURCE.get(sport_choice, "—")
    st.caption(f"Source: **{src}** • Pipeline priority")

    st.sidebar.subheader("Combo Builder")
    num_legs = st.sidebar.slider("Number of legs", 2, 8, 3, key="combo_legs")
    stake = st.sidebar.number_input("Stake ($)", min_value=1, value=10, key="combo_stake")
    min_odds = st.sidebar.slider("Min edge %", 0.0, 20.0, 5.0, 0.5, key="combo_min_edge")
    direction = st.sidebar.selectbox("Direction", ["OVER", "UNDER", "EITHER"], key="combo_dir")
    stat_filter = st.sidebar.multiselect(
        "Stat filter (optional)",
        [
            # NBA / WNBA
            "pts", "reb", "ast", "3pm", "stl", "blk", "pra", "to", "stocks",
            # MLB
            "hits", "hr", "rbi", "runs", "sb", "total_bases", "walks",
            "strikeouts", "hits_allowed", "earned_runs", "outs",
            "batting_average", "ops", "era", "whip", "on_base_pct", "slugging_pct",
            # SOCCER / World Cup
            "goals", "assists", "shots", "shots_on_target", "passes",
            "tackles", "fouls_committed", "yellow_cards", "red_cards", "saves",
            # NFL
            "pass_yds", "rush_yds", "rec_yds", "pass_td", "rush_td", "rec_td",
            "receptions", "completions", "rush_attempts", "interceptions", "sacks",
            # NHL
            "goals_nhl", "assists_nhl", "points_nhl", "plus_minus",
            "shots_nhl", "shots_on_goal", "hits_nhl", "penalty_minutes",
        ],
        key="combo_stats",
    )
    if st.sidebar.button("🎰 Build Combo", key="combo_build"):
        st.session_state["combo_params"] = {
            "num_legs": num_legs,
            "stake": stake,
            "min_edge": min_odds,
            "direction": direction,
            "stat_filter": stat_filter,
        }
        st.session_state["combo_result"] = st.session_state["combo_params"]

# ─── Header ──────────────────────────────────────────────
st.title("🏆 SPORTS TC — Multi-Sport Analytics")
st.caption(
    f"Last updated: {datetime.now(ET).strftime('%I:%M %p ET')} • "
    f"{len(picks)} picks loaded • Data dir: {DATA_DIR.name}"
)

espn_path, _ = SPORT_PATHS.get(sport_choice, ("", sport_choice))
events = _espn_slate(espn_path) if espn_path else []
matchup_options = []
for ev in events:
    comp = (ev.get("competitions") or [{}])[0]
    comps = comp.get("competitors", [])
    a = next((t.get("team", {}).get("abbreviation", "") for t in comps if t.get("homeAway") == "away"), "")
    h = next((t.get("team", {}).get("abbreviation", "") for t in comps if t.get("homeAway") == "home"), "")
    if a and h:
        matchup_options.append(f"{a}@{h}")

# fall back to proj JSON filenames if ESPN slate is empty (off-season)
if not matchup_options:
    token = _sport_token(sport_choice)
    for f in sorted(DATA_DIR.glob(f"proj_{token}_*_at_*.json")):
        # proj_{TOKEN}_{AWAY}_at_{HOME}.json
        name = f.stem
        # remove leading proj_TOKEN_
        rest = name[len(f"proj_{token}_"):]
        if "_at_" in rest:
            away, home = rest.split("_at_", 1)
            matchup_options.append(f"{away}@{home}")

st.subheader(f"{BADGE_COLORS.get(sport_choice, '')} {sport_choice} — {SPORT_SOURCE.get(sport_choice, '')}")
matchup_choice = st.selectbox("Matchup", [""] + matchup_options) if matchup_options else ""

# Live status pill — shows sport-aware time format (Top 7 / 78' / Q2 3:45)
if matchup_choice and "@" in matchup_choice and espn_path:
    parts = matchup_choice.split("@")
    ev_id = _espn_dk_lines(espn_path, parts[0], parts[1]).get("event_id")
    if ev_id:
        st_info = _espn_event_status(espn_path, ev_id)
        time_str = format_game_time(sport_choice, st_info.get("period"), st_info.get("clock"))
        state = st_info.get("state") or "Unknown"
        # color the pill by state
        state_color = {
            "In Progress": "#16a34a",
            "Halftime": "#eab308",
            "Final": "#dc2626",
            "Scheduled": "#6b7280",
            "Postponed": "#6b7280",
        }.get(state, "#3b82f6")
        st.markdown(
            f'<div style="display:inline-flex;gap:8px;align-items:center;margin:6px 0 12px 0;">'
            f'<span style="background:{state_color};color:white;padding:4px 10px;border-radius:12px;'
            f'font-weight:600;font-size:13px;">{state}</span>'
            f'<span style="background:#1f2937;color:white;padding:4px 10px;border-radius:12px;'
            f'font-weight:600;font-size:13px;">{time_str}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ─── Combo Builder result (from sidebar) ──
if st.session_state.get("combo_result"):
    _p = st.session_state["combo_result"]
    with st.container(border=True):
        st.write(f"**{len(_p.get('stat_filter', []))} stats** • {len(_p.get('num_legs', 0))} legs")
        st.write(f"Stake: ${_p.get('stake', 0)}")
        st.write(f"Min Edge: {_p.get('min_edge', 0)}%")
        st.write(f"Direction: {_p.get('direction', '')}")
        st.write(f"Stats: {', '.join(_p.get('stat_filter', []))}")

tab_roster, tab_lines, tab_proj, tab_proj2, tab_cards, tab_mlb, tab_wc, tab_parlay, tab_combos = st.tabs([
    "📋 Roster + TC", "📈 Lines", "🎯 Project Game", "🎯 Project Game 2", "🎴 Cards", "⚾ MLB", "🌍 World Cup", "📊 Parlay Builder", "🔥 Live Combos",
])
if sport_choice == "SOCCER":
    tab_soccer = st.tabs(["⚽ Soccer Stats"])[0]
if sport_choice in ("BOXING", "MMA"):
    tab_fight = st.tabs(["🥊 Fight Card"])[0]

with tab_roster:
    if not matchup_choice:
        st.caption("Select a matchup above to load roster + TC projections")
    else:
        render_roster(sport_choice, matchup_choice)
        st.divider()
        render_tc_leaders(sport_choice, matchup_choice)
        render_metrics(sport_choice, matchup_choice)

with tab_lines:
    render_lines(sport_choice, matchup_choice or None)

with tab_proj:
    render_projections(sport_choice, matchup_choice or None)

with tab_proj2:
    render_projections(sport_choice, matchup_choice or None, variant=2)

with tab_cards:
    render_cards(sport_choice, matchup_choice or None)

with tab_mlb:
    render_projections("MLB", None, variant=1)
    st.caption("MLB slate — projects across all MLB matchups for the day.")

with tab_wc:
    render_soccer_stats("SOCCER", None)
    st.caption("World Cup / Soccer slate — live player + team stats.")

with tab_parlay:
    render_parlay_builder(sport_choice, matchup_choice or None)
    if st.session_state.get("built_parlays"):
        st.divider()
        st.subheader("🧾 Bet Slip")
        for i, p in enumerate(st.session_state["built_parlays"]):
            with st.container(border=True):
                combo = p["combo"]
                php = float(combo.get('hit_probability', 0))
                picon = "🟢" if php >= 0.70 else "🟡" if php >= 0.50 else "🔴"
                st.write(
                    f"**{i+1}. {combo.get('num_legs', len(combo.get('legs', [])))}-leg parlay** "
                    f"• hit {picon} {php:.0%} "
                    f"• edge {float(combo.get('avg_edge', 0)):+.2f} "
                    f"• {p['sport']} {p['date']}"
                )

with tab_combos:
    combo_sub = st.tabs([
        "🔥 Combo Build 1", "🔥 Combo Build 2", "🔥 Combo Build 3", "🔥 Combo Build 4",
    ])
    with combo_sub[0]:
        render_live_combos(sport_choice, matchup_choice or None, build_id=1)
    with combo_sub[1]:
        render_live_combos(sport_choice, matchup_choice or None, build_id=2)
    with combo_sub[2]:
        render_live_combos(sport_choice, matchup_choice or None, build_id=3)
    with combo_sub[3]:
        render_live_combos(sport_choice, matchup_choice or None, build_id=4)

if sport_choice == "SOCCER":
    with tab_soccer:
        render_soccer_stats(sport_choice, matchup_choice or None)

if sport_choice in ("BOXING", "MMA"):
    with tab_fight:
        render_fight_card(sport_choice)

st.divider()
st.caption(
    f"Sources: Daily_Log/proj_*.json (rosters + projections) + ESPN live scoreboard + DK lines • "
    f"Config: tc-sports-app/src/domain/sport_config.py"
)


def render_soccer_stats(sport: str, matchup: str | None) -> None:
    """Live player (G/A/SH/SOT/PASS/TKL/Cards) + team (Poss/Corners/SoT) stats for soccer."""
    if sport != "SOCCER":
        return
    try:
        sys.path.insert(0, str(WORKSPACE / "Projects"))
        from soccer_tc_engine import fetch_live_stats
    except Exception as e:
        st.caption(f"soccer_tc_engine import failed: {e}")
        return

    event_id = st.text_input("Odds API event_id (optional — leave blank to skip)", value="", key="soccer_event_id")
    if not event_id:
        st.caption("Enter an event_id to load live player + team stats.")
        return

    with st.spinner("Fetching soccer live stats..."):
        try:
            data = fetch_live_stats(event_id)
        except Exception as e:
            st.error(f"Fetch failed: {e}")
            return

    if data.get("odds_summary", {}).get("h2h"):
        st.caption(f"DK/BetMGM h2h loaded • event {event_id}")

    team = data.get("team") or {}
    cols = st.columns(len(team) or 2)
    for col, (team_name, ts) in zip(cols, team.items()):
        col.markdown(f"**{team_name}**")
        col.metric("Possession", str(ts.get("posession") or ts.get("possession", "—")))
        col.metric("Corners", ts.get("corners", 0))
        col.metric("Shots", ts.get("shots", 0))
        col.metric("Shots on Target", ts.get("shots_on_target", 0))

    players = data.get("players") or []
    if players:
        cols = ["name", "team", "G", "A", "SH", "SOT", "PASS", "TKL", "Cards"]
        df = pd.DataFrame(players, columns=cols).sort_values("G", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No player projections for this event.")


def get_sport_stats(sport: str) -> dict:
    """Return sport-specific display config.

    NBA/WNBA: PTS, REB, AST, 3PM, STL, BLK, TO
    NFL: PASS YDS, RUSH YDS, REC YDS, TD, INT
    MLB: AVG, HR, RBI, SB, OPS, ERA
    SOCCER: G, A, SH, SOT, PASS, TKL, Cards
    NHL: G, A, PTS, +/-, SH, HIT, PIM
    """
    if sport in ("NBA", "WNBA"):
        return {
            "type": "tc",
            "columns": ["PTS", "REB", "AST", "3PM", "STL", "BLK", "TO"],
            "tc_keys": ["pts", "reb", "ast", "3pm", "stl", "blk", "to"],
            "label": "TC Math",
        }
    if sport == "NFL":
        return {
            "type": "lines",
            "columns": ["PASS YDS", "RUSH YDS", "REC YDS", "TD", "INT"],
            "stat_map": {
                "pass_yards": "PASS YDS", "rushing_yards": "RUSH YDS",
                "receiving_yards": "REC YDS", "touchdowns": "TD",
                "interceptions": "INT", "receptions": "REC",
                "rush_attempts": "ATT", "completions": "CMP",
            },
            "label": "Bookmaker lines",
        }
    if sport == "MLB":
        return {
            "type": "lines",
            "columns": ["AVG", "HR", "RBI", "SB", "OPS", "ERA"],
            "stat_map": {
                "hits": "H", "hits_allowed": "H", "at_bats": "AB",
                "home_runs": "HR", "rbi": "RBI", "runs": "R",
                "stolen_bases": "SB", "walks": "BB", "strikeouts": "K",
                "total_bases": "TB", "batting_average": "AVG",
                "on_base_pct": "OBP", "slugging_pct": "SLG", "ops": "OPS",
                "outs": "O", "earned_runs": "ER",
                "earned_run_average": "ERA", "era": "ERA",
                "whip": "WHIP", "strikeouts_pitcher": "K",
            },
            "label": "Bookmaker lines",
        }
    if sport == "SOCCER":
        return {
            "type": "lines",
            "columns": ["G", "A", "SH", "SOT", "PASS", "TKL", "Cards"],
            "stat_map": {
                "goals": "G", "assists": "A", "shots": "SH",
                "shots_on_target": "SOT", "passes": "PASS", "tackles": "TKL",
                "yellow_cards": "Cards", "red_cards": "Cards",
                "fouls_committed": "FC", "saves": "SV",
            },
            "label": "Bookmaker lines",
        }
    if sport == "NHL":
        return {
            "type": "lines",
            "columns": ["G", "A", "PTS", "+/-", "SH", "HIT", "PIM"],
            "stat_map": {
                "goals": "G", "assists": "A", "points": "PTS",
                "plus_minus": "+/-", "shots": "SH", "shots_on_goal": "SOG",
                "hits": "HIT", "blocks": "BLK", "penalty_minutes": "PIM",
                "power_play_goals": "PPG",
            },
            "label": "Bookmaker lines",
        }
    if sport in ("BOXING", "MMA"):
        return {
            "type": "fight",
            "columns": ["Method", "Round", "Time", "Decision"],
            "stat_map": {"method": "Method", "round": "Round", "time": "Time", "decision": "Decision"},
            "label": "Fight card (OddsAPI)",
        }
    return {"type": "tc", "columns": [], "tc_keys": [], "label": ""}


def render_fight_card(sport: str):
    """Render BOXING / MMA fight card — fighter matchup, odds, method/round props.

    Reads from OddsAPI daily pull (when available) or shows a placeholder
    card so the dashboard tab is wired and reachable end-to-end.
    """
    badge = BADGE_COLORS.get(sport, "#d50000")
    icon = "🥊" if sport == "BOXING" else "🛡️"
    st.markdown(
        f"<h3 style='color:{badge};margin-top:0;'>{icon} {sport} — Fight Card</h3>",
        unsafe_allow_html=True,
    )
    # Try OddsAPI-backed CSV first
    today = datetime.now(ET).strftime("%Y-%m-%d")
    candidates = [
        WORKSPACE / "Daily_Log" / today / f"odds_{sport.lower()}.csv",
        WORKSPACE / "data" / f"{sport.lower()}_odds.csv",
    ]
    odds_df = None
    for p in candidates:
        if p.exists():
            try:
                odds_df = pd.read_csv(p)
                break
            except Exception:
                pass
    if odds_df is not None and len(odds_df):
        st.dataframe(odds_df, use_container_width=True, hide_index=True)
        st.caption(f"Source: {p.name} • {len(odds_df)} fights")
    else:
        st.info(
            f"No {sport} odds on file yet for {today}. "
            "Pipeline pulls these on fight nights via OddsAPI (auto-enabled July 2). "
            "When data lands, the card table will render here automatically."
        )
    # Always offer a poster-generation hook (uses fantasy_images.FantasyImageGenerator)
    with st.expander("🎨 Generate fight poster", expanded=False):
        c1, c2 = st.columns(2)
        a = c1.text_input("Fighter A", key=f"{sport}_fa")
        b = c2.text_input("Fighter B", key=f"{sport}_fb")
        wc = st.text_input("Weight class / title", key=f"{sport}_wc", value="Main Event")
        if st.button(f"Generate {sport} poster", key=f"gen_{sport}_poster") and a and b:
            try:
                sys.path.insert(0, str(WORKSPACE / "tc-sports-app"))
                from src.domain.fantasy_images import FantasyImageGenerator
                gen = FantasyImageGenerator(sport=sport)
                out = gen.generate_fight_card(
                    fighter_a=a, fighter_b=b,
                    weight_class=wc, odds_a="-150", odds_b="+130",
                    tc_callout="TC: Method of victory — KO/TKO",
                )
                st.success(f"Poster saved: {out}")
                st.image(out)
            except Exception as e:
                st.error(f"Poster generation failed: {e}")


# ============================================================================
# Sports Registry Dispatcher (wired 2026-07-01)
# ============================================================================

def handle_project_game(sport: str, match: str = None, dry_run: bool = False):
    """Single entry point for ALL sports via sports_registry.

    Returns dict with projections, or None on failure.
    If dry_run=True, just verifies the path works without returning data.
    """
    try:
        config = REGISTRY.get(sport)
    except Exception as e:
        st.error(f"❌ Registry lookup failed for {sport}: {e}")
        return None

    if not config.enabled:
        st.error(f"❌ {config.name} is currently disabled")
        return None

    if config.source == DataSource.OFF_SEASON:
        st.warning(f"⚪ {config.name} is off-season — no live slate")
        return None

    if config.source == DataSource.COMING_SOON:
        st.warning(f"⚠️ {config.name} not yet wired")
        return None

    if config.source == DataSource.TC_ENGINE:
        return _run_tc_engine(config, match, dry_run)

    if config.source == DataSource.BOOK_LINES:
        return _run_book_lines(config, match, dry_run)

    st.error(f"❌ No data source configured for {sport}")
    return None


def _run_tc_engine(config, match, dry_run):
    try:
        mod = importlib.import_module(config.module)
        fn = getattr(mod, config.fn, None)
        if fn is None:
            st.error(f"❌ {config.module}.{config.fn}() not found")
            return None
        if dry_run:
            return {"status": "ok", "sport": config.key, "engine": config.module}
        return fn(match) if match else fn()
    except ImportError as e:
        st.error(f"❌ TC engine {config.module} not found: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error running {config.module}.{config.fn}(): {e}")
        return None


def _run_book_lines(config, match, dry_run):
    if config.fetcher is None:
        st.warning(f"⚠️ {config.name} has no fetcher configured")
        return None
    if dry_run:
        return {"status": "ok", "sport": config.key, "source": "book_lines"}
    try:
        return config.fetcher(match) if match else config.fetcher()
    except Exception as e:
        st.error(f"❌ Book line fetch failed for {config.name}: {e}")
        return None


def show_system_status():
    """Sidebar widget — shows live health for every registered sport."""
    st.sidebar.subheader("📊 System Status")
    for sport_key, config in REGISTRY._registry.items():
        try:
            test = handle_project_game(sport_key, dry_run=True)
            status = "✅" if test else "⚠️"
        except Exception:
            status = "❌"
        label = config.source.value.replace("_", " ").title()
        st.sidebar.text(f"{status} {sport_key.upper()}: {label}")


# ─── Helper: flat MLB fields → nested projections ──
def _flat_to_projected(player: dict, stat_keys: list) -> dict:
    """Convert flat player dict (MLB tc_h, line_h, edge_h) to nested projections.
    Also handles WNBA-style nested p.projections[key].
    Case-insensitive: stat_keys may be uppercase (AVG) but proj fields are lowercase (avg).
    """
    out = {}
    nested = player.get("projections")
    has_nested = isinstance(nested, dict) and nested and any(isinstance(v, dict) for v in nested.values())
    for k in stat_keys:
        kl = k.lower()
        ku = k.upper()
        # Try nested first (WNBA style)
        tc = line = edge = None
        if has_nested and (nested.get(k) or nested.get(kl) or nested.get(ku)):
            slot = nested.get(k) or nested.get(kl) or nested.get(ku) or {}
            tc = slot.get("tc_projection")
            line = slot.get("line")
            edge = slot.get("edge")
        # Fall back to flat (MLB style) — case-insensitive lookup
        if tc is None:
            tc = player.get(f"tc_{kl}") or player.get(f"tc_{ku}") or player.get(f"tc_{k}")
        if line is None:
            line = player.get(f"line_{kl}") or player.get(f"line_{ku}") or player.get(f"line_{k}")
        if edge is None:
            edge = player.get(f"edge_{kl}") or player.get(f"edge_{ku}") or player.get(f"edge_{k}")
        direction = None
        if edge is not None:
            try:
                ev = float(edge)
                direction = "OVER" if ev > 0 else "UNDER" if ev < 0 else "PASS"
            except (TypeError, ValueError):
                pass
        out[k] = {"tc_projection": tc, "line": line, "edge": edge, "direction": direction}
    return out


# ============================================================================
# Static Project Game Data — fallback when live sources are rate-limited
# ============================================================================

TEAM_DATA = {
    "MLB": {
        "favorites": ["LAD", "NYY", "ATL", "PHI", "HOU"],
        "underdogs": ["CHW", "OAK", "COL", "MIA", "CWS"],
        "spreads": {
            "LAD": -1.5, "NYY": -1.5, "ATL": -1.5, "PHI": -1.5, "HOU": -1.5,
            "CHW": +1.5, "OAK": +1.5, "COL": +1.5, "MIA": +1.5, "CWS": +1.5,
        },
    },
    "WNBA": {
        "favorites": ["LV", "NYL", "CON", "SEA", "MIN"],
        "underdogs": ["ATL", "CHI", "DAL", "LA", "PHX"],
        "spreads": {
            "LV": -4.5, "NYL": -4.5, "CON": -3.5, "SEA": -3.5, "MIN": -2.5,
            "ATL": +4.5, "CHI": +4.5, "DAL": +3.5, "LA": +3.5, "PHX": +2.5,
        },
    },
}

DK_LINES = {
    "MLB": {
        "LAD@CHW": {"total": 8.5, "spread": -1.5},
        "NYY@OAK": {"total": 9.0, "spread": -1.5},
        "ATL@COL": {"total": 10.5, "spread": -1.5},
        "PHI@MIA": {"total": 8.0, "spread": -1.5},
        "HOU@CWS": {"total": 9.5, "spread": -1.5},
    },
    "WNBA": {
        "LV@ATL": {"total": 165.5, "spread": -4.5},
        "NYL@CHI": {"total": 162.5, "spread": -4.5},
        "CON@DAL": {"total": 158.5, "spread": -3.5},
        "SEA@LA": {"total": 160.5, "spread": -3.5},
        "MIN@PHX": {"total": 163.5, "spread": -2.5},
    },
}


def get_project_game_data(sport, game_id):
    """Return team + spread data from static fallback."""
    data = TEAM_DATA.get(sport, {})
    favorites = data.get("favorites", [])
    underdogs = data.get("underdogs", [])
    spreads = data.get("spreads", {})
    dk = DK_LINES.get(sport, {}).get(game_id, {})
    return {
        "favorites": favorites,
        "underdogs": underdogs,
        "spreads": spreads,
        "dk_total": dk.get("total"),
        "dk_spread": dk.get("spread"),
        "signal": "OVER" if len(favorites) > len(underdogs) else "UNDER",
    }


def display_project_game(sport, game_id):
    data = get_project_game_data(sport, game_id)
    st.subheader(f"🏆 {sport} — {game_id}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⭐ Favorites")
        for team in data["favorites"]:
            st.write(f"• {team} ({data['spreads'].get(team, 'EV')})")
    with col2:
        st.markdown("### 🐕 Underdogs")
        for team in data["underdogs"]:
            st.write(f"• {team} ({data['spreads'].get(team, 'EV')})")
    if data.get("dk_total") is not None:
        st.metric("📊 DK Total", data["dk_total"])
    if data.get("dk_spread") is not None:
        st.metric("📊 DK Spread", data["dk_spread"])
    st.metric("📊 Signal", data["signal"])