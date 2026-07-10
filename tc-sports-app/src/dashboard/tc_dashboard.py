#!/usr/bin/env python3
"""TC Sports Dashboard — streamlit entrypoint for the tc-sports-app package.

Fully self-contained: reads Daily_Log/YYYY-MM-DD/picks.csv, proj_*.json (which
contain DK-scraped valid_props), and adapters/market_line_provider directly.

Run:  streamlit run src/dashboard/tc_dashboard.py
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

WORKSPACE = Path("/home/workspace")
DAILY_LOG = WORKSPACE / "Daily_Log"
PROJ_DIR = WORKSPACE / "Projects"
PROJ_IMG_DIR = WORKSPACE / "reports" / "images"
SRC_ROOT = WORKSPACE / "tc-sports-app"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SPORT_LIST = ["WNBA", "MLB", "SOCCER", "NBA", "NHL"]

_STAT_LABELS = {
    "PTS": "PTS", "REB": "REB", "AST": "AST", "3PM": "3PM",
    "STL": "STL", "BLK": "BLK",
    "hits": "H", "home_runs": "HR", "rbi": "RBI", "runs": "R",
    "strikeouts": "K", "hits_allowed": "HA", "earned_runs": "ER",
    "pass_yds": "PASS", "rush_yds": "RUSH", "rec_yds": "REC",
    "pass_td": "PASS TD", "rush_td": "RUSH TD", "rec_td": "REC TD",
    "shots_on_goal": "SOG", "goals": "G", "assists": "A",
    "shots": "SHOTS", "fouls": "FOULS", "cards": "CARDS",
    "TOTAL": "TOTAL", "ML": "ML", "SPREAD": "SPREAD",
}


# ── Data loaders ──────────────────────────────────────────────────

def _today_et() -> str:
    return datetime.now(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d")


def _load_picks(date_str: str, sport: str) -> List[Dict[str, Any]]:
    csv_path = DAILY_LOG / date_str / "picks.csv"
    if not csv_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            league = (r.get("league") or r.get("sport") or "").upper()
            if sport == "ALL" or league == sport:
                out.append(r)
    return out


def _load_matchup_projections(date_str: str) -> Dict[str, Dict[str, Any]]:
    """Return map: matchup_upper → proj json (with players + valid_props + DK lines)."""
    out: Dict[str, Dict[str, Any]] = {}
    base = DAILY_LOG / date_str
    if not base.exists():
        return out
    for f in base.glob("proj_*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        matchup = (data.get("matchup") or f.stem.replace("proj_", "")).upper().replace("_AT_", "@")
        if matchup:
            out[matchup] = data
    return out


def _extract_dk_lines(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull every DK-scraped prop (valid_props + game-level lines) from a proj json."""
    out: List[Dict[str, Any]] = []
    for prop in data.get("valid_props", []) or []:
        out.append(prop)
    # Game-level DK line (moneyline, spread, total) lives at top of json
    if data.get("dk_total") is not None or data.get("dk_spread") is not None or data.get("dk_ml_home") is not None:
        out.append({
            "player": "GAME",
            "team": "",
            "stat": "GAME_TOTAL",
            "direction": "N/A",
            "market_line": data.get("dk_total", ""),
            "tc_projection": data.get("tc_total", ""),
            "edge": "",
            "source": data.get("source", ""),
        })
    return out


def _format_edge(v) -> str:
    try:
        return f"{float(v):+.1f}"
    except (TypeError, ValueError):
        return "—"


def _stat_label(stat: str) -> str:
    return _STAT_LABELS.get(stat, stat)


def _matchup_options(rows: List[Dict[str, Any]]) -> List[str]:
    seen = []
    for r in rows:
        m = r.get("matchup") or ""
        if m and m not in seen:
            seen.append(m)
    return ["ALL"] + seen


def _flatten_roster(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """proj json has {home, away} each with {all: {players: [...]}, starters: {...}, bench: {...}}."""
    out: List[Dict[str, Any]] = []
    for side in ("home", "away"):
        block = data.get(side) or {}
        for group in ("all", "starters", "bench"):
            g = block.get(group) or {}
            for p in g.get("players", []) or []:
                p = dict(p)
                p["_side"] = side
                p["_group"] = group
                out.append(p)
    return out


# ── Page sections ────────────────────────────────────────────────

def _render_top_edges(sport: str, date_str: str, matchup: Optional[str]) -> None:
    rows = _load_picks(date_str, sport)
    if matchup and matchup != "ALL":
        rows = [r for r in rows if (r.get("matchup") or "").upper() == matchup.upper()]
    if not rows:
        st.info(f"No {sport} picks found for {date_str}.")
        return
    rows = sorted(rows, key=lambda r: abs(float(r.get("edge") or 0)), reverse=True)
    display = []
    for r in rows[:20]:
        display.append({
            "Player": r.get("player", "TOTAL" if r.get("stat") == "TOTAL" else ""),
            "Matchup": r.get("matchup", ""),
            "Stat": _stat_label(r.get("stat", "")),
            "Line": r.get("market_line") or r.get("line") or "",
            "Proj": r.get("tc_projection") or r.get("proj") or "",
            "Edge": _format_edge(r.get("edge")),
            "Dir": r.get("direction", ""),
            "Source": r.get("source", ""),
        })
    st.dataframe(display, use_container_width=True)


def _render_dk_lines(sport: str, date_str: str, matchup: Optional[str]) -> None:
    """Show every DK-scraped line for the selected sport, with matchup filter."""
    projs = _load_matchup_projections(date_str)
    if not projs:
        st.caption("No matchup projection files found.")
        return
    if matchup and matchup != "ALL":
        key = matchup.upper().replace(" @ ", "@")
        projs = {k: v for k, v in projs.items() if key == k or key in k}
    if not projs:
        st.caption(f"No DK lines for {matchup}.")
        return
    rows: List[Dict[str, Any]] = []
    for matchup_key, data in projs.items():
        m_sport = (data.get("sport") or "").upper()
        if sport != "ALL" and m_sport and m_sport != sport:
            continue
        for prop in _extract_dk_lines(data):
            rows.append({
                "Matchup": matchup_key,
                "Player": prop.get("player", ""),
                "Team": prop.get("team", ""),
                "Stat": _stat_label(prop.get("stat", "")),
                "Line": prop.get("market_line", ""),
                "Proj": prop.get("tc_projection", ""),
                "Edge": _format_edge(prop.get("edge", "")),
                "Dir": prop.get("direction", ""),
                "Source": prop.get("source", ""),
            })
    if not rows:
        st.caption(f"No DK player props scraped for {sport} on {date_str} (lines only post 30-60 min before tip).")
        return
    rows = sorted(rows, key=lambda r: abs(float(str(r.get("Edge", "0")).replace("+", "") or 0)), reverse=True)
    st.dataframe(rows, use_container_width=True)


def _render_projections(sport: str, date_str: str, matchup: Optional[str]) -> None:
    """Show full player projections from proj_*.json for the selected matchup."""
    projs = _load_matchup_projections(date_str)
    if not projs:
        st.caption("No matchup projection files found.")
        return
    if matchup and matchup != "ALL":
        key = matchup.upper().replace(" @ ", "@")
        projs = {k: v for k, v in projs.items() if key == k or key in k}
    if not projs:
        st.caption(f"No projections for {matchup}.")
        return
    for matchup_key, data in projs.items():
        m_sport = (data.get("sport") or "").upper()
        if sport != "ALL" and m_sport and m_sport != sport:
            continue
        players = _flatten_roster(data)
        with st.expander(f"📊 {matchup_key} — {len(players)} players | source: {data.get('source', '?')}", expanded=True):
            if not players:
                st.caption("No roster players in this projection file.")
                continue
            rows = []
            for p in players[:30]:
                rows.append({
                    "Side": p.get("_side", "").upper(),
                    "Group": p.get("_group", "").title(),
                    "Player": p.get("name", ""),
                    "Pos": p.get("position", ""),
                    "Role": p.get("role", ""),
                    "PTS": p.get("tc_pts", p.get("pts", "")),
                    "REB": p.get("tc_reb", p.get("reb", "")),
                    "AST": p.get("tc_ast", p.get("ast", "")),
                    "3PM": p.get("tc_3pm", p.get("tpm", p.get("3pm", ""))),
                    "STL": p.get("tc_stl", p.get("stl", "")),
                    "BLK": p.get("tc_blk", p.get("blk", "")),
                })
            st.dataframe(rows, use_container_width=True)


def _render_combo_builder() -> None:
    """Real combo builder — pulls live DK lines from proj_*.json, runs ComboQualifier."""
    st.subheader("🧩 Combo Builder (all sports)")

    # Discover combos stored on disk by the pipeline
    today = _today_et()
    base = DAILY_LOG / today
    if not base.exists():
        st.caption("No daily log yet — run daily_picks.py first.")
        return

    combo_files = sorted(base.glob("combos_*.json"))
    if not combo_files:
        st.caption(f"No combos_*.json found in {base}. Run daily_picks.py to generate.")
        return

    rows: List[Dict[str, Any]] = []
    for f in combo_files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(data, list):
            data = [data]
        for c in data:
            if not isinstance(c, dict):
                continue
            rows.append({
                "File": f.name.replace("combos_", "").replace(".json", ""),
                "Matchup": c.get("matchup", c.get("Matchup", "")),
                "Type": c.get("type", c.get("combo_type", "")),
                "Legs": c.get("legs", c.get("leg_count", "?")),
                "Combined Edge": _format_edge(c.get("combined_edge", c.get("edge", ""))),
                "Est Odds": c.get("est_odds", c.get("estimated_odds", "")),
                "Players": ", ".join(
                    l.get("player", "") for l in (c.get("leg_list") or c.get("legs_detail") or [])
                ) or str(c.get("players", "")),
                "Bet": c.get("bet", c.get("wager", "")),
            })

    if not rows:
        st.caption("Combos files exist but are empty.")
        return

    st.dataframe(rows, use_container_width=True)


def _render_adapter_status() -> None:
    st.subheader("🔌 Adapter Status (Market Lines)")
    try:
        from src.adapters.market_line_provider import MarketLineProvider
        for s in SPORT_LIST:
            st_obj = MarketLineProvider.status(s)
            st.write(
                f"**{s}** — source: `{st_obj.get('source', '?')}`, "
                f"events: {st_obj.get('events', 0)}, "
                f"props: {st_obj.get('props', False)}, "
                f"msg: {st_obj.get('message', '')}"
            )
    except Exception as e:
        st.caption(f"Adapter status: {e}")


def _render_event_trigger() -> None:
    st.subheader("⚡ Event Trigger Monitor")
    try:
        from src.services.event_trigger import EventTrigger
        et = EventTrigger()
        st.metric("Subscriptions", len(getattr(et, "subscribers", [])))
        st.metric("Triggers fired", len(getattr(et, "history", [])))
        history = getattr(et, "history", [])[-10:]
        if history:
            st.dataframe(history, use_container_width=True)
    except Exception as e:
        st.caption(f"Event trigger unavailable: {e}")


def _render_cache_panel() -> None:
    st.subheader("🗄️ Cache + Live Poller")
    try:
        from src.cache.optimized_cache import OptimizedCache
        c = OptimizedCache()
        st.metric("Cache entries", len(getattr(c, "_store", {})))
    except Exception as e:
        st.caption(f"Cache unavailable: {e}")
    try:
        from src.gates.live_poller import LivePoller
        lp = LivePoller()
        st.metric("Polls completed", getattr(lp, "polls", 0))
    except Exception as e:
        st.caption(f"Live poller unavailable: {e}")


def _render_health() -> None:
    st.subheader("📊 System Health")
    tab1, tab2, tab3 = st.tabs(["Quota", "Projections", "Backups"])
    with tab1:
        try:
            from src.monitoring.api_call_budget import report_all
            for svc, st_data in (report_all() or {}).items():
                if isinstance(st_data, dict):
                    st.write(
                        f"- **{svc}**: {st_data.get('used', '?')}/{st_data.get('limit', '?')} "
                        f"({st_data.get('pct_used', '?')}% used, "
                        f"{st_data.get('remaining', '?')} remaining)"
                    )
        except Exception as e:
            st.caption(f"Quota unavailable: {e}")
    with tab2:
        if st.button("Run health check"):
            try:
                from src.domain.projection_service import ProjectionService
                svc = ProjectionService()
                rows = []
                for s in SPORT_LIST:
                    r = svc.get_projections(s)
                    rows.append({
                        "Sport": s,
                        "Source": r.get("source", "?"),
                        "Count": r.get("count", 0),
                    })
                st.dataframe(rows, use_container_width=True)
            except Exception as e:
                st.error(f"Health check failed: {e}")
    with tab3:
        if st.button("Run daily backup now"):
            try:
                from src.domain.services.backup_service import backup_daily_data
                result = backup_daily_data()
                st.success(
                    f"Copied {result.get('files_copied', 0)} files "
                    f"({result.get('bytes', 0)} bytes) → {result.get('dest', '')}"
                )
            except Exception as e:
                st.error(f"Backup failed: {e}")


# ── Main ────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="TC Sports Dashboard", layout="wide")
    st.title("🟢 TC — Triple Conservative Dashboard")
    st.caption("Reads picks.csv + proj_*.json from Daily_Log/. Surfaces DK-scraped lines + projections + combos.")

    today = _today_et()
    sport = st.sidebar.selectbox("Sport", SPORT_LIST, index=0)
    date_str = st.sidebar.text_input("Date (YYYY-MM-DD)", today)
    matchup = st.sidebar.selectbox("Matchup", _matchup_options(_load_picks(date_str, sport)))

    # API budget sidebar
    try:
        from src.monitoring.api_call_budget import budget_status
        b = budget_status("oddsapi")
        st.sidebar.metric("Odds API calls today", f"{b['calls_today']}/{b['daily_limit']}")
    except Exception as e:
        st.sidebar.caption(f"Budget: unavailable ({e})")

    # Top edges
    st.subheader(f"📊 Top Edges — {sport} ({date_str})" + (f" / {matchup}" if matchup != "ALL" else ""))
    _render_top_edges(sport, date_str, matchup)

    # DK lines (scraped)
    st.subheader(f"📈 DK-Scraped Lines — {sport}" + (f" / {matchup}" if matchup != "ALL" else ""))
    _render_dk_lines(sport, date_str, matchup)

    # Matchup projections (roster)
    st.subheader("🧢 Player Projections (Roster)")
    _render_projections(sport, date_str, matchup)

    # Combo builder
    _render_combo_builder()

    # Adapter status
    _render_adapter_status()

    # Event trigger
    _render_event_trigger()

    # Cache + poller
    _render_cache_panel()

    # Health
    _render_health()


if __name__ == "__main__":
    main()
