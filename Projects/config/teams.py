"""
Team abbreviation mappings for all sports.
"""

WNBA_TEAM_ABBR = {
    "Las Vegas Aces": "LV",
    "Indiana Fever": "IND",
    "New York Liberty": "NY",
    "Chicago Sky": "CHI",
    "Minnesota Lynx": "MIN",
    "Connecticut Sun": "CON",
    "Seattle Storm": "SEA",
    "Los Angeles Sparks": "LA",
    "Atlanta Dream": "ATL",
    "Washington Mystics": "WAS",
    "Dallas Wings": "DAL",
    "Phoenix Mercury": "PHX"
}

MLB_TEAM_ABBR = {
    "Los Angeles Dodgers": "LAD",
    "New York Yankees": "NYY",
    "New York Mets": "NYM",
    "Boston Red Sox": "BOS",
    "Houston Astros": "HOU",
    "Atlanta Braves": "ATL",
    "Chicago Cubs": "CHC",
    "Philadelphia Phillies": "PHI",
    "San Diego Padres": "SD",
    "Seattle Mariners": "SEA",
    "Texas Rangers": "TEX",
    "Tampa Bay Rays": "TB",
    "St. Louis Cardinals": "STL",
    "Toronto Blue Jays": "TOR",
    "Baltimore Orioles": "BAL",
    "Cleveland Guardians": "CLE",
    "Detroit Tigers": "DET",
    "Kansas City Royals": "KC",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "Oakland Athletics": "OAK",
    "Pittsburgh Pirates": "PIT",
    "San Francisco Giants": "SF",
    "Washington Nationals": "WAS",
    "Arizona Diamondbacks": "ARI",
    "Cincinnati Reds": "CIN",
    "Colorado Rockies": "COL",
    "Los Angeles Angels": "LAA"
}

WC_TEAM_ABBR = {
    "Argentina": "ARG",
    "Brazil": "BRA",
    "Colombia": "COL",
    "Peru": "PER",
    "Germany": "GER",
    "France": "FRA",
    "Portugal": "POR",
    "Spain": "ESP",
    "England": "ENG",
    "Netherlands": "NED",
    "Italy": "ITA",
    "Belgium": "BEL",
    "Mexico": "MEX",
    "USA": "USA",
    "Canada": "CAN",
    "Costa Rica": "CRC",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Australia": "AUS",
    "New Zealand": "NZL",
    "Morocco": "MAR",
    "Nigeria": "NGA",
    "Senegal": "SEN",
    "Ghana": "GHA",
    "Egypt": "EGY",
    "Cameroon": "CMR",
    "Tunisia": "TUN",
    "Algeria": "ALG",
    "Saudi Arabia": "KSA",
    "Iran": "IRN",
    "UAE": "UAE",
    "Qatar": "QAT"
}

def get_team_abbr(team_name: str, sport: str) -> str:
    """Get team abbreviation for a sport."""
    if sport == "wnba":
        return WNBA_TEAM_ABBR.get(team_name, team_name[:3].upper())
    elif sport == "mlb":
        return MLB_TEAM_ABBR.get(team_name, team_name[:3].upper())
    elif sport in ["wc", "soccer"]:
        return WC_TEAM_ABBR.get(team_name, team_name[:3].upper())
    return team_name[:3].upper()
