"""TC Sports Dashboard — Multi-sport Streamlit UI.
Reads clean picks from sports_betting_dashboard/data/picks/.
Serves on port 8510."""
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

SPORT_BADGES = {
    "WNBA": "#ff6b00",
    "MLB": "#1e88e5",
    "WORLD CUP": "#00897b",
    "WORLD_CUP": "#00897b",
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
    """Load picks from CSV file. Returns list of dicts."""
    if not csv_path.exists():
        return []
    try:
        rows = []
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("direction", "") == "INVALID":
                    continue
                try:
                    row["edge"] = float(row.get("edge", 0) or 0)
                except (ValueError, TypeError):
                    row["edge"] = 0.0
                try:
                    row["tc_projection"] = float(row.get("tc_projection", 0) or 0)
                except (ValueError, TypeError):
                    row["tc_projection"] = 0.0
                try:
                    row["market_line"] = float(row.get("market_line", 0) or 0)
                except (ValueError, TypeError):
                    row["market_line"] = 0.0
                rows.append(row)
        return rows
    except Exception:
        return []


def load_picks_for_dashboard():
    """Load picks from actionable CSV first, fall back to clean, then today."""
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


def load_summaries(data_dir):
    path = data_dir / "summaries.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def load_last_run():
    path = LOG_DIR / "last_run.json"
    if not path.exists():
        return {"timestamp": "never", "sports": [], "games_logged": 0, "picks_logged": 0}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def render_summary_card(last_run):
    ts = last_run.get("timestamp", "never")
    sports = last_run.get("sports", [])
    games = last_run.get("games_logged", 0)
    total_picks = last_run.get("picks_logged", 0)
    errors = last_run.get("errors", [])

    cols = st.columns(4)
    cols[0].metric("Last Run", ts[:19] if ts != "never" else "never")
    cols[1].metric("Sports", ", ".join(sports) if sports else "none")
    cols[2].metric("Games", games)
    cols[3].metric("Picks", total_picks)
    if errors:
        with st.expander(f"{len(errors)} errors"):
            for e in errors:
                st.write(f"- {e}")


def render_sport_section(sport, picks, source_file):
    badge = SPORT_BADGES.get(sport, "#666")
    st.markdown(
        f"<h3 style='color:{badge};border-bottom:2px solid {badge};padding-bottom:4px;'>{sport}</h3>",
        unsafe_allow_html=True,
    )

    csv_league = sport.replace(" ", "_")
    sport_picks = [p for p in picks if p.get("league", "") in (sport, csv_league)]

    if not sport_picks:
        st.caption(f"No picks for {sport} today.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        over_picks = [p for p in sport_picks if p.get("direction") == "OVER"]
        under_picks = [p for p in sport_picks if p.get("direction") == "UNDER"]

        st.write(f"**{len(sport_picks)} picks** — {len(over_picks)} OVER · {len(under_picks)} UNDER")
        st.caption(f"Source: {source_file} | Showing top 25 by edge")

        sorted_picks = sorted(sport_picks, key=lambda x: abs(x.get("edge", 0)), reverse=True)[:25]
        pick_rows = []
        for p in sorted_picks:
            edge_val = p.get("edge", 0)
            direction = p.get("direction", "")
            dir_icon = "▲" if direction == "OVER" else "▼" if direction == "UNDER" else "•"
            pick_rows.append({
                "Player": p.get("player", "?"),
                "Team": p.get("team", "?"),
                "Matchup": p.get("matchup", ""),
                "Stat": p.get("stat", "?"),
                "Dir": f"{dir_icon} {direction}",
                "TC Proj": f"{p.get('tc_projection', 0):.1f}",
                "Line": f"{p.get('market_line', 0):.1f}",
                "Edge": f"{edge_val:+.2f}",
            })
        st.dataframe(pick_rows, use_container_width=True, hide_index=True)

    with col2:
        st.write("**Edge Distribution**")
        try:
            import matplotlib.pyplot as plt
            edges = [abs(p.get("edge", 0) or 0) for p in sport_picks if p.get("edge") is not None]
            if edges:
                fig, ax = plt.subplots(figsize=(4, 3))
                ax.hist(edges, bins=10, color=badge, alpha=0.7, edgecolor="white")
                ax.axvline(x=2.0, color="red", linestyle="--", alpha=0.7, label="TC threshold (2.0)")
                ax.set_xlabel("|Edge|")
                ax.set_ylabel("Count")
                ax.legend(fontsize=8)
                st.pyplot(fig)
            else:
                st.caption("No edge data")
        except Exception:
            st.caption("No edge data available")

    st.divider()


def render_mlb_live():
    st.subheader("⚾ MLB Live Scoreboard (ESPN)")
    try:
        sys.path.insert(0, str(WORKSPACE / "tc-sports-app"))
        from src.adapters import espn
        data = espn.fetch_scoreboard("baseball/mlb", ttl=30)
        if not data:
            st.info("No MLB games on ESPN scoreboard right now")
            return
        events = data.get("events", [])
        live_games = []
        for g in events:
            comp = g.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            status = g.get("status", {})
            st_type = status.get("type", {})
            state = st_type.get("state", "")
            live_games.append({
                "away": away.get("team", {}).get("abbreviation", "?"),
                "home": home.get("team", {}).get("abbreviation", "?"),
                "away_score": away.get("score", "0"),
                "home_score": home.get("score", "0"),
                "inning": status.get("period", 0),
                "detail": st_type.get("shortDetail", ""),
                "state": state,
            })
        for g in live_games:
            emoji = "🔴" if g["state"] == "in" else "⏰" if g["state"] == "pre" else "✅"
            st.write(
                f"{emoji} **{g['away']}** {g['away_score']} @ **{g['home']}** {g['home_score']} — {g['detail']}"
            )
    except Exception as e:
        st.caption(f"Live scoreboard unavailable: {e}")


def main():
    st.title("🏀 TC Sports Dashboard")
    st.caption(f"Triple Conservative Projections — {datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S ET')}")

    picks, source_file = load_picks_for_dashboard()

    total_picks = len(picks)
    over_count = len([p for p in picks if p.get("direction") == "OVER"])
    under_count = len([p for p in picks if p.get("direction") == "UNDER"])
    sports_set = set(p.get("league", "?").replace("_", " ") for p in picks)

    cols = st.columns(5)
    cols[0].metric("📋 Total Picks", total_picks)
    cols[1].metric("▲ OVER", over_count)
    cols[2].metric("▼ UNDER", under_count)
    cols[3].metric("🏟 Sports", len(sports_set))
    cols[4].metric("📁 Source", source_file or "none")

    # Top edges
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

    if not picks:
        st.warning("No picks found. Run: `python3 Projects/daily_picks.py --sport wnba && --sport mlb && --sport wc`")
        return

    sport_list = sorted(sports_set)
    tabs = st.tabs(sport_list)

    for i, sport in enumerate(sport_list):
        with tabs[i]:
            render_sport_section(sport, picks, source_file)

    st.divider()
    st.caption(
        f"TC Sports Dashboard — {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')} | "
        f"Load from: {source_file or 'none'}"
    )


if __name__ == "__main__":
    main()
