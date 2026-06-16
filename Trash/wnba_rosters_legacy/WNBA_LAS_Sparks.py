"""
Los Angeles Sparks — WNBA Roster
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
    Player("Ta'Niya Latson", "G", "5-8", 0.7, 0.3, 0.0, 0.1),
    Player("Chance Gray", "G", "5-9", 1.2, 0.8, 0.4, 0.1),
    Player("Laura Ziegler", "F", "6-2", 0.0, 0.0, 0.0, 0.0),
    Player("Dearica Hamby", "F", "6-3", 19.0, 8.8, 2.4, 1.9),
    Player("Jihyun Park", "G", "6-1", 1.3, 0.7, 1.0, 0.1),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Ariel Atkins", "G", "5-10", 7.0, 2.3, 2.3, 0.7),
    Player("Kelsey Plum", "G", "5-8", 24.6, 1.4, 5.8, 2.5),
    Player("Rae Burrell", "G-F", "6-2", 8.4, 2.6, 1.6, 0.8),
    Player("Erica Wheeler", "G", "5-7", 4.6, 1.4, 4.6, 0.5),
    Player("Sania Feagin", "F", "6-3", 0.0, 0.0, 0.0, 0.0),
    Player("Kate Martin", "G", "6-0", 3.7, 0.3, 0.0, 0.4),
    Player("Cameron Brink", "F", "6-4", 8.0, 3.6, 1.0, 0.8),
    Player("Nneka Ogwumike", "F", "6-2", 15.6, 6.6, 2.0, 1.6),
    Player("Emma Cannon", "F", "6-2", 3.0, 0.0, 0.0, 0.3),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players