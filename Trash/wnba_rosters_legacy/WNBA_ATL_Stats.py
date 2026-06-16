"""
ATL — WNBA Roster
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
    Player("Allisha Gray","G","6'0\"",8.3,2.3,0.4,0.0),
    Player("Rhyne Howard","G","6'0\"",7.3,2.3,2.3,0.0),
    Player("Jordin Canada","G","6'0\"",4.7,1.3,1.8,0.0),
    Player("Angel Reese","F","6'0\"",3.6,4.2,0.8,0.0),
    Player("Te-Hina Paopao","G","6'0\"",3.0,1.1,0.8,0.0),
]

BENCH = [
    Player("Naz Hillmon","F","6'0\"",2.4,1.7,0.3,0.0),
    Player("Madina Okot","C","6'0\"",2.4,2.2,0.1,0.0),
    Player("Isobel Borlase","G","6'0\"",0.3,0.1,0.0,0.0),
    Player("Aaliyah Nye","G","6'0\"",0.0,0.0,0.0,0.0),
    Player("Sika Kone","F","6'0\"",0.0,0.2,0.0,0.0),
    Player("Indya Nivar","G","6'0\"",0.0,1.8,0.8,0.0),
]
