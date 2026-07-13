from sources.scrapers.soccer_roster_wiki import fetch_team_roster

POSITION_PROJ = {
    "F":  {"goals": 0.55, "assists": 0.25, "shots": 2.4, "sot": 1.1, "passes": 28, "tackles": 0.8, "fouls": 1.0},
    "M":  {"goals": 0.20, "assists": 0.30, "shots": 1.0, "sot": 0.4, "passes": 55, "tackles": 2.2, "fouls": 1.4},
    "D":  {"goals": 0.05, "assists": 0.10, "shots": 0.3, "sot": 0.1, "passes": 60, "tackles": 2.8, "fouls": 1.3},
    "G":  {"goals": 0.00, "assists": 0.00, "shots": 0.0, "sot": 0.0, "passes": 35, "tackles": 0.0, "fouls": 0.0, "saves": 3.2},
}


def get_player_projections(team: str) -> list:
    players = fetch_team_roster(team)
    for p in players:
        pos = p.get("position", "M")
        base = POSITION_PROJ.get(pos, POSITION_PROJ["M"])
        p.update(base)
    return players
