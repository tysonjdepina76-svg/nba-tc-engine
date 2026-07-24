#!/usr/bin/env python3
"""
WNBA Team Lookup — corrects team assignments that get scrambled in projection files.
ESPN boxscore data is ground truth. Only override when team clearly conflicts
with matchup context. Hardcoded roster lookup is last resort.
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
        "Elizabeth Williams", "Natasha Cloud", "Azura Stevens",
        "Courtney Vandersloot", "Sydney Taylor",
        "Gabriela Jaquez", "Jacy Sheldon", "Aicha Coulibaly",
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
        "Layshia Clarendon", "Kia Nurse", "Li Yueru",
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
        "Bridget Carleton", "Dorka Juhasz", "Alanna Smith",
        "Courtney Williams", "Cecilia Zandalasini", "Sika Kone",
    ],
    "NY": [  
        "Breanna Stewart", "Sabrina Ionescu", "Jonquel Jones", "Betnijah Laney-Hamilton",
        "Kayla Thornton", "Nyara Sabally", "Leonie Fiebich",
        "Marine Johannes", "Han Xu", "Kennedy Burke", "Ivana Dojkic",
        "Rebecca Allen", "Pauline Astier", "Raquel Carrera", "Rebekah Gardner",
        "Marine Fauthoux",
    ],
    "PHX": [  
        "Diana Taurasi", "Brittney Griner", "Kahleah Copper", "Sophie Cunningham",
        "Megan Walker", "Sug Sutton",
        "Mikiah Herbert Harrigan", "Liz Dixon", "Charisma Osborne",
    ],
    "SEA": [  
        "Jewell Loyd", "Ezi Magbegor", "Nneka Ogwumike", "Skylar Diggins-Smith",
        "Sami Whitcomb", "Jordan Horston", "Mercedes Russell", "Joyner Holmes",
        "Kaila Charles", "Dulcy Fankam Mendjiadeu", "Jade Melbourne",
    ],
    "WSH": [  
        "Ariel Atkins", "Shakira Austin", "Brittney Sykes", "Shatori Walker-Kimbrough",
        "Myisha Hines-Allen", "Karlie Samuelson",
        "Kristi Toliver", "Abby Meyers", "Elena Tsineke",
    ],
}

TEAM_ABBREV_MAP = {
    "atlanta dream": "ATL", "chicago sky": "CHI", "connecticut sun": "CON",
    "dallas wings": "DAL", "indiana fever": "IND", "las vegas aces": "LV",
    "los angeles sparks": "LA", "minnesota lynx": "MIN", "new york liberty": "NY",
    "phoenix mercury": "PHX", "seattle storm": "SEA", "washington mystics": "WSH",
}


def get_team_for_player(player_name):
    """Return the correct WNBA team abbreviation for a player from hardcoded roster."""
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
    ESPN boxscore is ground truth. Only override when team clearly conflicts
    with matchup context. Roster lookup is last resort.
    """
    if league.lower() != "wnba":
        return current_team

    current_lower = (current_team or "").strip().lower()

    matchup_teams = []
    if "_at_" in matchup:
        parts = matchup.split("_at_")
        matchup_teams = [p.strip() for p in parts]
    elif "@" in matchup:
        parts = matchup.split("@")
        matchup_teams = [p.strip() for p in parts]

    # ESPN-sourced team is ground truth
    current_abbrev = TEAM_ABBREV_MAP.get(current_lower, None)
    if not current_abbrev and len(current_team) <= 3 and current_team.isalpha():
        current_abbrev = current_team.upper()

    if current_abbrev:
        if not matchup_teams or current_abbrev in matchup_teams:
            return current_abbrev

    if current_lower in TEAM_ABBREV_MAP:
        abbrev = TEAM_ABBREV_MAP[current_lower]
        if matchup_teams and abbrev in matchup_teams:
            return abbrev
        return abbrev

    roster_team = get_team_for_player(player_name)
    if roster_team:
        if not matchup_teams or roster_team in matchup_teams:
            return roster_team

    return current_abbrev or current_team or roster_team or "???"


if __name__ == "__main__":
    tests = [
        ("Brittney Griner", "Atlanta Dream", "PHX_at_LA"),
        ("Natasha Cloud", "Chicago Sky", "CHI_at_NY"),
        ("Azura Stevens", "Chicago Sky", "CHI_at_NY"),
        ("Breanna Stewart", "New York Liberty", "CHI_at_NY"),
        ("Caitlin Clark", "Indiana Fever", "CON_at_IND"),
        ("A'ja Wilson", "Las Vegas Aces", "LV_at_WSH"),
    ]
    for name, team, matchup in tests:
        correct = correct_team(name, team, "wnba", matchup)
        print(f"{name}: {team} → {correct}  (matchup: {matchup})")
