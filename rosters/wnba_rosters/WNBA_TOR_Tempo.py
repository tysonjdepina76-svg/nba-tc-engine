"""
Toronto Tempo — WNBA Roster
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
    Player("Kiki Rice", "G", "5-11", 11.3, 3.8, 2.2, 1.1),
    Player("Laura Juskaite", "F", "6-4", 7.8, 3.8, 1.2, 0.8),
    Player("Marina Mabrey", "G", "6-1", 17.8, 3.8, 2.2, 1.8),
    Player("Teonni Key", "F", "6-4", 3.3, 3.0, 0.3, 0.3),
    Player("Nyara Sabally", "F", "6-5", 9.3, 6.0, 2.5, 0.9),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Maria Conde", "F", "6-3", 5.7, 3.3, 1.0, 0.6),
    Player("Kia Nurse", "G", "6-0", 6.5, 1.3, 0.8, 0.7),
    Player("Lexi Held", "G", "5-9", 1.0, 0.3, 0.7, 0.1),
    Player("Temi Fagbenle", "C", "6-5", 2.0, 1.0, 1.0, 0.2),
    Player("Brittney Sykes", "G", "5-11", 22.3, 4.3, 4.7, 2.2),
    Player("Isabelle Harrison", "F", "6-5", 0.0, 0.0, 0.0, 0.0),
    Player("Julie Allemand", "G", "5-10", 3.3, 2.3, 4.0, 0.3),
    Player("Nikolina Milic", "C", "6-3", 3.5, 1.0, 0.5, 0.4),
    Player("Mariella Fasoula", "C", "6-4", 2.0, 1.0, 0.5, 0.2),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players