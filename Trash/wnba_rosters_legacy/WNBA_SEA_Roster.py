"""
Seattle Storm — WNBA Roster
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
    Player("Lexie Brown","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Zia Cooke","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Stefanie Dolson","C","6' 5"",0.0,0.0,0.0,0.0),
    Player("Awa Fam","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Natisha Hiedeman","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Mackenzie Holmes","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Jordan Horston","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Flau'jae Johnson","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Ezi Magbegor","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Taina Mair","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Dominique Malonga","C","6' 6"",0.0,0.0,0.0,0.0),
    Player("Jade Melbourne","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Katie Lou Samuelson","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Taylor Thierry","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Grace VanSlooten","F","6' 3"",0.0,0.0,0.0,0.0),
]
