"""
Minnesota Lynx — WNBA Roster
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
    Player("Natasha Howard", "F", "6-2", 15.2, 7.2, 3.6, 1.5),
    Player("Liatu King", "F", "5-11", 9.0, 7.0, 0.0, 0.9),
    Player("Maya Caldwell", "G", "5-11", 5.4, 1.8, 1.6, 0.5),
    Player("Olivia Miles", "G", "5-10", 15.2, 4.2, 5.6, 1.5),
    Player("Anastasiia Olairi Kosu", "F", "6-1", 3.0, 1.4, 0.6, 0.3),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Antonia Delaere", "G", "5-11", 2.6, 0.4, 1.6, 0.3),
    Player("Courtney Williams", "G", "5-8", 15.6, 5.4, 4.0, 1.6),
    Player("Eliska Hamzova", "G", "6-0", 2.0, 2.3, 0.7, 0.2),
    Player("Nia Coffey", "F", "6-1", 7.8, 5.4, 1.2, 0.8),
    Player("Dorka Juhasz", "F", "6-5", 0.0, 0.0, 0.0, 0.0),
    Player("Kayla McBride", "G", "5-11", 15.6, 4.6, 1.8, 1.6),
    Player("Emma Cechova", "C", "6-4", 8.3, 3.7, 0.0, 0.8),
    Player("Napheesa Collier", "F", "6-1", 0.0, 0.0, 0.0, 0.0),
    Player("Emese Hof", "C", "6-3", 2.5, 1.5, 1.0, 0.2),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players