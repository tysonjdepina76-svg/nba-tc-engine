"""bet_tracker.py — Log placed bets + compute P&L."""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

TRACKER = Path("/home/workspace/data/bets_log.csv")
TRACKER.parent.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "date", "sport", "league", "matchup", "player", "stat",
    "direction", "line", "odds", "stake", "result", "profit", "graded_at",
]


def _ensure_header():
    if not TRACKER.exists():
        with TRACKER.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()


def log_bet(bet: Dict) -> None:
    _ensure_header()
    bet.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
    with TRACKER.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writerow(bet)


def grade_bet(bet_id: int, result: str, profit: float) -> None:
    if not TRACKER.exists():
        return
    rows = list(csv.DictReader(TRACKER.open()))
    if bet_id >= len(rows):
        return
    rows[bet_id]["result"] = result
    rows[bet_id]["profit"] = profit
    rows[bet_id]["graded_at"] = datetime.now().isoformat()
    with TRACKER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def get_pnl(days: int = 30) -> Dict:
    if not TRACKER.exists():
        return {"wins": 0, "losses": 0, "profit": 0.0, "roi": 0.0}
    rows = list(csv.DictReader(TRACKER.open()))
    wins = sum(1 for r in rows if r.get("result") == "WIN")
    losses = sum(1 for r in rows if r.get("result") == "LOSS")
    profit = sum(float(r.get("profit") or 0) for r in rows)
    stake = sum(float(r.get("stake") or 0) for r in rows)
    return {
        "wins": wins,
        "losses": losses,
        "profit": round(profit, 2),
        "stake": round(stake, 2),
        "roi": round((profit / stake * 100) if stake else 0, 2),
    }


if __name__ == "__main__":
    print(json.dumps(get_pnl(), indent=2))
