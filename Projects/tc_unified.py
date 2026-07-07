#!/usr/bin/env python3
"""TC Unified Dashboard — single-page, multi-sport, all components.
Replaces tc_dashboard.py on :8510.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
sys.path.insert(0, str(WORKSPACE / "tc-sports-app"))
from src.domain.entities import BADGE_COLORS

ET = timezone(timedelta(hours=-4))


def main():
    st.set_page_config(
        page_title="SPORTS TC — Unified",
        page_icon="🏆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # ── Data sources ──────────────────────────────────────────
    SPORT_PATHS = {
        "NBA":    ("basketball/nba", "NBA"),
        "WNBA":   ("basketball/wnba", "WNBA"),
        "NFL":    ("football/nfl", "NFL"),
        "MLB":    ("baseball/mlb", "MLB"),
        "SOCCER": ("soccer/World Cup", "WORLD CUP"),
        "NHL":    ("hockey/nhl", "NHL"),
    }


    def _latest_log_dir() -> Path:
        today = LOG_DIR / datetime.now(ET).strftime("%Y-%m-%d")
        if (today / "picks.csv").exists():
            try:
                if len(pd.read_csv(today / "picks.csv")) > 0:
                    return today
            except Exception:
                pass
        for d in sorted([x for x in LOG_DIR.iterdir() if x.is_dir()], reverse=True):
            if (d / "picks.csv").exists():
                try:
                    if len(pd.read_csv(d / "picks.csv")) > 0:
                        return d
                except Exception:
                    continue
        return today


    DATA_DIR = _latest_log_dir()


    def _sport_token(sport: str) -> str:
        return {"SOCCER": "WORLD CUP"}.get(sport, sport)


    def _proj_path(sport: str, matchup: str) -> Path | None:
        if not matchup or "@" not in matchup:
            return None
        away, home = matchup.split("@", 1)
        token = _sport_token(sport)
        p = DATA_DIR / f"proj_{token}_{away}_at_{home}.json"
        if p.exists():
            return p
        for d in sorted(LOG_DIR.iterdir(), reverse=True):
            if d.is_dir():
                cand = d / f"proj_{token}_{away}_at_{home}.json"
                if cand.exists():
                    return cand
        return None


    def _load_proj(sport: str, matchup: str | None) -> dict | None:
        p = _proj_path(sport, matchup) if matchup else None
        if not p or not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None


    def _espn_get(path: str) -> list:
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read().decode("utf-8", errors="ignore")).get("events", [])
        except Exception:
            return []


    def _espn_event_status(path: str, event_id: str) -> dict:
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={event_id}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                header = data.get("header", {}) or {}
                comps = (header.get("competitions") or [{}])[0]
                status = comps.get("status", {}) or {}
                return {
                    "state": status.get("type", {}).get("description", "Unknown"),
                    "period": status.get("period"),
                    "clock": status.get("displayClock"),
                }
        except Exception:
            return {}


    # ── Combos data ───────────────────────────────────────────
    def _combo_row(combo: dict, source_file: str = "", source_dir: str = "") -> dict:
        books = combo.get("books", combo.get("sources", []))
        return {
            "sport": combo.get("sport", "?"),
            "matchup": combo.get("matchup", "?"),
            "players": ", ".join(combo.get("players", [])[:4]),
            "num_legs": combo.get("num_legs", len(combo.get("legs", []))),
            "hit_prob": float(combo.get("hit_probability", 0) or 0),
            "avg_edge": float(combo.get("avg_edge", 0) or 0),
            "avg_confidence": float(combo.get("avg_confidence", 0) or 0),
            "books": books,
            "source": "bookline (SGO/OddsAPI) — NOT TC math",
            "source_dir": source_dir,
            "source_file": source_file,
        }


    def _load_all_combos() -> pd.DataFrame:
        rows = []
        for d in sorted(LOG_DIR.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            for f in d.glob("combos_*.json"):
                if f.name == "combos_summary.json":
                    continue
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, list):
                        for combo in data:
                            rows.append(_combo_row(combo, source_file=f.name, source_dir=d.name))
                    elif isinstance(data, dict):
                        rows.append(_combo_row(data, source_file=f.name, source_dir=d.name))
                except Exception:
                    continue
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if "hit_prob" in df.columns:
            df = df.sort_values("hit_prob", ascending=False)
        return df


    def _load_picks() -> pd.DataFrame:
        p = DATA_DIR / "picks.csv"
        if not p.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(p)
        except Exception:
            return pd.DataFrame()


    def _load_backtest(sport: str) -> dict:
        out = {"hit_rate": None, "graded": 0, "roi": None, "path": None}
        cands = sorted(WORKSPACE.glob(f"Reports/{sport.lower()}_backtest_*.csv"), reverse=True)
        if not cands:
            cands = sorted(WORKSPACE.glob(f"Reports/{sport}_backtest_*.csv"), reverse=True)
        if not cands:
            return out
        out["path"] = str(cands[0])
        try:
            df = pd.read_csv(cands[0])
            out["graded"] = len(df)
            for col in ("hit", "won", "win", "result"):
                if col in df.columns:
                    out["hit_rate"] = float(df[col].mean())
                    break
            for col in ("roi", "profit", "p_l", "pnl"):
                if col in df.columns:
                    out["roi"] = float(df[col].sum())
                    break
        except Exception:
            pass
        return out


    def _fetch_worldcup_props() -> list:
        candidates = [
            "https://true.zo.space/api/worldcup-props",
            "http://localhost:3099/api/worldcup-props",
        ]
        for url in candidates:
            try:
                r = requests.get(url, timeout=8, headers={"Accept": "application/json"})
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        return data.get("props") or data.get("data") or []
            except Exception:
                continue
        props = []
        wc_dir = LOG_DIR / "worldcup"
        if wc_dir.exists():
            for f in sorted(wc_dir.rglob("props.json"), reverse=True)[:5]:
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, list):
                        props.extend(data)
                except Exception:
                    continue
        return props


# ── Sport-aware data loaders + sport-specific columns ─────────
# Each sport shows ONLY its own stats — no basketball stats on MLB/SOCCER/NHL
SPORT_COLUMNS = {
    "MLB":    ["Player", "Team", "AVG", "HR", "RBI", "SB", "OPS", "ERA", "Edge", "Conf"],
    "SOCCER": ["Player", "Team", "G", "A", "SH", "SOT", "PASS", "TKL", "Cards", "Edge", "Conf"],
    "NHL":    ["Player", "Team", "G", "A", "PTS", "+/-", "SH", "HIT", "PIM", "Edge", "Conf"],
    "NBA":    ["Player", "Team", "PTS", "REB", "AST", "3PM", "STL", "BLK", "TO", "Edge", "Conf"],
    "WNBA":   ["Player", "Team", "PTS", "REB", "AST", "3PM", "STL", "BLK", "TO", "Edge", "Conf"],
    "NFL":    ["Player", "Team", "PASS YDS", "RUSH YDS", "REC YDS", "TD", "INT", "Edge", "Conf"],
}


def render_wnba_projections(proj: dict) -> pd.DataFrame:
    """Flatten all players into a one-row-per-player table with PTS/REB/AST/STL/BLK/3PM + max edge.
    No edge filter applied — all roster players shown. Edge column gets a green dot
    when the player's best edge across stats is >= 2.0.
    """
    rows = []
    for side in ("away", "home"):
        for player in (proj.get(side, {}).get("all", {}).get("players") or []):
            if (player.get("status") or "ACTIVE").upper() == "OUT":
                continue
            proj_map = player.get("projections") or {}
            stat_row = {
                "Player": player.get("player", "?"),
                "Team": player.get("team", ""),
                "Role": player.get("role", ""),
                "PTS": "-", "REB": "-", "AST": "-", "STL": "-", "BLK": "-", "3PM": "-",
            }
            max_edge = 0.0
            for stat_key, sd in proj_map.items():
                tc = sd.get("tc_projection", 0)
                edge = sd.get("edge", 0)
                stat_row[stat_key] = round(tc, 1)
                if abs(edge) > abs(max_edge):
                    max_edge = edge
            stat_row["Max Edge"] = f"🟢 {round(max_edge, 1)}" if abs(max_edge) >= 2.0 else round(max_edge, 1)
            rows.append(stat_row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)





def get_sport_columns(sport: str) -> list:
    return SPORT_COLUMNS.get(sport, ["Player", "Team", "Stats", "Edge", "Conf"])


def load_tc_data(sport: str, date: str) -> dict:
    """Load TC-Math data for NBA/WNBA/NFL from proj JSONs."""
    token = _sport_token(sport)
    pattern = f"proj_{token}_*_at_*.json"
    proj_files = list(DATA_DIR.glob(pattern))
    if not proj_files:
        for d in sorted(LOG_DIR.iterdir(), reverse=True):
            if d.is_dir():
                proj_files.extend(d.glob(pattern))
                if proj_files:
                    break
    rows = []
    for pf in proj_files:
        try:
            data = json.loads(pf.read_text())
            vp = data.get("valid_props", []) or []
            for p in vp:
                rows.append({
                    "Player": p.get("player", "?"),
                    "Team": p.get("team", ""),
                    "Stat": p.get("stat", ""),
                    "Line": p.get("market_line", p.get("line", 0)),
                    "TC": p.get("tc_projection", 0),
                    "Direction": p.get("direction", ""),
                    "Edge": p.get("edge", 0),
                    "Conf": p.get("confidence", 0.0),
                })
        except Exception:
            continue
    return {
        "players": rows,
        "columns": get_sport_columns(sport),
        "message": "" if rows else f"No TC data for {sport} {date}",
    }


def load_bookline_data(sport: str, date: str) -> dict:
    """Load bookline (SGO/OddsAPI) data for MLB/SOCCER/NHL — fallback to empty."""
    rows = []
    sgo_files = list(DATA_DIR.glob(f"slate_{sport}.json"))
    if not sgo_files:
        for d in sorted(LOG_DIR.iterdir(), reverse=True):
            if d.is_dir():
                sgo_files.extend(d.glob(f"slate_{sport}.json"))
                if sgo_files:
                    break
    for sf in sgo_files:
        try:
            data = json.loads(sf.read_text())
            if isinstance(data, list):
                for item in data:
                    rows.append({
                        "Player": item.get("player", item.get("name", "?")),
                        "Team": item.get("team", ""),
                        "Line": item.get("line", item.get("market_line", 0)),
                        "Direction": item.get("direction", ""),
                        "Edge": item.get("edge", 0),
                        "Conf": item.get("confidence", 0.0),
                    })
        except Exception:
            continue
    return {
        "players": rows,
        "columns": get_sport_columns(sport),
        "message": "" if rows else f"No bookline data for {sport} {date}",
    }


def get_sport_data(sport: str, date: str) -> dict:
    """Sport-aware data loader.

    NBA/WNBA/NFL → TC Math (proj JSONs)
    MLB/SOCCER/NHL → Bookline (SGO / OddsAPI)
    """
    if sport in ("NBA", "WNBA", "NFL"):
        return load_tc_data(sport, date)
    return load_bookline_data(sport, date)


    # ── UI state ──────────────────────────────────────────────
    if "selected_sport" not in st.session_state:
        st.session_state.selected_sport = "WNBA"
    if "selected_matchup" not in st.session_state:
        st.session_state.selected_matchup = ""
    if "built_parlays" not in st.session_state:
        st.session_state.built_parlays = []
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    if "min_edge" not in st.session_state:
        st.session_state.min_edge = 0.5
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = True
    if "combo_source" not in st.session_state:
        st.session_state.combo_source = "booklines (SGO / OddsAPI) — NOT TC math"

    # ── Combo Builder sidebar ──────────────────────────
    st.sidebar.subheader("🎯 Combo Builder")

    num_legs = st.sidebar.slider(
        "Number of legs",
        min_value=2,
        max_value=8,
        value=3,
        help="How many legs to include in each combo"
    )

    stake = st.sidebar.number_input(
        "Stake ($)",
        min_value=1,
        value=10,
        step=1
    )

    min_odds = st.sidebar.slider(
        "Minimum odds (American)",
        min_value=100,
        max_value=500,
        value=200,
        step=10,
        help="Only include legs with odds >= this value"
    )

    # Optional extras
    direction = st.sidebar.selectbox(
        "Direction",
        options=["Any", "Over", "Under"],
        index=0,
        help="Filter by Over/Under (optional)"
    )

    stat_filter = st.sidebar.multiselect(
        "Stat types",
        options=["PTS", "REB", "AST", "AVG", "HR", "RBI", "Goals", "Shots"],
        default=[],
        help="Leave empty to include all stats"
    )

    if st.sidebar.button("Generate Combos"):
        st.sidebar.success(f"Combos generated with {num_legs} legs, min odds {min_odds}.")


    # ── Header ────────────────────────────────
    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.title("🏆 SPORTS TC — Unified")
        st.caption(
            f"Live data from Daily_Log/{DATA_DIR.name} • "
            f"Sports: NBA / WNBA / NFL / MLB / SOCCER / NHL • "
            f"Refreshed: {datetime.now(ET).strftime('%I:%M:%S %p ET')}"
        )
    with hdr_r:
        if st.button("🔄 Refresh now", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.rerun()
        st.session_state.auto_refresh = st.toggle("Auto-refresh 60s", value=st.session_state.auto_refresh)

    # Auto-refresh every 60s
    if st.session_state.auto_refresh and (time.time() - st.session_state.last_refresh) > 60:
        st.session_state.last_refresh = time.time()
        st.rerun()


    # ── Sport selector ────────────────────────────────────────
    sport = st.selectbox(
        "Sport",
        list(SPORT_PATHS.keys()),
        index=list(SPORT_PATHS.keys()).index(st.session_state.selected_sport),
        key="sport_pick",
    )
    st.session_state.selected_sport = sport
    espn_path, _ = SPORT_PATHS[sport]
    events = _espn_get(espn_path)

    matchup_options = []
    event_lookup = {}
    for ev in events:
        comp = (ev.get("competitions") or [{}])[0]
        comps = comp.get("competitors", []) or []
        a = next((t.get("team", {}).get("abbreviation", "") for t in comps if t.get("homeAway") == "away"), "")
        h = next((t.get("team", {}).get("abbreviation", "") for t in comps if t.get("homeAway") == "home"), "")
        if a and h:
            m = f"{a}@{h}"
            matchup_options.append(m)
            event_lookup[m] = ev.get("id", "")
    if not matchup_options:
        token = _sport_token(sport)
        for f in sorted(DATA_DIR.glob(f"proj_{token}_*_at_*.json")):
            rest = f.stem[len(f"proj_{token}_"):]
            if "_at_" in rest:
                away, home = rest.split("_at_", 1)
                matchup_options.append(f"{away}@{home}")
    if not matchup_options:
        matchup_options = [""]

    matchup = st.selectbox(
        "Matchup",
        matchup_options,
        index=0 if st.session_state.selected_matchup not in matchup_options else matchup_options.index(st.session_state.selected_matchup),
        key="matchup_pick",
    )
    st.session_state.selected_matchup = matchup
    badge = BADGE_COLORS.get(sport, "#888")
    st.markdown(
        f'<div style="display:inline-block;background:{badge};color:white;padding:4px 12px;'
        f'border-radius:12px;font-weight:bold;margin:4px 0 12px 0;">{sport} — {matchup or "no matchup"}</div>',
        unsafe_allow_html=True,
    )


    # ── COMPONENT 3: Live Scoreboard (ESPN, 60s refresh) ──────
    st.subheader("📡 Live Scoreboard")
    if not events:
        st.caption("ESPN scoreboard returned no events for this sport right now.")
    else:
        rows = []
        for ev in events:
            comp = (ev.get("competitions") or [{}])[0]
            comps = comp.get("competitors", []) or []
            a = next((t for t in comps if t.get("homeAway") == "away"), {})
            h = next((t for t in comps if t.get("homeAway") == "home"), {})
            a_team = a.get("team", {}) or {}
            h_team = h.get("team", {}) or {}
            status = comp.get("status", {}) or {}
            st_info = status.get("type", {}) or {}
            rows.append({
                "Matchup": f"{a_team.get('abbreviation', '')} @ {h_team.get('abbreviation', '')}",
                "Away": f"{a_team.get('abbreviation', '')} {a.get('score', '—')}",
                "Home": f"{h_team.get('abbreviation', '')} {h.get('score', '—')}",
                "State": st_info.get("description", "—"),
                "Clock": status.get("displayClock", "—"),
                "Period": status.get("period", "—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


    # ── COMPONENT 4: Top Picks (highest edge) ────────────────
    st.subheader("🎯 Top Picks — Highest Edge")
    picks = _load_picks()
    if picks.empty:
        st.caption(f"No picks in {DATA_DIR.name}/picks.csv — run daily_picks.py")
    else:
        edge_col = next((c for c in ("edge", "Edge", "tc_edge", "self_edge") if c in picks.columns), None)
        if edge_col:
            top = picks.reindex(picks[edge_col].abs().sort_values(ascending=False).index).head(10)
            sport_col = next((c for c in ("sport", "Sport", "SPORT") if c in picks.columns), None)
            if sport_col:
                top = top[top[sport_col].str.upper() == sport]
                if top.empty:
                    top = picks.reindex(picks[edge_col].abs().sort_values(ascending=False).index).head(10)
            show_cols = [c for c in ("player", "Player", "stat", "Stat", "line", "Line",
                                      "direction", "Direction", edge_col, "matchup", "Matchup")
                         if c in top.columns]
            st.dataframe(top[show_cols], use_container_width=True, hide_index=True)
        else:
            st.caption(f"No edge column in picks.csv (cols: {', '.join(picks.columns[:8])}...)")


    # ── COMPONENT 5: Player Grid + filters ────────────────────
    st.subheader("🧮 Player Grid — Full Projections")
    filt_l, filt_m, filt_r, filt_x = st.columns(4)
    with filt_l:
        st.session_state.min_edge = st.number_input(
            "Min |edge|", min_value=0.0, max_value=20.0, value=st.session_state.min_edge, step=0.5
        )
    with filt_m:
        dir_choice = st.selectbox("Direction", ["ALL", "OVER", "UNDER"], index=0)
    with filt_r:
        team_filter = st.text_input("Team (optional, e.g. LV)", "").strip().upper()
    with filt_x:
        stat_filter = st.text_input("Stat contains (optional)", "").strip().upper()

    # ── Multi-book selector (DK / FD / Caesars / BetMGM / SGO) ─────
    book_options = ["DraftKings", "FanDuel", "Caesars", "BetMGM", "SGO"]
    books = st.multiselect(
        "Select Books (multi-select; lines from selected books only)",
        book_options,
        default=["DraftKings", "SGO"],
        key="book_filter",
        help="Combos are built from these booklines (SGO/OddsAPI), NOT from TC math.",
    )

    if not matchup:
        st.caption("Pick a matchup to load projections.")
    else:
        proj = _load_proj(sport, matchup)
        if not proj:
            st.caption(f"No proj JSON for {sport} {matchup} in {DATA_DIR.name}")
        else:
            # Build player grid. Default to per-player view (one row per
            # player) since valid_props is usually sparse — the per-stat view
            # is for when you want to see all stats for a single player.
            vp = proj.get("valid_props", []) or []
            if not vp:
                vp = proj.get("all", {}).get("players", []) or []
            if not vp:
                st.caption("No player projections in this proj JSON.")
            else:
                if sport == "WNBA":
                    df = render_wnba_projections(proj)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    edges = []
                    for side in ("away", "home"):
                        for player in (proj.get(side, {}).get("all", {}).get("players") or []):
                            if (player.get("status") or "ACTIVE").upper() == "OUT":
                                continue
                            best = 0.0
                            for sk, sd in (player.get("projections") or {}).items():
                                e = sd.get("edge", 0)
                                if abs(e) > abs(best):
                                    best = e
                            edges.append(best)
                    if edges:
                        n = len(edges)
                        mean_edge = sum(edges) / n
                        max_edge = max(edges)
                        min_edge = min(edges)
                        count_ge_2 = sum(1 for e in edges if abs(e) >= 2.0)
                        st.caption(f"Edge stats: n={n}, mean={mean_edge:+.2f}, max={max_edge:+.2f}, min={min_edge:+.2f}, >=2.0={count_ge_2}")
                    else:
                        st.caption("Edge stats: no players")
                else:
                    df = pd.DataFrame(vp)
                    if "edge" in df.columns:
                        df = df[df["edge"].abs() >= st.session_state.min_edge]
                    if dir_choice != "ALL" and "direction" in df.columns:
                        df = df[df["direction"].str.upper() == dir_choice]
                    if team_filter and "team" in df.columns:
                        df = df[df["team"].str.upper() == team_filter]
                    if stat_filter and "stat" in df.columns:
                        df = df[df["stat"].str.upper().str.contains(stat_filter, na=False)]
                    if "books" in df.columns and books:
                        df = df[df["books"].apply(lambda bs: any(b in (bs or []) for b in books))]
                    elif "book" in df.columns and books:
                        df = df[df["book"].str.upper().isin([b.upper() for b in books])]
                    if df.empty:
                        st.caption("No props match filters — try lowering min_edge or clearing team/stat/books")
                    else:
                        st.dataframe(
                            df, use_container_width=True, hide_index=True,
                            column_config={
                                "edge": st.column_config.NumberColumn(format="%+.2f"),
                                "tc_projection": st.column_config.NumberColumn(format="%.2f"),
                                "market_line": st.column_config.NumberColumn(format="%.2f"),
                            } if "edge" in df.columns else None,
                        )
                        st.caption(f"{len(df)} props after filters")


    # ── COMPONENT 6: Parlay Builder (merged with combos) ─────
    st.subheader("🎟️ Parlay Builder — Combos + Bet Slip")
    pcl, pcr = st.columns([3, 1])
    with pcl:
        st.markdown("**All-sport combos** (sorted by hit probability)")
    with pcr:
        combo_sport_filter = st.selectbox("Sport filter", ["ALL"] + list(SPORT_PATHS.keys()), index=0)

    all_combos = _load_all_combos()
    if all_combos.empty:
        st.caption("No combos found in Daily_Log/*/combos_*.json — run build_pregame_combos.py")
    else:
        df_combos = all_combos
        if combo_sport_filter != "ALL":
            df_combos = df_combos[df_combos["sport"].str.upper() == combo_sport_filter]
        if df_combos.empty:
            st.caption(f"No combos for {combo_sport_filter}")
        else:
            st.caption(f"{len(df_combos)} combos available")
            for idx, combo in df_combos.head(10).iterrows():
                hp = float(combo['hit_prob'])
                icon = "🟢" if hp >= 0.70 else "🟡" if hp >= 0.50 else "🔴"
                with st.expander(
                    f"{icon} {int(combo['num_legs'])}-leg {combo['sport']} {combo['matchup']}  •  "
                    f"edge {combo['avg_edge']:+.2f}  •  {combo['players'][:40]}"
                ):
                    cm1, cm2, cm3 = st.columns(3)
                    cm1.metric("Hit Prob", f"{icon} {hp:.0%}")
                    cm2.metric("Avg Edge", f"{combo['avg_edge']:+.2f}")
                    cm3.metric("Confidence", f"{combo['avg_confidence']:.1%}")
                    if st.button(f"✅ Build Parlay", key=f"build_{idx}"):
                        st.session_state.built_parlays.append({
                            "sport": combo["sport"],
                            "matchup": combo["matchup"],
                            "hit_prob": combo["hit_prob"],
                            "avg_edge": combo["avg_edge"],
                            "players": combo["players"],
                            "num_legs": int(combo["num_legs"]),
                        })
                        st.success(f"Parlay built ({len(st.session_state.built_parlays)} in slip)")

    # Bet slip
    if st.session_state.built_parlays:
        st.divider()
        st.markdown("**🧾 Bet Slip**")
        for i, p in enumerate(st.session_state.built_parlays):
            with st.container(border=True):
                st.write(
                    f"**{i+1}. {p['num_legs']}-leg {p['sport']} {p['matchup']}** "
                    f"• {('🟢' if p['hit_prob']>=0.70 else '🟡' if p['hit_prob']>=0.50 else '🔴')} hit {p['hit_prob']:.0%} • edge {p['avg_edge']:+.2f} • {p['players']}"
                )
        if st.button("🗑️ Clear slip"):
            st.session_state.built_parlays = []
            st.rerun()


    # ── COMPONENT 7: WC Support (live props + stats) ─────────
    if sport == "SOCCER":
        st.subheader("⚽ World Cup — Live Props & Stats")
        wc_props = _fetch_worldcup_props()
        if not wc_props:
            st.caption("No /api/worldcup-props available. Fallback: scan Daily_Log/worldcup/ returned no data.")
        else:
            wc_df = pd.DataFrame(wc_props)
            st.caption(f"{len(wc_df)} WC props loaded from /api/worldcup-props")
            st.dataframe(wc_df.head(20), use_container_width=True, hide_index=True)
        # Also show WC backtest summary
        wc_bt = _load_backtest("wc")
        if wc_bt["hit_rate"] is not None:
            b1, b2 = st.columns(2)
            b1.metric("WC Hit Rate", f"{wc_bt['hit_rate']*100:.1f}%", delta=f"{wc_bt['graded']} graded")
            if wc_bt["roi"] is not None:
                b2.metric("WC ROI", f"{wc_bt['roi']:+.2f}")


    # ── COMPONENT 8: All-Sport Combos (already in #6, but expose broader table) ───
    st.subheader("🔥 All-Sport Combos (combined)")
    if not all_combos.empty:
        show_cols = ["sport", "matchup", "num_legs", "hit_prob", "avg_edge", "avg_confidence", "players"]
        st.dataframe(
            all_combos[show_cols].head(30),
            use_container_width=True, hide_index=True,
            column_config={
                "hit_prob": st.column_config.NumberColumn(format="%.1f"),
                "avg_edge": st.column_config.NumberColumn(format="%+.2f"),
            },
        )


    # ── COMPONENT 9: Performance (hit rate / ROI per sport) ──
    st.subheader("📈 Performance — Hit Rate & ROI")
    perf_cols = st.columns(6)
    for col, sp in zip(perf_cols, ["NBA", "WNBA", "MLB", "NFL", "SOCCER", "NHL"]):
        bt = _load_backtest(sp if sp != "SOCCER" else "wc")
        with col:
            if bt["hit_rate"] is not None:
                col.metric(f"{sp} Hit Rate", f"{bt['hit_rate']*100:.1f}%", delta=f"{bt['graded']} graded")
            else:
                col.metric(f"{sp} Hit Rate", "—", delta="no data")
            if bt["roi"] is not None:
                col.metric(f"{sp} ROI", f"{bt['roi']:+.2f}")
            else:
                col.metric(f"{sp} ROI", "—")


    # Sources footer
    st.divider()
    st.caption(
        f"Sources: ESPN scoreboard (60s auto-refresh) • Daily_Log/{DATA_DIR.name}/picks.csv (top picks) • "
        f"proj_*.json (player grid) • combos_*.json (parlay builder) • "
        f"/api/worldcup-props (WC) • Reports/*_backtest_*.csv (performance)"
    )


if __name__ == "__main__":
    main()