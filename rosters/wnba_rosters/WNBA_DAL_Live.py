"""
ESPN Live Roster — DAL
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
    Player("Alanna Smith","F","6'4\"",7.3,4.5,2.0,0.8),
    Player("Arike Ogunbowale","G","5'8\"",19.9,3.2,3.9,2.4),
    Player("Jessica Shepard","F","6'4\"",7.0,6.6,2.8,0.1),
    Player("Odyssey Sims","G","5'8\"",11.1,2.4,3.8,0.7),
    Player("Paige Bueckers","G","6'0\"",19.3,3.8,5.4,1.2),
]

BENCH = [
    Player("Alysha Clark","F","5'11\"",6.5,3.4,1.4,0.9),
    Player("Awak Kuier","F","6'6\"",2.7,2.5,0.7,0.1),
    Player("Aziaha James","G","5'10\"",7.5,2.8,1.5,0.9),
    Player("Azzi Fudd","G","5'11\"",7.7,1.3,1.0,0.3),
    Player("Costanza Verona","G","5'7\"",0.0,0.0,0.0,0.0),
    Player("Dulcy Fankam Mendjiadeu","F","6'3\"",3.4,3.9,0.3,0.0),
    Player("JJ Quinerly","G","5'8\"",6.5,1.9,2.3,0.6),
    Player("Li Yueru","C","6'7\"",4.7,3.6,0.6,0.3),
    Player("Maddy Siegrist","F","6'2\"",8.0,2.8,0.6,0.5),
]
