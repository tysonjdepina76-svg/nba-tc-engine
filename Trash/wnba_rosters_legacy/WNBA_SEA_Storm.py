"""
Seattle Storm — WNBA Roster
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
    Player("Natisha Hiedeman", "G", "5-8", 12.2, 2.0, 3.6, 1.2),
    Player("Flau'jae Johnson", "G", "5-10", 10.8, 4.6, 1.0, 1.1),
    Player("Taylor Thierry", "G-F", "6-1", 6.0, 2.0, 0.0, 0.6),
    Player("Jade Melbourne", "G", "5-10", 13.0, 1.4, 4.2, 1.3),
    Player("Zia Cooke", "G", "5-9", 9.8, 3.2, 1.8, 1.0),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Lexie Brown", "G", "5-9", 5.0, 2.2, 1.4, 0.5),
    Player("Awa Fam", "C", "6-4", 0.0, 0.0, 0.0, 0.0),
    Player("Ezi Magbegor", "F-C", "6-6", 0.0, 0.0, 0.0, 0.0),
    Player("Dominique Malonga", "C", "6-6", 16.0, 7.3, 0.3, 1.6),
    Player("Taina Mair", "G", "5-9", 0.0, 0.0, 1.0, 0.0),
    Player("Jordan Horston", "F", "6-2", 1.4, 2.8, 1.0, 0.1),
    Player("Stefanie Dolson", "C", "6-5", 7.4, 4.0, 1.4, 0.7),
    Player("Katie Lou Samuelson", "G", "6-3", 0.0, 0.0, 0.0, 0.0),
    Player("Mackenzie Holmes", "F", "6-3", 5.8, 4.0, 0.6, 0.6),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players