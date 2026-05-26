"""
LAS — WNBA Roster
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
    Player("Kelsey Plum","G","6'0\"",6.7,0.4,1.4,0.0),
    Player("Dearica Hamby","F","6'0\"",4.3,1.8,0.6,0.0),
    Player("Nneka Ogwumike","F","6'0\"",4.1,1.7,0.5,0.0),
    Player("Emma Cannon","F","6'0\"",3.0,0.0,0.0,0.0),
    Player("Kate Martin","G","6'0\"",2.8,0.3,0.0,0.0),
]

BENCH = [
    Player("Ariel Atkins","G","6'0\"",2.5,1.5,1.3,0.0),
    Player("Rae Burrell","G","6'0\"",1.9,0.8,0.4,0.0),
    Player("Cameron Brink","F","6'0\"",1.8,0.8,0.3,0.0),
    Player("Erica Wheeler","G","6'0\"",1.1,0.4,1.2,0.0),
    Player("Jihyun Park","F","6'0\"",0.5,0.3,0.5,0.0),
    Player("Chance Gray","G","6'0\"",0.4,0.3,0.1,0.0),
    Player("Ta&#x27;Niya Latson","G","6'0\"",0.2,0.1,0.0,0.0),
    Player("Sania Feagin","F","6'0\"",0.0,0.0,0.0,0.0),
]
