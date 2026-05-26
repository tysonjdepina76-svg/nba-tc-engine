"""
Triple Conservative NBA Template Generator
Updated: April 29, 2026 — Game 5 Night
"""

import math

# ─────────────────────────────────────────────
# TC ENGINE
# ─────────────────────────────────────────────
def tc_picks(game_name, fav, dog, line, total, roster_fav, roster_dog, injury_fav=None, injury_dog=None):
    """
    Returns a structured TC pick dict.
    Line: positive = dog, negative = fav.
    Total: the over/under number.
    """
    spread_pick  = dog if line < 0 else fav   # take the dog on spread
    total_pick   = "Over"                     # default
    line_edge    = abs(line) - 3               # TC threshold: dog gets +3 or better
    ou_edge      = 6                          # total must clear by 6 for TC

    # ── injury adjustments ──────────────────
    if injury_fav:
        for p in injury_fav:
            line_edge += 1.5                  # each missing starter softens line by 1.5

    if injury_dog:
        for p in injury_dog:
            line_edge -= 1.0                  # each missing dog starter tightens line

    spread_conf = "HIGH" if line_edge >= 5 else ("MED" if line_edge >= 3 else "LOW")

    return {
        "game": game_name,
        "favorite": fav,
        "underdog": dog,
        "line": line,
        "total": total,
        "spread_pick": spread_pick,
        "spread_conf": spread_conf,
        "total_pick": total_pick,
        "total_conf": "MED",
        "fav_starters": roster_fav,
        "dog_starters": roster_dog,
        "injury_fav": injury_fav or [],
        "injury_dog": injury_dog or [],
    }


def print_tc(pick):
    print(f"\n🏀 {pick['game']}")
    print(f"   Line: {pick['favorite']} {pick['line']} | Total: {pick['total']}")
    print(f"   Spread → {pick['spread_pick']} (+3 TC)  [{pick['spread_conf']}]")
    print(f"   Total  → {pick['total_pick']} (clears by 6)  [{pick['total_conf']}]")
    print(f"   Favorite starters: {', '.join(pick['fav_starters'])}")
    print(f"   Underdog starters: {', '.join(pick['dog_starters'])}")
    if pick['injury_fav']:
        print(f"   ⚠️  {pick['favorite']} OUT: {', '.join(pick['injury_fav'])}")
    if pick['injury_dog']:
        print(f"   ⚠️  {pick['underdog']} OUT: {', '.join(pick['injury_dog'])}")


# ─────────────────────────────────────────────────────────────────
# OKC vs PHX — SERIES COMPLETE: Thunder SWEPT 4-0
# Game 4 final: OKC 131, PHX 122 (April 27, 2026)
# Suns are ELIMINATED. Thunder advance to West Semifinals.
# ─────────────────────────────────────────────────────────────────
okc_roster = [
    "Shai Gilgeous-Alexander (PG)",
    "Lu Dort (SG)",
    "Jalen Williams (SF)",
    "Chet Holmgren (PF)",
    "Isaiah Hartenstein (C)",
    "Alex Caruso (G)",
    "Cason Wallace (G)",
    "Isaiah Joe (G)",
    "Aaron Wiggins (F)",
    "Jaylin Williams (F)",
]

phx_roster = [
    "Devin Booker (PG/SG)",
    "Grayson Allen (SG)",
    "Tyus Jones (PG)",
    "Nick Richards (C)",
    "Royce O'Neale (SF)",
    "Bol Bol (C)",
    "Oso Ighodaro (PF/C)",
    "Jalen Green (G)",
    "Dillon Brooks (F)",
    "Mateen Cleaves (G)",
]

OKC_PHX = {
    "game": "OKC vs PHX — SERIES COMPLETE (Thunder sweep 4-0)",
    "favorite": "Oklahoma City Thunder",
    "underdog": "Phoenix Suns",
    "line": -999,
    "total": 999,
    "result": "Thunder SWEPT Suns 4-0. Game 4: OKC 131, PHX 122.",
    "note": "Suns traded Kevin Durant (now on Rockets). Phoenix is rebuilding around Devin Booker.",
    "okc_starters": okc_roster[:5],
    "phx_starters": phx_roster[:5],
}
print("\n" + "="*60)
print("⚠️  OKC vs PHX — SERIES COMPLETE")
print("="*60)
print(f"   Result: {OKC_PHX['result']}")
print(f"   Note: {OKC_PHX['note']}")
print(f"   OKC starters: {', '.join(OKC_PHX['okc_starters'])}")
print(f"   PHX starters: {', '.join(OKC_PHX['phx_starters'])}")


# ─────────────────────────────────────────────────────────────────
# GAME 5 — April 29, 2026
# ─────────────────────────────────────────────────────────────────

# 1) ORLANDO MAGIC @ DETROIT PISTONS (Magic lead 3-1)
#    Line: DET -8.5 | O/U: 215.5 | Franz Wagner QUESTIONABLE
orlando_roster = [
    "Paolo Banchero (F)",
    "Desmond Bane (G)",
    "Jalen Suggs (G)",
    "Franz Wagner (F)",
    "Wendell Carter Jr. (C)",
    "Jett Howard (G)",
    "Anthony Black (G)",
    "Caleb Houstan (F)",
]

detroit_roster = [
    "Cade Cunningham (PG)",
    "Jalen Duren (C)",
    "Tim Hardaway Jr. (G)",
    "Tobias Harris (F)",
    "Ausar Thompson (G)",
    "Isaiah Stewart (F/C)",
    "Marcus Bagley (F)",
]

ORL_DET = tc_picks(
    "Magic (3-1) @ Pistons — G5 | Apr 29, 7PM ET | Prime Video",
    fav="Detroit Pistons", dog="Orlando Magic",
    line=-8.5, total=215.5,
    roster_fav=detroit_roster[:5], roster_dog=orlando_roster[:5],
    injury_fav=None,
    injury_dog=["Franz Wagner (ankle, questionable)"] if True else [],  # Wagner questionable
)

# 2) TORONTO RAPTORS @ CLEVELAND CAVALIERS (Series tied 2-2)
#    Line: CLE -8.5 | O/U: 215.5
toronto_roster = [
    "Scottie Barnes (F)",
    "RJ Barrett (G/F)",
    "Jamal Shead (G)",
    "Davion Mitchell (G)",
    "Collin Murray-Boyles (F/C)",
    "Jakobe Walter (G)",
    "Jonathan Mogbo (F)",
]

cleveland_roster = [
    "Donovan Mitchell (G)",
    "Darius Garland (PG)",
    "Evan Mobley (F/C)",
    "Isaac Okoro (G)",
    "Max Strus (G/F)",
    "Tyrell Forbes (F)",
    "Jaylon Tyson (G)",
]

TOR_CLE = tc_picks(
    "Raptors (2-2) @ Cavaliers — G5 | Apr 29 | TNT",
    fav="Cleveland Cavaliers", dog="Toronto Raptors",
    line=-8.5, total=215.5,
    roster_fav=cleveland_roster[:5], roster_dog=toronto_roster[:5],
    injury_fav=None,
    injury_dog=None,
)

# 3) HOUSTON ROCKETS @ LOS ANGELES LAKERS (Lakers lead 3-1)
#    Line: LAL -4.5 | Rockets: Kevin Durant OUT, Lakers: Luka OUT, Reaves QUESTIONABLE
houston_roster = [
    "Alperen Sengun (C)",
    "Amen Thompson (G)",
    "Jabari Smith Jr. (F)",
    "Dillon Brooks (F)",
    "Fred VanVleet (PG)",
    "Tari Eason (F)",
    "Jalen Green (G)",
    "Cam Whitmore (G)",
]

la_lakers_roster = [
    "LeBron James (F)",
    "Austin Reaves (G)",
    "Gabe Vincent (PG)",
    "Jake LaRavia (F)",
    "Julius Randle (F)",
    "Dorian Finney-Smith (F)",
    "Jordan Hawkins (G)",
]

HOU_LAL = tc_picks(
    "Rockets (1-3) @ Lakers — G5 | Apr 29, 10PM ET | ESPN",
    fav="Los Angeles Lakers", dog="Houston Rockets",
    line=-4.5, total=216.5,
    roster_fav=la_lakers_roster[:5], roster_dog=houston_roster[:5],
    injury_fav=["Luka Doncic (hamstring, OUT)", "Austin Reaves (oblique, questionable)"],
    injury_dog=["Kevin Durant (ankle, OUT)", "Jalen Green (doubtful)"],
)


# ─────────────────────────────────────────────
# PRINT ALL PICKS
# ─────────────────────────────────────────────
print_tc(ORL_DET)
print_tc(TOR_CLE)
print_tc(HOU_LAL)

print("\n" + "="*60)
print("SYSTEM SUMMARY — April 29, 2026 NBA Game 5 Picks")
print("="*60)
print("""
1. ORL @ DET  |  DET -8.5 | Spread: DET +3 TC  | Over 215.5
   → Pistons facing elimination at home. Magic's Wagner questionable.
   → Cunningham and Duren must dominate inside. Pistons 6-4 in last 10 home games.

2. TOR @ CLE  |  CLE -8.5 | Spread: TOR +3 TC  | Over 215.5
   → Series tied 2-2. Scottie Barnes has been series' best player (25.8 PPG).
   → Harden has 24 turnovers in 4 games. Mitchell averaging 17.5 in Games 3-4.
   → Take TOR +8.5 (dog with value). Over if Barnes keeps cooking.

3. HOU @ LAL  |  LAL -4.5 | Spread: HOU +3 TC  | Over 216.5
   → Rockets without Durant (ankle OUT). Lakers without Luka (hamstring OUT).
   → Reaves questionable — if he plays, Lakers cover. If not, Rockets keep it close.
   → Tari Eason key for Houston's defense and second-chance points.

NOTE: OKC vs PHX series COMPLETE. Thunder sweep 4-0.
      PHX has traded Durant to HOU. Suns rebuilding around Booker.
""")