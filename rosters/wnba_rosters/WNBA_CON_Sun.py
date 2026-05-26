"""
Connecticut Sun — WNBA Roster
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
    Player("Diamond Miller", "F", "6-1", 8.2, 2.5, 0.7, 0.8),
    Player("Hailey Van Lith", "G", "5-9", 9.3, 1.0, 2.8, 0.9),
    Player("Ashlon Jackson", "G", "6-0", 4.0, 1.0, 1.0, 0.4),
    Player("Charlisse Leger-Walker", "G", "5-10", 8.0, 1.7, 2.3, 0.8),
    Player("Gianna Kneepkens", "G", "5-11", 3.5, 2.2, 0.5, 0.4),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Aaliyah Edwards", "F", "6-3", 10.0, 3.0, 1.0, 1.0),
    Player("Olivia Nelson-Ododa", "C", "6-5", 6.7, 3.0, 2.3, 0.7),
    Player("Raegan Beers", "F", "6-4", 5.6, 3.8, 0.8, 0.6),
    Player("Saniya Rivers", "G", "6-1", 6.7, 2.3, 4.8, 0.7),
    Player("Aneesah Morrow", "F", "6-1", 12.0, 9.7, 1.2, 1.2),
    Player("Kennedy Burke", "G-F", "6-1", 7.7, 4.2, 3.3, 0.8),
    Player("Nell Angloma", "F", "6-1", 7.7, 2.7, 0.3, 0.8),
    Player("Brittney Griner", "C", "6-9", 15.0, 5.7, 2.0, 1.5),
    Player("Leila Lacan", "G", "5-11", 0.0, 0.0, 0.0, 0.0),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players