"""
ESPN Live Roster — POR
Source: espn_wnba_live_20260520.json (2026-05-21)
TC-adjusted stats from live scrape (PTS=pts*0.85, REB=reb*0.77, AST=ast*0.74, 3PM=3pm*0.77)
"""
from dataclasses import dataclass

@dataclass
class Player:
    name: str; pos: str; ht: str
    ppg: float; rpg: float; apg: float; tpm: float
    status: str = 'ACTIVE'; injury: str = ''

STARTERS = [
    Player("Bridget Carleton","F","6'2\"",5.9,2.9,1.6,1.2),
    Player("Carla Leite","G","5'9\"",7.9,1.4,2.2,0.4),
    Player("Luisa Geiselsoder","C","6'4\"",6.9,4.8,1.7,1.1),
    Player("Nyadiew Puoch","F","6'3\"",7.0,2.5,1.0,0.8),
    Player("Sug Sutton","G","5'8\"",6.1,1.7,3.5,0.7),
]

BENCH = [
    Player("Emily Engstler","F","6'1\"",4.7,3.9,1.4,0.5),
    Player("Frieda Buhner","F","6'1\"",2.0,1.7,0.0,0.0),
    Player("Haley Jones","G","6'1\"",4.7,2.6,2.2,0.2),
    Player("Holly Winterburn","G","5'11\"",2.0,1.0,4.0,0.0),
    Player("Kamiah Smalls","F","5'10\"",3.1,0.9,1.7,0.7),
    Player("Karlie Samuelson","G","6'0\"",5.3,2.0,1.4,1.1),
    Player("Megan Gustafson","C","6'4\"",4.4,2.4,0.4,0.4),
    Player("Sarah Ashlee Barker","G","6'0\"",3.9,2.1,1.0,0.6),
    Player("Serah Williams","C","6'4\"",1.3,3.0,0.7,0.0),
    Player("Teja Oblak","G","5'8\"",0.0,0.0,0.0,0.0),
]
