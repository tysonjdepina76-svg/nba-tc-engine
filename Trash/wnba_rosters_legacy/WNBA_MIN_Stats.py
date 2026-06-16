"""
MIN — WNBA Roster
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
    Player("Kayla McBride","G","6'0\"",4.1,1.2,0.5,0.0),
    Player("Natasha Howard","F","6'0\"",4.0,1.9,0.9,0.0),
    Player("Courtney Williams","G","6'0\"",4.0,1.2,1.1,0.0),
    Player("Olivia Miles","G","6'0\"",3.9,1.1,1.4,0.0),
    Player("Emma Cechova","F","6'0\"",2.8,1.2,0.0,0.0),
]

BENCH = [
    Player("Nia Coffey","F","6'0\"",1.9,1.5,0.3,0.0),
    Player("Emese Hof","C","6'0\"",1.3,0.8,0.5,0.0),
    Player("Maya Caldwell","G","6'0\"",0.7,0.4,0.3,0.0),
    Player("Antonia Delaere","F","6'0\"",0.6,0.1,0.3,0.0),
    Player("Anastasiia Olairi Kosu","F","6'0\"",0.6,0.2,0.2,0.0),
    Player("Eliska Hamzova","G","6'0\"",0.5,0.3,0.0,0.0),
]
