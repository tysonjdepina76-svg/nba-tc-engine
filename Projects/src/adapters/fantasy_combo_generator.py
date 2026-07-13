"""Fantasy combo generator for multi-leg parlays."""

from typing import List, Dict, Any
from itertools import combinations
from datetime import datetime


class FantasyComboGenerator:
    """Generate fantasy combos (parlays) for player props."""

    def __init__(self, min_legs: int = 2, max_legs: int = 4, min_edge: float = 0.5):
        self.min_legs = min_legs
        self.max_legs = max_legs
        self.min_edge = min_edge

    def generate_combos(self, sport: str, players: List[Dict[str, Any]],
                        max_combos: int = 100) -> List[Dict[str, Any]]:
        combos = []
        eligible = [p for p in players if p.get("edge", 0) >= self.min_edge]
        if len(eligible) < self.min_legs:
            return []
        for n in range(self.min_legs, min(self.max_legs + 1, len(eligible) + 1)):
            for combo_players in combinations(eligible, n):
                total_edge = sum(p.get("edge", 0) for p in combo_players)
                combo = {
                    "name": " + ".join(p.get("name", "Unknown")[:15] for p in combo_players),
                    "legs": n,
                    "players": [p.get("name") for p in combo_players],
                    "total_edge": round(total_edge, 2),
                    "avg_edge": round(total_edge / n, 2),
                    "sport": sport,
                    "timestamp": datetime.now().isoformat()
                }
                combos.append(combo)
                if len(combos) >= max_combos:
                    break
            if len(combos) >= max_combos:
                break
        combos.sort(key=lambda x: x["total_edge"], reverse=True)
        return combos[:max_combos]

    def generate_optimal_combos(self, sport: str, players: List[Dict[str, Any]],
                                target_legs: int = 3, top_n: int = 10) -> List[Dict[str, Any]]:
        eligible = [p for p in players if p.get("edge", 0) >= self.min_edge]
        if len(eligible) < target_legs:
            return []
        eligible.sort(key=lambda x: x.get("edge", 0), reverse=True)
        top_players = eligible[:top_n]
        combos = []
        for combo_players in combinations(top_players, target_legs):
            total_edge = sum(p.get("edge", 0) for p in combo_players)
            combo = {
                "name": " + ".join(p.get("name", "Unknown")[:15] for p in combo_players),
                "legs": target_legs,
                "players": [p.get("name") for p in combo_players],
                "total_edge": round(total_edge, 2),
                "avg_edge": round(total_edge / target_legs, 2),
                "sport": sport
            }
            combos.append(combo)
        combos.sort(key=lambda x: x["total_edge"], reverse=True)
        return combos[:20]
