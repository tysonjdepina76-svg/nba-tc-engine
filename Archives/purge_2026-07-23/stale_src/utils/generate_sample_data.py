#!/usr/bin/env python3
"""Generate sample data for all sports — used in dev/backtest when live scrapers fail."""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta

DAILY = Path("/home/workspace/Daily_Log")
SPORTS = {
    "WNBA": {"stats": ["PTS", "REB", "AST", "3PM", "STL", "BLK"], "teams": ["NYL", "LAS", "CON", "MIN", "IND", "CHI", "SEA", "PHO"]},
    "MLB": {"stats": ["hits", "runs", "total_bases", "rbi", "hr", "sb"], "teams": ["NYY", "BOS", "LAD", "HOU", "ATL", "PHI", "TOR", "STL"]},
    "NFL": {"stats": ["pass_yds", "rush_yds", "rec_yds", "receptions", "pass_td", "rush_td"], "teams": ["KC", "BUF", "SF", "DAL", "PHI", "CIN"]},
    "NBA": {"stats": ["PTS", "REB", "AST", "3PM", "STL", "BLK"], "teams": ["BOS", "LAL", "MIL", "DEN", "PHX", "GSW"]},
    "NHL": {"stats": ["goals", "assists", "shots", "saves"], "teams": ["BOS", "EDM", "TOR", "NYR", "FLA", "DAL"]},
    "WORLD_CUP": {"stats": ["goals", "shots", "assists", "saves"], "teams": ["BRA", "ARG", "FRA", "ENG", "GER", "ESP"]},
}


def gen_player_stats(sport, n_players=50):
    cfg = SPORTS[sport]
    players = []
    for i in range(n_players):
        player = {
            "id": f"{sport}_{i}",
            "name": f"Player {i+1}",
            "team": random.choice(cfg["teams"]),
            "stats": {s: round(random.gauss(15, 5), 1) for s in cfg["stats"]}
        }
        players.append(player)
    return players


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = DAILY / today / "sample"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("GENERATE SAMPLE DATA")
    print(f"  {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 60)

    for sport, cfg in SPORTS.items():
        players = gen_player_stats(sport)
        out = out_dir / f"{sport}_sample.json"
        out.write_text(json.dumps({"sport": sport, "date": today, "players": players}, indent=2))
        print(f"  {sport}: {len(players)} players -> {out.name}")

    print("=" * 60)
    print(f"Sample data written to {out_dir}")


if __name__ == "__main__":
    main()
