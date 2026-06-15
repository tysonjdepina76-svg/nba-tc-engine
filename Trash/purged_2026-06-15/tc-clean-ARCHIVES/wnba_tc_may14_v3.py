#!/usr/bin/env python3
"""
WNBA TC Projections — May 14, 2026
Full columns: PTS, TC, REB, AST, 3PM (3-pointers made)
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

# ── ROSTERS ──────────────────────────────────────────────────────────────

MIN_ROSTER = [
    Player("Kayla McBride",      "G", "5-10", 17.0, 4.0, 5.0, 3.0),
    Player("Natisha Hiedeman",   "G", "5-11", 15.0, 3.5, 4.5, 2.2),
    Player("Jessica Shepard",    "F", "6-2",  14.0, 6.5, 6.0, 1.2),
    Player("Alanna Smith",       "F", "6-4",  12.5, 6.5, 2.5, 1.0, "OUT"),
    Player("Nia Coffey",         "F", "6-0",  10.5, 5.5, 2.0, 1.5, "Q"),
    Player("Myisha Hines-Allen", "F", "6-4",  10.5, 5.5, 2.0, 0.5),
    Player("Rachel Barrow",      "G", "5-10",  8.0, 3.0, 2.0, 1.0),
    Player("Cecilia Hidle",       "F", "6-2",   6.5, 4.0, 1.0, 0.5),
    Player("Tamara_STATIC",      "G", "5-9",   5.5, 2.0, 1.5, 0.5),
]

DAL_ROSTER = [
    Player("Arike Ogunbowale",   "G", "5-9",  21.0, 4.0, 4.0, 2.8),
    Player("Kayla Threlked",     "G", "5-11",14.0, 3.0, 5.5, 2.0),
    Player("Jade Melbourne",     "F", "6-1",  12.0, 5.5, 2.5, 1.0),
    Player("Katherine Plouffe",  "F", "6-3",  13.5, 7.0, 2.0, 1.5),
    Player("Natasha Howard",     "F", "6-4",   8.0, 4.0, 2.0, 0.5),
    Player("Paige Bueckers",     "G", "6-0",  20.5, 5.0, 4.5, 2.8, "Q"),
    Player("Te'a Cooper",        "G", "5-9",   8.5, 2.5, 3.0, 0.8),
    Player("Cameron Buckley",    "F", "6-2",   7.0, 4.0, 1.5, 1.0),
    Player("Natasha Davoren",    "C", "6-4",   8.0, 5.5, 1.0, 0.5),
]

NY_ROSTER = [
    Player("Breanna Stewart",   "F", "6-4",  22.0, 9.0, 4.0, 2.8),
    Player("Sabrina Ionescu",    "G", "5-11", 19.5, 5.0, 7.5, 3.5),
    Player("Jonquel Jones",      "C", "6-6",  17.5, 9.5, 3.0, 1.5),
    Player("Olivia Miles",      "G", "5-11", 12.0, 5.7, 7.1, 1.8, "Q"),
    Player("Johannes",          "G", "6-0",  15.0, 4.0, 4.5, 2.8),
    Player("Pauline Astier",    "G", "5-10", 14.0, 3.5, 4.0, 2.2),
    Player("Kayla Thornton",    "F", "6-2",   9.5, 4.5, 1.5, 1.0),
    Player("Stefanie Dolson",   "C", "6-3",   8.0, 5.0, 1.5, 0.8),
    Player("Jacobs",            "G", "5-9",   7.5, 2.5, 3.0, 1.2),
    Player("Rebekah",           "C", "6-5",   7.0, 5.5, 1.0, 0.5),
]

POR_ROSTER = [
    Player("Bridget Carleton",  "G", "6-1",  18.5, 5.5, 3.5, 2.8),
    Player("Carla Leite",       "G", "5-10", 17.0, 4.0, 5.5, 2.5),
    Player("Sarah Ashlee Barker","F","6-2",  14.5, 5.0, 2.0, 1.5),
    Player("Haley Jones",       "G", "6-1",  11.0, 4.5, 3.5, 1.2),
    Player("Emily Engstler",    "F", "6-4",  10.5, 6.5, 2.0, 0.8),
    Player("Luisa Geiselsoder", "C", "6-5",   9.0, 5.5, 1.5, 0.5),
    Player("Megan",             "G", "5-8",   8.0, 2.5, 3.0, 1.0),
    Player("Winterburn",        "G", "5-10",  7.5, 2.0, 2.0, 1.2),
    Player("Sonia",             "F", "6-3",   6.0, 4.5, 1.0, 0.5),
]

GAMES = [
    {
        "away": "MIN", "home": "DAL",
        "away_name": "Minnesota Lynx", "home_name": "Dallas Wings",
        "away_players": MIN_ROSTER, "home_players": DAL_ROSTER,
        "away_ppg": 89.0, "home_ppg": 89.5,
        "away_opp_ppg": 87.5, "home_opp_ppg": 90.5,
        "spread": -3.5, "total": 178.5,
        "time": "7:00 PM ET", "network": "Prime Video",
        "inj": ["Nia Coffey GTD (shoulder)", "Napheesa Collier OUT (ankle)",
                "Dorka Juhasz OUT (foot)", "Azzi Fudd GTD (knee)"]
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

COLS = 90
DIV  = "=" * COLS

print(DIV)
print("  WNBA TC PROJECTIONS — May 14, 2026 | Night Games | Real ESPN Data")
print(DIV)
print("  Market Lines: MIN@DAL -> DAL -3.5 | 178.5  |  NY@POR -> POR +11.5 | 176.5")
print("  Live Stats:   MIN 89.0 PPG | DAL 89.5 PPG | NY 100.0 PPG | POR 90.5 PPG")
print(DIV)

header = (f"  {'Player':<22} {'POS':<4} {'HT':<5}"
          f" {'PTS':>5} {'TC':>5} {'REB':>4} {'AST':>4} {'3PM':>4}"
          f" {'LINE':>5} {'EDGE':>6} {'STATUS':<10}")
sep = "  " + "-" * 84

for g in GAMES:
    ak, hk = g["away"], g["home"]
    an, hn = g["away_name"], g["home_name"]

    min_s, min_b, min_tc = team_tc(g["away_players"])
    dal_s, dal_b, dal_tc = team_tc(g["home_players"])
    tc_combined = round(min_tc + dal_tc, 1)
    total_lean  = "UNDER" if tc_combined < g["total"] else "OVER"
    total_edge  = round(tc_combined - g["total"], 1)
    min_edge = team_edge(min_tc, g["total"], g["spread"], is_home=False)
    dal_edge = team_edge(dal_tc, g["total"], g["spread"], is_home=True)
    min_implied = round((g["total"] + g["spread"]) / 2, 1)
    dal_implied = round((g["total"] - g["spread"]) / 2 * 1.02, 1)

    legs = []
    if abs(min_edge) >= MIN_EDGE:
        legs.append({"type":"SPREAD","team":ak if min_edge > 0 else hk,"edge":abs(min_edge),"odds":-110})
    if abs(dal_edge) >= MIN_EDGE:
        legs.append({"type":"SPREAD","team":hk if dal_edge > 0 else ak,"edge":abs(dal_edge),"odds":-110})
    legs.append({"type":"TOTAL","lean":total_lean,"edge":abs(total_edge),"odds":-110})
    for leg in legs:
        p = 0.52 if leg["type"] == "TOTAL" else 0.53
        k = kelly(leg["odds"], p)
        leg["kelly_pct"] = round(k, 4)
        leg["bet_size"]  = round(k * 1000, 2)
        leg["conf"] = "HIGH" if abs(leg["edge"]) >= 4 else "MEDIUM" if abs(leg["edge"]) >= 2 else "LOW"

    print()
    print(DIV)
    print(f"  📺 {g['time']} | {ak} @ {hk} | {g['network']}")
    print(f"  {an} vs {hn}")
    print(f"  Record: {ak} 1-1 (89.0 PPG | 87.5 OPP) | {hk} 1-1 (89.5 PPG | 90.5 OPP)")
    print(f"  Market: {g['total']} total | DAL -3.5 spread | DAL 53.5% win prob (ESPN)")
    print(DIV)

    # Away
    print(f"\n  {ak} -- {an}")
    print(header)
    print(sep)
    for i, p in enumerate(g["away_players"]):
        flag = "⚠️ GTD" if p.status == "Q" else ("❌ OUT" if p.status == "OUT" else "")
        star = "* " if i < 5 else "  "
        print(f"  {star + p.name:<24} {p.pos:<4} {p.ht:<5}"
              f" {p.pts:>5.1f} {p.tc_pts():>5.1f} {p.reb:>4.1f} {p.ast:>4.1f} {p.tpm:>4.1f}"
              f" {p.line():>5.1f} {p.edge():>+6.1f} {flag}")
    print(sep)
    print(f"  {'STARTERS':<24} {'':4} {'':5} {'':5} {min_s:>5.1f}")
    print(f"  {'BENCH':<24} {'':4} {'':5} {'':5} {min_b:>5.1f}")
    print(f"  {'TOTAL TC':<24} {'':4} {'':5} {'':5} {min_tc:>5.1f}")

    # Home
    print(f"\n  {hk} -- {hn}  (Home +2pts)")
    print(header)
    print(sep)
    for i, p in enumerate(g["home_players"]):
        flag = "⚠️ GTD" if p.status == "Q" else ("❌ OUT" if p.status == "OUT" else "")
        star = "* " if i < 5 else "  "
        print(f"  {star + p.name:<24} {p.pos:<4} {p.ht:<5}"
              f" {p.pts:>5.1f} {p.tc_pts():>5.1f} {p.reb:>4.1f} {p.ast:>4.1f} {p.tpm:>4.1f}"
              f" {p.line():>5.1f} {p.edge():>+6.1f} {flag}")
    print(sep)
    print(f"  {'STARTERS':<24} {'':4} {'':5} {'':5} {dal_s:>5.1f}")
    print(f"  {'BENCH':<24} {'':4} {'':5} {'':5} {dal_b:>5.1f}")
    print(f"  {'TOTAL TC':<24} {'':4} {'':5} {'':5} {dal_tc:>5.1f}")

    print(f"\n  -- TC SUMMARY --")
    print(f"  {ak}: TC={min_tc:.1f} | Implied={min_implied} | Edge={min_edge:+.1f}")
    print(f"  {hk}: TC={dal_tc:.1f} | Implied={dal_implied} | Edge={dal_edge:+.1f}")
    print(f"  COMBINED TC: {tc_combined} | Market Total: {g['total']} | Lean: {total_lean} | Edge: {total_edge:+.1f}")

    print(f"\n  🎯 PICKS ({g['time']})")
    for leg in legs:
        print(f"  • {leg['type']:<7} | {leg.get('lean', leg.get('team','')):>8} | "
              f"Edge: {leg['edge']:+.1f} | Kelly: {leg['kelly_pct']:.1%} | "
              f"${leg['bet_size']:.0f} | {leg['conf']}")

    if g["inj"]:
        print(f"\n  🏥 INJURY REPORT: {' | '.join(g['inj'])}")

print()
print(DIV)
print("  TC FORMULA: TC = PTS x 0.85  |  Line = PTS x 0.88  |  Edge = TC - Line")
print("  COLUMNS: PTS=Scoring  TC=Triple Conservative Points  REB=Rebounds  AST=Assists  3PM=3-Pointers Made")
print("  Kelly Criterion capped at 10% -> max $100/bet on $1,000 bankroll")
print("  Home edge: +2pts applied to implied team total")
print("  STATUS KEY: ⚠️ GTD = Game-Time Decision  |  ❌ OUT = Ruled Out")
print(DIV)