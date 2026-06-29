# TC - TC Trademark 2026
"""Cape Verde team - WC 2026 first-class citizen."""
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class CapeVerdePlayer:
    name: str
    position: str
    club: str
    number: int = 0
CAPE_VERDE_GROUP = "H"
CAPE_VERDE_RANKING = 65
CAPE_VERDE_STAR = "Bebe"
CAPE_VERDE_PLAYERS = [
    CapeVerdePlayer("Bebe", "FWD", "Rayo Vallecano", 9),
    CapeVerdePlayer("Ryan Mendes", "FWD", "Fatih Karagumruk", 17),
    CapeVerdePlayer("Julio Tavares", "FWD", "Al-Faisaly", 19),
    CapeVerdePlayer("Nuno Borges", "MID", "PAOK", 20),
    CapeVerdePlayer("Deroy Duarte", "MID", "Maccabi Haifa", 6),
    CapeVerdePlayer("Joao Paulo", "MID", "Almeria", 10),
    CapeVerdePlayer("Carlos Pina", "MID", "Feirense", 16),
    CapeVerdePlayer("Dylan Tavares", "DEF", "Bastia", 3),
    CapeVerdePlayer("Roberto Lopes", "DEF", "Shamrock Rovers", 4),
    CapeVerdePlayer("Stopira", "DEF", "PAS Giannina", 5),
    CapeVerdePlayer("Vozinha", "GK", "Trofense", 1),
]
CAPE_VERDE_BOOST = {
    "group_stage": 1.05,
    "knockout": 1.10,
    "vs_top_20": 1.15,
}
CAPE_VERDE_GROUP_OPPONENTS = ["Portugal", "Ghana", "Uruguay"]
TOP_20 = ["Brazil", "Argentina", "France", "Spain", "England", "Germany", "Portugal", "Netherlands", "Belgium", "Italy", "Uruguay", "Croatia", "Morocco", "Colombia", "Mexico", "USA", "Senegal", "Japan", "Switzerland", "Denmark"]
def cv_multiplier(player_team, opponent_team):
    if player_team != "Cape Verde":
        return 1.0
    if opponent_team in TOP_20:
        return 1.15
    return 1.05
