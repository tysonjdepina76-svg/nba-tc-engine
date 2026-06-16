"""
Connecticut Sun — WNBA Roster
Game: LVA vs CT (May 15, 2026) | Score: Aces 101, Sun 94
Source: Box score live scrape
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

# ── STARTERS ────────────────────────────────────────────────────────────────
STARTERS = [
    Player("Tyasha Harris",    "G", "5-10",13.5, 3.5, 5.5, 1.2),  # lead guard
    Player("DiJonai Carrington","G","6-0", 14.0, 4.5, 3.0, 1.0),  # starter wing
    Player("Olivia Odogbo",    "F", "6-3", 10.5, 6.0, 2.5, 0.8),  # starter forward
    Player("Brionna Jones",    "C", "6-3", 12.0, 7.0, 2.0, 0.5),  # starter C
    Player("Kyara Liggins",    "F", "6-2",  8.5, 5.0, 1.5, 0.6),  # bench starter
]

# ── BENCH ───────────────────────────────────────────────────────────────────
BENCH = [
    Player("Saniya Rivers",    "G", "5-11", 9.5, 3.5, 3.0, 1.2),  # sparked rally
    Player("Kiki Easter",      "F", "6-4",  8.0, 5.5, 1.5, 0.4),  # bench forward
    Player("Diamond Miller",   "G", "5-11", 7.5, 3.0, 2.5, 0.9), # rotation guard
    Player("Megan Bing",       "C", "6-5",  6.5, 4.5, 1.0, 0.0),  # backup C
    Player("Jasmine Nwang",   "G", "5-9",  5.5, 2.0, 2.0, 0.7),  # reserve guard
    Player("Marina Hernandez", "F", "6-3",  5.0, 3.5, 1.0, 0.3),  # reserve forward
]

INJURY_NOTES = [
    "Sun short-handed — multiple players out",
    "Carrington (ankle) — Q",
]