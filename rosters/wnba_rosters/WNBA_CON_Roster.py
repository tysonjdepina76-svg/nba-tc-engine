"""
Connecticut Sun — WNBA Roster
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
    Player("Nell Angloma","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Raegan Beers","F","6' 4"",0.0,0.0,0.0,0.0),
    Player("Kennedy Burke","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Aaliyah Edwards","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Brittney Griner","C","6' 9"",0.0,0.0,0.0,0.0),
    Player("Ashlon Jackson","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Gianna Kneepkens","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Leila Lacan","G","5' 11"",0.0,0.0,0.0,0.0),
    Player("Charlisse Leger-Walker","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Diamond Miller","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Aneesah Morrow","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Olivia Nelson-Ododa","C","6' 5"",0.0,0.0,0.0,0.0),
    Player("Saniya Rivers","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Hailey Van Lith","G","5' 9"",0.0,0.0,0.0,0.0),
]
