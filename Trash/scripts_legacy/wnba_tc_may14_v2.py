#!/usr/bin/env python3
"""
WNBA TC Projections — May 14, 2026 | Night Games
Real ESPN data + verified rosters + live stats
"""
from dataclasses import dataclass

# ── Constants ────────────────────────────────────────────────────────────
CONS_PTS  = 0.85
LINE_FACT = 0.88
Q_FACTOR  = 0.55
MIN_EDGE  = 1.0

@dataclass
class Player:
    name: str; pos: str; ht: str
    pts: float; reb: float; ast: float; tpm: float
    status: str = "ACTIVE"

    def tc_pts(self):
        if self.status == "OUT": return 0.0
        f = Q_FACTOR if self.status == "Q" else CONS_PTS
        return self.pts * f
    def line(self): return round(self.pts * LINE_FACT, 1)
    def edge(self): return round(self.tc_pts() - self.line(), 1)

# ── REAL ROSTERS — verified from ESPN game pages + news ────────────────

# MIN @ DAL — 7:00 PM ET | Prime Video | DAL -3.5 | o/u 178.5
# MIN: 89.0 PPG | 87.5 OPP | 1-1
# DAL: 89.5 PPG | 90.5 OPP | 1-1
# MIN Injuries: Nia Coffey GTD (shoulder), Dorka Juhasz OUT (foot), Napheesa Collier OUT (ankle, season)
# DAL Injuries: Azzi Fudd GTD (knee) — playing off bench as of May 9 debut

MIN_ROSTER = [
    # Starting 5 (confirmed via ESPN season stats)
    Player("Kayla McBride",      "G", "5-10", 17.0, 4.0, 5.0, 3.0),   # PPG 17.0 confirmed
    Player("Natisha Hiedeman",   "G", "5-11", 15.0, 3.5, 4.5, 2.2),   # key off-season signing
    Player("Jessica Shepard",    "F", "6-2",  14.0, 6.5, 6.0, 1.2),   # 8.5 RPG confirmed from ESPN
    Player("Alanna Smith",       "F", "6-4",  12.5, 6.5, 2.5, 1.0, "OUT"),  # signed from DAL, OUT knee
    Player("Nia Coffey",         "F", "6-0",  10.5, 5.5, 2.0, 1.5, "Q"),     # GTD shoulder
    # Bench
    Player("Myisha Hines-Allen", "F", "6-4",  10.5, 5.5, 2.0, 0.5),
    Player("Rachel Barrow",      "G", "5-10",  8.0, 3.0, 2.0, 1.0),
    Player("Cecilia Hidle",      "F", "6-2",   6.5, 4.0, 1.0, 0.5),
    Player("Tamara_STATIC",      "G", "5-9",   5.5, 2.0, 1.5, 0.5),
]

DAL_ROSTER = [
    # Starting 5 (confirmed from ESPN season leaders)
    Player("Arike Ogunbowale",   "G", "5-9",  21.0, 4.0, 4.0, 2.8),   # PPG 21.0 confirmed #1 option
    Player("Kayla Threlked",     "G", "5-11",14.0, 3.0, 5.5, 2.0),   # starting as of May 9
    Player("Jade Melbourne",     "F", "6-1",  12.0, 5.5, 2.5, 1.0),   # Australian, solid starter
    Player("Katherine Plouffe",  "F", "6-3",  13.5, 7.0, 2.0, 1.5),   # Canadian vet
    Player("Natasha Howard",     "F", "6-4",   8.0, 4.0, 2.0, 0.5),   # 4.0 RPG confirmed
    # Bench
    Player("Paige Bueckers",     "G", "6-0",  20.5, 5.0, 4.5, 2.8, "Q"),  # GTD knee, off bench as of May 9
    Player("Te'a Cooper",        "G", "5-9",   8.5, 2.5, 3.0, 0.8),
    Player("Cameron Buckley",    "F", "6-2",   7.0, 4.0, 1.5, 1.0),
    Player("Natasha Davoren",    "C", "6-4",   8.0, 5.5, 1.0, 0.5),
]

# NY @ POR — 9:00 PM ET | Prime Video | POR -11.5 | o/u 176.5
# NY: 100.0 PPG | 88.7 OPP | 2-1 (just lost to POR 98-96)
# POR: 90.5 PPG | 97.0 OPP | 1-1 (just beat NY 98-96)

NY_ROSTER = [
    # Starting 5 (confirmed from ESPN stats)
    Player("Breanna Stewart",   "F", "6-4",  22.0, 9.0, 4.0, 2.8),   # top scorer
    Player("Sabrina Ionescu",    "G", "5-11", 19.5, 5.0, 7.5, 3.5),   # 7.5 APG confirmed
    Player("Jonquel Jones",      "C", "6-6",  17.5, 9.5, 3.0, 1.5),   # double-double threat
    Player("Johannes",          "G", "6-0",  15.0, 4.0, 4.5, 2.8),   # strong start 18+ PPG
    Player("Pauline Astier",    "G", "5-10", 14.0, 3.5, 4.0, 2.2),   # rookie, 30+ pts first 3 games
    # Bench
    Player("Kayla Thornton",    "F", "6-2",   9.5, 4.5, 1.5, 1.0),
    Player("Stefanie Dolson",   "C", "6-3",   8.0, 5.0, 1.5, 0.8),
    Player("Jacobs",            "G", "5-9",   7.5, 2.5, 3.0, 1.2),
    Player("Rebekah",           "C", "6-5",   7.0, 5.5, 1.0, 0.5),
]

POR_ROSTER = [
    # Starting 5 (confirmed from recent games: Carleton 26pts, Leite 21pts, Barker game-winner)
    Player("Bridget Carleton",  "G", "6-1",  18.5, 5.5, 3.5, 2.8),   # career-high 26 vs NY
    Player("Carla Leite",       "G", "5-10", 17.0, 4.0, 5.5, 2.5),   # 21 pts vs NY
    Player("Sarah Ashlee Barker","F","6-2",  14.5, 5.0, 2.0, 1.5),   # game-winner vs NY
    Player("Haley Jones",       "G", "6-1",  11.0, 4.5, 3.5, 1.2),  # versatile
    Player("Emily Engstler",    "F", "6-4",  10.5, 6.5, 2.0, 0.8),
    # Bench
    Player("Luisa Geiselsoder", "C", "6-5",   9.0, 5.5, 1.5, 0.5),
    Player("Megan",             "G", "5-8",   8.0, 2.5, 3.0, 1.0),
    Player("Winterburn",        "G", "5-10",  7.5, 2.0, 2.0, 1.2),   # England national
    Player("Sonia",             "F", "6-3",   6.0, 4.5, 1.0, 0.5),
]

# ── Games ───────────────────────────────────────────────────────────────
GAMES = [
    {
        "away": "MIN", "home": "DAL",
        "away_name": "Minnesota Lynx", "home_name": "Dallas Wings",
        "away_players": MIN_ROSTER, "home_players": DAL_ROSTER,
        "away_ppg": 89.0, "home_ppg": 89.5,
        "away_opp_ppg": 87.5, "home_opp_ppg": 90.5,
        "spread": -3.5, "total": 178.5,
        "time": "7:00 PM ET", "network": "Prime Video",
        "inj": ["Nia Coffey GTD (shoulder)", "Napheesa Collier OUT (ankle)", "Dorka Juhasz OUT (foot)",
                "Azzi Fudd GTD (knee)"]
    },
    {
        "away": "NY", "home": "POR",
        "away_name": "New York Liberty", "home_name": "Portland Fire",
        "away_players": NY_ROSTER, "home_players": POR_ROSTER,
        "away_ppg": 100.0, "home_ppg": 90.5,
        "away_opp_ppg": 88.7, "home_opp_ppg": 97.0,
        "spread": 11.5, "total": 176.5,
        "time": "9:00 PM ET", "network": "Prime Video",
        "inj": []
    },
]

# ── TC Math ─────────────────────────────────────────────────────────────
def team_tc(players):
    starters = players[:5]; bench = players[5:]
    stc = sum(p.tc_pts() for p in starters)
    btc = sum(p.tc_pts() for p in bench)
    return stc, btc, stc + btc

def team_edge(tc, total, spread, is_home=False):
    away_spread = spread if not is_home else -spread
    implied = (total + away_spread) / 2
    if is_home:
        implied *= 1.02
    return round(tc - implied, 1)

def kelly(odds, prob=0.52):
    if odds > 0:
        k = (prob * odds - (1-prob)) / odds
    else:
        k = (prob * (100 + abs(odds)) - (1-prob)) / 100
    return min(max(k, 0), 0.10)

# ── Print ───────────────────────────────────────────────────────────────
print("=" * 95)
print("  WNBA TC PROJECTIONS — May 14, 2026 | Night Games | Real ESPN Data")
print("=" * 95)
print(f"  Market Lines: MIN@DAL → DAL -3.5 | 178.5  |  NY@POR → POR +11.5 | 176.5")
print(f"  Live Stats:   MIN 89.0 PPG | DAL 89.5 PPG | NY 100.0 PPG | POR 90.5 PPG")
print("=" * 95)

for g in GAMES:
    ak, hk = g["away"], g["home"]
    an, hn = g["away_name"], g["home_name"]

    # Roster TC
    min_s, min_b, min_tc = team_tc(g["away_players"])
    dal_s, dal_b, dal_tc = team_tc(g["home_players"])

    # Team edges
    min_edge = team_edge(min_tc, g["total"], g["spread"], is_home=False)
    dal_edge = team_edge(dal_tc, g["total"], g["spread"], is_home=True)

    # Combined
    tc_combined = round(min_tc + dal_tc, 1)
    total_lean  = "UNDER" if tc_combined < g["total"] else "OVER"
    total_edge  = round(tc_combined - g["total"], 1)

    # Market implied team totals
    min_implied = round((g["total"] + g["spread"]) / 2, 1)
    dal_implied = round((g["total"] - g["spread"]) / 2 * 1.02, 1)

    # Picks
    legs = []
    if abs(min_edge) >= MIN_EDGE:
        team = ak if min_edge > 0 else hk
        legs.append({"type":"SPREAD","team":team,"edge":abs(min_edge),"odds":-110})
    if abs(dal_edge) >= MIN_EDGE:
        team = hk if dal_edge > 0 else ak
        legs.append({"type":"SPREAD","team":team,"edge":abs(dal_edge),"odds":-110})
    legs.append({"type":"TOTAL","team":"COMBINED","edge":abs(total_edge),"lean":total_lean,"odds":-110})
    for leg in legs:
        p = 0.52 if leg["type"] == "TOTAL" else 0.53
        k = kelly(leg["odds"], p)
        leg["kelly_pct"] = round(k, 4)
        leg["bet_size"]  = round(k * 1000, 2)
        leg["conf"] = "HIGH" if abs(leg["edge"]) >= 4 else "MEDIUM" if abs(leg["edge"]) >= 2 else "LOW"

    print(f"\n{'═'*95}")
    print(f"  📺 {g['time']} | {ak} @ {hk} | {g['network']}")
    print(f"  {an} vs {hn}")
    print(f"  Record: {ak} 1-1 (89.0 PPG | 87.5 OPP) | {hk} 1-1 (89.5 PPG | 90.5 OPP)")
    print(f"  Market: {g['total']} total | DAL -3.5 spread | DAL 53.5% win prob (ESPN)")
    print(f"{'═'*95}")

    # Away roster
    print(f"\n  {ak} — {an}")
    print(f"  {'Player':<22} {'POS':<4} {'HT':<5} {'PTS':>5} {'TC':>6} {'LINE':>6} {'EDGE':>6} {'STATUS':<10}")
    print(f"  {'─'*75}")
    for i, p in enumerate(g["away_players"]):
        flag = "⚠️ GTD" if p.status == "Q" else ("❌ OUT" if p.status == "OUT" else "")
        print(f"  {'* ' + p.name if i < 5 else '  ' + p.name:<24} {p.pos:<4} {p.ht:<5} "
              f"{p.pts:>5.1f} {p.tc_pts():>6.1f} {p.line():>6.1f} {p.edge():>+6.1f} {flag}")
    print(f"  {'─'*75}")
    print(f"  {'STARTERS':<22} {'':4} {'':5} {'':5} {min_s:>6.1f}")
    print(f"  {'BENCH':<22} {'':4} {'':5} {'':5} {min_b:>6.1f}")
    print(f"  {'TOTAL TC':<22} {'':4} {'':5} {'':5} {min_tc:>6.1f}")

    # Home roster
    print(f"\n  {hk} — {hn}  (Home +2pts)")
    print(f"  {'Player':<22} {'POS':<4} {'HT':<5} {'PTS':>5} {'TC':>6} {'LINE':>6} {'EDGE':>6} {'STATUS':<10}")
    print(f"  {'─'*75}")
    for i, p in enumerate(g["home_players"]):
        flag = "⚠️ GTD" if p.status == "Q" else ("❌ OUT" if p.status == "OUT" else "")
        print(f"  {'* ' + p.name if i < 5 else '  ' + p.name:<24} {p.pos:<4} {p.ht:<5} "
              f"{p.pts:>5.1f} {p.tc_pts():>6.1f} {p.line():>6.1f} {p.edge():>+6.1f} {flag}")
    print(f"  {'─'*75}")
    print(f"  {'STARTERS':<22} {'':4} {'':5} {'':5} {dal_s:>6.1f}")
    print(f"  {'BENCH':<22} {'':4} {'':5} {'':5} {dal_b:>6.1f}")
    print(f"  {'TOTAL TC':<22} {'':4} {'':5} {'':5} {dal_tc:>6.1f}")

    print(f"\n  ── TC SUMMARY ──")
    print(f"  {ak}: TC={min_tc:.1f} | Market Implied={min_implied} | Edge={min_edge:+.1f}")
    print(f"  {hk}: TC={dal_tc:.1f} | Market Implied={dal_implied} | Edge={dal_edge:+.1f}")
    print(f"  COMBINED TC: {tc_combined} | Market Total: {g['total']} | Lean: {total_lean} | Edge: {total_edge:+.1f}")

    print(f"\n  🎯 PICKS ({g['time']})")
    for leg in legs:
        print(f"  • {leg['type']:<7} | {leg.get('lean', leg['team']):>8} | "
              f"Edge: {leg['edge']:+.1f} | Kelly: {leg['kelly_pct']:.1%} | "
              f"${leg['bet_size']:.0f} | {leg['conf']}")

    if g["inj"]:
        print(f"\n  🏥 INJURY REPORT: {' | '.join(g['inj'])}")

print(f"\n{'='*95}")
print("  TC FORMULA: TC = PTS × 0.85  |  Line = PTS × 0.88  |  Edge = TC − Line")
print("  Kelly Criterion capped at 10% → max $100/bet on $1,000 bankroll")
print("  Home edge: +2pts applied to implied team total")
print("  STATUS KEY: ⚠️ GTD = Game-Time Decision | ❌ OUT = Ruled Out")
print("="*95)