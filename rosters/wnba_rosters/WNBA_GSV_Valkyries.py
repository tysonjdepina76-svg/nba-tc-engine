"""
Golden State Valkyries — WNBA Roster
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
    Player("Gabby Williams", "F", "5-11", 15.0, 4.5, 2.5, 1.5),
    Player("Kaitlyn Chen", "G", "5-9", 5.5, 2.5, 1.3, 0.6),
    Player("Laeticia Amihere", "F", "6-3", 6.0, 4.8, 1.8, 0.6),
    Player("Juste Jocyte", "G-F", "6-0", 0.0, 0.0, 0.0, 0.0),
    Player("Kayla Thornton", "F", "6-1", 10.8, 5.5, 0.5, 1.1),
]

# ── BENCH (10 players) ──
BENCH = [
    Player("Kaila Charles", "G-F", "6-1", 8.0, 6.5, 1.5, 0.8),
    Player("Miela Sowah", "G", "5-10", 0.0, 0.0, 0.0, 0.0),
    Player("Ashten Prechtel", "F", "6-5", 0.0, 0.0, 0.0, 0.0),
    Player("Iliana Rupert", "C", "6-4", 0.0, 0.0, 0.0, 0.0),
    Player("Janelle Salaun", "F", "6-2", 14.8, 3.0, 1.0, 1.5),
    Player("Tiffany Hayes", "G", "5-10", 5.0, 0.5, 1.5, 0.5),
    Player("Veronica Burton", "G", "5-9", 14.5, 3.0, 7.3, 1.5),
    Player("Cecilia Zandalasini", "F", "6-2", 8.0, 2.0, 1.0, 0.8),
    Player("Ndjakalenga Mwenentanda", "G", "6-2", 0.0, 0.0, 0.0, 0.0),
    Player("Kiah Stokes", "C", "6-3", 5.0, 5.3, 2.0, 0.5),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 15 players