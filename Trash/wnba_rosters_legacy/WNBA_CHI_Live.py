"""
ESPN Live Roster — CHI
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
    Player("Courtney Vandersloot","G","5'8\"",10.0,3.2,6.6,0.9),
    Player("Gabriela Jaquez","G","6'0\"",12.5,5.8,1.3,0.8),
    Player("Kamilla Cardoso","C","6'7\"",11.9,8.4,2.1,0.0),
    Player("Rickea Jackson","F","6'2\"",14.2,3.6,1.6,1.4),
    Player("Skylar Diggins","G","5'9\"",16.3,2.9,5.3,1.3),
]

BENCH = [
    Player("Aicha Coulibaly","G","6'0\"",5.3,1.3,0.7,0.0),
    Player("Azura Stevens","F","6'6\"",10.1,5.6,1.3,1.1),
    Player("DiJonai Carrington","G","5'11\"",8.5,3.5,1.2,0.6),
    Player("Elizabeth Williams","C","6'3\"",8.6,5.8,1.4,0.0),
    Player("Jacy Sheldon","G","5'10\"",6.5,2.0,2.3,1.0),
    Player("Maddy Westbeld","F","6'3\"",4.1,2.4,0.9,0.7),
    Player("Natasha Cloud","G","5'10\"",8.8,3.3,5.3,1.0),
    Player("Rachel Banham","G","5'10\"",5.8,1.2,1.6,1.2),
    Player("Sydney Taylor","G","5'9\"",3.3,0.3,0.7,0.3),
]
