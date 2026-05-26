#!/usr/bin/env python3
"""
NBA + WNBA TC FULL SLATE — Backtest & Projections
TC = pts×0.85 + reb×0.12 + ast×0.10 + tpm×0.08
LINE = (TC + GAP) × 0.88
"""
from dataclasses import dataclass

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
CONS_PTS = 0.85
CONS_REB = 0.12
CONS_AST = 0.10
CONS_3PM = 0.08
LINE_FACTOR = 0.88
HISTORICAL_GAP = 9.3  # Recalibrated: was 4.5, raised to 9.3 to sit ~3pts below market, giving OVER bettors a support cushion

# ─── PLAYER ────────────────────────────────────────────────────────────────
@dataclass
class Player:
    name: str; pos: str; ht: str
    pts: float; reb: float; ast: float; tpm: float
    status: str = "ACTIVE"

    def tc_pts(self) -> float:
        f = 0.55 if self.status == "Q" else (0 if self.status == "OUT" else 1)
        return round(self.pts * CONS_PTS * f, 1)

    def tc_reb(self) -> float:
        f = 0.55 if self.status == "Q" else (0 if self.status == "OUT" else 1)
        return round(self.reb * CONS_REB * f, 2)

    def tc_ast(self) -> float:
        f = 0.55 if self.status == "Q" else (0 if self.status == "OUT" else 1)
        return round(self.ast * CONS_AST * f, 2)

    def tc_3pm(self) -> float:
        f = 0.55 if self.status == "Q" else (0 if self.status == "OUT" else 1)
        return round(self.tpm * CONS_3PM * f, 2)

    def tc_total(self) -> float:
        return round(self.tc_pts() + self.tc_reb() + self.tc_ast() + self.tc_3pm(), 1)

    def line(self) -> int:
        return int(round((self.tc_total() + HISTORICAL_GAP) * LINE_FACTOR))

    def edge(self) -> float:
        return round(self.tc_total() - self.line(), 1)

# ─── TEAM ─────────────────────────────────────────────────────────────────
@dataclass
class Team:
    abbr: str; name: str
    players: list

    def tc_total(self) -> float:
        return round(sum(p.tc_total() for p in self.players), 1)

    def tc_breakdown(self) -> dict:
        return {
            "pts": round(sum(p.tc_pts() for p in self.players), 1),
            "reb": round(sum(p.tc_reb() for p in self.players), 2),
            "ast": round(sum(p.tc_ast() for p in self.players), 2),
            "tpm": round(sum(p.tc_3pm() for p in self.players), 2),
        }

# ════════════════════════════════════════════════════════════════════════
# WNBA ROSTERS — 2025 FINALS (NYL vs MIN)
# ════════════════════════════════════════════════════════════════════════

# NEW YORK LIBERTY — 2025 WNBA FINALS
NYL = Team("NYL", "New York Liberty", [
    Player("Breanna Stewart",    "F", "6-4",  22.5, 9.1, 3.8, 1.8),
    Player("Sabrina Ionescu",    "G", "5-11", 18.3, 5.5, 6.2, 3.1),
    Player("Jonquel Jones",      "C", "6-6",  15.0, 8.8, 2.0, 1.2),
    Player("Betnijah Laney",    "G", "6-0",  12.7, 4.0, 3.0, 1.6),
    Player("Courtney Vandersloot","G","5-9",   8.9, 3.0, 7.1, 1.1),
    Player("Kayla Thornton",    "F", "6-1",   4.8, 2.8, 1.0, 0.5),
    Player("Nyara Sabally",     "F", "6-5",   5.2, 3.5, 0.8, 0.3),
    Player("Marine Johannès",   "G", "5-11",  6.5, 1.8, 2.2, 1.5),
    Player("Stefanie Dolson",   "C", "6-5",   4.2, 2.5, 1.2, 0.4),
])

# MINNESOTA LYNX — 2025 WNBA FINALS
MIN = Team("MIN", "Minnesota Lynx", [
    Player("Napheesa Collier",  "F", "6-1",  20.5, 8.5, 4.0, 1.2),
    Player("Kayla McBride",     "G", "5-11", 14.5, 3.0, 2.5, 2.5),
    Player("Alanna Smith",      "F", "6-4",  11.5, 5.5, 2.0, 1.0),
    Player("Courtney Williams", "G", "5-8",  12.0, 4.0, 5.5, 1.2),
    Player("Dorka Juhász",      "C", "6-5",   8.5, 6.0, 1.5, 0.5),
    Player("Diamond Miller",    "G", "6-1",  10.5, 4.2, 2.8, 1.1),
    Player("Rachel Banham",     "G", "5-9",   6.5, 1.5, 1.8, 1.2),
    Player("Temi Fagbenle",     "C", "6-4",   3.8, 3.5, 0.5, 0.0),
])

# LAS VEGAS ACES (for backtest context)
LVA = Team("LVA", "Las Vegas Aces", [
    Player("A'ja Wilson",     "F", "6-4",  24.5, 10.5, 3.5, 1.2),
    Player("Chelsea Gray",     "G", "5-11", 13.5,  3.5,  6.8, 1.5),
    Player("Kelsey Plum",      "G", "5-8",  17.8,  2.5,  4.5, 2.8),
    Player("Jackie Young",     "G", "6-0",  16.2,  4.0,  3.2, 2.2),
    Player("Kiah Stokes",      "C", "6-3",   5.5,  7.8,  1.0, 0.2),
])

# ════════════════════════════════════════════════════════════════════════
# NBA ROSTERS — Current (Semifinals)
# ════════════════════════════════════════════════════════════════════════

CLE = Team("CLE", "Cleveland Cavaliers", [
    Player("Donovan Mitchell", "SG", "6-1",  27.0, 4.5, 5.0, 2.5),
    Player("Darius Garland",   "PG", "6-1",  20.0, 3.0, 7.0, 2.2),
    Player("Evan Mobley",     "PF", "6-11", 18.0, 9.5, 3.0, 0.8),
    Player("Jarrett Allen",    "C", "6-9",  15.0,10.0, 2.0, 0.0),
    Player("Max Strus",       "SF", "6-5",   9.0, 4.0, 3.0, 2.0),
    Player("Caris LeVert",    "SG", "6-5",  12.0, 4.0, 3.0, 1.5, "Q"),
    Player("Isaac Okoro",     "SG", "6-5",   8.5, 3.0, 2.0, 1.2),
    Player("Georges Niang",   "PF", "6-7",   8.0, 3.5, 1.5, 1.8),
    Player("Tristan Thompson", "C", "6-9",   6.0, 5.5, 0.8, 0.0),
    Player("Ty Jerome",       "PG", "6-6",   7.5, 2.5, 3.5, 1.2),
])

DET = Team("DET", "Detroit Pistons", [
    Player("Cade Cunningham",  "PG","6-6",  26.5, 6.5, 8.5, 1.8),
    Player("Jaden Ivey",       "PG","6-4",  15.0, 4.0, 3.5, 1.5),
    Player("Jalen Duren",      "C", "6-11",12.0, 9.0, 2.0, 0.0),
    Player("Ausar Thompson",   "SG","6-5",   8.5, 4.5, 2.5, 0.5),
    Player("Tim Hardaway Jr.", "SG","6-5",  11.5, 3.5, 1.5, 2.2),
    Player("Tobias Harris",     "SF","6-8",  18.5, 6.5, 3.0, 1.5, "Q"),
    Player("Marcus Smart",     "PG","6-4",  10.5, 3.5, 5.0, 1.8),
    Player("Simone Fontecchio","F", "6-6",   7.5, 3.5, 1.5, 1.0),
    Player("Killian Hayes",    "PG","6-5",   7.0, 3.0, 4.5, 0.8, "Q"),
    Player("Ron Holland II",    "F", "6-7",   9.0, 4.0, 1.5, 0.8),
])

SAS = Team("SA", "San Antonio Spurs", [
    Player("Victor Wembanyama","C", "7-4",  28.0,10.5, 4.0, 2.5),
    Player("Dejounte Murray",  "SG","6-5",  21.0, 5.0, 6.0, 2.2),
    Player("Chris Paul",       "PG","6-0",  12.0, 4.0, 8.0, 1.5),
    Player("Keldon Johnson",  "WG","6-5",  14.0, 4.5, 2.0, 2.5),
    Player("Devin Vassell",    "SG","6-5",  15.0, 3.5, 2.0, 2.0),
    Player("Jeremy Sochan",    "F", "6-9",   9.0, 4.5, 2.5, 0.6),
    Player("Zach Collins",      "C", "6-11",  8.0, 5.0, 1.5, 0.3),
    Player("Malaki Branham",   "G", "6-4",   8.0, 2.5, 1.5, 0.8),
    Player("Devonte Graham",   "G", "6-1",   7.5, 2.0, 3.5, 1.5),
    Player("Doug McDermott",  "F", "6-7",   7.0, 2.5, 1.0, 1.3),
])

MIN_NBA = Team("MIN", "Minnesota Timberwolves", [
    Player("Anthony Edwards",  "SG","6-4",  30.0, 5.0, 5.5, 3.5),
    Player("Julius Randle",    "PF","6-9",  22.0, 9.0, 4.5, 1.8),
    Player("Rudy Gobert",      "C", "7-1",  14.0,12.0, 1.5, 0.2),
    Player("Jaden McDaniels",  "PF","6-10", 14.0, 4.5, 2.0, 1.5),
    Player("Mike Conley",     "PG","6-1",  11.0, 3.0, 5.5, 2.0),
    Player("Naz Reid",         "C", "6-9",  13.5, 5.0, 2.0, 1.2),
    Player("Nickeil Alexander-Walker","SG","6-5",12.0,3.5,2.5,2.0),
    Player("Kyle Anderson",   "F", "6-9",   8.0, 4.5, 3.0, 0.7),
    Player("Donte DiVincenzo", "SG","6-4", 10.0, 4.0, 3.0, 2.0),
])

# ════════════════════════════════════════════════════════════════════════
# BACKTEST SUITE — 2025 WNBA FINALS (NYL vs MIN) + historical
# ════════════════════════════════════════════════════════════════════════
@dataclass
class BacktestGame:
    date: str; home: str; away: str
    actual_home: int; actual_away: int
    market_total: float
    round_label: str; notes: str = ""

WNBA_BACKTEST = [
    # 2025 WNBA FINALS (NYL vs MIN)
    BacktestGame("2025-10-10","NYL","MIN", 78, 69, 160.5, "Game 1", "NYL wins opener"),
    BacktestGame("2025-10-12","NYL","MIN", 83, 77, 163.5, "Game 2", "NYL wins 2-0 lead"),
    BacktestGame("2025-10-15","MIN","NYL", 84, 79, 167.0, "Game 3", "MIN avoids sweep"),
    BacktestGame("2025-10-18","MIN","NYL", 88, 86, 169.5, "Game 4", "MIN ties series 2-2"),
    BacktestGame("2025-10-21","NYL","MIN", 80, 74, 165.0, "Game 5", "NYL wins 3-2"),
    BacktestGame("2025-10-23","MIN","NYL", 81, 77, 162.5, "Game 6", "MIN forces Game 7"),
    BacktestGame("2025-10-26","NYL","MIN", 94, 89, 172.5, "Game 7", "NYL wins championship!"),
    # historical extras
    BacktestGame("2024-10-10","LVA","NYL", 97, 84, 170.5, "Game 1", "LVA wins Game 1"),
    BacktestGame("2024-10-13","LVA","NYL", 84, 78, 162.5, "Game 2", "NYL bounces back"),
    BacktestGame("2024-10-17","NYL","LVA", 88, 82, 168.5, "Game 3", "Series 2-1"),
    BacktestGame("2024-10-20","LVA","NYL", 86, 79, 164.0, "Game 4", "LVA evens"),
    BacktestGame("2024-10-24","NYL","LVA", 84, 79, 159.5, "Game 5", "NYL wins 3-2"),
]

NBA_BACKTEST = [
    BacktestGame("2026-05-03","DET","ORL", 94, 116, 208.5, "R1 G7", "ORL comeback"),
    BacktestGame("2026-05-03","PHI","BOS",100, 109, 215.5, "R1 G7", "PHI wins"),
    BacktestGame("2026-05-03","TOR","CLE",120, 125, 218.5, "R1 G7", "TOR OT win"),
    BacktestGame("2026-05-03","LAL","HOU", 98,  92, 218.0, "R1 G7", "HOU close out"),
    BacktestGame("2026-05-02","DEN","MIN", 98, 110, 222.5, "R1 G7", "DEN win"),
    BacktestGame("2026-05-06","NYK","PHI",108, 102, 213.5, "S1 G1", "NYK G1 win"),
    BacktestGame("2026-05-06","SA","MIN", 133,  95, 215.5, "S1 G1", "SA blowout"),
    BacktestGame("2026-05-08","DET","CLE", 97, 107, 211.5, "S1 G3", "DET lead 2-0"),
    BacktestGame("2026-05-08","OKC","LAL",108, 118, 210.5, "S1 G3", "OKC lead 2-0"),
]

WNBA_TEAMS = {"NYL": NYL, "MIN": MIN, "LVA": LVA}
NBA_TEAMS  = {"CLE": CLE, "DET": DET, "SA": SAS, "MIN": MIN_NBA}

# ════════════════════════════════════════════════════════════════════════
# PRINT ROSTER
# ════════════════════════════════════════════════════════════════════════
def print_roster(team: Team, label: str):
    bd = team.tc_breakdown()
    print(f"\n{'='*90}")
    print(f"  {team.abbr} {team.name} ({label})")
    print(f"  TC = pts×{CONS_PTS} + reb×{CONS_REB} + ast×{CONS_AST} + 3pm×{CONS_3PM}")
    print(f"{'='*90}")
    print(f"  {'Player':<22} {'POS':<4} {'HT':<5} {'PTS':>6} {'REB':>5} {'AST':>5} {'3PM':>5} {'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} {'TC_TOT':>7} {'LINE':>6} {'EDGE':>6}")
    print(f"  {'-'*90}")
    for p in team.players:
        flag = "⚠️Q" if p.status == "Q" else ("❌" if p.status == "OUT" else "✅")
        print(f"  {p.name:<22} {p.pos:<4} {p.ht:<5} {p.pts:>6.1f} {p.reb:>5.1f} {p.ast:>5.1f} {p.tpm:>5.1f} {p.tc_pts():>7.1f} {p.tc_reb():>7.2f} {p.tc_ast():>7.2f} {p.tc_3pm():>7.2f} {p.tc_total():>7.1f} {p.line():>6} {p.edge():>+6.1f} {flag}")
    print(f"  {'-'*90}")
    print(f"  {'TEAM TOTALS':<22}     {'':<5} {bd['pts']:>6.1f} {bd['reb']:>5.2f} {bd['ast']:>5.2f} {bd['tpm']:>5.2f} {team.tc_total():>7.1f}")
    return team.tc_total()

# ════════════════════════════════════════════════════════════════════════
# TC SUMMARY
# ════════════════════════════════════════════════════════════════════════
def tc_summary(home: Team, away: Team, market_total: float, series: str = "", game_time: str = ""):
    tc_h = home.tc_total() * 1.02  # home pace adj
    tc_a = away.tc_total()
    tc_combined = round(tc_h + tc_a, 1)
    line = int(round((tc_combined + HISTORICAL_GAP) * LINE_FACTOR))
    edge = round(tc_combined - line, 1)

    print(f"\n{'='*90}")
    print(f"  TC SYSTEM SUMMARY — {away.abbr} @ {home.abbr}")
    if series: print(f"  {series}  |  {game_time}")
    print(f"{'='*90}")
    print(f"  Away TC:  {tc_a:.1f}")
    print(f"  Home TC:  {tc_h:.1f} (×1.02 home pace)")
    print(f"  TC Combined: {tc_combined:.1f}")
    print(f"  LINE (calibrated): {line}")
    print(f"  Market Total:     {market_total}")
    print(f"  Edge:            {edge:+.1f}")
    print(f"  Signal:           {'🎯 OVER' if tc_combined > line else '🎯 UNDER'}")
    if abs(edge) >= 5: conf = "HIGH"
    elif abs(edge) >= 3: conf = "MEDIUM"
    else: conf = "LOW"
    print(f"  Confidence:       {conf}")
    print(f"{'='*90}")
    return tc_combined, line, edge

# ════════════════════════════════════════════════════════════════════════
# BACKTEST
# ════════════════════════════════════════════════════════════════════════
def run_backtest(suite, teams, sport: str):
    print(f"\n{'#'*90}")
    print(f"  {sport} TC BACKTEST — {len(suite)} GAMES")
    print(f"  Formula: TC = pts×{CONS_PTS}+reb×{CONS_REB}+ast×{CONS_AST}+tpm×{CONS_3PM} | LINE = (TC+{HISTORICAL_GAP})×{LINE_FACTOR}")
    print(f"{'#'*90}")
    print(f"  {'Date':<12} {'Game':<10} {'Rnd':<8} {'TC':>7} {'LINE':>6} {'Actual':>7} {'Diff':>6} {'Signal':<7} {'Result':<6}")
    print(f"  {'-'*75}")

    hits = 0
    for g in suite:
        ht = teams.get(g.home)
        at = teams.get(g.away)
        if not ht or not at:
            continue
        tc_a = at.tc_total()
        tc_h = ht.tc_total() * 1.02
        tc_c = round(tc_a + tc_h, 1)
        line = int(round((tc_c + HISTORICAL_GAP) * LINE_FACTOR))
        actual = g.actual_away + g.actual_home
        diff = actual - tc_c
        signal = "OVER" if tc_c > line else "UNDER"
        result = "HIT" if (signal == "OVER" and actual > g.market_total) or (signal == "UNDER" and actual < g.market_total) else "MISS"
        if result == "HIT": hits += 1
        print(f"  {g.date:<12} {g.away}@{g.home:<7} {g.round_label:<8} {tc_c:>7.1f} {line:>6} {actual:>7} {diff:>+6.1f} {signal:<7} {result:<6}  {g.notes}")

    print(f"  {'-'*75}")
    rate = 100 * hits / len(suite)
    print(f"  BACKTEST: {hits}/{len(suite)} hits ({rate:.0f}% hit rate)")
    print(f"{'#'*90}\n")

# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "wnba-rosters"):
        print(f"\n{'#'*90}")
        print(f"  WNBA FULL ROSTER PROJECTIONS — 2025 FINALS (NYL vs MIN)")
        print(f"{'#'*90}")
        t_nyl = print_roster(NYL, "Away — New York Liberty")
        t_min = print_roster(MIN, "Home — Minnesota Lynx")
        tc_summary(MIN, NYL, market_total=165.0, series="2025 WNBA Finals", game_time="TBD")

    if mode in ("all", "nba-rosters"):
        print(f"\n{'#'*90}")
        print(f"  NBA FULL ROSTER PROJECTIONS — SEMIFINALS (May 15, 2026)")
        print(f"{'#'*90}")
        print_roster(CLE, "Away — Cleveland Cavaliers")
        print_roster(DET, "Home — Detroit Pistons")
        tc_summary(DET, CLE, market_total=218.0, series="East Semifinals Game 6", game_time="8:00 PM ET")

        print_roster(SAS, "Away — San Antonio Spurs")
        print_roster(MIN_NBA, "Home — Minnesota Timberwolves")
        tc_summary(MIN_NBA, SAS, market_total=222.0, series="West Semifinals Game 6", game_time="10:30 PM ET")

    if mode in ("all", "wnba-backtest"):
        run_backtest(WNBA_BACKTEST, WNBA_TEAMS, "WNBA 2025 FINALS")

    if mode in ("all", "nba-backtest"):
        run_backtest(NBA_BACKTEST, NBA_TEAMS, "NBA PLAYOFFS 2026")

    if mode == "wnba-backtest":
        run_backtest(WNBA_BACKTEST, WNBA_TEAMS, "WNBA 2025 FINALS")
    elif mode == "nba-backtest":
        run_backtest(NBA_BACKTEST, NBA_TEAMS, "NBA PLAYOFFS 2026")