"""
TC Sports Dashboard — Multi-sport Streamlit UI
Reads Daily_Log projection files for WNBA, MLB, World Cup.
Serves on port 8510.
"""
import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="TC Sports Dashboard", page_icon="🏀", layout="wide")

ET = timezone(timedelta(hours=-4))
WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
TODAY = datetime.now(ET).strftime("%Y-%m-%d")

SPORT_BADGES = {
    "WNBA": "#ff6b00",
    "MLB": "#1e88e5",
    "WORLD CUP": "#00897b",
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


def load_picks(data_dir):
    picks_path = data_dir / "picks.json"
    if not picks_path.exists():
        return []
    try:
        return json.loads(picks_path.read_text())
    except Exception:
        return []


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


def render_sport_section(sport, picks, summaries):
    badge = SPORT_BADGES.get(sport, "#666")
    st.markdown(
        f"<h3 style='color:{badge};border-bottom:2px solid {badge};padding-bottom:4px;'>{sport}</h3>",
        unsafe_allow_html=True,
    )

    sport_picks = [p for p in picks if p.get("league") == sport]
    sport_summaries = [s for s in summaries if s.get("sport") == sport]

    if not sport_picks and not sport_summaries:
        st.caption(f"No picks or summaries for {sport} today.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        if sport_summaries:
            st.write("**Game Summaries**")
            summary_rows = []
            for s in sport_summaries:
                away = s.get("away_team", "?")
                home = s.get("home_team", "?")
                signal = s.get("signal", "N/A")
                picks_count = s.get("picks", s.get("picks_with_dk", 0))
                summary_rows.append({
                    "Matchup": f"{away} @ {home}",
                    "Signal": signal,
                    "Picks": picks_count,
                    "DK Picks": s.get("picks_with_dk", "N/A"),
                    "Pending Props": s.get("pending_props_no_dk", "N/A"),
                })
            st.dataframe(summary_rows, use_container_width=True, hide_index=True)

        if sport_picks:
            st.write("**Top Picks by Edge**")
            valid = [p for p in sport_picks if p.get("result", "PENDING") == "PENDING"]
            sorted_picks = sorted(valid, key=lambda x: abs(x.get("edge", 0) or 0), reverse=True)[:15]
            pick_rows = []
            for p in sorted_picks:
                pick_rows.append({
                    "Player": p.get("player", "?"),
                    "Team": p.get("team", "?"),
                    "Stat": p.get("stat", "?"),
                    "Dir": p.get("direction", ""),
                    "Line": p.get("market_line", ""),
                    "TC Proj": p.get("tc_projection", ""),
                    "Edge": f"{p.get('edge', 0):+.1f}" if p.get("edge") is not None else "",
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
    st.caption("WNBA · MLB · World Cup — Triple Conservative Pipeline")

    data_dir = find_latest_data_dir()
    picks = load_picks(data_dir)
    summaries = load_summaries(data_dir)
    last_run = load_last_run()

    st.sidebar.metric("Data Date", str(data_dir).split("/")[-1])
    st.sidebar.metric("Total Picks", len(picks))
    st.sidebar.metric("Games", len(summaries))

    if st.sidebar.button("🔄 Refresh"):
        st.rerun()

    st.sidebar.divider()
    st.sidebar.caption(
        f"Dashboard v2.0\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}"
    )

    render_summary_card(last_run)
    st.divider()

    tabs = st.tabs(["📊 All Picks", "🏀 WNBA", "⚾ MLB", "⚽ World Cup", "📺 Live MLB"])

    with tabs[0]:
        render_sport_section("ALL", picks, summaries)

    with tabs[1]:
        render_sport_section("WNBA", picks, summaries)

    with tabs[2]:
        render_sport_section("MLB", picks, summaries)

    with tabs[3]:
        render_sport_section("WORLD CUP", picks, summaries)

    with tabs[4]:
        render_mlb_live()

    st.divider()
    st.caption(
        f"TC Sports Dashboard — {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')} | "
        f"Source: {data_dir}"
    )


if __name__ == "__main__":
    main()
