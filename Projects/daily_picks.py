"""Daily picks generator — run via cron for automated measurement."""

import sys
import os
import argparse
from datetime import datetime
import json
import csv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.domain.entities import REGISTRY
from src.adapters.odds_api_adapter import OddsAPIAdapter
from src.adapters.cache_adapter import CacheAdapter
from src.adapters.fantasy_combo_generator import FantasyComboGenerator


def generate_picks(sport: str, output_dir: str = "data/picks"):
    os.makedirs(output_dir, exist_ok=True)
    config = REGISTRY.get(sport)
    if not config or not config.enabled:
        print(f"Skipping {sport}: disabled")
        return
    print(f"Generating picks for {sport}...")
    if config.source.value == "tc_engine":
        try:
            module = __import__(f"sources.{config.module}", fromlist=["project_game"])
            data = module.project_game()
        except Exception as e:
            print(f"TC engine failed: {e}")
            return
    else:
        data = config.fetcher() if config.fetcher else {"players": []}
    players = data.get("players", [])
    if not players:
        print(f"No players found for {sport}")
        return
    picks = []
    for p in players:
        pick = {
            "sport": sport,
            "player": p.get("name", "Unknown"),
            "team": p.get("team", ""),
            "projection": p.get("projection", p.get("pts", 0)),
            "edge": p.get("edge", 0),
            "timestamp": datetime.now().isoformat()
        }
        picks.append(pick)
    date_str = datetime.now().strftime("%Y-%m-%d")
    csv_file = os.path.join(output_dir, f"{sport}_{date_str}.csv")
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=picks[0].keys())
        writer.writeheader()
        writer.writerows(picks)
    print(f"Saved {len(picks)} picks to {csv_file}")
    json_file = os.path.join(output_dir, f"{sport}_{date_str}.json")
    with open(json_file, "w") as f:
        json.dump(picks, f, indent=2)
    print(f"Saved {len(picks)} picks to {json_file}")
    return picks


def generate_combo_picks(sport: str, output_dir: str = "data/combos"):
    os.makedirs(output_dir, exist_ok=True)
    config = REGISTRY.get(sport)
    if not config:
        return
    generator = FantasyComboGenerator()
    data = config.fetcher() if config.fetcher else {"players": []}
    combos = generator.generate_combos(sport, data.get("players", []))
    date_str = datetime.now().strftime("%Y-%m-%d")
    csv_file = os.path.join(output_dir, f"{sport}_combos_{date_str}.csv")
    if combos:
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["combo", "legs", "total_edge", "timestamp"])
            for combo in combos:
                writer.writerow([combo.get("name", ""), combo.get("legs", 0), combo.get("total_edge", 0), datetime.now().isoformat()])
        print(f"Saved {len(combos)} combos to {csv_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate daily picks for TC Sports App")
    parser.add_argument("--sport", choices=["mlb", "wnba", "wc", "all"], default="all")
    parser.add_argument("--output", default="data/picks", help="Output directory")
    parser.add_argument("--combos", action="store_true", help="Generate combos too")
    args = parser.parse_args()
    sports = ["mlb", "wnba", "wc"] if args.sport == "all" else [args.sport]
    for sport in sports:
        generate_picks(sport, args.output)
        if args.combos:
            generate_combo_picks(sport, args.output.replace("picks", "combos"))


if __name__ == "__main__":
    main()
