WC_TEAMS = {
    "Cape Verde": {
        "fifa_ranking": 65,
        "group": "H",
        "flag": "CV",
        "star": "Bebe",
        "key_players": ["Bebe", "Ryan Mendes", "Julio Tavares"],
    },
    "Portugal": {
        "fifa_ranking": 6,
        "group": "H",
        "flag": "PT",
        "star": "Cristiano Ronaldo",
        "key_players": ["Cristiano Ronaldo", "Bruno Fernandes"],
    },
    "Ghana": {
        "fifa_ranking": 45,
        "group": "H",
        "flag": "GH",
        "star": "Mohammed Kudus",
        "key_players": ["Mohammed Kudus", "Thomas Partey"],
    },
    "Uruguay": {
        "fifa_ranking": 15,
        "group": "H",
        "flag": "UY",
        "star": "Federico Valverde",
        "key_players": ["Federico Valverde", "Darwin Nunez"],
    },
    "USA": {"fifa_ranking": 11, "group": "A", "flag": "US", "star": "Christian Pulisic"},
    "Mexico": {"fifa_ranking": 13, "group": "A", "flag": "MX", "star": "Hirving Lozano"},
    "Canada": {"fifa_ranking": 27, "group": "A", "flag": "CA", "star": "Alphonso Davies"},
    "Argentina": {"fifa_ranking": 2, "group": "B", "flag": "AR", "star": "Lionel Messi"},
    "Brazil": {"fifa_ranking": 5, "group": "B", "flag": "BR", "star": "Vinicius Jr"},
    "France": {"fifa_ranking": 3, "group": "C", "flag": "FR", "star": "Kylian Mbappe"},
    "England": {"fifa_ranking": 4, "group": "C", "flag": "GB", "star": "Jude Bellingham"},
    "Spain": {"fifa_ranking": 8, "group": "D", "flag": "ES", "star": "Lamine Yamal"},
    "Germany": {"fifa_ranking": 9, "group": "D", "flag": "DE", "star": "Florian Wirtz"},
    "Netherlands": {"fifa_ranking": 7, "group": "D", "flag": "NL", "star": "Virgil van Dijk"},
    "Japan": {"fifa_ranking": 18, "group": "E", "flag": "JP", "star": "Takefusa Kubo"},
    "South Korea": {"fifa_ranking": 23, "group": "E", "flag": "KR", "star": "Son Heung-min"},
    "Belgium": {"fifa_ranking": 14, "group": "F", "flag": "BE", "star": "Kevin De Bruyne"},
    "Morocco": {"fifa_ranking": 12, "group": "F", "flag": "MA", "star": "Achraf Hakimi"},
    "Senegal": {"fifa_ranking": 19, "group": "G", "flag": "SN", "star": "Sadio Mane"},
    "Iran": {"fifa_ranking": 21, "group": "G", "flag": "IR", "star": "Mehdi Taremi"},
    "Switzerland": {"fifa_ranking": 16, "group": "G", "flag": "CH", "star": "Granit Xhaka"},
}

def get_team(name: str) -> dict:
    for n, data in WC_TEAMS.items():
        if n.lower() == name.lower():
            return {"name": n, **data}
    raise KeyError(f"Team not found: {name}")

def get_group(group: str) -> list:
    return [{"name": n, **d} for n, d in WC_TEAMS.items() if d.get("group") == group.upper()]

def cape_verde_group() -> list:
    return get_group("H")

def is_cape_verde(name: str) -> bool:
    return name.lower() == "cape verde"

CAPE_VERDE = get_team("Cape Verde")

def cv_multiplier(player_team: str, opponent_rank: int, stage: str = "group") -> float:
    """Boost CV players in important matches."""
    if player_team.lower() != "cape verde":
        return 1.0
    if opponent_rank > 0 and opponent_rank < 20:
        return 1.15
    if "knockout" in stage.lower():
        return 1.10
    return 1.05