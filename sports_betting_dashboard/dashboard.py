"""TC Sports Dashboard — Multi-sport Streamlit UI.
WNBA + MLB. Reads picks from sports_betting_dashboard/data/picks/.
Serves on port 8510.
"""
import streamlit as st
import csv
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="TC Sports Dashboard", page_icon="🏀", layout="wide")

ET = timezone(timedelta(hours=-4))
WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
TODAY = datetime.now(ET).strftime("%Y-%m-%d")
PICKS_DIR = WORKSPACE / "sports_betting_dashboard" / "data" / "picks"

SPORT_CONFIG = {
    "WNBA": {"badge": "#ff6b00", "icon": "🏀", "label": "WNBA"},
    "MLB": {"badge": "#1e88e5", "icon": "⚾", "label": "MLB"},
}

SIGNAL_COLORS = {
    "STRONG": "🟢",
    "MODERATE": "🟡",
    "WEAK": "🔴",
}


def find_latest_data_dir():
    today_dir = LOG_DIR / TODAY
    if (today_dir / "picks.csv").exists():
        return today_dir
    dirs = sorted(
        [d for d in LOG_DIR.iterdir() if d.is_dir() and (d / "picks.csv").exists()],
        reverse=True,
    )
    return dirs[0] if dirs else today_dir


def load_picks_from_csv(csv_path):
    if not csv_path.exists():
        return []
    try:
        rows = []
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("direction", "") == "INVALID":
                    continue
                if row.get("league", "") == "WC":
                    continue
                for col in ("edge", "tc_projection", "market_line", "tc_target", "threshold"):
                    try:
                        row[col] = float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        row[col] = 0.0
                rows.append(row)
        return rows
    except Exception:
        return []


def load_picks_for_dashboard():
    paths = [
        PICKS_DIR / "actionable_picks.csv",
        PICKS_DIR / "clean_picks.csv",
        PICKS_DIR / "today_picks.csv",
    ]
    for p in paths:
        picks = load_picks_from_csv(p)
        if picks:
            return picks, p.name
    return [], "none"


def load_last_run():
    path = LOG_DIR / "last_run.json"
    if not path.exists():
        return {"timestamp": "never", "sports": [], "games_logged": 0, "picks_logged": 0}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def render_sport_section(sport, picks, source_file):
    cfg = SPORT_CONFIG.get(sport, {"badge": "#666", "icon": "📊", "label": sport})
    badge = cfg["badge"]
    icon = cfg["icon"]

    st.markdown(
        f"<h3 style='color:{badge};border-bottom:2px solid {badge};padding-bottom:4px;'>{icon} {cfg['label']}</h3>",
        unsafe_allow_html=True,
    )

    sport_picks = [p for p in picks if p.get("league", "") == sport]

    if not sport_picks:
        st.caption(f"No picks for {cfg['label']} today.")
        return

    over_picks = [p for p in sport_picks if p.get("direction") == "OVER"]
    under_picks = [p for p in sport_picks if p.get("direction") == "UNDER"]
    strong = [p for p in sport_picks if p.get("signal") == "STRONG"]
    moderate = [p for p in sport_picks if p.get("signal") == "MODERATE"]

    st.write(
        f"**{len(sport_picks)} picks** — "
        f"{len(over_picks)} OVER · {len(under_picks)} UNDER | "
        f"{len(strong)} STRONG · {len(moderate)} MODERATE"
    )
    st.caption(f"Source: {source_file} | Sorted by edge strength")

    sorted_picks = sorted(sport_picks, key=lambda x: abs(x.get("edge", 0)), reverse=True)[:30]

    for p in sorted_picks:
        edge_val = abs(p.get("edge", 0))
        direction = p.get("direction", "")
        dir_icon = "▲" if direction == "OVER" else "▼" if direction == "UNDER" else "•"
        signal = p.get("signal", "WEAK")
        signal_icon = SIGNAL_COLORS.get(signal, "⚪")
        proj = float(p.get("tc_projection", 0))
        line = float(p.get("market_line", 0))
        why = p.get("why", "")

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 5])
            with col1:
                st.markdown(
                    f"**{p.get('player', '?')}** · {p.get('team', '?')}  \n"
                    f"{p.get('stat', '?')} {dir_icon} {direction}"
                )
            with col2:
                st.markdown(
                    f"{signal_icon} {signal}  \n"
                    f"Proj **{proj:.1f}** vs **{line:.1f}**  \n"
                    f"Edge **{edge_val:+.1f}%**"
                )
            with col3:
                st.caption(why)
        st.divider()


def main():
    st.title("🏀 TC Sports Dashboard")
    st.caption(f"Triple Conservative Projections — WNBA + MLB | {datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S ET')}")

    picks, source_file = load_picks_for_dashboard()

    total_picks = len(picks)
    over_count = len([p for p in picks if p.get("direction") == "OVER"])
    under_count = len([p for p in picks if p.get("direction") == "UNDER"])
    strong_count = len([p for p in picks if p.get("signal") == "STRONG"])
    sports_set = set(p.get("league", "?") for p in picks)

    cols = st.columns(5)
    cols[0].metric("📋 Total Picks", total_picks)
    cols[1].metric("▲ OVER", over_count)
    cols[2].metric("▼ UNDER", under_count)
    cols[3].metric("🟢 Strong", strong_count)
    cols[4].metric("🏟 Sports", len(sports_set))

    if picks:
        top_by_edge = sorted(picks, key=lambda x: abs(x.get("edge", 0)), reverse=True)[:3]
        with st.expander("🔥 Top 3 picks by edge"):
            for p in top_by_edge:
                dir_icon = "▲" if p.get("direction") == "OVER" else "▼"
                st.write(
                    f"**{p.get('player', '?')}** ({p.get('team', '?')}) — "
                    f"{p.get('stat', '?')} {dir_icon} {p.get('direction', '?')} "
                    f"| Proj {float(p.get('tc_projection', 0)):.1f} vs Line {float(p.get('market_line', 0)):.1f} "
                    f"| Edge **{float(p.get('edge', 0)):+.2f}**"
                )
                if p.get("why"):
                    st.caption(p["why"])

    if not picks:
        st.warning("No picks found. Run: `python3 Projects/daily_picks.py --sport all`")
        return

    sport_list = sorted(sports_set)
    if sport_list:
        tabs = st.tabs(sport_list)
        for i, sport in enumerate(sport_list):
            with tabs[i]:
                render_sport_section(sport, picks, source_file)

    st.divider()
    st.caption(
        f"TC Sports Dashboard — {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')} | "
        f"Source: {source_file or 'none'}"
    )


if __name__ == "__main__":
    main()
