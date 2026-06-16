"""
Las Vegas Aces — WNBA Roster
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
    Player("Jackie Young", "G", "6-0", 11.2, 5.0, 6.2, 1.1),
    Player("Kierstan Bell", "F", "6-1", 0.0, 2.3, 0.7, 0.0),
    Player("Janiah Barker", "F", "6-4", 0.0, 0.0, 0.0, 0.0),
    Player("NaLyssa Smith", "F", "6-4", 9.2, 5.4, 1.2, 0.9),
    Player("Stephanie Talbot", "F", "6-2", 3.0, 2.4, 1.4, 0.3),
]

# ── BENCH (7 players) ──
BENCH = [
    Player("Dana Evans", "G", "5-6", 0.0, 0.0, 0.0, 0.0),
    Player("Chelsea Gray", "G", "5-11", 12.0, 4.4, 6.6, 1.2),
    Player("Brianna Turner", "F-C", "6-3", 0.8, 3.0, 0.2, 0.1),
    Player("A'ja Wilson", "C", "6-4", 25.0, 5.6, 2.4, 2.5),
    Player("Chennedy Carter", "G", "5-9", 19.4, 2.8, 2.0, 1.9),
    Player("Jewell Loyd", "G", "5-11", 6.4, 3.2, 1.6, 0.6),
    Player("Cheyenne Parker-Tyus", "F", "6-4", 4.0, 2.4, 0.6, 0.4),
]

INJURY_NOTES = [
    'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.',
]

# Total: 12 players