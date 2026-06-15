#!/usr/bin/env python3
"""
WNBA TC PROP PROJECTIONS v2
==========================
TC = stat × 0.85 (conservative projection)
Line = stat × 0.88 (market approximation)
Signal: OVER if TC > Line, UNDER if TC < Line
"""

CONS = 0.85
LINE_F = 0.88

# All players with projections
players = {
    # MIN @ DAL
    ("MIN", "Napheesa Collier", "F"): {"pts": 21.8, "reb": 8.5, "ast": 3.2, "3pm": 1.5},
    ("MIN", "Kayla McBride", "G"): {"pts": 14.5, "reb": 2.8, "ast": 2.5, "3pm": 2.2},
    ("MIN", "Diamond Miller", "G"): {"pts": 12.3, "reb": 4.2, "ast": 2.8, "3pm": 1.1},
    ("MIN", "Alanna Smith", "F"): {"pts": 9.8, "reb": 5.5, "ast": 1.8, "3pm": 0.8},
    ("MIN", "Jessica Shepard", "F"): {"pts": 7.2, "reb": 6.8, "ast": 2.2, "3pm": 0.3},
    ("DAL", "Arike Ogunbowale", "G"): {"pts": 22.5, "reb": 4.0, "ast": 4.2, "3pm": 2.8},
    ("DAL", "Satou Sabally", "F"): {"pts": 17.8, "reb": 7.2, "ast": 3.5, "3pm": 2.0},
    ("DAL", "Natasha Howard", "F"): {"pts": 14.2, "reb": 6.8, "ast": 1.8, "3pm": 0.9},
    ("DAL", "Teaira McCowan", "C"): {"pts": 10.5, "reb": 8.8, "ast": 0.8, "3pm": 0.0},
    ("DAL", "Jacy Sheldon", "G"): {"pts": 8.5, "reb": 2.2, "ast": 3.0, "3pm": 1.5},
    # NY @ POR
    ("NY", "Breanna Stewart", "F"): {"pts": 22.5, "reb": 9.1, "ast": 3.8, "3pm": 1.8},
    ("NY", "Sabrina Ionescu", "G"): {"pts": 18.3, "reb": 5.5, "ast": 6.2, "3pm": 3.1},
    ("NY", "Jonquel Jones", "C"): {"pts": 15.0, "reb": 8.8, "ast": 2.0, "3pm": 1.2},
    ("NY", "Betnijah Laney", "G"): {"pts": 12.7, "reb": 4.0, "ast": 3.0, "3pm": 1.6},
    ("NY", "Courtney Vandersloot", "G"): {"pts": 8.9, "reb": 3.0, "ast": 7.1, "3pm": 1.1},
    ("POR", "Satie Betschidze", "G"): {"pts": 15.2, "reb": 3.5, "ast": 4.5, "3pm": 2.0},
    ("POR", "Ruth Hamblin", "C"): {"pts": 12.5, "reb": 8.2, "ast": 1.5, "3pm": 0.5},
    ("POR", "Astou Traoré", "F"): {"pts": 11.8, "reb": 6.0, "ast": 2.0, "3pm": 1.0},
    ("POR", "Yderis Rivas", "G"): {"pts": 10.5, "reb": 2.8, "ast": 3.8, "3pm": 1.8},
    ("POR", "Emma Cannon", "F"): {"pts": 9.2, "reb": 5.5, "ast": 1.5, "3pm": 0.8},
}

print("="*80)
print("  WNBA TC PROP PROJECTIONS — MAY 14, 2026")
print("="*80)
print(f"  Formula: TC = stat × {CONS} | Line = stat × {LINE_F}")
print("  Signal: OVER if TC > Line | UNDER if TC < Line")
print("="*80)

# Group by game
games = {
    "GAME 1: MIN @ DAL": [("MIN", "MINNESOTA LYNX"), ("DAL", "DALLAS WINGS")],
    "GAME 2: NY @ POR": [("NY", "NEW YORK LIBERTY"), ("POR", "PORTLAND FIRE")],
}

for game_title, teams in games.items():
    print(f"\n{game_title}")
    print("="*80)
    
    for abbr, team_name in teams:
        print(f"\n  {team_name}")
        print("-"*80)
        print(f"{'Player':<22} {'Prop':<6} {'AVG':>5} {'TC':>6} {'Line':>5} {'Signal':>8}")
        print("-"*80)
        
        for (team, player, pos), stats in players.items():
            if team != abbr:
                continue
            
            for prop_name, stat_key in [("PTS", "pts"), ("REB", "reb"), ("AST", "ast"), ("3PM", "3pm")]:
                avg = stats[stat_key]
                tc = round(avg * CONS, 1)
                line = round(avg * LINE_F)
                
                # Determine signal
                if tc > line:
                    signal = "OVER"
                elif tc < line:
                    signal = "UNDER"
                else:
                    signal = "PUSH"
                
                print(f"{player:<22} {prop_name:<6} {avg:>5.1f} {tc:>6.1f} {line:>5} {signal:>8}")
            print("-"*80)

# Top prop plays
print("\n" + "="*80)
print("  TOP PROP PLAYS — STRONGEST SIGNALS")
print("="*80)

prop_plays = []
for (team, player, pos), stats in players.items():
    for prop_name, stat_key in [("PTS", "pts"), ("REB", "reb"), ("AST", "ast"), ("3PM", "3pm")]:
        avg = stats[stat_key]
        tc = round(avg * CONS, 1)
        line = round(avg * LINE_F)
        edge = round(tc - line, 1)
        
        if edge > 0:
            signal = "OVER"
            strength = edge
        elif edge < 0:
            signal = "UNDER"
            strength = abs(edge)
        else:
            continue
        
        prop_plays.append((team, player, prop_name, avg, tc, line, signal, strength))

# Sort by strength
prop_plays.sort(key=lambda x: x[7], reverse=True)

print(f"\n{'Team':<5} {'Player':<20} {'Prop':<6} {'TC':>5} {'Line':>5} {'Signal':>7} {'Edge':>5}")
print("-"*80)

for team, player, prop, avg, tc, line, signal, strength in prop_plays[:12]:
    edge_str = f"+{tc-line:.1f}" if tc > line else f"{tc-line:.1f}"
    print(f"{team:<5} {player:<20} {prop:<6} {tc:>5.1f} {line:>5} {signal:>7} {edge_str:>5}")

print("\n" + "="*80)
