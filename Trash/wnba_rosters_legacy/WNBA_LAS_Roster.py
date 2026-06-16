"""
Los Angeles Sparks — WNBA Roster
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
    Player("Ariel Atkins","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Cameron Brink","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Rae Burrell","G","6' 2"",0.0,0.0,0.0,0.0),
    Player("Emma Cannon","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Sania Feagin","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Chance Gray","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Dearica Hamby","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Ta'Niya Latson","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Kate Martin","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Nneka Ogwumike","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Jihyun Park","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Kelsey Plum","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Erica Wheeler","G","5' 7"",0.0,0.0,0.0,0.0),
    Player("Laura Ziegler","F","6' 2"",0.0,0.0,0.0,0.0),
]
