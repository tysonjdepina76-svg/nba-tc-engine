"""Arbitrage Finder — Scans lines across bookmakers for arbitrage opportunities.

Detects positive-expected-value arbitrage by comparing OVER/UNDER lines
across multiple sportsbooks.
"""
from typing import List, Dict


class ArbitrageFinder:
    def __init__(self):
        self.min_arb_pct = 0.5

    @staticmethod
    def _american_to_prob(american: float) -> float:
        if american > 0:
            return 100.0 / (american + 100.0)
        return abs(american) / (abs(american) + 100.0)

    def scan(self, lines: List[Dict]) -> List[Dict]:
        if not lines:
            return []

        results = []
        for i, line_a in enumerate(lines):
            for j, line_b in enumerate(lines):
                if i >= j:
                    continue
                if (line_a.get("player") != line_b.get("player") or
                        line_a.get("stat") != line_b.get("stat")):
                    continue

                over_a = float(line_a.get("over", 0))
                under_b = float(line_b.get("under", 0))
                over_b = float(line_b.get("over", 0))
                under_a = float(line_a.get("under", 0))

                for over_odds, under_odds, book_over, book_under in [
                    (over_a, under_b, line_a["bookmaker"], line_b["bookmaker"]),
                    (over_b, under_a, line_b["bookmaker"], line_a["bookmaker"]),
                ]:
                    if over_odds == 0 or under_odds == 0:
                        continue
                    prob_over = self._american_to_prob(over_odds)
                    prob_under = self._american_to_prob(under_odds)
                    total_prob = prob_over + prob_under

                    if total_prob < 1.0:
                        arb_pct = (1.0 - total_prob) * 100
                        if arb_pct >= self.min_arb_pct:
                            results.append({
                                "player": line_a["player"],
                                "stat": line_a["stat"],
                                "arb_pct": round(arb_pct, 2),
                                "over_odds": over_odds,
                                "over_book": book_over,
                                "under_odds": under_odds,
                                "under_book": book_under,
                            })

        return sorted(results, key=lambda r: r["arb_pct"], reverse=True)
