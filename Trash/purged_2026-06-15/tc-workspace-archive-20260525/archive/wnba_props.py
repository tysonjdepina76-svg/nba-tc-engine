#!/usr/bin/env python3
"""
WNBA TC PROP PROJECTIONS
=======================
Formula: TC = stat × 0.85 | Line = stat × 0.88 | Edge = TC - Line
"""

# MIN @ DAL Players with multi-stat projections
min_players = {
    "Napheesa Collier": {"pts": 21.8, "reb": 8.5, "ast": 3.2, "3pm": 1.5, "pos": "F"},
    "Kayla McBride": {"pts": 14.5, "reb": 2.8, "ast": 2.5, "3pm": 2.2, "pos": "G"},
    "Diamond Miller": {"pts": 12.3, "reb": 4.2, "ast": 2.8, "3pm": 1.1, "pos": "G"},
    "Alanna Smith": {"pts": 9.8, "reb": 5.5, "ast": 1.8, "3pm": 0.8, "pos": "F"},
    "Jessica Shepard": {"pts": 7.2, "reb": 6.8, "ast": 2.2, "3pm": 0.3, "pos": "F"},
    "Rachel Banham": {"pts": 6.5, "reb": 1.5, "ast": 1.8, "3pm": 1.2, "pos": "G"},
    "Dorka Juhász": {"pts": 5.8, "reb": 5.2, "ast": 1.0, "3pm": 0.2, "pos": "C"},
    "Bridget Carleton": {"pts": 4.5, "reb": 2.0, "ast": 1.2, "3pm": 0.8, "pos": "G"},
}

dal_players = {
    "Arike Ogunbowale": {"pts": 22.5, "reb": 4.0, "ast": 4.2, "3pm": 2.8, "pos": "G"},
    "Satou Sabally": {"pts": 17.8, "reb": 7.2, "ast": 3.5, "3pm": 2.0, "pos": "F"},
    "Natasha Howard": {"pts": 14.2, "reb": 6.8, "ast": 1.8, "3pm": 0.9, "pos": "F"},
    "Teaira McCowan": {"pts": 10.5, "reb": 8.8, "ast": 0.8, "3pm": 0.0, "pos": "C"},
    "Jacy Sheldon": {"pts": 8.5, "reb": 2.2, "ast": 3.0, "3pm": 1.5, "pos": "G"},
    "Maddy Siegrist": {"pts": 7.2, "reb": 3.5, "ast": 1.0, "3pm": 0.8, "pos": "F"},
    "Kalani Brown": {"pts": 5.5, "reb": 4.2, "ast": 0.5, "3pm": 0.0, "pos": "C"},
    "Sevval Gül": {"pts": 3.8, "reb": 1.5, "ast": 1.2, "3pm": 0.6, "pos": "G"},
}

# NY @ POR Players
ny_players = {
    "Breanna Stewart": {"pts": 22.5, "reb": 9.1, "ast": 3.8, "3pm": 1.8, "pos": "F"},
    "Sabrina Ionescu": {"pts": 18.3, "reb": 5.5, "ast": 6.2, "3pm": 3.1, "pos": "G"},
    "Jonquel Jones": {"pts": 15.0, "reb": 8.8, "ast": 2.0, "3pm": 1.2, "pos": "C"},
    "Betnijah Laney": {"pts": 12.7, "reb": 4.0, "ast": 3.0, "3pm": 1.6, "pos": "G"},
    "Courtney Vandersloot": {"pts": 8.9, "reb": 3.0, "ast": 7.1, "3pm": 1.1, "pos": "G"},
    "Marine Johannès": {"pts": 6.5, "reb": 1.8, "ast": 2.2, "3pm": 1.5, "pos": "G"},
    "Nyara Sabally": {"pts": 5.2, "reb": 3.5, "ast": 0.8, "3pm": 0.3, "pos": "F"},
    "Kayla Thornton": {"pts": 4.8, "reb": 2.8, "ast": 1.0, "3pm": 0.5, "pos": "F"},
}

por_players = {
    "Satie Betschidze": {"pts": 15.2, "reb": 3.5, "ast": 4.5, "3pm": 2.0, "pos": "G"},
    "Ruth Hamblin": {"pts": 12.5, "reb": 8.2, "ast": 1.5, "3pm": 0.5, "pos": "C"},
    "Astou Traoré": {"pts": 11.8, "reb": 6.0, "ast": 2.0, "3pm": 1.0, "pos": "F"},
    "Yderis Rivas": {"pts": 10.5, "reb": 2.8, "ast": 3.8, "3pm": 1.8, "pos": "G"},
    "Emma Cannon": {"pts": 9.2, "reb": 5.5, "ast": 1.5, "3pm": 0.8, "pos": "F"},
    "Talia Henderson": {"pts": 6.8, "reb": 2.2, "ast": 2.0, "3pm": 1.2, "pos": "G"},
    "Megan Gustafson": {"pts": 5.5, "reb": 4.0, "ast": 0.8, "3pm": 0.3, "pos": "C"},
    "Amanda Zahui B.": {"pts": 4.8, "reb": 3.2, "ast": 0.5, "3pm": 0.4, "pos": "F"},
}

CONS = 0.85
LINE_F = 0.88

def calc_props(player_name, stats):
    """Calculate TC prop projections for all stat categories"""
    props = []
    
    # Points prop
    pts_tc = round(stats["pts"] * CONS, 1)
    pts_line = round(stats["pts"] * LINE_F)
    pts_edge = round(pts_tc - pts_line, 1)
    props.append(("PTS", stats["pts"], pts_tc, pts_line, pts_edge))
    
    # Rebounds prop
    reb_tc = round(stats["reb"] * CONS, 1)
    reb_line = round(stats["reb"] * LINE_F, 1)
    reb_edge = round(reb_tc - reb_line, 1)
    props.append(("REB", stats["reb"], reb_tc, reb_line, reb_edge))
    
    # Assists prop
    ast_tc = round(stats["ast"] * CONS, 1)
    ast_line = round(stats["ast"] * LINE_F, 1)
    ast_edge = round(ast_tc - ast_line, 1)
    props.append(("AST", stats["ast"], ast_tc, ast_line, ast_edge))
    
    # 3PM prop
    tpm_tc = round(stats["3pm"] * CONS, 1)
    tpm_line = round(stats["3pm"] * LINE_F, 1)
    tpm_edge = round(tpm_tc - tpm_line, 1)
    props.append(("3PM", stats["3pm"], tpm_tc, tpm_line, tpm_edge))
    
    return props

def print_props_table(team_name, players):
    print(f"\n{'='*75}")
    print(f"  {team_name}")
    print(f"{'='*75}")
    print(f"{'Player':<22} {'PROP':<5} {'AVG':>5} {'TC':>6} {'LINE':>5} {'EDGE':>7}")
    print(f"{'-'*75}")
    
    for player, stats in players.items():
        props = calc_props(player, stats)
        for i, (prop_type, avg, tc, line, edge) in enumerate(props):
            if i == 0:
                print(f"{player:<22} {prop_type:<5} {avg:>5.1f} {tc:>6.1f} {line:>5} {edge:>+7.1f}")
            else:
                print(f"{'':<22} {prop_type:<5} {avg:>5.1f} {tc:>6.1f} {line:>5} {edge:>+7.1f}")
        print(f"{'-'*75}")

# Generate prop projections
print("\n" + "="*75)
print("  WNBA TC PROP PROJECTIONS — MAY 14, 2026")
print("  TC = stat × 0.85 | LINE = stat × 0.88 | EDGE = TC - LINE")
print("="*75)

print("\n" + "="*75)
print("  GAME 1: MINNESOTA LYNX @ DALLAS WINGS")
print("="*75)

print_props_table("MINNESOTA LYNX", min_players)
print_props_table("DALLAS WINGS", dal_players)

print("\n" + "="*75)
print("  GAME 2: NEW YORK LIBERTY @ PORTLAND FIRE")
print("="*75)

print_props_table("NEW YORK LIBERTY", ny_players)
print_props_table("PORTLAND FIRE", por_players)

# Top props summary
print("\n" + "="*75)
print("  TOP PROP VALUES — HIGHEST EDGES")
print("="*75)

all_players = [
    ("MIN", min_players),
    ("DAL", dal_players),
    ("NY", ny_players),
    ("POR", por_players),
]

top_props = []
for team, players in all_players:
    for player, stats in players.items():
        props = calc_props(player, stats)
        for prop_type, avg, tc, line, edge in props:
            if edge > 0.5:  # Only show significant edges
                top_props.append((team, player, prop_type, avg, tc, line, edge))

# Sort by edge descending
top_props.sort(key=lambda x: x[6], reverse=True)

print(f"{'TEAM':<5} {'Player':<22} {'PROP':<5} {'TC':>6} {'LINE':>5} {'EDGE':>7}")
print(f"{'-'*75}")
for team, player, prop_type, avg, tc, line, edge in top_props[:15]:
    print(f"{team:<5} {player:<22} {prop_type:<5} {tc:>6.1f} {line:>5} {edge:>+7.1f}")

print("\n" + "="*75)
