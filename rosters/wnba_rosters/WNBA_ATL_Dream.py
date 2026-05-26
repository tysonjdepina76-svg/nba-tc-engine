"""
Atlanta Dream — WNBA Roster
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
    Player("Naz Hillmon", "F", "6-2", 7.3, 5.0, 1.0, 0.7),
    Player("Amy Okonkwo", "F", "6-2", 0.0, 0.0, 0.0, 0.0),
    Player("Te-Hina Paopao", "G", "5-9", 9.0, 3.3, 2.3, 0.9),
    Player("Jordin Canada", "G", "5-6", 14.0, 4.0, 5.3, 1.4),
    Player("Angel Reese", "F", "6-4", 10.7, 12.7, 2.3, 1.1),
]

# ── BENCH (8 players) ──
BENCH = [
    Player("Rhyne Howard", "G", "6-2", 14.5, 4.5, 4.5, 1.5),
    Player("Madina Okot", "C", "6-6", 7.3, 6.7, 0.3, 0.7),
    Player("Allisha Gray", "G", "6-0", 25.0, 7.0, 1.3, 2.5),
    Player("Isobel Borlase", "G", "5-11", 1.0, 0.3, 0.0, 0.1),
    Player("Indya Nivar", "G", "5-10", 0.0, 3.5, 1.5, 0.0),
    Player("Sika Kone", "F", "6-3", 0.0, 0.7, 0.0, 0.0),
    Player("Aaliyah Nye", "G-F", "6-0", 0.0, 0.0, 0.0, 0.0),
    Player("Brionna Jones", "F", "6-3", 0.0, 0.0, 0.0, 0.0),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 13 players