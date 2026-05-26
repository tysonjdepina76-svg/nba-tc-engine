"""
Minnesota Lynx — WNBA Roster
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
    Player("Maya Caldwell","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Emma Cechova","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Nia Coffey","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Napheesa Collier","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Antonia Delaere","F","5' 11"",0.0,0.0,0.0,0.0),
    Player("Eliska Hamzova","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Emese Hof","C","6' 3"",0.0,0.0,0.0,0.0),
    Player("Natasha Howard","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Dorka Juhasz","F","6' 5"",0.0,0.0,0.0,0.0),
    Player("Liatu King","F","6' 0"",0.0,0.0,0.0,0.0),
    Player("Anastasiia Olairi Kosu","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Kayla McBride","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Olivia Miles","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Courtney Williams","G","5' 8"",0.0,0.0,0.0,0.0),
]
