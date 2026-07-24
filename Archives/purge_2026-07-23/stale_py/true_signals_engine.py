"""
TRUE SIGNALS ENGINE
Per game | Per market | Confidence-weighted
"""

from typing import Dict, List


class TrueSignalsEngine:
    """Calculate true signal probabilities vs market implied probabilities."""

    def __init__(self, sport: str = 'NBA'):
        self.sport = sport
        self.edge_threshold = 0.05

    def calculate_signals(self, game_data: Dict) -> Dict:
        signals = {}
        signals['home_win_prob'] = self._project_home_win(game_data)
        signals['away_win_prob'] = 1 - signals['home_win_prob']
        signals['over_prob'] = self._project_total(game_data, side='over')
        signals['under_prob'] = 1 - signals['over_prob']
        signals['cover_prob'] = self._project_cover(game_data)
        signals['confidence'] = self._calculate_confidence(game_data)
        return signals

    def _project_home_win(self, g: Dict) -> float:
        base = 0.5
        base += g.get('home_advantage', 0.03)
        base += g.get('rest_advantage', 0.0) * 0.02
        base += g.get('star_impact', 0.0) * 0.05
        base += g.get('h2h_edge', 0.0) * 0.03
        return max(0.05, min(0.95, base))

    def _project_total(self, g: Dict, side: str) -> float:
        base = 0.5
        line = g.get('total_line', 0)
        proj = g.get('projected_total', line)
        diff = (proj - line) / max(line, 1)
        if side == 'over':
            return max(0.3, min(0.7, 0.5 + diff * 1.5))
        return max(0.3, min(0.7, 0.5 - diff * 1.5))

    def _project_cover(self, g: Dict) -> float:
        return 0.52

    def _calculate_confidence(self, g: Dict) -> float:
        return min(0.95, 0.5 + g.get('data_completeness', 0.5) * 0.3)

    def find_value(self, signals: Dict, market_lines: Dict) -> List[Dict]:
        values = []
        ml = market_lines.get('moneyline', {})
        home_odds = ml.get('home', 0)
        if home_odds != 0:
            implied = 1 / (1 + home_odds/100) if home_odds > 0 else 1 / (1 + 100/abs(home_odds))
            edge = signals['home_win_prob'] - implied
            if edge >= self.edge_threshold:
                values.append({'market': 'moneyline', 'side': 'home', 'edge': edge, 'odds': home_odds})

        tot = market_lines.get('total', {})
        over_odds = tot.get('over', -110)
        implied = 0.524
        edge = signals['over_prob'] - implied
        if edge >= self.edge_threshold:
            values.append({'market': 'total', 'side': 'over', 'edge': edge, 'odds': over_odds})

        return values
