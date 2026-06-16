"""
Washington Mystics — WNBA Roster
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
    Player("Shakira Austin", "C", "6-5", 16.3, 8.5, 3.0, 1.6),
    Player("Alicia Florez Getino", "G", "5-9", 0.0, 0.0, 0.0, 0.0),
    Player("Rori Harmon", "G", "5-6", 1.5, 1.8, 2.3, 0.2),
    Player("Alex Wilson", "G", "5-9", 3.0, 1.8, 0.8, 0.3),
    Player("Darianna Littlepage-Buggs", "G-F", "6-1", 0.0, 0.0, 0.0, 0.0),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Georgia Amoore", "G", "5-6", 5.8, 1.3, 4.3, 0.6),
    Player("Michaela Onyenwere", "F", "6-0", 0.0, 0.0, 0.0, 0.0),
    Player("Cassandre Prosper", "G", "6-3", 4.5, 2.0, 1.3, 0.5),
    Player("Sonia Citron", "G", "6-1", 20.0, 3.5, 1.8, 2.0),
    Player("Cotie McMahon", "G", "6-0", 10.0, 3.0, 1.5, 1.0),
    Player("Angela Dugalic", "F", "6-4", 2.3, 2.5, 0.3, 0.2),
    Player("Lucy Olsen", "G", "5-10", 4.3, 0.0, 1.3, 0.4),
    Player("Kiki Iriafen", "F", "6-3", 16.5, 12.8, 2.3, 1.7),
    Player("Lauren Betts", "C", "6-7", 5.5, 3.0, 0.5, 0.6),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players