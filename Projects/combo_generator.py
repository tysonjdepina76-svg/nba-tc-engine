"""
COMBO GENERATOR
Player + Team | ML + Total | Prop + ML | Spread + Total
"""

from typing import Dict, List


class ComboGenerator:
    """Generate combo bets from available signals and market lines."""

    COMBO_TYPES = [
        'player_plus_spread',
        'ml_plus_total',
        'prop_plus_ml',
        'prop_plus_spread',
        'spread_plus_total',
    ]

    def __init__(self, min_combined_edge: float = 0.03):
        self.min_combined_edge = min_combined_edge

    def generate(self, game: Dict, value_bets: List[Dict], props: List[Dict] = None) -> List[Dict]:
        combos = []
        ml_bets = [b for b in value_bets if b['type'] == 'moneyline']
        spread_bets = [b for b in value_bets if b['type'] == 'spread']
        total_bets = [b for b in value_bets if b['type'] == 'total']
        props = props or []

        if ml_bets and total_bets:
            ml, tot = ml_bets[0], total_bets[0]
            edge = ml['edge'] + tot['edge']
            if edge >= self.min_combined_edge:
                combos.append({
                    'type': 'ml_plus_total',
                    'legs': [ml['side'], tot['side']],
                    'combined_edge': round(edge, 4),
                    'true_signal': round(0.5 + edge / 2, 4),
                })

        if ml_bets and props:
            ml, prop = ml_bets[0], props[0]
            edge = ml['edge'] + prop.get('edge', 0.04)
            if edge >= self.min_combined_edge:
                combos.append({
                    'type': 'prop_plus_ml',
                    'legs': [prop.get('player', 'prop'), ml['side']],
                    'combined_edge': round(edge, 4),
                    'true_signal': round(0.5 + edge / 2, 4),
                })

        if spread_bets and total_bets:
            sp, tot = spread_bets[0], total_bets[0]
            edge = sp['edge'] + tot['edge']
            if edge >= self.min_combined_edge:
                combos.append({
                    'type': 'spread_plus_total',
                    'legs': [sp['side'], tot['side']],
                    'combined_edge': round(edge, 4),
                    'true_signal': round(0.5 + edge / 2, 4),
                })

        if props and spread_bets:
            prop, sp = props[0], spread_bets[0]
            edge = prop.get('edge', 0.04) + sp['edge']
            if edge >= self.min_combined_edge:
                combos.append({
                    'type': 'prop_plus_spread',
                    'legs': [prop.get('player', 'prop'), sp['side']],
                    'combined_edge': round(edge, 4),
                    'true_signal': round(0.5 + edge / 2, 4),
                })
        return combos
