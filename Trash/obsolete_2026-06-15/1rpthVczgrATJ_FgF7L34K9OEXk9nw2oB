#!/usr/bin/env python3
"""
WNBA TC ROSTER PROJECTIONS — Full Player Stats
===============================================
TC = PTS×0.85 + REB×0.12 + AST×0.10 + 3PM×0.08
Line = PTS×0.88
Edge = TC - Line
"""
import json

# ─── WNBA ROSTERS — 2026 Season ─────────────────────────────────────────────────

MIN = {  # Minnesota Lynx
    "Napheesa Collier":      {"pos":"F","ht":"6-1", "pts":21.8,"reb":8.5,"ast":3.2,"tpm":1.5},
    "Kayla McBride":         {"pos":"G","ht":"5-11","pts":14.5,"reb":2.8,"ast":2.5,"tpm":2.2},
    "Diamond Miller":        {"pos":"G","ht":"6-1", "pts":12.3,"reb":4.2,"ast":2.8,"tpm":1.1},
    "Alanna Smith":          {"pos":"F","ht":"6-4", "pts":9.8, "reb":5.5,"ast":1.8,"tpm":0.8},
    "Jessica Shepard":       {"pos":"F","ht":"6-4", "pts":7.2, "reb":6.8,"ast":2.2,"tpm":0.3},
    # Bench
    "Rachel Banham":         {"pos":"G","ht":"5-9", "pts":6.5, "reb":1.5,"ast":1.8,"tpm":1.2},
    "Dorka Juhász":          {"pos":"C","ht":"6-5", "pts":5.8, "reb":5.2,"ast":1.0,"tpm":0.2},
    "Bridget Carleton":      {"pos":"G","ht":"6-1", "pts":4.5, "reb":2.0,"ast":1.2,"tpm":0.8},
    "Temi Fagbenle":         {"pos":"C","ht":"6-4", "pts":3.8, "reb":3.5,"ast":0.5,"tpm":0.0},
}

DAL = {  # Dallas Wings
    "Arike Ogunbowale":      {"pos":"G","ht":"5-8", "pts":22.5,"reb":4.0,"ast":4.2,"tpm":2.8},
    "Satou Sabally":         {"pos":"F","ht":"6-4", "pts":17.8,"reb":7.2,"ast":3.5,"tpm":2.0},
    "Natasha Howard":        {"pos":"F","ht":"6-2", "pts":14.2,"reb":6.8,"ast":1.8,"tpm":0.9},
    "Teaira McCowan":        {"pos":"C","ht":"6-7", "pts":10.5,"reb":8.8,"ast":0.8,"tpm":0.0},
    "Jacy Sheldon":          {"pos":"G","ht":"5-11","pts":8.5, "reb":2.2,"ast":3.0,"tpm":1.5},
    # Bench
    "Maddy Siegrist":        {"pos":"F","ht":"6-1", "pts":7.2, "reb":3.5,"ast":1.0,"tpm":0.8},
    "Kalani Brown":          {"pos":"C","ht":"6-7", "pts":5.5, "reb":4.2,"ast":0.5,"tpm":0.0},
    "Sevval Gül":            {"pos":"G","ht":"5-11","pts":3.8, "reb":1.5,"ast":1.2,"tpm":0.6},
    "Tyasha Harris":         {"pos":"G","ht":"5-9", "pts":3.2, "reb":1.2,"ast":2.5,"tpm":0.5},
}

NY = {  # New York Liberty
    "Breanna Stewart":       {"pos":"F","ht":"6-4", "pts":22.5,"reb":9.1,"ast":3.8,"tpm":1.8},
    "Sabrina Ionescu":       {"pos":"G","ht":"5-11","pts":18.3,"reb":5.5,"ast":6.2,"tpm":3.1},
    "Jonquel Jones":         {"pos":"C","ht":"6-6", "pts":15.0,"reb":8.8,"ast":2.0,"tpm":1.2},
    "Betnijah Laney":        {"pos":"G","ht":"6-0", "pts":12.7,"reb":4.0,"ast":3.0,"tpm":1.6},
    "Courtney Vandersloot":  {"pos":"G","ht":"5-9", "pts":8.9, "reb":3.0,"ast":7.1,"tpm":1.1},
    # Bench
    "Marine Johannès":       {"pos":"G","ht":"5-11","pts":6.5, "reb":1.8,"ast":2.2,"tpm":1.5},
    "Nyara Sabally":         {"pos":"F","ht":"6-5", "pts":5.2, "reb":3.5,"ast":0.8,"tpm":0.3},
    "Kayla Thornton":        {"pos":"F","ht":"6-1", "pts":4.8, "reb":2.8,"ast":1.0,"tpm":0.5},
    "Stefanie Dolson":       {"pos":"C","ht":"6-5", "pts":4.2, "reb":2.5,"ast":1.2,"tpm":0.4},
}

POR = {  # Portland Fire
    "Satie Betschidze":      {"pos":"G","ht":"5-10","pts":15.2,"reb":3.5,"ast":4.5,"tpm":2.0},
    "Ruth Hamblin":          {"pos":"C","ht":"6-6", "pts":12.5,"reb":8.2,"ast":1.5,"tpm":0.5},
    "Astou Traoré":          {"pos":"F","ht":"6-2", "pts":11.8,"reb":6.0,"ast":2.0,"tpm":1.0},
    "Yderis Rivas":          {"pos":"G","ht":"5-9", "pts":10.5,"reb":2.8,"ast":3.8,"tpm":1.8},
    "Emma Cannon":           {"pos":"F","ht":"6-1", "pts":9.2, "reb":5.5,"ast":1.5,"tpm":0.8},
    # Bench
    "Talia Henderson":       {"pos":"G","ht":"5-11","pts":6.8, "reb":2.2,"ast":2.0,"tpm":1.2},
    "Megan Gustafson":       {"pos":"C","ht":"6-3", "pts":5.5, "reb":4.0,"ast":0.8,"tpm":0.3},
    "Amanda Zahui B.":       {"pos":"F","ht":"6-5", "pts":4.8, "reb":3.2,"ast":0.5,"tpm":0.4},
    "Tiffany Hayes":         {"pos":"G","ht":"5-10","pts":7.5, "reb":2.5,"ast":1.8,"tpm":1.0},
}

TEAMS = {"MIN": MIN, "DAL": DAL, "NY": NY, "POR": POR}

# ─── TC CALCULATIONS ────────────────────────────────────────────────────────────

CONS = 0.85
LINE_F = 0.88

def calc_tc(p):
    pts = p["pts"] * CONS
    reb = p["reb"] * 0.12
    ast = p["ast"] * 0.10
    tpm = p["tpm"] * 0.08
    return round(pts + reb + ast + tpm, 1)

def calc_line(p):
    return round(p["pts"] * LINE_F)

def calc_edge(p):
    return round(calc_tc(p) - calc_line(p), 1)

# ─── PRINT ROSTER ──────────────────────────────────────────────────────────────

def print_roster(team_name, roster, starters=5):
    print(f"\n{'='*80}")
    print(f" {team_name}")
    print(f"{'='*80}")
    print(f"{'Player':<24} {'POS':<4} {'HT':<5} {'PTS':>6} {'REB':>5} {'AST':>5} {'3PM':>5} {'TC':>6} {'LINE':>6} {'EDGE':>7}")
    print(f"{'-'*80}")
    
    team_tc = 0
    team_pts = 0
    team_reb = 0
    team_ast = 0
    team_tpm = 0
    
    items = list(roster.items())
    for i, (name, p) in enumerate(items):
        tc = calc_tc(p)
        line = calc_line(p)
        edge = calc_edge(p)
        
        team_tc += tc
        team_pts += p["pts"] * CONS
        team_reb += p["reb"] * 0.12
        team_ast += p["ast"] * 0.10
        team_tpm += p["tpm"] * 0.08
        
        role = "START" if i < starters else "BENCH"
        print(f"{name:<24} {p['pos']:<4} {p['ht']:<5} {p['pts']:>6.1f} {p['reb']:>5.1f} {p['ast']:>5.1f} {p['tpm']:>5.1f} {tc:>6.1f} {line:>6.0f} {edge:>+7.1f}")
    
    print(f"{'-'*80}")
    print(f"{'TEAM TOTALS':<24} {'':<9} {team_pts:>6.1f} {team_reb:>5.1f} {team_ast:>5.1f} {team_tpm:>5.1f} {team_tc:>6.1f}")
    
    return team_tc

# ─── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" WNBA TC ROSTER PROJECTIONS — MAY 14, 2026")
    print("="*80)
    print(" TC = PTS×0.85 + REB×0.12 + AST×0.10 + 3PM×0.08 | Line = PTS×0.88 | Edge = TC - Line")
    
    # Game 1: MIN @ DAL
    print(f"\n{'#'*80}")
    print(f"# GAME 1: MINNESOTA LYNX @ DALLAS WINGS")
    print(f"# Total: 178.5 | Spread: DAL -4.5 | 8:00 PM ET")
    print(f"{'#'*80}")
    
    min_tc = print_roster("MINNESOTA LYNX (Away)", MIN)
    dal_tc = print_roster("DALLAS WINGS (Home)", DAL)
    
    print(f"\n{'='*80}")
    print(f" TC SYSTEM SUMMARY — MIN @ DAL")
    print(f"{'='*80}")
    print(f" MIN TC: {min_tc:.1f}")
    print(f" DAL TC: {dal_tc:.1f}")
    print(f" TC Combined: {min_tc + dal_tc:.1f}")
    print(f" Market Total: 178.5")
    print(f" Edge: {(min_tc + dal_tc) - 178.5:+.1f}")
    print(f" Signal: {'UNDER' if (min_tc + dal_tc) < 178.5 else 'OVER'}")
    
    # Game 2: NY @ POR
    print(f"\n{'#'*80}")
    print(f"# GAME 2: NEW YORK LIBERTY @ PORTLAND FIRE")
    print(f"# Total: 176.5 | Spread: NY -11.5 | 10:00 PM ET")
    print(f"{'#'*80}")
    
    ny_tc = print_roster("NEW YORK LIBERTY (Away)", NY)
    por_tc = print_roster("PORTLAND FIRE (Home)", POR)
    
    print(f"\n{'='*80}")
    print(f" TC SYSTEM SUMMARY — NY @ POR")
    print(f"{'='*80}")
    print(f" NY TC: {ny_tc:.1f}")
    print(f" POR TC: {por_tc:.1f}")
    print(f" TC Combined: {ny_tc + por_tc:.1f}")
    print(f" Market Total: 176.5")
    print(f" Edge: {(ny_tc + por_tc) - 176.5:+.1f}")
    print(f" Signal: {'UNDER' if (ny_tc + por_tc) < 176.5 else 'OVER'}")
    
    print(f"\n{'='*80}")
    print(" END WNBA TC ROSTER PROJECTIONS")
    print(f"{'='*80}\n")
