"""
Phoenix Mercury — WNBA Roster
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
    Player("Monique Akoa Makani","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Valeriane Ayayi","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("DeWanna Bonner","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Noemie Brochant","F","5' 11"",0.0,0.0,0.0,0.0),
    Player("Sha Carter","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Shay Ciezki","G","5' 7"",0.0,0.0,0.0,0.0),
    Player("Kahleah Copper","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Kyara Linskens","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Natasha Mack","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Jovana Nogic","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Marta Suarez","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Alyssa Thomas","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Sami Whitcomb","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Kiana Williams","G","5' 7"",0.0,0.0,0.0,0.0),
]
