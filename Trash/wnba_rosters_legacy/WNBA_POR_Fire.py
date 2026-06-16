"""
Portland Fire — WNBA Roster
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
    Player("Carla Leite", "G", "5-9", 15.0, 2.7, 3.3, 1.5),
    Player("Jordan Harrison", "G", "5-6", 4.0, 0.0, 4.0, 0.4),
    Player("Sarah Ashlee Barker", "G", "6-0", 10.0, 3.8, 1.8, 1.0),
    Player("Bridget Carleton", "F", "6-2", 16.8, 3.0, 1.8, 1.7),
    Player("Holly Winterburn", "G", "5-11", 3.0, 1.5, 2.5, 0.3),
]

# ── BENCH (8 players) ──
BENCH = [
    Player("Teja Oblak", "G", "5-8", 0.0, 0.0, 0.0, 0.0),
    Player("Nyadiew Puoch", "F", "6-3", 5.6, 2.2, 0.8, 0.6),
    Player("Luisa Geiselsoder", "C", "6-4", 6.6, 4.0, 2.2, 0.7),
    Player("Megan Gustafson", "C", "6-4", 7.4, 2.6, 0.4, 0.7),
    Player("Frieda Buhner", "F-C", "6-2", 2.0, 1.7, 0.0, 0.2),
    Player("Emily Engstler", "F", "6-1", 8.2, 2.8, 1.0, 0.8),
    Player("Serah Williams", "F", "6-4", 2.5, 2.8, 0.5, 0.2),
    Player("Karlie Samuelson", "G", "6-0", 0.0, 0.0, 0.0, 0.0),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 13 players