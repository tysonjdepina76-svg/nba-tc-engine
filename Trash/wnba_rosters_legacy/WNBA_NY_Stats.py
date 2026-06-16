"""
NY — WNBA Roster
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
    Player("Alex Fowler","F","6'0\"",12.0,0.0,1.0,0.0),
    Player("Breanna Stewart","F","6'0\"",5.8,2.3,0.7,0.0),
    Player("Pauline Astier","G","6'0\"",4.2,0.9,1.0,0.0),
    Player("Marine Johannes","G","6'0\"",4.0,0.8,1.3,0.0),
    Player("Rebecca Allen","G","6'0\"",3.0,0.0,1.0,0.0),
]

BENCH = [
    Player("Jonquel Jones","C","6'0\"",2.9,1.8,0.6,0.0),
    Player("Rebekah Gardner","G","6'0\"",2.5,0.9,0.7,0.0),
    Player("Betnijah Laney-Hamilton","G","6'0\"",2.1,0.6,0.6,0.0),
    Player("Julie Vanloo","G","6'0\"",1.7,0.5,1.2,0.0),
    Player("Han Xu","C","6'0\"",0.9,0.6,0.2,0.0),
    Player("Aubrey Griffin","F","6'0\"",0.1,0.1,0.0,0.0),
]
