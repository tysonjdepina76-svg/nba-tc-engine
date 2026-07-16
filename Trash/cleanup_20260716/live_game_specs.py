"""
LIVE GAME SPECIFICATIONS
Period | Time | Status | Score tracking
"""

from typing import Dict
from datetime import datetime


class LiveGameSpecs:
    SPORT_PERIODS = {
        'NBA': {'periods': ['Q1', 'Q2', 'Q3', 'Q4', 'OT'], 'period_length': 12, 'total_minutes': 48},
        'WNBA': {'periods': ['Q1', 'Q2', 'Q3', 'Q4', 'OT'], 'period_length': 10, 'total_minutes': 40},
        'NFL': {'periods': ['Q1', 'Q2', 'Q3', 'Q4', 'OT'], 'period_length': 15, 'total_minutes': 60},
        'MLB': {'periods': ['Top 1', 'Bot 1', 'Top 2', 'Bot 2'], 'period_length': None, 'total_minutes': None},
        'NHL': {'periods': ['P1', 'P2', 'P3', 'OT', 'SO'], 'period_length': 20, 'total_minutes': 60},
        'SOCCER': {'periods': ['H1', 'H2', 'ET', 'PK'], 'period_length': 45, 'total_minutes': 90},
    }

    @classmethod
    def get_spec(cls, sport: str) -> Dict:
        return cls.SPORT_PERIODS.get(sport, cls.SPORT_PERIODS['NBA'])

    @classmethod
    def format_clock(cls, sport: str, period: str, time_remaining: str) -> str:
        return f"{period} {time_remaining}"

    @classmethod
    def game_status(cls, sport: str, period_idx: int, total_periods: int) -> str:
        if period_idx < 0:
            return 'Scheduled'
        if period_idx >= total_periods:
            return 'Final'
        return 'Live'
