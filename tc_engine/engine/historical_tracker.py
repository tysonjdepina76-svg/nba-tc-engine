"""Historical Tracker — H2H, recent form, rest days, and trends.

Provides context dict for PredictiveEngine with rolling averages,
head-to-head stats, and rest-day information.
"""
from pathlib import Path
from typing import Dict, Optional
import json


class HistoricalTracker:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("data/tc_pipeline.db")
        self._history: Dict = {}

    def get_context(self, player: str, sport: str) -> Dict:
        player_data = self._history.get(player, {}).get(sport, {})
        
        stats = player_data if player_data else {}
        values = []
        for v in stats.values():
            if isinstance(v, (int, float)):
                values.append(float(v))
            elif isinstance(v, list):
                values.extend([float(x) for x in v if isinstance(x, (int, float))])
        
        last_5_avg = sum(values[-5:]) / min(len(values[-5:]), 5) if values else 0
        last_10_avg = sum(values[-10:]) / min(len(values[-10:]), 10) if values else 0
        h2h_avg = sum(values) / len(values) if values else 0

        return {
            "last_5_avg": round(last_5_avg, 2),
            "last_10_avg": round(last_10_avg, 2),
            "h2h_avg": round(h2h_avg, 2),
            "rest_days": player_data.get("rest_days", 1),
            "games_played": len(values),
            "trend": "up" if len(values) >= 3 and values[-3:] == sorted(values[-3:]) else "flat",
        }

    def update(self, player: str, sport: str, stats: Dict) -> None:
        if player not in self._history:
            self._history[player] = {}
        if sport not in self._history[player]:
            self._history[player][sport] = {}
        self._history[player][sport].update(stats)

    def save(self) -> None:
        path = Path("data/historical_tracker.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._history, indent=2, default=str))

    def load(self) -> None:
        path = Path("data/historical_tracker.json")
        if path.exists():
            self._history = json.loads(path.read_text())
