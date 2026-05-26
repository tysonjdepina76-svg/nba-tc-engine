"""
ESPN Live Roster — SEA
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
    Player("Dominique Malonga","C","6'6\"",8.2,4.8,0.8,0.1),
    Player("Ezi Magbegor","F","6'4\"",9.7,6.0,1.7,0.4),
    Player("Flau'jae Johnson","G","5'10\"",12.3,5.0,1.3,1.0),
    Player("Natisha Hiedeman","G","5'8\"",7.4,1.8,2.5,1.2),
    Player("Stefanie Dolson","C","6'5\"",8.3,4.4,1.8,0.7),
]

BENCH = [
    Player("Awa Fam","C","6'4\"",0.0,0.0,0.0,0.0),
    Player("Grace VanSlooten","F","6'3\"",4.3,1.5,0.8,0.5),
    Player("Jade Melbourne","G","5'10\"",5.2,1.5,2.1,0.5),
    Player("Jordan Horston","F","6'2\"",6.6,4.6,1.7,0.3),
    Player("Katie Lou Samuelson","F","6'3\"",5.9,2.5,1.4,1.0),
    Player("Lexie Brown","G","5'9\"",5.7,1.5,1.7,1.1),
    Player("Mackenzie Holmes","F","6'3\"",1.5,1.6,0.3,0.1),
    Player("Taina Mair","G","5'9\"",0.0,0.0,0.0,0.0),
    Player("Taylor Thierry","F","6'1\"",0.4,0.4,0.1,0.1),
    Player("Zia Cooke","G","5'9\"",4.3,0.8,0.7,0.5),
]
