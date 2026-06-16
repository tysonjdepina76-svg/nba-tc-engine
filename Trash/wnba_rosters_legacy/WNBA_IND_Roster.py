"""
Indiana Fever — WNBA Roster
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
    Player("Monique Billings","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Aliyah Boston","C","6' 5"",0.0,0.0,0.0,0.0),
    Player("Caitlin Clark","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Sophie Cunningham","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Damiris Dantas","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Bree Hall","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Tyasha Harris","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Myisha Hines-Allen","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Lexie Hull","G","6' 2"",0.0,0.0,0.0,0.0),
    Player("Raven Johnson","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Kelsey Mitchell","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Justine Pissott","G","6' 4"",0.0,0.0,0.0,0.0),
    Player("Makayla Timpson","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Shatori Walker-Kimbrough","G","5' 9"",0.0,0.0,0.0,0.0),
]
