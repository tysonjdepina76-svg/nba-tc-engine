"""MLB cross-model betting dashboard (Streamlit)."""
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from src.adapters.mlb_pipeline import MLBPipeline

st.set_page_config(page_title="MLB Cross-Model Dashboard", layout="wide")

if "pipeline" not in st.session_state:
    st.session_state.pipeline = MLBPipeline("picks.csv")


def main() -> None:
    st.title("⚾ MLB Cross-Model Betting Dashboard")
    st.caption(f"Last Updated: {datetime.now():%Y-%m-%d %H:%M:%S}")

    with st.sidebar:
        st.header("Filters")
        min_edge = st.slider(
            "Minimum Cross Edge", -30.0, -5.0, -20.0, 0.5,
            help="More negative = stronger UNDER signal",
        )
        show_all = st.checkbox("Show All Games", value=False)
        if st.button("🔄 Refresh Live Odds"):
            st.session_state.pipeline.adapter.cache.clear()
            st.rerun()
        st.divider()
        st.header("Export")
        if st.button("📊 Export Best Bets"):
            out = st.session_state.pipeline.export_best_bets("best_bets.json", min_edge)
            st.success(f"Exported {out['total_games']} bets")

    best = st.session_state.pipeline.get_best_bets(min_cross_edge=min_edge)
    if not show_all:
        best = best[:10]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Strong Signals", len(best))
    with c2:
        avg = (sum(b["cross_score"] for b in best) / len(best)) if best else 0
        st.metric("Avg Cross Edge", f"{avg:.1f}")
    with c3:
        st.metric("Games with Live Odds",
                  sum(1 for b in best if b.get("live_odds_available")))
    with c4:
        st.metric("Top Edge",
                  f"{best[0]['cross_score']:.1f}" if best else "N/A")

    for bet in best:
        with st.expander(
            f"⭐ {bet['game']} | Cross: {bet['cross_score']:.1f} | "
            f"Pitch {bet['pitching_score']:.1f} | Bat {bet['batting_score']:.1f} | "
            f"{bet['total_legs']} legs"
        ):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🎯 Top Legs")
                legs_df = pd.DataFrame(bet["top_legs"])

                def _color(val):
                    if val < -5:
                        return "background-color: #ffcccc"
                    if val < -3:
                        return "background-color: #fff3bf"
                    return ""

                if not legs_df.empty:
                    st.dataframe(
                        legs_df.style.applymap(_color, subset=["edge"]),
                        use_container_width=True,
                    )
            with c2:
                st.subheader("📊 Live Odds")
                if bet.get("live_odds_available"):
                    st.json(bet.get("current_lines", {}))
                else:
                    st.info("No live odds (quota exhausted or game not posted)")

    st.divider()
    st.caption("Quota-guarded: falls back to cached/self-edge projections if Odds API 401s.")

    # ── NEW: Position sizing / ML confidence / historical performance ──
    _render_enhancement_section()


def _render_enhancement_section() -> None:
    """Surface size, ML confidence, and history from daily_picks wiring files."""
    from pathlib import Path

    log_root = Path("/home/workspace/Daily_Log")
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = log_root / today
    if not today_dir.exists():
        st.info("No picks for today yet — run `python daily_picks.py --sport MLB`.")
        return

    wiring_files = sorted(today_dir.glob("wiring_*.json"))
    if not wiring_files:
        st.info("No wiring data for today — Position Manager / ML / History will appear after the next run.")
        return

    st.subheader("📐 Sizing + ML + History")
    rows = []
    for wf in wiring_files:
        try:
            data = json.loads(wf.read_text())
        except Exception:
            continue
        for pos in data.get("positions", []):
            rows.append({
                "Sport": wf.stem.replace("wiring_", ""),
                "Player": pos.get("player"),
                "Stat": pos.get("stat"),
                "Direction": pos.get("direction"),
                "Line": pos.get("line"),
                "Edge": pos.get("edge"),
                "Stake": pos.get("stake"),
                "ML Conf": pos.get("ml_confidence"),
            })
    if rows:
        df = pd.DataFrame(rows)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Sized Picks", len(df))
        with c2:
            st.metric("Total Stake", f"${df['Stake'].sum():.0f}")
        with c3:
            avg = df["ML Conf"].dropna().mean() if "ML Conf" in df else None
            st.metric("Avg ML Conf", f"{avg:.0%}" if avg is not None else "N/A")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Wiring files present but no sized positions.")


if __name__ == "__main__":
    main()
