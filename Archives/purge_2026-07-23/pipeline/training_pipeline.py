#!/usr/bin/env python3
"""Build training data for hybrid ML predictor."""
import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from src.adapters.cache_adapter import CacheAdapter

PROJECTS = Path("/home/workspace/Projects")
cache = CacheAdapter()

SAMPLE_PLAYERS = {
    "wnba": ["A'ja Wilson", "Breanna Stewart", "Aliyah Boston", "Caitlin Clark"],
    "mlb": ["Shohei Ohtani", "Aaron Judge", "Juan Soto", "Ronald Acuna"],
    "wc": ["Kylian Mbappe", "Erling Haaland", "Vinicius Jr", "Jude Bellingham"],
}

def build_training_data(sport: str, days: int = 60):
    cache_key = f"training_{sport}_{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    random.seed(42)
    rows = []
    for player in SAMPLE_PLAYERS.get(sport, ["Player X"]):
        for d in range(days):
            game_date = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
            rows.append({
                "player": player,
                "date": game_date,
                "target": round(random.uniform(8, 30), 1),
                "sample_size": random.randint(10, 40),
                "sport": sport,
            })

    cache.set(cache_key, rows, ttl_seconds=3600)
    return rows

if __name__ == "__main__":
    for s in ["wnba", "mlb", "wc"]:
        data = build_training_data(s, days=30)
        print(f"{s}: {len(data)} training rows")
