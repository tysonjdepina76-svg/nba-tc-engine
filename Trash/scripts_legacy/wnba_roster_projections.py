"""
WNBA Full Roster Projections — Points / Rebounds / Assists / 3PM
TC-adjusted player-level projections for every active roster player.
"""
from dataclasses import dataclass

CONS_PTS  = 0.85
CONS_REB  = 0.12
CONS_AST  = 0.10
CONS_3PM  = 0.08
LINE_FACT = 0.88
Q_FACTOR  = 0.55

@dataclass
class Player:
    name: str; pos: str; ht: str
    pts: float; reb: float; ast: float; tpm: float
    status: str = "ACTIVE"

    def tc(self):
        if self.status == "OUT":   return 0.0, 0.0, 0.0, 0.0
        f = Q_FACTOR if self.status == "Q" else 1.0
        tc_pts = self.pts * CONS_PTS * f
        tc_reb = self.reb * CONS_REB * f
        tc_ast = self.ast * CONS_AST * f
        tc_3pm = self.tpm * CONS_3PM * f
        return tc_pts, tc_reb, tc_ast, tc_3pm

    def line_pts(self): return round(self.pts * LINE_FACT, 1)
    def line_reb(self): return round(self.reb * LINE_FACT, 1)
    def line_ast(self): return round(self.ast * LINE_FACT, 1)
    def line_3pm(self): return round(self.tpm * LINE_FACT, 1)

    def edge_pts(self): return round(self.tc()[0] - self.line_pts(), 1)
    def edge_reb(self): return round(self.tc()[1] - self.line_reb(), 1)
    def edge_ast(self): return round(self.tc()[2] - self.line_ast(), 1)
    def edge_3pm(self): return round(self.tc()[3] - self.line_3pm(), 1)

# ── ROSTERS ──────────────────────────────────────────────────────────────

MIN_ROSTER = [
    Player("Kayla McBride",      "G","5-10", 17.0, 4.0, 5.0, 3.0),
    Player("Natisha Hiedeman",   "G","5-11", 15.0, 3.5, 4.5, 2.2),
    Player("Jessica Shepard",    "F","6-2",  14.0, 6.5, 6.0, 1.2),
    Player("Alanna Smith",       "F","6-4",  12.5, 6.5, 2.5, 1.0, "OUT"),
    Player("Nia Coffey",         "F","6-0",  10.5, 5.5, 2.0, 1.5, "Q"),
    Player("Myisha Hines-Allen", "F","6-4",  10.5, 5.5, 2.0, 0.5),
    Player("Rachel Barrow",      "G","5-10",  8.0, 3.0, 2.0, 1.0),
    Player("Cecilia Hidle",     "F","6-2",   6.5, 4.0, 1.0, 0.5),
    Player("Tamara",            "G","5-9",   5.5, 2.0, 1.5, 0.5),
]

DAL_ROSTER = [
    Player("Arike Ogunbowale",  "G","5-9",  21.0, 4.0, 4.0, 2.8),
    Player("Kayla Threlked",    "G","5-11",14.0, 3.0, 5.5, 2.0),
    Player("Jade Melbourne",    "F","6-1",  12.0, 5.5, 2.5, 1.0),
    Player("Katherine Plouffe", "F","6-3",  13.5, 7.0, 2.0, 1.5),
    Player("Natasha Howard",    "F","6-4",   8.0, 4.0, 2.0, 0.5),
    Player("Paige Bueckers",    "G","6-0",  20.5, 5.0, 4.5, 2.8, "Q"),
    Player("Te'a Cooper",       "G","5-9",   8.5, 2.5, 3.0, 0.8),
    Player("Cameron Buckley",   "F","6-2",   7.0, 4.0, 1.5, 1.0),
    Player("Natasha Davoren",   "C","6-4",   8.0, 5.5, 1.0, 0.5),
]

NY_ROSTER = [
    Player("Breanna Stewart",   "F","6-4",  22.0, 9.0, 4.0, 2.8),
    Player("Sabrina Ionescu",   "G","5-11",19.5, 5.0, 7.5, 3.5),
    Player("Jonquel Jones",     "C","6-6",  17.5, 9.5, 3.0, 1.5),
    Player("Olivia Miles",     "G","5-11",12.0, 5.7, 7.1, 1.8, "Q"),
    Player("Johannes",         "G","6-0",  15.0, 4.0, 4.5, 2.8),
    Player("Pauline Astier",   "G","5-10",14.0, 3.5, 4.0, 2.2),
    Player("Kayla Thornton",   "F","6-2",  9.5,  4.5, 1.5, 1.0),
    Player("Stefanie Dolson",  "C","6-3",   8.0, 5.0, 1.5, 0.8),
    Player("Jacobs",           "G","5-9",   7.5, 2.5, 3.0, 1.2),
    Player("Rebekah",          "C","6-5",   7.0, 5.5, 1.0, 0.5),
]

POR_ROSTER = [
    Player("Bridget Carleton",  "G","6-1",  18.5, 5.5, 3.5, 2.8),
    Player("Carla Leite",      "G","5-10", 17.0, 4.0, 5.5, 2.5),
    Player("Sarah Ashlee Barker","F","6-2",14.5, 5.0, 2.0, 1.5),
    Player("Haley Jones",      "G","6-1",  11.0, 4.5, 3.5, 1.2),
    Player("Emily Engstler",   "F","6-4",  10.5, 6.5, 2.0, 0.8),
    Player("Luisa Geiselsoder","C","6-5",   9.0, 5.5, 1.5, 0.5),
    Player("Megan",            "G","5-8",   8.0, 2.5, 3.0, 1.0),
    Player("Winterburn",       "G","5-10",  7.5, 2.0, 2.0, 1.2),
    Player("Sonia",            "F","6-3",   6.0, 4.5, 1.0, 0.5),
]

TEAMS = {
    "MIN": ("Minnesota Lynx",  MIN_ROSTER),
    "DAL": ("Dallas Wings",   DAL_ROSTER),
    "NY":  ("New York Liberty", NY_ROSTER),
    "POR": ("Portland Fire",  POR_ROSTER),
}

COLS = 110
DIV  = "=" * COLS
HDR  = (f"  {'Player':<22} {'POS':<4} {'HT':<5}"
        f" {'PTS':>5} {'TC_PTS':>7} {'LINE_PTS':>8} {'EDGE_PTS':>8}"
        f" {'REB':>5} {'TC_REB':>7} {'LINE_REB':>8} {'EDGE_REB':>8}"
        f" {'AST':>5} {'TC_AST':>7} {'LINE_AST':>8} {'EDGE_AST':>8}"
        f" {'3PM':>5} {'TC_3PM':>7} {'LINE_3PM':>8} {'EDGE_3PM':>8}"
        f" {'STATUS':<8}")
SEP  = "  " + "-" * 105

print(DIV)
print("  WNBA FULL ROSTER PROJECTIONS — Points / Rebounds / Assists / 3PM")
print("  TC Formula: TC_PTS=PTS×0.85  TC_REB=REB×0.12  TC_AST=AST×0.10  TC_3PM=3PM×0.08")
print("  Line: ×0.88  |  Q-Factor: 0.55  |  OUT = 0")
print(DIV)

for abbr, (name, roster) in TEAMS.items():
    starters = roster[:5]
    bench    = roster[5:]

    print(f"\n{'=' * COLS}")
    print(f"  {abbr} — {name} ({len(roster)} players)")
    print(DIV)
    print(HDR)
    print(SEP)

    s_pts = s_reb = s_ast = s_3pm = 0
    b_pts = b_reb = b_ast = b_3pm = 0

    for i, p in enumerate(roster):
        tc_pts, tc_reb, tc_ast, tc_3pm = p.tc()
        flag = " ❌ OUT" if p.status == "OUT" else (" ⚠️ Q " if p.status == "Q" else "")
        star = "* " if i < 5 else "  "

        print(f"  {star + p.name:<22} {p.pos:<4} {p.ht:<5}"
              f" {p.pts:>5.1f} {tc_pts:>7.1f} {p.line_pts():>8.1f} {p.edge_pts():>+8.1f}"
              f" {p.reb:>5.1f} {tc_reb:>7.2f} {p.line_reb():>8.1f} {p.edge_reb():>+8.2f}"
              f" {p.ast:>5.1f} {tc_ast:>7.2f} {p.line_ast():>8.1f} {p.edge_ast():>+8.2f}"
              f" {p.tpm:>5.1f} {tc_3pm:>7.2f} {p.line_3pm():>8.1f} {p.edge_3pm():>+8.2f}"
              f" {flag}")

        if i < 5:
            s_pts += tc_pts; s_reb += tc_reb; s_ast += tc_ast; s_3pm += tc_3pm
        else:
            b_pts += tc_pts; b_reb += tc_reb; b_ast += tc_ast; b_3pm += tc_3pm

    print(SEP)
    print(f"  {'STARTERS':<22} {'':4} {'':5}"
          f" {s_pts:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {s_reb:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {s_ast:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {s_3pm:>5.1f} {'—':>7} {'—':>8} {'—':>8}")
    print(f"  {'BENCH':<22} {'':4} {'':5}"
          f" {b_pts:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {b_reb:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {b_ast:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {b_3pm:>5.1f} {'—':>7} {'—':>8} {'—':>8}")
    print(f"  {'TEAM TOTAL':<22} {'':4} {'':5}"
          f" {s_pts+b_pts:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {s_reb+b_reb:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {s_ast+b_ast:>5.1f} {'—':>7} {'—':>8} {'—':>8}"
          f" {s_3pm+b_3pm:>5.1f} {'—':>7} {'—':>8} {'—':>8}")

print()
print(DIV)
print("  WEIGHT LEGEND:")
print("    TC_PTS × 0.85 — TC Reb × 0.12  —  TC Ast × 0.10  —  TC 3PM × 0.08")
print("    Line = PTS × 0.88  (rebound/assist/3PM lines also × 0.88)")
print("    Edge = TC value − Line  (positive = TC above line)")
print("    Q status = TC reduced by 0.55 factor | OUT = 0 contribution")
print(DIV)
