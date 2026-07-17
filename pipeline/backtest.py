import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Dict, List
from src.utils.logging import get_logger

logger = get_logger(__name__)

class BacktestResult:
    def __init__(self, sport, total_picks, hits, hit_rate, avg_edge, roi):
        self.sport = sport
        self.total_picks = total_picks
        self.hits = hits
        self.hit_rate = hit_rate
        self.avg_edge = avg_edge
        self.roi = roi
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "sport": self.sport,
            "total_picks": self.total_picks,
            "hits": self.hits,
            "hit_rate": self.hit_rate,
            "avg_edge": self.avg_edge,
            "roi": self.roi,
            "timestamp": self.timestamp
        }

class HistoricalBacktest:
    def __init__(self, sport: str):
        self.sport = sport
        self.logger = get_logger(f"backtest.{sport}")

    def load_historical_picks(self, days: int = 30) -> List[Dict]:
        picks = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            file_path = f"data/picks/{self.sport}_{date}.csv"
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                picks.extend(df.to_dict("records"))
        return picks

    def calculate_accuracy(self, picks: List[Dict]) -> Dict:
        total = len(picks)
        if total == 0:
            return {"error": "No picks found"}
        hits = sum(1 for p in picks if p.get("hit", False))
        hit_rate = hits / total
        avg_edge = sum(p.get("edge", 0) for p in picks) / total
        roi = 0.0
        return {
            "total_picks": total,
            "hits": hits,
            "hit_rate": hit_rate,
            "avg_edge": avg_edge,
            "roi": roi
        }

    def run_backtest(self, days: int = 30) -> Dict:
        self.logger.info(f"Running backtest for {self.sport} ({days} days)")
        picks = self.load_historical_picks(days)
        results = self.calculate_accuracy(picks)
        results["sport"] = self.sport
        results["days"] = days
        return results

def run_backtest(sport: str, days: int = 30) -> Dict:
    return HistoricalBacktest(sport).run_backtest(days)
