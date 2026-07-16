"""
VALUE BET DETECTOR
Edge = model probability - implied probability
"""

from typing import Dict, List


class ValueBetDetector:
    def __init__(self, min_edge: float = 0.05, min_confidence: float = 0.55):
        self.min_edge = min_edge
        self.min_confidence = min_confidence

    @staticmethod
    def implied_prob(american_odds: int) -> float:
        if american_odds > 0:
            return 100 / (american_odds + 100)
        return abs(american_odds) / (abs(american_odds) + 100)

    def detect(self, signals: Dict, market: Dict) -> List[Dict]:
        bets = []
        confidence = signals.get('confidence', 0.5)
        if confidence < self.min_confidence:
            return bets

        ml = market.get('moneyline', {})
        for side in ['home', 'away']:
            odds = ml.get(side, 0)
            if odds == 0:
                continue
            imp = self.implied_prob(odds)
            proj = signals.get(f'{side}_win_prob', 0.5)
            edge = proj - imp
            if edge >= self.min_edge:
                bets.append({
                    'type': 'moneyline', 'side': side,
                    'edge': round(edge, 4), 'odds': odds,
                    'strength': 'high' if edge > 0.10 else 'medium'
                })

        tot = market.get('total', {})
        for side in ['over', 'under']:
            odds = tot.get(side, -110)
            imp = self.implied_prob(odds)
            proj = signals.get(f'{side}_prob', 0.5)
            edge = proj - imp
            if edge >= self.min_edge:
                bets.append({
                    'type': 'total', 'side': side,
                    'edge': round(edge, 4), 'odds': odds,
                    'strength': 'high' if edge > 0.10 else 'medium'
                })

        spread = market.get('spread', {})
        proj = signals.get('cover_prob', 0.5)
        imp = 0.524
        edge = proj - imp
        if edge >= self.min_edge:
            bets.append({
                'type': 'spread', 'side': 'home',
                'edge': round(edge, 4),
                'strength': 'high' if edge > 0.10 else 'medium'
            })
        return bets
