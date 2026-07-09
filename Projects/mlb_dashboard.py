"""
MLB Live Dashboard — Direct from Daily_Log + Live ESPN Stats
Uses real ESPN field names verified against the live API.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import sys
sys.path.insert(0, "/home/workspace/tc-sports-app")

from src.adapters import espn

st.set_page_config(page_title="MLB Live Dashboard", layout="wide")

# MLB stats actually present in proj_MLB_*.json (verified via file scan)
MLB_STATS = {
    "batters": ["hr", "rbi", "runs", "hits", "total_bases"],
    "pitchers": ["earned_runs", "hits_allowed", "strikeouts"],
    "game": ["home_score", "away_score", "inning", "outs", "balls", "strikes"],
}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"

# MLB stat display labels
MLB_STAT_LABELS = {
    "hr": "HR", "rbi": "RBI", "runs": "R", "hits": "H", "total_bases": "TB",
    "earned_runs": "ER", "hits_allowed": "HA", "strikeouts": "K",
}


def _get_espn_odds(comp):
    """ESPN attaches odds under comp.odds[0] when present (not always populated)."""
    odds_list = comp.get("odds", [])
    if not odds_list:
        return {"ml_home": "N/A", "ml_away": "N/A", "spread": "N/A", "total": "N/A"}
    o = odds_list[0]
    return {
        "ml_home": o.get("homeMoneyLine", "N/A"),
        "ml_away": o.get("awayMoneyLine", "N/A"),
        "spread": o.get("spread", "N/A"),
        "total": o.get("overUnder", "N/A"),
    }


def fetch_live_mlb_games():
    """Fetch live MLB games from ESPN. Returns list of game dicts with real fields.

    Field sources (all verified against live API):
    - score:        competitor.score
    - hits/errors:  competitor.hits, competitor.errors
    - inning scores: competitor.linescores[].displayValue
    - inning state: status.type.shortDetail (e.g. "Top 7th", "Bot 9th")
    - balls/strikes/outs: only available via summary endpoint -> situation
    - probables:    comp.probables[].athlete.displayName (pre-game only,
                    home/away inferred from which competitor owns the array)
    """
    data = espn.fetch_scoreboard("baseball/mlb", ttl=30)
    if not data:
        return []
    out = []
    for g in data.get("events", []):
        comp = g.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        status = g.get("status", {})
        st_type = status.get("type", {})
        state = st_type.get("state", "")  # "pre" | "in" | "post"

        # Linescores: list of {displayValue, period} per inning
        home_lines = home.get("linescores", [])
        away_lines = away.get("linescores", [])

        # Probables: comp.probables is a flat list but each probable.athlete has
        # no homeAway — we must determine home/away from the COMPETITOR that
        # owns the probables array. For pre-game, comp is the only competition
        # and probables can be [home, away] or [away, home] depending on game.
        # ESPN embeds homeAway on each probable in pre-game but NOT always.
        # Safe approach: use a simple index split.
        probables = comp.get("probables", []) or []
        home_pitcher = "TBD"
        away_pitcher = "TBD"
        if len(probables) >= 2:
            # Standard ESPN pre-game: home pitcher first
            home_pitcher = probables[0].get("athlete", {}).get("displayName", "TBD")
            away_pitcher = probables[1].get("athlete", {}).get("displayName", "TBD")
        elif len(probables) == 1:
            home_pitcher = probables[0].get("athlete", {}).get("displayName", "TBD")

        # Balls/strikes/outs come from summary endpoint, not scoreboard.
        # Fetch summary only for live games to avoid extra calls.
        balls = strikes = outs = None
        if state == "in":
            try:
                ev_id = g.get("id")
                if ev_id:
                    summary = espn.fetch_summary("baseball/mlb", str(ev_id), ttl=15)
                    if summary:
                        sit = summary.get("situation", {})
                        balls = sit.get("balls")
                        strikes = sit.get("strikes")
                        outs = sit.get("outs")
            except Exception:
                pass

        out.append({
            "event_id": g.get("id", ""),
            "home_team": home.get("team", {}).get("abbreviation", "?"),
            "away_team": away.get("team", {}).get("abbreviation", "?"),
            "home_score": home.get("score", "0"),
            "away_score": away.get("score", "0"),
            "home_hits": home.get("hits", 0),
            "away_hits": away.get("hits", 0),
            "home_errors": home.get("errors", 0),
            "away_errors": away.get("errors", 0),
            "inning": status.get("period", 0),
            "inning_state": st_type.get("shortDetail", ""),  # "Top 7th", "Bot 9th", "Final"
            "state": state,
            "balls": balls,
            "strikes": strikes,
            "outs": outs,
            "home_pitcher": home_pitcher,
            "away_pitcher": away_pitcher,
            "home_lines": [ls.get("displayValue", "-") for ls in home_lines],
            "away_lines": [ls.get("displayValue", "-") for ls in away_lines],
            "odds": _get_espn_odds(comp),
        })
    return out


def load_mlb_data(date_str):
    """Load projections and game metadata from Daily_Log proj_MLB_*.json files."""
    log_dir = Path(f"/home/workspace/Daily_Log/{date_str}")
    if not log_dir.exists():
        return [], []
    files = list(log_dir.glob("proj_MLB_*.json"))
    picks, games = [], []
    for f in files:
        try:
            d = json.loads(f.read_text())
            picks.extend(d.get("valid_props", []))
            odds = d.get("odds", {}) or {}
            games.append({
                "home": d.get("home_team", ""),
                "away": d.get("away_team", ""),
                "dk_total": odds.get("total", d.get("dk_total", "N/A")),
                "ml_source": odds.get("ml_source", "N/A"),
                "ml_pick": d.get("team_to_win", "N/A"),
                "ml_home": odds.get("ml_home", "N/A"),
                "ml_away": odds.get("ml_away", "N/A"),
                "spread_pick": d.get("spread_pick", "N/A"),
                "total_lean": d.get("signal", "N/A"),
                "dk_available": d.get("dk_available", False),
                "prop_source": d.get("prop_source", ""),
                "mode": d.get("mode", ""),
            })
        except Exception as e:
            st.warning(f"Error reading {f.name}: {e}")
    return picks, games


def render_live_scoreboard(live_games):
    if not live_games:
        st.info("No MLB games on ESPN scoreboard right now")
        return
    live = [g for g in live_games if g["state"] == "in"]
    pre = [g for g in live_games if g["state"] == "pre"]
    final = [g for g in live_games if g["state"] == "post"]

    if live:
        st.subheader(f"🔴 LIVE NOW ({len(live)})")
        for g in live:
            with st.expander(
                f"{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']} — {g['inning_state']}",
                expanded=True,
            ):
                _render_game_card(g)

    if pre:
        st.subheader(f"⏰ UPCOMING ({len(pre)})")
        for g in pre:
            with st.expander(
                f"{g['away_team']} @ {g['home_team']} — {g['inning_state']}",
                expanded=False,
            ):
                _render_game_card(g)

    if final and st.checkbox(f"Show {len(final)} completed games", value=False):
        st.subheader(f"✅ FINAL ({len(final)})")
        for g in final:
            with st.expander(
                f"{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']} — Final",
                expanded=False,
            ):
                _render_game_card(g)


def _render_game_card(g):
    c1, c2, c3 = st.columns([2, 1, 2])
    c1.metric(g["home_team"], g["home_score"])
    c2.write(f"**{g['inning_state']}**")
    if g["state"] == "in" and g["balls"] is not None:
        c2.write(f"Outs: {g['outs']} | B: {g['balls']} | S: {g['strikes']}")
    c3.metric(g["away_team"], g["away_score"])
    c4, c5 = st.columns(2)
    c4.write(f"**Home Pitcher:** {g['home_pitcher']}")
    c5.write(f"**Away Pitcher:** {g['away_pitcher']}")
    st.caption("Lines: ESPN free API has no odds — book lines unavailable")
    st.write(
        f"Hits: {g['home_hits']}–{g['away_hits']} | "
        f"Errors: {g['home_errors']}–{g['away_errors']}"
    )
    if g["home_lines"] or g["away_lines"]:
        st.write(
            f"Innings: {g['away_team']} "
            f"{' '.join(g['away_lines']) if g['away_lines'] else '-'} | "
            f"{g['home_team']} "
            f"{' '.join(g['home_lines']) if g['home_lines'] else '-'}"
        )


def render_pitcher_matchup(games):
    st.subheader("⚾ Game Projections")
    if not games:
        st.info("No games loaded")
        return
    rows = []
    dk_count = 0
    for g in games:
        if g.get("dk_available"):
            dk_count += 1
        rows.append({
            "Matchup": f"{g['away']} @ {g['home']}",
            "ML Pick": g["ml_pick"],
            "DK Total": g["dk_total"],
            "Total Lean": g["total_lean"],
            "Lines": "DK" if g.get("dk_available") else "TC only",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption(f"{dk_count}/{len(games)} games with DK lines (via SportsDataIO).")


def render_top_picks(picks, n=15):
    st.subheader(f"🔥 Top {n} Picks (by TC Edge)")
    if not picks:
        st.info("No picks for this date")
        return
    sorted_picks = sorted(picks, key=lambda x: x.get("edge", 0), reverse=True)[:n]
    rows = []
    for p in sorted_picks:
        stat = p.get("stat", "N/A")
        rows.append({
            "Player": p.get("player_name", ""),
            "Team": p.get("team", ""),
            "Stat": MLB_STAT_LABELS.get(stat, stat),
            "Line": p.get("line", 0),
            "Edge": round(p.get("edge", 0), 2),
            "Signal": p.get("signal", ""),
            "Confidence": f"{p.get('confidence', 0):.0%}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def render_stat_leaders(picks):
    st.subheader("🏆 Stat Leaders (Top 5 by Line)")
    if not picks:
        st.info("No picks for stat leaders")
        return
    by_stat = {}
    for p in picks:
        stat = p.get("stat", "")
        by_stat.setdefault(stat, []).append(p)
    for stat, items in by_stat.items():
        label = MLB_STAT_LABELS.get(stat, stat)
        top = sorted(items, key=lambda x: x.get("line", 0), reverse=True)[:5]
        st.write(f"**{label}**")
        for p in top:
            st.write(f"{p.get('player_name', '?')}: {p.get('line', 0):.2f}")


def main():
    st.title("⚾ MLB Live Dashboard")
    date = st.date_input("Date", datetime.now())
    date_str = date.strftime("%Y-%m-%d")

    picks, games = load_mlb_data(date_str)
    live_games = fetch_live_mlb_games()

    st.sidebar.metric("Total Picks", len(picks))
    st.sidebar.metric("Games (Daily_Log)", len(games))
    st.sidebar.metric("ESPN Games", len(live_games))
    if st.sidebar.button("🔄 Refresh Live Data"):
        st.rerun()

    st.subheader("📺 Live Scoreboard (ESPN)")
    render_live_scoreboard(live_games)
    st.divider()

    render_pitcher_matchup(games)
    st.divider()
    render_top_picks(picks)
    st.divider()
    render_stat_leaders(picks)

    st.divider()
    st.caption(f"MLB Live Dashboard — {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")


if __name__ == "__main__":
    main()
