"""
Las Vegas Aces — WNBA Roster
Updated: 2026-05-21
Source: ESPN API
"""
from dataclasses import dataclass

@dataclass
class Player:
    name: str; pos: str; ht: str
    ppg: float; rpg: float; apg: float; tpm: float
    status: str = 'ACTIVE'; injury: str = ''

STARTERS = [
]

BENCH = [
    Player("Janiah Barker","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Kierstan Bell","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Chennedy Carter","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Dana Evans","G","5' 6"",0.0,0.0,0.0,0.0),
    Player("Chelsea Gray","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Jewell Loyd","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Cheyenne Parker-Tyus","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("NaLyssa Smith","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Stephanie Talbot","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Brianna Turner","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("A'ja Wilson","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Jackie Young","G","6' 0"",0.0,0.0,0.0,0.0),
]
