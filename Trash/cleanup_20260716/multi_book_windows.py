"""
MULTI-BOOK WINDOWS - All Sports Live Viewing
DraftKings | FanDuel | BetMGM | Caesars | PointsBet
"""

from typing import Dict, List
from datetime import datetime


class MultiBookWindows:
    """Multi-book window management for all sports"""

    def __init__(self):
        self.books = ['DraftKings', 'FanDuel', 'BetMGM', 'Caesars', 'PointsBet']
        self.sports = ['NBA', 'NFL', 'MLB', 'NHL', 'WNBA', 'CBB', 'SOCCER']
        self.windows = {}

    def create_windows(self, sport: str, game_data: Dict) -> Dict:
        """Create book-specific windows for a game"""
        windows = {}
        for book in self.books:
            windows[book] = {
                'book': book,
                'lines': self._get_book_lines(book, game_data),
                'signals': self._get_book_signals(book, game_data),
                'value': self._calculate_book_value(book, game_data),
                'timestamp': datetime.now().isoformat()
            }
        return windows

    def _get_book_lines(self, book: str, game_data: Dict) -> Dict:
        return {
            'moneyline': game_data.get('books', {}).get(book, {}).get('moneyline', {}),
            'spread': game_data.get('books', {}).get(book, {}).get('spread', {}),
            'total': game_data.get('books', {}).get(book, {}).get('total', {}),
            'player_props': game_data.get('books', {}).get(book, {}).get('player_props', {})
        }

    def _get_book_signals(self, book: str, game_data: Dict) -> Dict:
        return {
            'home_win_prob': game_data.get('signals', {}).get('home_win_prob', 0.5),
            'away_win_prob': game_data.get('signals', {}).get('away_win_prob', 0.5),
            'over_prob': game_data.get('signals', {}).get('over_prob', 0.5),
            'under_prob': game_data.get('signals', {}).get('under_prob', 0.5),
            'confidence': game_data.get('signals', {}).get('confidence', 0.0)
        }

    def _calculate_book_value(self, book: str, game_data: Dict) -> Dict:
        value_bets = []
        signals = game_data.get('signals', {})
        book_lines = self._get_book_lines(book, game_data)

        ml = book_lines.get('moneyline', {})
        home_odds = ml.get('home', 0)
        if home_odds != 0:
            implied = 1 / (1 + home_odds/100) if home_odds > 0 else 1 / (1 + 100/abs(home_odds))
            edge = signals.get('home_win_prob', 0.5) - implied
            if edge > 0.05:
                value_bets.append({'type': 'moneyline', 'side': 'home', 'edge': edge, 'odds': home_odds})

        total = book_lines.get('total', {})
        over_odds = total.get('over', 0)
        if over_odds != 0:
            implied = 1 / (1 + over_odds/100) if over_odds > 0 else 1 / (1 + 100/abs(over_odds))
            edge = signals.get('over_prob', 0.5) - implied
            if edge > 0.05:
                value_bets.append({'type': 'total', 'side': 'over', 'edge': edge, 'odds': over_odds})

        return {
            'value_bets': value_bets,
            'count': len(value_bets),
            'best_edge': max([b['edge'] for b in value_bets]) if value_bets else 0
        }
