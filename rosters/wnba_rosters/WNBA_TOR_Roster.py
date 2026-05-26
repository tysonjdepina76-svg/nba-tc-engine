"""
Toronto Tempo — WNBA Roster
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
    Player("Julie Allemand","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Maria Conde","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Temi Fagbenle","C","6' 5"",0.0,0.0,0.0,0.0),
    Player("Mariella Fasoula","C","6' 5"",0.0,0.0,0.0,0.0),
    Player("Isabelle Harrison","F","6' 5"",0.0,0.0,0.0,0.0),
    Player("Lexi Held","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Laura Juskaite","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Teonni Key","F","6' 5"",0.0,0.0,0.0,0.0),
    Player("Marina Mabrey","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Nikolina Milic","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Kia Nurse","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Kiki Rice","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Nyara Sabally","F","6' 5"",0.0,0.0,0.0,0.0),
    Player("Brittney Sykes","G","5' 11"",0.0,0.0,0.0,0.0),
]
