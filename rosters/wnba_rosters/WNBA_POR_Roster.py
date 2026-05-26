"""
Portland Fire — WNBA Roster
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
    Player("Sarah Ashlee Barker","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Frieda Buhner","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Bridget Carleton","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Emily Engstler","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Luisa Geiselsoder","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Megan Gustafson","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Haley Jones","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Carla Leite","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Teja Oblak","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Nyadiew Puoch","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Karlie Samuelson","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Kamiah Smalls","F","5' 10"",0.0,0.0,0.0,0.0),
    Player("Sug Sutton","G","5' 8"",0.0,0.0,0.0,0.0),
    Player("Serah Williams","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Holly Winterburn","G","5' 11"",0.0,0.0,0.0,0.0),
]
