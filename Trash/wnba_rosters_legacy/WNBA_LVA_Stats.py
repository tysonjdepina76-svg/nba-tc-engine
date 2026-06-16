"""
LVA — WNBA Roster
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
    Player("A&#x27;ja Wilson","C","6'0\"",5.0,1.1,0.5,0.0),
    Player("Chennedy Carter","G","6'0\"",3.9,0.6,0.4,0.0),
    Player("Chelsea Gray","G","6'0\"",2.4,0.9,1.3,0.0),
    Player("Jackie Young","G","6'0\"",2.2,1.0,1.2,0.0),
    Player("NaLyssa Smith","F","6'0\"",1.8,1.1,0.2,0.0),
]

BENCH = [
    Player("Jewell Loyd","G","6'0\"",1.3,0.6,0.3,0.0),
    Player("Cheyenne Parker-Tyus","F","6'0\"",0.8,0.5,0.1,0.0),
    Player("Stephanie Talbot","F","6'0\"",0.6,0.5,0.3,0.0),
    Player("Brianna Turner","F","6'0\"",0.2,0.6,0.0,0.0),
    Player("Kierstan Bell","F","6'0\"",0.0,0.8,0.2,0.0),
]
