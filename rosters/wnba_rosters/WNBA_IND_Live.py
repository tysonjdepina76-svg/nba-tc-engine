"""
ESPN Live Roster — IND
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
    Player("Aliyah Boston","C","6'5\"",14.4,8.4,3.0,0.1),
    Player("Caitlin Clark","G","6'0\"",18.9,5.5,8.6,2.9),
    Player("Kelsey Mitchell","G","5'8\"",17.5,2.0,2.9,2.4),
    Player("Myisha Hines-Allen","F","6'2\"",7.8,5.0,2.1,0.5),
    Player("Sophie Cunningham","G","6'1\"",7.9,2.8,1.4,1.4),
]

BENCH = [
    Player("Bree Hall","G","6'1\"",0.8,0.8,0.0,0.0),
    Player("Damiris Dantas","C","6'4\"",6.9,3.8,1.4,0.8),
    Player("Justine Pissott","G","6'4\"",0.0,0.0,0.0,0.0),
    Player("Lexie Hull","G","6'2\"",5.5,2.9,1.2,0.8),
    Player("Makayla Timpson","F","6'2\"",2.9,1.9,0.1,0.0),
    Player("Monique Billings","F","6'4\"",6.3,5.6,0.9,0.1),
    Player("Raven Johnson","G","5'8\"",1.0,2.0,1.3,0.0),
    Player("Shatori Walker-Kimbrough","G","5'9\"",5.6,1.5,1.2,0.6),
    Player("Tyasha Harris","G","5'10\"",6.4,1.3,2.5,0.9),
]
