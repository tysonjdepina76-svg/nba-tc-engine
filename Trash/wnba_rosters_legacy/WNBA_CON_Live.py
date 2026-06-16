"""
ESPN Live Roster — CON
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
    Player("Aaliyah Edwards","F","6'3\"",6.5,4.6,0.9,0.0),
    Player("Aneesah Morrow","F","6'1\"",8.3,7.3,0.6,0.5),
    Player("Brittney Griner","C","6'9\"",16.8,7.1,1.8,0.1),
    Player("Leila Lacan","G","5'11\"",10.4,2.4,3.7,0.6),
    Player("Saniya Rivers","G","6'1\"",8.7,2.7,3.0,1.0),
]

BENCH = [
    Player("Ashlon Jackson","G","6'0\"",0.0,0.0,0.0,0.0),
    Player("Charlisse Leger-Walker","G","5'10\"",6.4,1.6,2.2,0.8),
    Player("Diamond Miller","F","6'3\"",6.7,2.2,1.3,0.6),
    Player("Gianna Kneepkens","G","5'11\"",3.8,2.4,0.6,0.4),
    Player("Hailey Van Lith","G","5'9\"",4.6,1.1,1.8,0.4),
    Player("Kennedy Burke","G","6'1\"",5.3,1.8,0.9,0.6),
    Player("Nell Angloma","F","6'1\"",4.0,0.5,0.5,0.0),
    Player("Olivia Nelson-Ododa","C","6'5\"",5.1,3.6,0.6,0.0),
    Player("Raegan Beers","F","6'4\"",4.5,2.8,0.5,0.0),
]
