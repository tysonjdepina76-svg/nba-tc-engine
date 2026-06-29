# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""DailyPicks orchestrator — the use case runner.

One command runs the full day:
  python -m src.domain.daily_picks --sport NBA --date 2026-06-29 [--dry-run]

Steps:
  1. Fetch slate via ESPN adapter
  2. Fetch season stats
  3. Project each matchup (pure math in engine)
  4. Validate outputs (data_validator)
  5. Save reports/daily/<sport>_<date>.json

All network calls go through circuit breakers. Dry-run skips writes
and lets you see what WOULD happen.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Project-relative imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.adapters.espn import ESPNAdapter
from src.domain.engine import project_game
from src.domain.sport_config import get_config, stat_keys
from src.domain.entities import Projection  # noqa: F401  (export shape)


REPORTS_DIR = PROJECT_ROOT / "reports" / "daily"


class DailyPicks:
    """One day's worth of TC projections for one sport."""

    def __init__(self, sport: str, date: str, dry_run: bool = False, output_dir=None):
        self.sport = sport.upper()
        supported = {"NFL", "NBA", "WNBA", "MLB", "SOCCER"}
        if self.sport not in supported:
            raise ValueError(f"Unsupported sport: {self.sport}. Supported: {supported}")
        self.date = date
        self.dry_run = dry_run
        self.config = get_config(self.sport)
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR
        self.report_path = self.output_dir / f"{self.sport.lower()}_{self.date}.json"
        self.report: dict = {
            "sport": self.sport,
            "date": self.date,
            "generated_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "matchups": [],
            "summary": {},
        }

    def run(self, adapter: object = None) -> List[dict]:
        """Execute the daily pipeline. Returns list of matchup result dicts."""
        print(f"\n=== DailyPicks :: {self.sport} :: {self.date} {'(DRY RUN)' if self.dry_run else ''} ===\n")

        # Step 1: fetch slate
        adapter = adapter if adapter is not None else ESPNAdapter(sport=self.sport)
        print(f"[1/4] Fetching slate for {self.sport}...")
        games = adapter.fetch_today_slate()
        if not games:
            print("  ⚠  No games on today's slate (or ESPN blocked)")
        else:
            print(f"  ✅ {len(games)} game(s) found")

        # Step 2: fetch season stats
        print(f"[2/4] Fetching season stats...")
        all_players = adapter.fetch_season_stats(limit=150)
        if not all_players:
            print("  ⚠  No player stats (or ESPN blocked)")
        else:
            print(f"  ✅ {len(all_players)} players loaded")

        # Step 3: project each game
        print(f"[3/4] Projecting matchups...")
        matchup_results: List[dict] = []
        keys = stat_keys(self.sport)

        for game in games:
            home_roster, away_roster = adapter.players_for_matchup(
                all_players, home=game.home_team, away=game.away_team
            )
            players = home_roster + away_roster
            if not players:
                print(f"  ⚠  {game.home_team}@{game.away_team}: no roster data, skipping")
                continue

            result = project_game(game, players, keys)
            valid = [p for p in result["valid_props"]]
            print(
                f"  ✅ {result['matchup']}: "
                f"signal={result['signal']} | "
                f"valid={len(valid)} | "
                f"roster={result['roster_counts']['total']}"
            )
            matchup_results.append(result)

        # Step 4: validate + save
        print(f"[4/4] Validating + saving...")
        from src.data_validator import gate_picks
        all_props: List[dict] = []
        for r in matchup_results:
            all_props.extend(r["valid_props"])

        validation = gate_picks(all_props)
        invalid_count = validation["invalid_count"]
        if invalid_count > 0:
            print(f"  ⚠  Validator rejected {invalid_count} props")
        else:
            print(f"  ✅ All {validation['valid_count']} props passed validation")

        self.report["matchups"] = matchup_results
        self.report["summary"] = {
            "matchup_count": len(matchup_results),
            "total_valid_props": validation["valid_count"],
            "rejected_by_validator": invalid_count,
        }

        if not self.dry_run:
            self.save()
        else:
            print("\n[DRY RUN] would have written to:")
            print(f"  {self.report_path}")

        return matchup_results

    def save(self, projections=None, format="json") -> Path:
        if projections is not None:
            self.report["projections"] = [p.to_dict() if hasattr(p, "to_dict") else p.__dict__ for p in projections]
            self.report["projection_count"] = len(projections)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.report_path, "w") as f:
            json.dump(self.report, f, indent=2, default=str)
        print(f"  ✅ Saved: {self.report_path}")
        return self.report_path


def main():
    parser = argparse.ArgumentParser(description="Daily TC Picks — one sport, one date")
    parser.add_argument("--sport", required=True, help="WNBA, NBA, NFL, MLB, SOCCER")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="YYYY-MM-DD (default: today)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen, don't write files")
    args = parser.parse_args()

    runner = DailyPicks(sport=args.sport, date=args.date, dry_run=args.dry_run)
    results = runner.run()

    if not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
