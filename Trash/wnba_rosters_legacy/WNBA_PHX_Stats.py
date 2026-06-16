"""
PHX — WNBA Roster
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
    Player("Kahleah Copper","G","6'0\"",3.6,0.4,0.5,0.0),
    Player("Alyssa Thomas","F","6'0\"",3.3,1.4,1.7,0.0),
    Player("Jovana Nogic","G","6'0\"",3.1,0.2,0.4,0.0),
    Player("DeWanna Bonner","F","6'0\"",2.2,1.3,0.3,0.0),
    Player("Natasha Mack","F","6'0\"",2.1,1.7,0.3,0.0),
]

BENCH = [
    Player("Valeriane Ayayi","F","6'0\"",1.9,1.0,0.6,0.0),
    Player("Kiana Williams","G","6'0\"",1.2,0.1,0.1,0.0),
    Player("Noemie Brochant","F","6'0\"",1.0,0.4,0.0,0.0),
    Player("Kyara Linskens","C","6'0\"",0.6,0.4,0.1,0.0),
    Player("Sha Carter","G","6'0\"",0.5,0.5,0.3,0.0),
    Player("Anneli Maley","F","6'0\"",0.3,0.5,0.0,0.0),
    Player("Peyton Williams","F","6'0\"",0.0,0.0,2.0,0.0),
]
