"""
WAS — WNBA Roster
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
    Player("Sonia Citron","G","6'0\"",5.0,0.9,0.5,0.0),
    Player("Cotie McMahon","G","6'0\"",5.0,1.5,0.8,0.0),
    Player("Kiki Iriafen","F","6'0\"",4.1,3.2,0.6,0.0),
    Player("Shakira Austin","C","6'0\"",4.1,2.1,0.8,0.0),
    Player("Georgia Amoore","G","6'0\"",1.4,0.3,1.1,0.0),
]

BENCH = [
    Player("Lauren Betts","C","6'0\"",1.4,0.8,0.1,0.0),
    Player("Lucy Olsen","G","6'0\"",1.4,0.0,0.4,0.0),
    Player("Cassandre Prosper","G","6'0\"",1.1,0.5,0.3,0.0),
    Player("Alex Wilson","G","6'0\"",0.8,0.5,0.2,0.0),
    Player("Angela Dugalic","F","6'0\"",0.6,0.6,0.1,0.0),
    Player("Rori Harmon","G","6'0\"",0.4,0.5,0.6,0.0),
]
