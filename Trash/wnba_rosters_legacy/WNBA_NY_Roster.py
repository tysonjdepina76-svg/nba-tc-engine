"""
New York Liberty — WNBA Roster
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
    Player("Rebecca Allen","G","6' 2"",0.0,0.0,0.0,0.0),
    Player("Pauline Astier","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Raquel Carrera","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Marine Fauthoux","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Leonie Fiebich","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Alex Fowler","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Rebekah Gardner","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Aubrey Griffin","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Sabrina Ionescu","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Marine Johannes","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Jonquel Jones","C","6' 6"",0.0,0.0,0.0,0.0),
    Player("Betnijah Laney-Hamilton","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Satou Sabally","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Breanna Stewart","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Julie Vanloo","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Han Xu","C","6' 11"",0.0,0.0,0.0,0.0),
]
