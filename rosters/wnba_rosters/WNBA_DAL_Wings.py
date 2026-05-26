"""
Dallas Wings — WNBA Roster
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
    Player("Odyssey Sims", "G", "5-8", 8.4, 0.8, 3.2, 0.8),
    Player("Paige Bueckers", "G", "6-0", 20.8, 2.8, 5.2, 2.1),
    Player("Costanza Verona", "G", "5-6", 0.0, 0.0, 0.0, 0.0),
    Player("Alysha Clark", "F", "5-11", 2.0, 1.5, 0.0, 0.2),
    Player("Alanna Smith", "F", "6-4", 4.8, 4.0, 2.2, 0.5),
]

# ── BENCH (9 players) ──
BENCH = [
    Player("Aziaha James", "G", "5-10", 6.4, 2.4, 0.4, 0.6),
    Player("JJ Quinerly", "G", "5-8", 0.0, 0.0, 0.0, 0.0),
    Player("Dulcy Fankam Mendjiadeu", "F-C", "6-3", 0.0, 0.0, 0.0, 0.0),
    Player("Maddy Siegrist", "F", "6-2", 7.2, 2.2, 0.8, 0.7),
    Player("Arike Ogunbowale", "G", "5-8", 17.4, 2.2, 3.0, 1.7),
    Player("Li Yueru", "C", "6-7", 3.7, 4.3, 1.0, 0.4),
    Player("Jessica Shepard", "F", "6-4", 12.4, 9.8, 6.8, 1.2),
    Player("Awak Kuier", "F", "6-6", 3.0, 2.0, 1.2, 0.3),
    Player("Azzi Fudd", "G", "5-11", 8.8, 1.0, 1.0, 0.9),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 14 players