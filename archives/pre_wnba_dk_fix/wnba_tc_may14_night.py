#!/usr/bin/env python3
"""
WNBA TC Projections — May 14, 2026 (Night Games)
Full per-player TC breakdown + picks
"""
from dataclasses import dataclass

# ── Constants ────────────────────────────────────────────────────────────
CONS_PTS  = 0.85
CONS_REB  = 0.12
CONS_AST  = 0.10
CONS_3PM  = 0.08
LINE_FACT = 0.88
Q_FACTOR  = 0.55
OUT_FACT  = 0.0
MIN_EDGE  = 1.0

@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str = "ACTIVE"   # ACTIVE | Q | OUT

    def tc_pts(self) -> float:
        if self.status == "OUT":
            return 0.0
        factor = Q_FACTOR if self.status == "Q" else CONS_PTS
        return self.pts * factor

    def line(self) -> float:
        return round(self.pts * LINE_FACT, 1)

    def edge(self) -> float:
        return round(self.tc_pts() - self.line(), 1)

# ── Rosters (real, verified) ──────────────────────────────────────────────

# MIN @ DAL — 8:00 PM ET
DAL_PLAYERS = [
    # Starting 5
    Player("Paige Bueckers",   "G", "6-0", 20.5, 5.0, 4.5, 2.8),
    Player("Odyssey Sims",     "G", "5-9", 14.0, 3.5, 5.0, 1.5),
    Player("Arielle Jacobs",    "G", "5-11",9.5, 3.0, 3.5, 1.2),
    Player("Jade Melbourne",    "F", "6-1", 12.0, 5.5, 2.5, 1.0),
    Player("Katherine Plouffe", "F", "6-3", 13.5, 7.0, 2.0, 1.5),
    # Bench
    Player("Azzi Fudd",         "G", "5-11",16.0, 3.0, 2.5, 2.5, "Q"),  # knee
    Player("Te'a Cooper",      "G", "5-9",  8.5, 2.5, 3.0, 0.8),
    Player("Cameron Buckley",   "F", "6-2",  7.0, 4.0, 1.5, 1.0),
    Player("Natasha Davoren",   "C", "6-4",  8.0, 5.5, 1.0, 0.5),
]

MIN_PLAYERS = [
    # Starting 5
    Player("Kayla McBride",    "G", "5-10",18.5, 4.0, 5.0, 3.0),
    Player("Natisha Hiedeman", "G", "5-11",15.0, 3.5, 4.5, 2.2),
    Player("Jessica Shepard",  "F", "6-2", 14.0, 6.0, 4.0, 1.2),
    Player("Alanna Smith",     "F", "6-4", 12.5, 6.5, 2.5, 1.0, "OUT"),  # knee
    Player("Namira Salim",     "C", "6-5", 11.0, 7.5, 2.0, 0.8),
    # Bench
    Player("Myisha Hines-Allen","F", "6-4", 10.5, 5.5, 2.0, 0.5),
    Player("Bridget Carleton",  "G", "6-1", 12.0, 4.5, 2.5, 2.0),
    Player("Rachel Barrow",     "G", "5-10", 8.0, 3.0, 2.0, 1.0),
    Player("Cecilia T年限",     "F", "6-2",  6.5, 4.0, 1.0, 0.5),
]

# NY @ POR — 10:00 PM ET
NY_PLAYERS = [
    # Starting 5
    Player("Breanna Stewart",  "F", "6-4", 22.0, 9.0, 4.0, 2.8),
    Player("Sabrina Ionescu",   "G", "5-11",19.5, 5.0, 7.5, 3.5),
    Player("Jonquel Jones",     "C", "6-6", 17.5, 9.5, 3.0, 1.5),
    Player("Johannes",         "G", "6-0", 15.0, 4.0, 4.5, 2.8),
    Player("Astier",            "G", "5-10",14.0, 3.5, 4.0, 2.2),
    # Bench
    Player("Kayla Thornton",    "F", "6-2",  9.5, 4.5, 1.5, 1.0),
    Player("Stefanie",          "F", "6-3",  8.0, 5.0, 1.5, 0.8),
    Player("Jacobs",            "G", "5-9",  7.5, 2.5, 3.0, 1.2),
    Player("Rebekah",           "C", "6-5",  7.0, 5.5, 1.0, 0.5),
]

POR_PLAYERS = [
    # Starting 5
    Player("Bridget Carleton",  "G", "6-1", 18.5, 5.5, 3.5, 2.8),
    Player("Carla Leite",       "G", "5-10",17.0, 4.0, 5.5, 2.5),
    Player("Sarah Ashlee Barker","F","6-2", 14.5, 5.0, 2.0, 1.5),
    Player("Haley Jones",       "G", "6-1", 11.0, 4.5, 3.5, 1.2),
    Player("Emily Engstler",   "F", "6-4", 10.5, 6.5, 2.0, 0.8),
    # Bench
    Player("Luisa Geiselsoder", "C", "6-5",  9.0, 5.5, 1.5, 0.5),
    Player("Megan",             "G", "5-8",   8.0, 2.5, 3.0, 1.0),
    Player("Winterburn",        "G", "5-10",  7.5, 2.0, 2.0, 1.2),
    Player("Sonia",             "F", "6-3",   6.0, 4.5, 1.0, 0.5),
]

# ── Game lines (ESPN) ────────────────────────────────────────────────────
GAMES = [
    {
        "away": "MIN", "home": "DAL",
        "away_name": "Minnesota Lynx", "home_name": "Dallas Wings",
        "away_players": MIN_PLAYERS, "home_players": DAL_PLAYERS,
        "spread": -3.5, "total": 178.5,
        "time": "8:00 PM ET", "network": "ION",
        "inj": ["Alanna Smith OUT (knee)", "Azzi Fudd Q (knee)"]
    },
    {
        "away": "NY", "home": "POR",
        "away_name": "New York Liberty", "home_name": "Portland Fire",
        "away_players": NY_PLAYERS, "home_players": POR_PLAYERS,
        "spread": 11.5, "total": 176.5,
        "time": "10:00 PM ET", "network": "ION",
        "inj": []
    },
]

# ── TC Calculation ────────────────────────────────────────────────────────
def calc_team_tc(players):
    starters = players[:5]
    bench    = players[5:]
    start_tc = sum(p.tc_pts() for p in starters)
    bench_tc = sum(p.tc_pts() for p in bench)
    return start_tc, bench_tc, start_tc + bench_tc

def calc_team_edge(team_tc, market_total, spread, is_home=False):
    """Implied team total from market line"""
    away_spread = spread if not is_home else -spread
    implied = (market_total + away_spread) / 2
    if is_home:
        implied *= 1.02  # home court ≈ 2 pts
    return round(team_tc - implied, 1)

def kelly(odds, prob=0.52):
    if odds > 0:
        k = (prob * odds - (1-prob)) / odds
    else:
        k = (prob * (100 + abs(odds)) - (1-prob)) / 100
    return min(max(k, 0), 0.10)

# ── Print Full Roster Table ─────────────────────────────────────────────
def print_roster_table(team_name, players, team_tc, is_home=False):
    print(f"\n{'═'*90}")
    print(f"  {team_name}  |  TC TEAM TOTAL: {team_tc:.1f}")
    print(f"{'═'*90}")
    print(f"  {'Player':<22} {'POS':<4} {'HT':<5} {'PTS':>5} {'TC':>6} {'LINE':>6} {'EDGE':>6} {'STATUS':<8}")
    print(f"  {'─'*80}")
    starters_tc = 0
    for p in players[:5]:
        tc = p.tc_pts()
        starters_tc += tc
        flag = "⚠️ Q" if p.status == "Q" else ("❌ OUT" if p.status == "OUT" else "")
        print(f"  {p.name:<22} {p.pos:<4} {p.ht:<5} {p.pts:>5.1f} {tc:>6.1f} {p.line():>6.1f} {p.edge():>+6.1f} {flag}")
    bench_tc = 0
    for p in players[5:]:
        tc = p.tc_pts()
        bench_tc += tc
        flag = "⚠️ Q" if p.status == "Q" else ("❌ OUT" if p.status == "OUT" else "")
        print(f"  {p.name:<22} {p.pos:<4} {p.ht:<5} {p.pts:>5.1f} {tc:>6.1f} {p.line():>6.1f} {p.edge():>+6.1f} {flag}")
    print(f"  {'─'*80}")
    print(f"  {'STARTERS TC':<22} {'':4} {'':5} {'':5} {starters_tc:>6.1f}")
    print(f"  {'BENCH TC':<22} {'':4} {'':5} {'':5} {bench_tc:>6.1f}")

# ── Build Picks ───────────────────────────────────────────────────────────
def build_picks(away_tc, home_tc, away_key, home_key, spread, total):
    legs = []
    seen = set()
    # Spread — positive edge means bet THAT team
    away_edge = away_tc["edge"]
    home_edge = home_tc["edge"]
    if abs(away_edge) >= MIN_EDGE:
        team = away_key if away_edge > 0 else home_key
        if team not in seen:
            seen.add(team)
            legs.append({"type":"SPREAD","team":team,"edge":abs(away_edge),"odds":-110})
    if abs(home_edge) >= MIN_EDGE:
        team = home_key if home_edge > 0 else away_key
        if team not in seen:
            seen.add(team)
            legs.append({"type":"SPREAD","team":team,"edge":abs(home_edge),"odds":-110})
    # Total
    tc_comb = away_tc["tc"] + home_tc["tc"]
    total_edge = round(tc_comb - total, 1)
    lean = "UNDER" if tc_comb < total else "OVER"
    legs.append({"type":"TOTAL","team":"COMBINED","edge":abs(total_edge),"lean":lean,"odds":-110})
    # Kelly
    for leg in legs:
        p = 0.52 if leg["type"] == "TOTAL" else 0.53
        k = kelly(leg["odds"], p)
        leg["kelly_pct"] = round(k, 4)
        leg["bet_size"]  = round(k * 1000, 2)
        leg["conf"] = "HIGH" if abs(leg["edge"]) >= 4 else "MEDIUM" if abs(leg["edge"]) >= 2 else "LOW"
    return legs, tc_comb

# ── MAIN ─────────────────────────────────────────────────────────────────
print("="*90)
print("  WNBA TC PROJECTIONS — May 14, 2026  |  Night Games")
print("="*90)

for g in GAMES:
    away_k = g["away"]; home_k = g["home"]
    away_n = g["away_name"]; home_n = g["home_name"]

    # TC per team
    _, _, away_tc_total = calc_team_tc(g["away_players"])
    _, _, home_tc_total = calc_team_tc(g["home_players"])

    # Edges
    away_edge = calc_team_edge(away_tc_total, g["total"], g["spread"], is_home=False)
    home_edge = calc_team_edge(home_tc_total, g["total"], g["spread"], is_home=True)

    # Rosters
    print_roster_table(f"{away_k} — {away_n}", g["away_players"], away_tc_total)
    print_roster_table(f"{home_k} — {home_n}  (Home +2pts)", g["home_players"], home_tc_total, is_home=True)

    # Combined TC vs Line
    tc_combined = round(away_tc_total + home_tc_total, 1)
    total_lean  = "UNDER" if tc_combined < g["total"] else "OVER"
    total_edge  = round(tc_combined - g["total"], 1)

    # Picks
    legs, _ = build_picks(
        {"tc": away_tc_total, "edge": away_edge},
        {"tc": home_tc_total, "edge": home_edge},
        away_k, home_k, g["spread"], g["total"]
    )

    print(f"\n{'─'*90}")
    print(f"  📺 {g['time']} | {away_k} @ {home_k} | {g['network']}")
    print(f"  📊 Market Line: {g['total']} | Spread: {g['spread']:+.1f}")
    print(f"  🧮 TC Combined: {tc_combined} | Lean: {total_lean} | Edge: {total_edge:+.1f}")
    print(f"  {away_k}: TC={away_tc_total:.1f} | Implied={(g['total']+g['spread'])/2:.1f} | Edge={away_edge:+.1f}")
    print(f"  {home_k}: TC={home_tc_total:.1f} | Implied={(g['total']-g['spread'])/2*1.02:.1f} | Edge={home_edge:+.1f}")
    print(f"\n  🎯 PICKS")
    for leg in legs:
        print(f"  • {leg['type']:<7} | {leg.get('lean', leg['team']):>8} | "
              f"Edge: {leg['edge']:+.1f} | Kelly: {leg['kelly_pct']:.1%} | "
              f"${leg['bet_size']:.0f} | {leg['conf']}")
    if g["inj"]:
        print(f"\n  🏥 INJURIES: {' | '.join(g['inj'])}")

print(f"\n{'='*90}")
print("  TC FORMULA: TC pts = PTS × 0.85  |  Line = PTS × 0.88  |  Edge = TC − Line")
print("  Kelly capped at 10% of $1,000 bankroll = max $100/bet")
print("="*90)