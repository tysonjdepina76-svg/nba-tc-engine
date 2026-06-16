"""
Chicago Sky — WNBA Roster
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
    Player("Rachel Banham","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Kamilla Cardoso","C","6' 7"",0.0,0.0,0.0,0.0),
    Player("DiJonai Carrington","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Natasha Cloud","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Aicha Coulibaly","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Skylar Diggins","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Rickea Jackson","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Gabriela Jaquez","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Jacy Sheldon","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Azura Stevens","F","6' 6"",0.0,0.0,0.0,0.0),
    Player("Sydney Taylor","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Courtney Vandersloot","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Maddy Westbeld","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Elizabeth Williams","C","6' 3"",0.0,0.0,0.0,0.0),
]
