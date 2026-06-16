"""
Golden State Valkyries — WNBA Roster
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
    Player("Laeticia Amihere","F","6' 3"",0.0,0.0,0.0,0.0),
    Player("Veronica Burton","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Kaila Charles","G","6' 1"",0.0,0.0,0.0,0.0),
    Player("Kaitlyn Chen","G","5' 9"",0.0,0.0,0.0,0.0),
    Player("Tiffany Hayes","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Juste Jocyte","G","6' 0"",0.0,0.0,0.0,0.0),
    Player("Ndjakalenga Mwenentanda","G","6' 2"",0.0,0.0,0.0,0.0),
    Player("Iliana Rupert","C","6' 4"",0.0,0.0,0.0,0.0),
    Player("Janelle Salaun","F","6' 2"",0.0,0.0,0.0,0.0),
    Player("Miela Sowah","G","5' 10"",0.0,0.0,0.0,0.0),
    Player("Kiah Stokes","C","6' 3"",0.0,0.0,0.0,0.0),
    Player("Kayla Thornton","F","6' 1"",0.0,0.0,0.0,0.0),
    Player("Gabby Williams","F","5' 11"",0.0,0.0,0.0,0.0),
    Player("Cecilia Zandalasini","F","6' 2"",0.0,0.0,0.0,0.0),
]
