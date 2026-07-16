import sys
import os
import csv
import argparse
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.core_math_engine import run_full_scan
from src.adapters.line_fetcher import fetch_lines
from src.utils.logging import setup_logging
from src.explanation_engine import generate_explanation
from telegram_bot import process_pending_picks

logger = setup_logging("daily_picks")

ET = timezone(timedelta(hours=-4))

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "picks")


def generate_picks(sport: str, output_dir: str = None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Generating picks for {sport}...")
    data = fetch_lines(sport)
    players = data.get("players", [])

    if data.get("quota_exhausted"):
        logger.warning(f"Odds API quota exhausted for {sport} — using self-edge only")
    if not players:
        logger.warning(f"No lines fetched for {sport}, skipping.")
        return []

    csv_rows = []
    for p in players:
        scan = run_full_scan(sport, "MOCK_GAME_ID", p["name"], "PTS", p, [])
        edge_val = round(scan["edge"] * 100, 1)
        reason = generate_explanation(
            player=p["name"],
            sport=sport,
            stat=p.get("stat", "PTS"),
            projection=float(p.get("projection", 0)),
            line=float(p.get("line", 0)),
            edge=edge_val
        )
        csv_rows.append({
            "player": p["name"],
            "team": p.get("team", ""),
            "projection": p.get("projection", 0),
            "edge": edge_val,
            "reason": reason,
        })

    date_str = datetime.now(ET).strftime("%Y-%m-%d")
    csv_file = os.path.join(output_dir, f"{sport}_{date_str}.csv")
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["player", "team", "projection", "edge", "reason"])
        writer.writeheader()
        writer.writerows(csv_rows)
    logger.info(f"Saved {len(csv_rows)} picks to {csv_file}")

    process_pending_picks()
    return csv_rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", choices=["mlb", "wnba", "wc", "all"], default="all")
    args = parser.parse_args()
    sports = ["mlb", "wnba", "wc"] if args.sport == "all" else [args.sport]
    for s in sports:
        generate_picks(s)
