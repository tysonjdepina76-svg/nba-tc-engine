"""
Bet tracking and ROI calculation.
"""

import json
import os
from datetime import datetime
from typing import Dict, List
from sources.utils.logging import get_logger

logger = get_logger(__name__)

class BetTracker:
    def __init__(self):
        self.bets_file = "/home/workspace/Projects/data/bets.json"
        self.bets = self._load_bets()

    def _load_bets(self) -> List[Dict]:
        if os.path.exists(self.bets_file):
            try:
                with open(self.bets_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_bets(self) -> None:
        os.makedirs(os.path.dirname(self.bets_file), exist_ok=True)
        try:
            with open(self.bets_file, "w") as f:
                json.dump(self.bets, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save bets: {e}")

    def add_bet(self, bet: Dict) -> Dict:
        bet["id"] = len(self.bets) + 1
        bet["placed_at"] = datetime.now().isoformat()
        bet["status"] = "pending"
        self.bets.append(bet)
        self._save_bets()
        return bet

    def resolve_bet(self, bet_id: int, result: float) -> Dict:
        for bet in self.bets:
            if bet.get("id") == bet_id:
                bet["result"] = result
                bet["resolved_at"] = datetime.now().isoformat()
                if bet.get("line") and result is not None:
                    if result > bet["line"]:
                        bet["profit"] = bet["stake"] * (bet["odds"] / 100)
                        bet["status"] = "won"
                    else:
                        bet["profit"] = -bet["stake"]
                        bet["status"] = "lost"
                    bet["roi"] = (bet["profit"] / bet["stake"]) * 100
                self._save_bets()
                return bet
        return {"error": "Bet not found"}

    def get_summary(self) -> Dict:
        won = sum(1 for b in self.bets if b.get("status") == "won")
        lost = sum(1 for b in self.bets if b.get("status") == "lost")
        pending = sum(1 for b in self.bets if b.get("status") == "pending")
        total_profit = sum(b.get("profit", 0) for b in self.bets if b.get("status") in ["won", "lost"])
        total_stake = sum(b.get("stake", 0) for b in self.bets)
        return {
            "total_bets": len(self.bets),
            "won": won,
            "lost": lost,
            "pending": pending,
            "win_rate": won / (won + lost) if (won + lost) > 0 else 0,
            "total_profit": round(total_profit, 2),
            "total_stake": round(total_stake, 2),
            "roi": round((total_profit / total_stake) * 100, 2) if total_stake > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
