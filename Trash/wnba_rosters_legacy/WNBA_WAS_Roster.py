"""
Washington Mystics — WNBA Roster
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
    Player("Georgia Amoore","G","5' 6"",0.0,0.0,0.0,0.0),
    Player("Shakira Austin","C","6' 5"",0.0,0.0,0.0,0.0),
    Player("Lauren Betts","C","6' 7"",0.0,0.0,0.0,0.0),
    Player("Sonia Citron","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Angela Dugalic","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Alicia Florez Getino","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Rori Harmon","G","5' 6"",0.0,0.0,0.0,0.0),
    Player("Kiki Iriafen","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Darianna Littlepage-Buggs","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Cotie McMahon","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Lucy Olsen","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Michaela Onyenwere","F","6' 0"",0.0,0.0,0.0,0.0),
    Player("Cassandre Prosper","G","6' 3"",0.0,0.0,0.0,0.0),
    Player("Alex Wilson","G","5' 9"",0.0,0.0,0.0,0.0),
]
