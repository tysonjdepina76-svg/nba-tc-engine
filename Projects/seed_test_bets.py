#!/usr/bin/env python3
"""Seed test bets into betting_history.db for demo / report.py visibility."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.tracking.historical_tracker import HistoricalTracker

DEMO_BETS = [
    {"sport": "MLB", "game": "PHI@DET", "player": "Jack Flaherty", "stat": "strikeouts", "line": 11.1, "projection": 0.3, "edge": -10.8, "bet_type": "UNDER", "stake": 110.0, "odds": 1.91, "model_confidence": 0.88, "true_edge": -10.8},
    {"sport": "MLB", "game": "MIL@PIT", "player": "Aaron Nola", "stat": "strikeouts", "line": 11.1, "projection": 1.9, "edge": -9.2, "bet_type": "UNDER", "stake": 92.0, "odds": 1.91, "model_confidence": 0.85, "true_edge": -9.2},
    {"sport": "WNBA", "game": "IND@LA", "player": "Caitlin Clark", "stat": "points", "line": 15.0, "projection": 17.2, "edge": 2.2, "bet_type": "OVER", "stake": 75.0, "odds": 1.91, "model_confidence": 0.78, "true_edge": 2.2},
    {"sport": "WORLD_CUP", "game": "ENG@NOR", "player": "Team Total", "stat": "goals", "line": 1.5, "projection": 1.95, "edge": 0.45, "bet_type": "OVER", "stake": 50.0, "odds": 1.95, "model_confidence": 0.65, "true_edge": 0.45},
]


def main() -> int:
    ht = HistoricalTracker()
    ids = []
    for b in DEMO_BETS:
        bid = ht.record_bet(b)
        ids.append(bid)
        print(f"  + bet {bid}: {b['player']} {b['stat']} {b['bet_type']} {b['line']}")
    print(f"\nSeeded {len(ids)} test bets. Run settle_positions.py to grade them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
