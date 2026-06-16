"""
Phoenix Mercury — WNBA Roster
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
    Player("Noemie Brochant", "F-G", "5-11", 4.0, 2.2, 0.3, 0.4),
    Player("Kahleah Copper", "G-F", "6-1", 18.5, 2.5, 2.5, 1.9),
    Player("Natasha Mack", "F-C", "6-3", 10.3, 8.7, 1.7, 1.0),
    Player("Shay Ciezki", "G", "5-7", 0.0, 0.0, 0.0, 0.0),
    Player("Monique Akoa Makani", "G", "5-10", 0.0, 0.0, 0.0, 0.0),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Valeriane Ayayi", "F", "6-1", 4.3, 2.8, 1.3, 0.4),
    Player("Quionche Carter", "F", "5-11", 0.7, 0.7, 0.3, 0.1),
    Player("Kiana Williams", "G", "5-8", 5.3, 0.3, 0.5, 0.5),
    Player("DeWanna Bonner", "F-G", "6-4", 10.7, 6.3, 1.5, 1.1),
    Player("Alyssa Thomas", "F", "6-2", 17.7, 7.2, 8.2, 1.8),
    Player("Jovana Nogic", "G", "6-0", 15.3, 1.2, 2.2, 1.5),
    Player("Kyara Linskens", "C", "6-4", 2.8, 2.2, 0.6, 0.3),
    Player("Sami Whitcomb", "G", "5-10", 0.0, 0.0, 0.0, 0.0),
    Player("Marta Suarez", "F", "6-3", 6.0, 1.0, 0.0, 0.6),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players