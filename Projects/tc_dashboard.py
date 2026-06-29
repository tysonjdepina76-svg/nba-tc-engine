#!/usr/bin/env python3
# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""TC Live Dashboard — sport-aware. Reads real pipeline output from Daily_Log/ and displays it for any sport (NBA, WNBA, NFL, MLB, SOCCER, NHL)."""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests
import subprocess
import streamlit as st

st.set_page_config(page_title="TC Picks Dashboard", page_icon="🏀", layout="wide")

ET = timezone(timedelta(hours=-4))  # EDT
WORKSPACE = Path("/home/workspace")
sys.path.insert(0, str(WORKSPACE / "tc-sports-app"))
from src.domain.entities import Sport, BADGE_COLORS
from src.domain.sport_config import get_sport_config, stat_keys

LOG_DIR = WORKSPACE / "Daily_Log"
IMAGES_DIR = WORKSPACE / "reports" / "images"


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


def _espn_slate(espn_path: str) -> list:
    """Fetch ESPN scoreboard for a sport path. Returns list of events."""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        return data.get("events", [])
    except Exception as e:
        return []


def _espn_event_roster(espn_path: str, event_id: str) -> dict:
    """Fetch boxscore roster for a specific ESPN event."""
    out = {"away_players": [], "home_players": []}
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/summary?event={event_id}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            summary = json.loads(resp.read().decode())
        for team_data in (summary.get("boxscore") or {}).get("players", []):
            team_abbr = (team_data.get("team") or {}).get("abbreviation", "")
            stats_block = (team_data.get("statistics") or [{}])[0]
            labels = stats_block.get("labels", [])
            athletes = stats_block.get("athletes", [])
            for athlete_entry in athletes:
                if athlete_entry.get("didNotPlay"):
                    continue
                athlete = athlete_entry.get("athlete", {})
                name = athlete.get("displayName", athlete.get("fullName", "Unknown"))
                pos = (athlete.get("position") or {}).get("abbreviation", "")
                raw_stats = athlete_entry.get("stats", [])
                stat_map = {}
                for i, label in enumerate(labels):
                    val = raw_stats[i] if i < len(raw_stats) else "0"
                    try:
                        stat_map[str(label).lower()] = float(val) if "." in str(val) or str(val).replace("-", "").isdigit() else 0
                    except Exception:
                        stat_map[str(label).lower()] = 0
                key = "home_players" if (team_data.get("homeAway") == "home") else "away_players"
                if key == "away_players" and team_abbr and not out["away_players"]:
                    pass
                if team_data.get("homeAway") == "home":
                    out["home_players"].append({"name": name, "team": team_abbr, "position": pos, "stats": stat_map})
                else:
                    out["away_players"].append({"name": name, "team": team_abbr, "position": pos, "stats": stat_map})
    except Exception:
        pass
    return out


def _espn_dk_lines(espn_path: str, away: str, home: str) -> dict:
    """Pull DK lines for the next upcoming event matching away@home."""
    out = {"total": None, "spread": None, "ml_home": None, "ml_away": None}
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


# Sport → ESPN path + display label + league filter token
SPORT_PATHS = {
    "NBA": ("basketball/nba", "NBA"),
    "WNBA": ("basketball/wnba", "WNBA"),
    "NFL": ("football/nfl", "NFL"),
    "MLB": ("baseball/mlb", "MLB"),
    "SOCCER": ("soccer/World Cup", "WORLD CUP"),  # ESPN uses "soccer/<league>"
    "NHL": ("hockey/nhl", "NHL"),
}


def render_roster(sport: str, data: dict):
    """Render a sport-specific roster table."""
    config = get_sport_config(sport)
    keys = config.get("stat_keys", [])
    # Build rows
    rows = []
    for side in ("away_players", "home_players"):
        for p in data.get(side, []):
            row = {"Player": p.get("name", "?"), "Position": p.get("position", ""), "Team": p.get("team", "")}
            for k in keys:
                v = (p.get("stats") or {}).get(k.lower(), 0)
                row[k] = v
            rows.append(row)
    if not rows:
        st.caption("No roster data — select a game or run pipeline")
        return
    df = pd.DataFrame(rows)
    cols = ["Player", "Position", "Team"] + keys
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


def render_projections(sport: str, matchup: str | None):
    """Show TC projections for the selected sport."""
    if not matchup:
        st.caption("Pick a matchup to see projections")
        return
    config = get_sport_config(sport)
    keys = config.get("stat_keys", [])
    # Pull from /api/tc if available, else from local picks.csv
    try:
        espn_path, _ = SPORT_PATHS.get(sport, ("", sport))
        params = {"sport": sport, "away": matchup.split("@")[0], "home": matchup.split("@")[1], "mode": "project"}
        r = requests.get(f"https://true.zo.space/api/tc", params=params, timeout=10, headers={"Accept": "application/json"})
        if r.ok:
            data = r.json()
            vp = data.get("valid_props", [])
            if vp:
                rows = [{"Player": p.get("player"), "Stat": p.get("stat"), "Line": p.get("market_line"),
                         "TC": p.get("tc_projection"), "Edge": p.get("edge"),
                         "Direction": p.get("direction"), "Status": p.get("status")} for p in vp]
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True,
                             column_config={"Edge": st.column_config.NumberColumn(format="%.2f"),
                                            "TC": st.column_config.NumberColumn(format="%.2f")})
                return
    except Exception:
        pass
    # Fallback to local picks.csv
    sport_col = "league" if "league" in picks.columns else "sport"
    if not picks.empty and sport_col in picks.columns:
        sub = picks[picks[sport_col].str.upper().str.contains(sport.upper(), na=False)]
        if matchup and "matchup" in sub.columns:
            sub = sub[sub["matchup"].astype(str).str.contains(matchup.split("@")[0], case=False, na=False)]
        if not sub.empty:
            st.dataframe(sub.head(20), use_container_width=True, hide_index=True,
                         column_config={"edge": st.column_config.NumberColumn(format="%.2f"),
                                        "tc_projection": st.column_config.NumberColumn(format="%.2f")})
            return
    st.caption(f"No projections for {sport} {matchup}")


def render_lines(sport: str, matchup: str | None):
    """Show game lines if available for selected sport."""
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
        st.caption(f"No DK lines available for {sport} {matchup} (off-season or lines not posted)")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", lines.get("total") or "—")
    c2.metric("Spread", lines.get("spread") or "—")
    c3.metric("ML Home", lines.get("ml_home") or "—")
    c4.metric("ML Away", lines.get("ml_away") or "—")


def render_cards(sport: str, matchup: str | None, max_n: int = 5):
    """Generate sport-specific fantasy cards."""
    badge = BADGE_COLORS.get(sport, "#888")
    st.markdown(
        f'<div style="display:inline-block;background:{badge};color:white;padding:4px 12px;'
        f'border-radius:12px;font-weight:bold;margin-bottom:8px;">{sport}</div>',
        unsafe_allow_html=True,
    )
    sport_token = {"SOCCER": "WORLD_CUP"}.get(sport, sport)
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







# ─── Live Combos (self-edge, no market dependency) ───────
def render_live_combos(sport: str, matchup: str | None):
    """Call FastAPI /live-combos endpoint instead of direct logic."""
    import requests
    from datetime import datetime as dt
    date_str = dt.now().strftime("%Y-%m-%d")
    API_BASE = os.environ.get("LIVE_COMBOS_API", "http://localhost:8000")

    try:
        resp = requests.get(
            f"{API_BASE}/live-combos",
            params={"sport": sport, "date": date_str,
                    "min_edge": 1.5, "min_conf": 0.6,
                    "min_corr": 0.3, "min_hit": 0.5,
                    "max_legs": 4, "min_legs": 2},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.caption(f"API unavailable: {e}. Falling back to local logic.")
        return _render_live_combos_local(sport, matchup)

    st.metric("Combos Found", data.get("combo_count", 0))
    report = data.get("filter_report", {})
    if report:
        st.caption(f"Filter: passed={len(report.get('passed', []))}, "
                   f"filtered={len(report.get('filtered', []))}")

    combos = data.get("combos", [])
    if not combos:
        st.caption("No qualifying combos today")
        return

    for c in combos[:8]:
        legs = c.get("legs", [])
        with st.expander(f"{c.get('total_legs', '?')}-leg | "
                         f"hit_prob={c.get('hit_probability', 0):.2f} | "
                         f"edge={c.get('avg_edge', 0):.1f}"):
            cols = st.columns(len(legs))
            for col, leg in zip(cols, legs):
                col.metric(
                    label=leg.get("player", "?"),
                    value=f"{leg.get('stat', '?')} {leg.get('direction', '?')} {leg.get('line', 0)}",
                    delta=f"proj {leg.get('tc_projection', 0):.1f} (edge {leg.get('edge', 0):+.1f})",
                )


def _render_live_combos_local(sport: str, matchup: str | None):
    """Local fallback when FastAPI unavailable."""
    try:
        from src.domain.combo_qualifier import ComboQualifier
    except Exception as e:
        st.caption(f"combo_qualifier import failed: {e}")
        return

    DATA_DIR = _find_latest_dir()
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


# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 TC Picks")
    sport_choice = st.selectbox(
        "Select Sport",
        ["NBA", "WNBA", "NFL", "MLB", "SOCCER", "NHL"],
        index=1,  # default WNBA
    )
    st.caption(f"Sport config: {get_sport_config(sport_choice)}")

# ─── Header ──────────────────────────────────────────────
st.title("🏀 TC Picks Dashboard")
st.caption(
    f"Last updated: {datetime.now(ET).strftime('%I:%M %p ET')} • "
    f"{len(picks)} picks loaded • Data dir: {DATA_DIR.name}"
)

espn_path, league_token = SPORT_PATHS.get(sport_choice, ("", sport_choice))
events = _espn_slate(espn_path) if espn_path else []
matchup_options = []
for ev in events:
    comp = (ev.get("competitions") or [{}])[0]
    comps = comp.get("competitors", [])
    a = next((t.get("team", {}).get("abbreviation", "") for t in comps if t.get("homeAway") == "away"), "")
    h = next((t.get("team", {}).get("abbreviation", "") for t in comps if t.get("homeAway") == "home"), "")
    if a and h:
        matchup_options.append(f"{a}@{h}")

st.subheader(f"{BADGE_COLORS.get(sport_choice, '')} {sport_choice}")
matchup_choice = st.selectbox("Matchup", [""] + matchup_options) if matchup_options else ""

tab_roster, tab_lines, tab_proj, tab_cards, tab_combos = st.tabs(["📋 Roster", "📈 Lines", "🎯 Projections", "🎴 Cards", "🔥 Live Combos"])

with tab_roster:
    if not matchup_choice:
        st.caption("Select a matchup above to load roster")
    else:
        parts = matchup_choice.split("@")
        ev_id = _espn_dk_lines(espn_path, parts[0], parts[1]).get("event_id")
        if ev_id:
            roster = _espn_event_roster(espn_path, ev_id)
            render_roster(sport_choice, roster)
        else:
            st.caption(f"No event ID for {matchup_choice}")

with tab_lines:
    render_lines(sport_choice, matchup_choice or None)

with tab_proj:
    render_projections(sport_choice, matchup_choice or None)

with tab_cards:
    render_cards(sport_choice, matchup_choice or None, max_n=5)

with tab_combos:
    render_live_combos(sport_choice, matchup_choice or None)

st.divider()
st.caption(f"Sources: ESPN live scoreboard + roster API + SGO/Odds API DK lines + TC math engine • Config: tc-sports-app/src/domain/sport_config.py")