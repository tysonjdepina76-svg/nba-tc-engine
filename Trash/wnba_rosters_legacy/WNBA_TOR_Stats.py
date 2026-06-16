"""
TOR — WNBA Roster
Updated: 2026-05-21
Source: sportbusy.com (WNBA 2026 season stats)
"""
from dataclasses import dataclass

@dataclass
class Player:
    name: str; pos: str; ht: str
    ppg: float; rpg: float; apg: float; tpm: float
    status: str = 'ACTIVE'; injury: str = ''
STARTERS = [
    Player("Brittney Sykes","G","6'0\"",5.1,0.9,1.0,0.0),
    Player("Marina Mabrey","G","6'0\"",4.2,0.8,0.5,0.0),
    Player("Kiki Rice","G","6'0\"",2.3,0.7,0.4,0.0),
    Player("Nyara Sabally","F","6'0\"",2.3,1.5,0.6,0.0),
    Player("Temi Fagbenle","C","6'0\"",2.0,1.0,1.0,0.0),
]

BENCH = [
    Player("Laura Juskaite","F","6'0\"",1.6,0.8,0.2,0.0),
    Player("Maria Conde","F","6'0\"",1.2,0.8,0.2,0.0),
    Player("Julie Allemand","G","6'0\"",1.1,0.8,1.3,0.0),
    Player("Nikolina Milic","F","6'0\"",0.7,0.3,0.1,0.0),
    Player("Kia Nurse","G","6'0\"",0.6,0.2,0.1,0.0),
    Player("Teonni Key","F","6'0\"",0.6,0.6,0.1,0.0),
    Player("Lexi Held","G","6'0\"",0.1,0.0,0.0,0.0),
    Player("Mariella Fasoula","C","6'0\"",0.0,1.0,0.0,0.0),
]
