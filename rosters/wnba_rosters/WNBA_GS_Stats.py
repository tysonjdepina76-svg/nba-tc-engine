"""
GS — WNBA Roster
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
    Player("Cecilia Zandalasini","F","6'0\"",8.0,2.0,1.0,0.0),
    Player("Janelle Salaun","F","6'0\"",5.2,0.7,0.3,0.0),
    Player("Veronica Burton","G","6'0\"",5.0,0.9,2.4,0.0),
    Player("Gabby Williams","F","6'0\"",4.9,1.8,0.9,0.0),
    Player("Kayla Thornton","F","6'0\"",3.6,1.9,0.1,0.0),
]

BENCH = [
    Player("Kaitlyn Chen","G","6'0\"",2.2,1.1,0.4,0.0),
    Player("Kaila Charles","G","6'0\"",2.1,2.1,0.6,0.0),
    Player("Laeticia Amihere","F","6'0\"",2.1,1.2,0.8,0.0),
    Player("Kiah Stokes","C","6'0\"",1.6,2.0,0.6,0.0),
    Player("Tiffany Hayes","G","6'0\"",1.0,0.0,1.0,0.0),
    Player("Miela Sowah","G","6'0\"",0.0,0.0,0.0,0.0),
    Player("Ndjakalenga Mwenentanda","G","6'0\"",0.0,0.0,0.0,0.0),
]
