"""
Chicago Sky — WNBA Roster
Live Scrape: May 22, 2026 | Source: wnba.com
"""

from dataclasses import dataclass


@dataclass
class Player:
    name: str
    pos: str
    ht: str
    ppg: float
    rpg: float
    apg: float
    tpm: float
    status: str = "ACTIVE"

# ── STARTERS (5 players) ──
STARTERS = [
    Player("Jacy Sheldon", "G", "5-10", 9.0, 2.4, 2.8, 0.9),
    Player("Elizabeth Williams", "C-F", "6-3", 4.0, 4.4, 0.8, 0.4),
    Player("Skylar Diggins", "G", "5-9", 12.8, 4.8, 5.3, 1.3),
    Player("Rickea Jackson", "F", "6-2", 18.0, 4.8, 2.0, 1.8),
    Player("DiJonai Carrington", "G-F", "5-11", 0.0, 0.0, 0.0, 0.0),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Natasha Cloud", "G", "5-10", 11.5, 5.3, 4.8, 1.2),
    Player("Kamilla Cardoso", "C", "6-7", 14.4, 10.4, 2.4, 1.4),
    Player("Gabriela Jaquez", "G", "6-0", 12.4, 5.6, 1.4, 1.2),
    Player("Sydney Taylor", "G", "5-9", 3.3, 0.3, 0.7, 0.3),
    Player("Maddy Westbeld", "F", "6-3", 0.0, 0.0, 0.0, 0.0),
    Player("Courtney Vandersloot", "G", "5-8", 0.0, 0.0, 0.0, 0.0),
    Player("Rachel Banham", "G", "5-10", 6.2, 0.2, 0.8, 0.6),
    Player("Azura Stevens", "F-C", "6-6", 0.0, 0.0, 0.0, 0.0),
    Player("Aicha Coulibaly", "G", "6-0", 4.0, 1.5, 0.8, 0.4),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players