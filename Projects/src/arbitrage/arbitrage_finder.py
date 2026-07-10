"""Arbitrage detection across bookmakers.

For a given stat/line, compares implied probabilities from each book and flags
combinations that guarantee a profit regardless of outcome.
"""

import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArbitrageFinder:
    """Find guaranteed-profit opportunities between bookmakers."""

    def __init__(self, min_profit_pct: float = 2.0):
        self.min_profit_pct = min_profit_pct

    @staticmethod
    def implied_prob(odds: float) -> float:
        if odds <= 1.0:
            return 0.0
        return 1.0 / odds

    def find_for_stat(self, stat: str, line: float, book_lines: Dict[str, Dict]) -> List[Dict]:
        """book_lines: {book: {'over': 1.91, 'under': 1.91}}"""
        arbs = []
        for b1, l1 in book_lines.items():
            for b2, l2 in book_lines.items():
                if b1 >= b2:
                    continue
                over_a = self.implied_prob(l1.get("over", 0))
                under_b = self.implied_prob(l2.get("under", 0))
                total = over_a + under_b
                if total < 1.0 and (1.0 - total) * 100 >= self.min_profit_pct:
                    arbs.append(
                        {
                            "stat": stat,
                            "line": line,
                            "book_a": b1,
                            "side_a": "over",
                            "odds_a": l1.get("over"),
                            "book_b": b2,
                            "side_b": "under",
                            "odds_b": l2.get("under"),
                            "profit_pct": (1.0 - total) * 100,
                        }
                    )
        return arbs

    def find_all(self, lines_by_stat: Dict[str, Dict[str, Dict]]) -> List[Dict]:
        """lines_by_stat: {stat: {book: {'over': x, 'under': y}}}"""
        out: List[Dict] = []
        for stat, books in lines_by_stat.items():
            line = next(iter(books.values())).get("line", 0.0) if books else 0.0
            out.extend(self.find_for_stat(stat, line, books))
        return out
