"""
New York Liberty — WNBA Roster
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
    Player("Satou Sabally", "F", "6-4", 5.0, 4.0, 2.0, 0.5),
    Player("Marine Fauthoux", "G", "5-9", 0.0, 0.0, 0.0, 0.0),
    Player("Rebekah Gardner", "G", "6-1", 10.4, 3.2, 2.2, 1.0),
    Player("Rebecca Allen", "F-G", "6-2", 4.0, 2.0, 1.5, 0.4),
    Player("Alex Fowler", "F", "6-2", 6.0, 0.0, 0.5, 0.6),
]

# ── BENCH (10 players) ──
BENCH = [
    Player("Leonie Fiebich", "F", "6-4", 0.0, 0.0, 0.0, 0.0),
    Player("Raquel Carrera", "C", "6-3", 0.0, 0.0, 0.0, 0.0),
    Player("Pauline Astier", "G", "5-11", 14.8, 4.0, 3.6, 1.5),
    Player("Sabrina Ionescu", "G", "5-11", 0.0, 0.0, 0.0, 0.0),
    Player("Han Xu", "C", "6-11", 4.0, 1.8, 0.6, 0.4),
    Player("Marine Johannes", "G", "5-10", 12.6, 3.2, 4.2, 1.3),
    Player("Breanna Stewart", "F", "6-4", 22.0, 9.0, 2.6, 2.2),
    Player("Jonquel Jones", "C", "6-6", 12.4, 7.4, 2.4, 1.2),
    Player("Betnijah Laney-Hamilton", "G-F", "6-0", 8.3, 2.3, 2.3, 0.8),
    Player("Julie Vanloo", "G", "5-8", 5.8, 2.0, 5.4, 0.6),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 15 players