"""
Indiana Fever — WNBA Roster
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
    Player("Kelsey Mitchell", "G", "5-8", 23.0, 1.0, 2.0, 2.3),
    Player("Myisha Hines-Allen", "F", "6-2", 5.8, 3.8, 3.4, 0.6),
    Player("Raven Johnson", "G", "5-8", 2.6, 2.2, 1.2, 0.3),
    Player("Aliyah Boston", "C-F", "6-5", 15.0, 5.8, 2.3, 1.5),
    Player("Sophie Cunningham", "G", "6-1", 8.2, 3.4, 1.4, 0.8),
]

# ── BENCH (8 players) ──
BENCH = [
    Player("Lexie Hull", "G", "6-2", 7.0, 3.6, 0.8, 0.7),
    Player("Damiris Dantas", "C-F", "6-4", 4.0, 1.0, 0.3, 0.4),
    Player("Justine Pissott", "G-F", "6-4", 0.0, 0.0, 0.0, 0.0),
    Player("Makayla Timpson", "F-C", "6-2", 4.2, 3.0, 0.6, 0.4),
    Player("Caitlin Clark", "G", "6-0", 24.3, 5.0, 9.0, 2.4),
    Player("Bree Hall", "G", "6-1", 0.0, 0.0, 0.0, 0.0),
    Player("Monique Billings", "F", "6-4", 8.0, 6.5, 1.8, 0.8),
    Player("Tyasha Harris", "G", "5-10", 2.6, 1.2, 2.4, 0.3),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 13 players