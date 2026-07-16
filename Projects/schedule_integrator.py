"""
SCHEDULE INTEGRATOR
WNBA 2026 schedule with game times, broadcast, and rivalry tagging.
"""

from datetime import datetime
from typing import Dict, List


RIVALRIES = [
    {'teams': ('LV', 'NY'), 'date': '2026-05-17', 'time_et': '1:00 PM', 'note': '2024 Finals rematch; Wilson vs Stewart'},
    {'teams': ('CHI', 'IND'), 'date': '2026-05-17', 'time_et': '3:00 PM', 'note': 'Clark vs Reese rivalry renewed'},
    {'teams': ('IND', 'LV'), 'date': '2026-07-12', 'time_et': '9:00 PM', 'note': 'Clark vs Wilson; Primetime matchup'},
    {'teams': ('NY', 'MIN'), 'date': '2026-07-30', 'time_et': '8:00 PM', 'note': '2024 Finals rematch'},
]


WNBA_SCHEDULE = [
    {'date': '2026-05-08', 'time_et': '7:30 PM', 'away': 'CON', 'home': 'NYL',  'tv': 'League Pass'},
    {'date': '2026-05-08', 'time_et': '7:30 PM', 'away': 'WAS', 'home': 'TOR',  'tv': 'League Pass'},
    {'date': '2026-05-08', 'time_et': '10:00 PM','away': 'GSV', 'home': 'SEA',  'tv': 'ION'},
    {'date': '2026-05-09', 'time_et': '1:00 PM', 'away': 'DAL', 'home': 'IND',  'tv': 'ABC'},
    {'date': '2026-05-09', 'time_et': '3:30 PM', 'away': 'PHX', 'home': 'LV',   'tv': 'ABC'},
    {'date': '2026-05-09', 'time_et': '9:00 PM', 'away': 'CHI', 'home': 'POR',  'tv': 'League Pass'},
    {'date': '2026-05-10', 'time_et': '1:00 PM', 'away': 'SEA', 'home': 'CON',  'tv': 'League Pass'},
    {'date': '2026-05-10', 'time_et': '3:00 PM', 'away': 'NYL', 'home': 'WAS',  'tv': 'League Pass'},
    {'date': '2026-05-10', 'time_et': '6:00 PM', 'away': 'LV',  'home': 'LA',   'tv': 'League Pass'},
    {'date': '2026-05-10', 'time_et': '7:00 PM', 'away': 'ATL', 'home': 'MIN',  'tv': 'League Pass'},
    {'date': '2026-05-10', 'time_et': '8:30 PM', 'away': 'PHX', 'home': 'GSV',  'tv': 'League Pass'},
]


class ScheduleIntegrator:
    def __init__(self):
        self.schedule = WNBA_SCHEDULE
        self.rivalries = RIVALRIES

    def get_today_games(self, date: str = None) -> List[Dict]:
        date = date or datetime.now().strftime('%Y-%m-%d')
        return [g for g in self.schedule if g['date'] == date]

    def get_rivalry_games(self) -> List[Dict]:
        return self.rivalries

    def tag_rivalries(self, games: List[Dict]) -> List[Dict]:
        tagged = []
        rivalry_keys = {tuple(sorted(r['teams'])): r for r in self.rivalries}
        for g in games:
            key = tuple(sorted([g['away'], g['home']]))
            if key in rivalry_keys:
                g = {**g, 'is_rivalry': True, 'rivalry_note': rivalry_keys[key]['note']}
            else:
                g = {**g, 'is_rivalry': False}
            tagged.append(g)
        return tagged
