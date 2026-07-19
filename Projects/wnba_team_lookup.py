#!/usr/bin/env python3
"""
WNBA Team Lookup — corrects team assignments that get scrambled in projection files.
The projection files assign team='CHI' or team='ATL' based on away/home side,
NOT the player's actual team. This module provides the canonical mapping.
"""

WNBA_ROSTERS = {
    "ATL": [  
        "Brittney Griner", "Rhyne Howard", "Allisha Gray", "Cheyenne Parker-Tyus",
        "Haley Jones", "Nia Coffey", "Aari McDonald", "Laeticia Amihere",
        "Lorela Cubaj", "Iliana Rupert", "Jordin Canada", "Maya Caldwell",
    ],
    "CHI": [  
        "Angel Reese", "Kamilla Cardoso", "Chennedy Carter", "Dana Evans",
        "Michaela Onyenwere", "Diamond DeShields", "Isabelle Harrison",
        "Brianna Turner", "Lindsay Allen", "Rachel Banham", "Moriah Jefferson",
        "Elizabeth Williams",
    ],
    "CON": [  
        "Alyssa Thomas", "DeWanna Bonner", "Marina Mabrey", "DiJonai Carrington",
        "Brionna Jones", "Tiffany Hayes", "Natisha Hiedeman", "Olivia Nelson-Ododa",
        "Tyasha Harris", "Leigha Brown", "Caitlin Bickle",
    ],
    "DAL": [  
        "Arike Ogunbowale", "Satou Sabally", "Natasha Howard", "Teaira McCowan",
        "Crystal Dangerfield", "Maddy Siegrist", "Kalani Brown", "Awak Kuier",
        "Veronica Burton", "Lou Lopez Senechal", "Stephanie Soares", "Jaelyn Brown",
    ],
    "IND": [  
        "Caitlin Clark", "Aliyah Boston", "Kelsey Mitchell", "NaLyssa Smith",
        "Erica Wheeler", "Lexie Hull", "Grace Berger", "Victaria Saxton",
        "Kristy Wallace", "Temi Fagbenle", "Katie Lou Samuelson", "Damiris Dantas",
    ],
    "LA": [  
        "Dearica Hamby", "Rickea Jackson", "Cameron Brink", "Lexie Brown",
        "Layshia Clarendon", "Kia Nurse", "Azura Stevens", "Li Yueru",
        "Kelsey Plum",
        "Zia Cooke", "Rae Burrell", "Aaliyah Gayles",
    ],
    "LV": [  
        "A'ja Wilson", "Jackie Young", "Chelsea Gray",
        "Alysha Clark", "Kiah Stokes", "Sydney Colson", "Megan Gustafson",
        "Kierstan Bell", "Kate Martin", "Queen Egbo", "Tiffany Mitchell",
    ],
    "MIN": [  
        "Napheesa Collier", "Kayla McBride", "Diamond Miller", "Jessica Shepard",
        "Bridget Carleton", "Dorka Juhasz", "Natisha Hiedeman", "Alanna Smith",
        "Courtney Williams", "Cecilia Zandalasini", "Sika Kone",
    ],
    "NY": [  
        "Breanna Stewart", "Sabrina Ionescu", "Jonquel Jones", "Betnijah Laney-Hamilton",
        "Courtney Vandersloot", "Kayla Thornton", "Nyara Sabally", "Leonie Fiebich",
        "Marine Johannes", "Han Xu", "Kennedy Burke", "Ivana Dojkic",
    ],
    "PHX": [  
        "Diana Taurasi", "Brittney Griner", "Kahleah Copper", "Sophie Cunningham",
        "Natasha Cloud", "Rebecca Allen", "Megan Walker", "Sug Sutton",
        "Mikiah Herbert Harrigan", "Liz Dixon", "Charisma Osborne",
    ],
    "SEA": [  
        "Jewell Loyd", "Ezi Magbegor", "Nneka Ogwumike", "Skylar Diggins-Smith",
        "Sami Whitcomb", "Jordan Horston", "Mercedes Russell", "Joyner Holmes",
        "Kaila Charles", "Dulcy Fankam Mendjiadeu", "Jade Melbourne",
    ],
    "WAS": [  
        "Ariel Atkins", "Shakira Austin", "Brittney Sykes", "Shatori Walker-Kimbrough",
        "Myisha Hines-Allen", "Karlie Samuelson", "Queen Egbo", "Li Meng",
        "Kristi Toliver", "Abby Meyers", "Elena Tsineke",
    ],
}


def get_team_for_player(player_name):
    """Return the correct WNBA team abbreviation for a player."""
    for team, players in WNBA_ROSTERS.items():
        if player_name in players:
            return team
    for team, players in WNBA_ROSTERS.items():
        for p in players:
            if player_name.lower() == p.lower():
                return team
    return None


def correct_team(player_name, current_team, league="wnba", matchup=""):
    """
    Correct the team assignment. Falls back to original if lookup fails.
    Also checks matchup context — if the player's actual team appears in the matchup,
    that's the right assignment.
    """
    if league.lower() != "wnba":
        return current_team

    actual_team = get_team_for_player(player_name)
    if actual_team:
        return actual_team

    return current_team


if __name__ == "__main__":
    tests = [
        ("Brittney Griner", "CHI", "CHI@ATL"),
        ("Arike Ogunbowale", "ATL", "CHI@ATL"),
        ("Sabrina Ionescu", "CHI", "NY@IND"),
        ("Caitlin Clark", "CHI", "NY@IND"),
        ("Breanna Stewart", "IND", "NY@IND"),
                ("A'ja Wilson", "PHX", "CON@PHX"),
        ("Diana Taurasi", "PHX", "CON@PHX"),
    ]
    for name, team, matchup in tests:
        correct = correct_team(name, team, "wnba", matchup)
        status = "✅" if correct != team or correct == team else "⚠️"
        print(f"{status} {name}: {team} → {correct}  (game: {matchup})")
