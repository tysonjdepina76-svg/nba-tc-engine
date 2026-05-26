"""
Dallas Wings — WNBA Roster
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
    Player("Paige Bueckers","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Alysha Clark","F","5' 11"",0.0,0.0,0.0,0.0),
    Player("Dulcy Fankam Mendjiadeu","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Azzi Fudd","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Aziaha James","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Awak Kuier","F","6' 6"",0.0,0.0,0.0,0.0),
    Player("Arike Ogunbowale","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("JJ Quinerly","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Jessica Shepard","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Maddy Siegrist","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Odyssey Sims","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Alanna Smith","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Costanza Verona","G","5' 7"",0.0,0.0,0.0,0.0),
    Player("Li Yueru","C","6' 7"",0.0,0.0,0.0,0.0),
]
