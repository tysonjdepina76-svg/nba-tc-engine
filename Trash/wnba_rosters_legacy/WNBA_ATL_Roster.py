"""
Atlanta Dream — WNBA Roster
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
    Player("Isobel Borlase","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Jordin Canada","G","5' 6"",0.0,0.0,0.0,0.0),
    Player("Allisha Gray","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Naz Hillmon","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Rhyne Howard","G","6' 2"",0.0,0.0,0.0,0.0),
    Player("Brionna Jones","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Sika Kone","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Indya Nivar","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Aaliyah Nye","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Madina Okot","C","6' 6"",0.0,0.0,0.0,0.0),
    Player("Te-Hina Paopao","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Angel Reese","F","6' 4"",0.0,0.0,0.0,0.0),
]
