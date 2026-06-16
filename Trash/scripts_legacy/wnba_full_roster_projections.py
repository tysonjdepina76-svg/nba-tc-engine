"""
WNBA Full Roster Projections — May 14, 2026 Night Games
TC prop-only: PTS, REB, AST, and 3PM each use stat × 0.85. TC does not apply to team/game totals.
Injury-adusted: OUT = 0, Q = × 0.55
"""

from dataclasses import dataclass
from typing import List, Dict

CONS_PTS_FACTOR = 0.85
LINE_FACTOR = 0.88
Q_FACTOR = 0.55

@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str = "ACTIVE"  # ACTIVE, Q (questionable), OUT


    def status_factor(self) -> float:
        if self.status == "OUT":
            return 0.0
        return Q_FACTOR if self.status == "Q" else 1.0

    def tc(self) -> float:
        if self.status == "OUT":
            return 0.0
        f = Q_FACTOR if self.status == "Q" else 1.0
        return round(self.pts * CONS_PTS_FACTOR * f, 1)

    def tc_line(self) -> float:
        if self.status == "OUT":
            return 0
        f = Q_FACTOR if self.status == "Q" else 1.0
        return round(self.pts * LINE_FACTOR * f)

    def edge(self) -> float:
        return round(self.tc() - self.tc_line(), 1)

@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]

    def starters(self) -> List[Player]:
        active = [p for p in self.players if p.status != "OUT"]
        return sorted(active, key=lambda p: p.tc(), reverse=True)[:5]

    def bench(self) -> List[Player]:
        active = [p for p in self.players if p.status != "OUT"]
        return sorted(active, key=lambda p: p.tc(), reverse=True)[5:]

    def tc_totals(self) -> dict:
        return {
            "pts": round(sum(p.tc() for p in self.players), 1),
            "reb": round(sum(p.reb * CONS_PTS_FACTOR * p.status_factor() for p in self.players), 1),
            "ast": round(sum(p.ast * CONS_PTS_FACTOR * p.status_factor() for p in self.players), 1),
            "3pm": round(sum(p.tpm * CONS_PTS_FACTOR * p.status_factor() for p in self.players), 1),
        }

    def starter_totals(self) -> dict:
        return {
            "pts": round(sum(p.tc() for p in self.starters()), 1),
            "reb": round(sum(p.reb * CONS_PTS_FACTOR * p.status_factor() for p in self.starters()), 1),
            "ast": round(sum(p.ast * CONS_PTS_FACTOR * p.status_factor() for p in self.starters()), 1),
            "3pm": round(sum(p.tpm * CONS_PTS_FACTOR * p.status_factor() for p in self.starters()), 1),
        }

    def bench_totals(self) -> dict:
        return {
            "pts": round(sum(p.tc() for p in self.bench()), 1),
            "reb": round(sum(p.reb * CONS_PTS_FACTOR * p.status_factor() for p in self.bench()), 1),
            "ast": round(sum(p.ast * CONS_PTS_FACTOR * p.status_factor() for p in self.bench()), 1),
            "3pm": round(sum(p.tpm * CONS_PTS_FACTOR * p.status_factor() for p in self.bench()), 1),
        }

    # Backward-compatible aliases: PTS prop totals only, not game/team totals.
    def tc_total(self) -> float:
        return self.tc_totals()["pts"]

    def tc_starters(self) -> float:
        return self.starter_totals()["pts"]

    def tc_bench(self) -> float:
        return self.bench_totals()["pts"]

    def tc_line(self) -> float:
        return round(sum(p.tc_line() for p in self.players))

# ── ROSTERS WITH ACTUAL MAY 14 INJURY STATUS ─────────────────────────────────

# NEW YORK LIBERTY
NYL = Team("NYL", "New York Liberty", [
    Player("Breanna Stewart",    "F", "6-4", 22.0, 9.5, 4.0, 2.5),
    Player("Sabrina Ionescu",    "G", "5-11", 20.0, 5.5, 6.5, 3.2, "OUT"),  # foot
    Player("Jonquel Jones",      "C", "6-6", 16.0, 9.0, 3.0, 1.0),
    Player("Betnijah Laney-Hamilton", "GF", "6-0", 14.0, 4.5, 3.5, 2.0),
    Player("Satou Sabally",      "F", "6-4", 13.0, 6.0, 4.0, 1.5, "OUT"),  # confirmed
    Player("Marine Johannes",   "G", "5-10", 11.0, 3.0, 4.0, 2.5),
    Player("Leonie Fiebich",     "F", "6-4", 10.0, 5.0, 2.0, 1.5),
    Player("Rebecca Allen",      "GF", "6-2", 9.0, 3.5, 2.5, 1.8, "Q"),     # leg
    Player("Han Xu",            "C", "6-11", 8.5, 5.5, 1.5, 0.3),
    Player("Raquel Carrera",     "C", "6-3", 8.0, 5.0, 1.5, 0.5),
    Player("Julie Vanloo",       "G", "5-8", 8.0, 2.5, 5.5, 1.2),
    Player("Marine Fauthoux",   "G", "5-9", 7.5, 2.0, 5.0, 1.5, "OUT"),   # confirmed
    Player("Aubrey Griffin",     "GF", "6-1", 7.0, 3.5, 2.0, 1.0),
    Player("Rebekah Gardner",    "G", "6-1", 6.5, 3.0, 2.5, 1.0),
    Player("Alex Fowler",       "F", "6-2", 6.0, 4.0, 1.0, 0.3),
    Player("Pauline Astier",    "G", "5-11", 5.5, 2.0, 2.5, 0.8),
    Player("Seehia Ridard",     "FC", "6-2", 5.0, 4.0, 0.5, 0.0),
])

# PORTLAND FIRE
PDX = Team("PDX", "Portland Fire", [
    Player("Nika Mühl",         "G", "6-0", 12.5, 4.0, 6.0, 1.5),
    Player("Haley Jones",       "GF", "6-1", 11.5, 5.5, 3.5, 1.0),
    Player("Bridget Carleton",  "F", "6-2", 11.0, 5.0, 2.5, 1.5),
    Player("Megan Gustafson",   "C", "6-4", 10.5, 6.5, 2.0, 0.4),
    Player("Luisa Geiselsöder", "C", "6-4", 10.0, 6.0, 1.5, 0.3),
    Player("Teja Oblak",       "G", "5-8", 9.5, 3.0, 6.0, 1.5),
    Player("Kamiah Smalls",     "G", "5-10", 9.0, 3.0, 4.0, 1.2),
    Player("Emily Engstler",    "F", "6-1", 8.5, 5.5, 2.0, 0.5),
    Player("Sarah Ashlee Barker","G","6-0", 8.0, 3.5, 3.5, 1.2),
    Player("Sug Sutton",        "G", "5-8", 7.5, 2.5, 4.0, 1.0, "Q"),    # knee
    Player("Karlie Samuelson",  "G", "6-0", 7.0, 3.0, 2.5, 1.5),
    Player("Carla Leite",       "G", "5-9", 6.5, 2.5, 3.0, 1.0),
    Player("Nyadiew Puoch",     "F", "6-3", 6.0, 4.0, 1.5, 0.5),
    Player("Frieda Buhner",     "FC", "6-2", 5.5, 4.0, 1.0, 0.3),
    Player("Holly Winterburn",  "G", "5-11", 5.5, 2.0, 3.0, 1.0),
    Player("Iyana Martín",      "G", "5-9", 5.0, 2.0, 2.5, 0.8),
    Player("Serah Williams",    "F", "6-4", 4.5, 3.5, 0.5, 0.2),
])

# MINNESOTA LYNX
MIN = Team("MIN", "Minnesota Lynx", [
    Player("Napheesa Collier",  "F", "6-1", 20.0, 8.0, 3.5, 1.2, "OUT"),  # ankle
    Player("Kayla McBride",     "G", "5-11", 16.5, 4.5, 4.0, 2.5),
    Player("Natasha Howard",    "F", "6-2", 14.0, 6.5, 3.0, 1.2),
    Player("Olivia Miles",      "G", "5-10", 13.0, 5.0, 6.5, 1.5),
    Player("Courtney Williams", "G", "5-8", 12.0, 4.0, 4.5, 1.8),
    Player("Dorka Juhász",      "F", "6-5", 10.5, 6.5, 2.5, 0.8, "OUT"),  # foot
    Player("Liatu King",        "F", "5-11", 9.5, 5.0, 2.0, 0.5),
    Player("Maya Caldwell",     "G", "5-11", 8.5, 3.0, 3.5, 1.2),
    Player("Emese Hof",         "C", "6-3", 8.0, 5.5, 1.5, 0.3),
    Player("Antonia Delaere",   "G", "5-11", 7.5, 3.0, 3.0, 1.2),
    Player("Eliska Hamzova",    "G", "6-0", 7.0, 2.5, 2.5, 1.0),
    Player("Anastasiia Olairi Kosu","F","6-1",6.5, 4.0, 1.0, 0.4),
    Player("Emma Cechova",      "C", "6-4", 5.5, 4.0, 0.5, 0.3),
    Player("Nia Coffey",        "F", "6-1", 5.0, 3.0, 1.0, 0.5),
])

# DALLAS WINGS
DAL = Team("DAL", "Dallas Wings", [
    Player("Paige Bueckers",    "G", "6-0", 20.0, 5.0, 5.5, 2.8),
    Player("Arike Ogunbowale",  "G", "5-8", 18.5, 4.5, 4.0, 2.5),
    Player("Azurá Stevens",     "FC", "6-6", 13.5, 7.0, 2.0, 1.0),
    Player("Maddy Siegrist",    "F", "6-2", 12.5, 6.0, 1.5, 1.5),
    Player("Alanna Smith",      "F", "6-4", 11.5, 6.5, 2.5, 1.0),
    Player("Awak Kuier",        "F", "6-6", 10.5, 7.5, 1.5, 0.3, "OUT"),  # confirmed
    Player("Odyssey Sims",      "G", "5-8", 10.0, 3.0, 5.0, 1.5),
    Player("Jessica Shepard",   "F", "6-4", 10.0, 6.5, 3.0, 0.4),
    Player("Azzi Fudd",         "G", "5-11", 9.5, 2.5, 2.5, 1.5, "Q"),    # knee
    Player("Alysha Clark",      "F", "5-11", 9.0, 4.5, 2.0, 1.0),
    Player("Aziaha James",      "G", "5-10", 8.5, 3.0, 3.0, 1.2),
    Player("JJ Quinerly",       "G", "5-8", 8.0, 3.0, 3.5, 1.0),
    Player("Dulcy Fankam Mendjiadeu","FC","6-3",7.5,5.5, 1.0, 0.3),
    Player("Li Yueru",          "C", "6-7", 7.0, 5.0, 0.5, 0.0),
    Player("Costanza Verona",   "G", "5-6", 5.5, 2.0, 2.5, 0.8),
])

# ── PRINT FUNCTION ───────────────────────────────────────────────────────────

def print_roster(team: Team, market_total=0.0, market_spread=0.0):
    print(f"\n{'═'*80}")
    print(f"  {team.abbr} — {team.name}")
    injuries = [f"{p.name} {p.status}" for p in team.players if p.status != "ACTIVE"]
    if injuries:
        print(f"  ⚠ Injuries: {', '.join(injuries)}")
    print(f"{'═'*80}")

    print(f"\n  STARTERS (Top 5 by TC points)")
    print(f"  {'Player':<22} {'POS':<4} {'HT':<5} {'PTS':>6} {'REB':>5} {'AST':>5} {'3PM':>5} {'TC_PTS':>6} {'TC_REB':>6} {'TC_AST':>6} {'TC_3PM':>6}")
    print(f"  {'─'*75}")

    for p in team.starters():
        status_flag = " ⚠Q" if p.status == "Q" else (" ✗OUT" if p.status == "OUT" else "")
        print(f"  {p.name:<22} {p.pos:<4} {p.ht:<5} {p.pts:>6.1f} {p.reb:>5.1f} {p.ast:>5.1f} {p.tpm:>5.1f} {p.tc():>6.1f} {p.reb*p.status_factor()*CONS_PTS_FACTOR:>6.1f} {p.ast*p.status_factor()*CONS_PTS_FACTOR:>6.1f} {p.tpm*p.status_factor()*CONS_PTS_FACTOR:>6.1f}{status_flag}")

    stt = team.starter_totals()
    print(f"  {'─'*75}")
    print(f"  {'STARTERS PROP TOTALS':<46} {'':>8} {'':>5} {'':>5} {'':>5} {stt['pts']:>6.1f} {stt['reb']:>6.1f} {stt['ast']:>6.1f} {stt['3pm']:>6.1f}")

    print(f"\n  BENCH")
    bench = team.bench()
    if bench:
        print(f"  {'Player':<22} {'POS':<4} {'HT':<5} {'PTS':>6} {'REB':>5} {'AST':>5} {'3PM':>5} {'TC_PTS':>6} {'TC_REB':>6} {'TC_AST':>6} {'TC_3PM':>6}")
        print(f"  {'─'*75}")
        for p in bench:
            status_flag = " ⚠Q" if p.status == "Q" else (" ✗OUT" if p.status == "OUT" else "")
            print(f"  {p.name:<22} {p.pos:<4} {p.ht:<5} {p.pts:>6.1f} {p.reb:>5.1f} {p.ast:>5.1f} {p.tpm:>5.1f} {p.tc():>6.1f} {p.reb*p.status_factor()*CONS_PTS_FACTOR:>6.1f} {p.ast*p.status_factor()*CONS_PTS_FACTOR:>6.1f} {p.tpm*p.status_factor()*CONS_PTS_FACTOR:>6.1f}{status_flag}")

        bt = team.bench_totals()
        print(f"  {'─'*75}")
        print(f"  {'BENCH PROP TOTALS':<46} {'':>8} {'':>5} {'':>5} {'':>5} {bt['pts']:>6.1f} {bt['reb']:>6.1f} {bt['ast']:>6.1f} {bt['3pm']:>6.1f}")

    print(f"\n  {'─'*75}")
    tt = team.tc_totals()
    print(f"  {'TEAM PROP TC TOTALS':<46} {'':>8} {'':>5} {'':>5} {'':>5} {tt['pts']:>6.1f} {tt['reb']:>6.1f} {tt['ast']:>6.1f} {tt['3pm']:>6.1f}")

    # No TC vs market total here: TC is prop-only, not team/game-total math.


def print_game_summary(home: Team, away: Team, market_total: float, market_spread: float):
    home_tc = home.tc_totals()["pts"]
    away_tc = away.tc_totals()["pts"]
    combined_tc = home_tc + away_tc
    edge_vs_total = combined_tc - market_total if market_total else 0

    # Spread pick: negative spread means home is underdog, so pick away
    spread_pick = home.abbr if market_spread > 0 else away.abbr
    spread_fav = home.abbr if market_spread < 0 else away.abbr

    print(f"\n{'═'*80}")
    print(f"  GAME PROJECTION SUMMARY")
    print(f"  {away.name} @ {home.name}")
    print(f"  Market Total: {market_total} | Market Spread: {spread_fav} {abs(market_spread):.1f}")
    print(f"{'═'*80}")
    print(f"  {'Team':<6} {'TC PTS':>8} {'TC LINE':>9} {'EDGE':>7} {'START5 TC':>10} {'BENCH TC':>9}")
    print(f"  {'─'*55}")
    print(f"  {away.abbr:<6} {away_tc:>8.1f} {sum(p.tc_line() for p in away.players):>9} {away_tc - sum(p.tc_line() for p in away.players):>7.1f} {away.tc_starters():>10.1f} {away.tc_bench():>9.1f}")
    print(f"  {home.abbr:<6} {home_tc:>8.1f} {sum(p.tc_line() for p in home.players):>9} {home_tc - sum(p.tc_line() for p in home.players):>7.1f} {home.tc_starters():>10.1f} {home.tc_bench():>9.1f}")
    print(f"  {'─'*55}")
    print(f"  {'COMBINED TC':>24} {combined_tc:>8.1f}")
    print(f"  {'EDGE vs TOTAL ({market_total})':>40} {edge_vs_total:>7.1f}")
    print(f"  {'SPREAD PICK':>50} {spread_pick}")
    print(f"  {'START5 vs TOTAL %':>50} {(home.tc_starters()+away.tc_starters())/combined_tc*100:.1f}%")


# ── RUN FOR TONIGHT'S GAMES ──────────────────────────────────────────────────

# Game 1: NYL @ PDX — 10:00 PM ET, NYL -11.5, Total 176.5
print("\n" + "═"*80)
print("  GAME 1 — NEW YORK LIBERTY @ PORTLAND FIRE")
print("  Thu May 14, 2026 | 10:00 PM ET | Moda Center, Portland OR")
print("  Line: NYL -11.5 | Total: 176.5")
print("═"*80)

print_roster(NYL, market_total=176.5)
print_roster(PDX, market_total=176.5)
print_game_summary(PDX, NYL, market_total=176.5, market_spread=-11.5)

# Game 2: MIN @ DAL — 8:00 PM ET, DAL -6.5, Total ~167
print("\n" + "═"*80)
print("  GAME 2 — MINNESOTA LYNX @ DALLAS WINGS")
print("  Thu May 14, 2026 | 8:00 PM ET | College Park Center, Dallas TX")
print("  Line: DAL -6.5 | Total: 167.0")
print("═"*80)

print_roster(MIN, market_total=167.0)
print_roster(DAL, market_total=167.0)
print_game_summary(DAL, MIN, market_total=167.0, market_spread=-6.5)

# ── FULL LEAGUE STANDINGS ─────────────────────────────────────────────────────
TEAMS_ALL = {
    "ATL": ("Atlanta Dream", [
        Player("Angel Reese","F","6-4",15.5,9.0,2.5,0.8,"OUT"),
        Player("Rhyne Howard","G","6-2",15.0,4.5,3.5,2.0),
        Player("Allisha Gray","G","6-0",13.5,4.0,3.0,1.5),
        Player("Brionna Jones","F","6-3",13.0,7.0,2.0,0.5),
        Player("Jordin Canada","G","5-6",12.0,3.0,5.5,1.8),
        Player("Naz Hillmon","F","6-2",10.0,5.5,2.0,0.4),
        Player("Sika Koné","F","6-3",9.5,7.0,1.5,0.3),
        Player("Te-Hina Paopao","G","5-9",8.5,2.5,3.0,1.5),
        Player("Aaliyah Nye","GF","6-0",7.5,3.5,1.5,1.0),
        Player("Indya Nivar","G","5-10",7.0,2.5,2.0,0.8),
        Player("Isoborlase Borlase","G","5-11",6.5,2.5,2.0,0.8),
        Player("Amy Okonkwo","F","6-2",6.0,3.0,1.0,0.5),
        Player("Madina Okot","C","6-6",5.5,5.0,0.5,0.0),
        Player("Kejia Ran","G","6-2",5.0,2.0,1.5,0.6),
    ]),
    "CHI": ("Chicago Sky", [
        Player("Skylar Diggins","G","5-9",18.0,4.0,6.5,2.0),
        Player("Rachel Banham","G","5-10",14.0,3.5,4.0,2.2),
        Player("Kamilla Cardoso","C","6-7",13.5,8.0,2.0,0.5),
        Player("DiJonai Carrington","GF","5-11",12.5,4.5,3.0,1.5),
        Player("Rickea Jackson","F","6-2",12.0,5.0,1.5,0.8),
        Player("Natasha Cloud","G","5-10",11.5,4.5,6.0,1.2),
        Player("Courtney Vandersloot","G","5-8",10.5,3.0,5.5,1.5),
        Player("Azurá Stevens","FC","6-6",10.0,5.5,1.5,0.8),
        Player("Elizabeth Williams","FC","6-3",9.0,6.0,1.5,0.3),
        Player("Jacy Sheldon","G","5-10",8.5,3.0,3.0,1.0),
        Player("Aicha Coulibaly","G","6-0",7.5,3.0,2.0,0.8),
        Player("Gabriela Jaquez","G","6-0",6.5,3.0,1.5,0.8),
        Player("Sydney Taylor","G","5-9",6.0,2.0,2.5,0.8),
        Player("Maddy Westbeld","F","6-3",5.5,4.0,1.0,0.5),
    ]),
    "CON": ("Connecticut Sun", [
        Player("Brittney Griner","C","6-9",17.5,9.0,2.5,0.5),
        Player("Aneesah Morrow","F","6-1",15.0,8.5,2.5,0.8),
        Player("Aaliyah Edwards","F","6-3",13.0,7.0,2.0,0.5),
        Player("Olivia Nelson-Ododa","C","6-5",11.5,7.0,2.5,0.8),
        Player("Diamond Miller","F","6-1",11.0,4.5,3.0,1.2),
        Player("Leila Lacan","G","5-11",10.5,3.5,4.0,1.8),
        Player("Saniya Rivers","G","6-1",10.0,4.0,3.0,1.0),
        Player("Kennedy Burke","GF","6-1",9.5,4.0,2.0,1.0),
        Player("Hailey Van Lith","G","5-9",9.0,3.0,3.5,1.5),
        Player("Gianna Kneepkens","G","5-11",8.5,3.0,2.5,1.5),
        Player("Raegan Beers","F","6-4",8.0,5.0,1.0,0.3),
        Player("Charlisse Leger-Walker","G","5-10",7.5,3.0,3.5,1.2),
        Player("Ashlon Jackson","G","6-0",7.0,2.5,2.0,1.0),
        Player("Nell Angloma","F","6-1",5.5,3.5,1.0,0.3),
    ]),
    "GSV": ("Golden State Valkyries", [
        Player("Gabby Williams","F","5-11",14.0,5.5,4.0,1.8),
        Player("Tiffany Hayes","G","5-10",13.0,4.0,3.5,2.0),
        Player("Kiah Stokes","C","6-3",10.5,8.0,1.5,0.0),
        Player("Kayla Thornton","F","6-1",10.0,6.0,2.0,1.0),
        Player("Iliana Rupert","C","6-4",9.5,5.5,1.5,0.3),
        Player("Kaila Charles","GF","6-1",9.0,4.5,2.5,1.2),
        Player("Janelle Salaün","F","6-2",8.5,4.5,1.5,1.5),
        Player("Veronica Burton","G","5-9",8.0,3.5,3.5,1.2),
        Player("Justė Jocytė","GF","6-0",7.5,3.5,2.0,1.0),
        Player("Cecilia Zandalasini","F","6-2",7.0,4.0,1.5,1.0),
        Player("Laeticia Amihere","F","6-3",6.5,4.0,1.0,0.3),
        Player("Miela Sowah","G","5-10",6.0,2.5,2.5,0.8),
        Player("Ndjakalenga Mwenentanda","G","6-2",5.5,2.5,2.0,0.8),
        Player("Kaitlyn Chen","G","5-9",5.5,2.0,3.0,0.8),
        Player("Ashten Prechtel","F","6-5",5.0,3.5,0.5,0.3),
    ]),
    "LVA": ("Las Vegas Aces", [
        Player("A'ja Wilson","C","6-4",26.0,11.5,3.0,0.8),
        Player("Jewell Loyd","G","5-11",20.0,4.5,4.0,2.8),
        Player("Chelsea Gray","G","5-11",15.5,4.0,6.5,2.0),
        Player("Kierstan Bell","F","6-1",13.0,5.5,2.5,1.5),
        Player("Jackie Young","G","6-0",12.5,4.5,4.0,2.0),
        Player("Cheyenne Parker-Tyus","F","6-4",11.5,6.5,2.0,0.4),
        Player("NaLyssa Smith","F","6-4",11.0,6.5,2.0,0.5),
        Player("Brianna Turner","FC","6-3",10.0,6.0,1.5,0.3),
        Player("Chennedy Carter","G","5-9",9.5,2.5,3.0,1.2),
        Player("Stephanie Talbot","F","6-2",8.5,4.5,2.5,0.8),
        Player("Dana Evans","G","5-6",8.0,2.0,3.5,1.2),
        Player("Janiah Barker","F","6-4",6.5,4.0,1.0,0.3),
    ]),
    "SEA": ("Seattle Storm", [
        Player("Ezi Magbegor","FC","6-6",15.5,8.5,2.0,0.5),
        Player("Zia Cooke","G","5-9",13.5,4.0,3.0,1.5),
        Player("Jade Melbourne","G","5-10",12.5,3.5,5.0,1.8),
        Player("Stefanie Dolson","C","6-5",12.0,7.0,3.0,0.5),
        Player("Jordan Horston","F","6-2",11.5,5.5,3.5,1.0),
        Player("Natisha Hiedeman","G","5-8",11.0,3.5,4.5,1.8),
        Player("Flau'jae Johnson","G","5-10",10.5,4.0,2.5,1.2),
        Player("Mackenzie Holmes","F","6-3",10.0,5.5,1.5,0.4),
        Player("Lexie Brown","G","5-9",9.5,3.0,3.5,1.8),
        Player("Katie Lou Samuelson","G","6-3",8.5,4.0,2.5,1.5),
        Player("Dominique Malonga","C","6-6",7.5,5.5,1.0,0.3),
        Player("Grace VanSlooten","F","6-3",7.0,4.5,1.0,0.3),
        Player("Taylor Thierry","GF","6-1",6.5,3.5,1.5,0.8),
        Player("Awa Fam","C","6-4",5.5,4.0,0.5,0.0),
        Player("Taina Mair","G","5-9",5.0,2.5,2.5,0.8),
    ]),
    "TOR": ("Toronto Tempo", [
        Player("Marina Mabrey","G","6-1",14.5,4.5,4.5,2.0),
        Player("Isabelle Harrison","F","6-5",12.5,7.5,2.0,0.5),
        Player("Kia Nurse","G","6-0",11.5,4.0,3.0,1.8),
        Player("Nyara Sabally","F","6-5",11.0,6.0,2.5,0.8),
        Player("Temi Fágbénlé","C","6-5",10.5,7.5,1.5,0.3),
        Player("Julie Allemand","G","5-10",10.0,3.0,5.5,1.5),
        Player("Brittney Sykes","G","5-11",10.0,3.5,4.0,1.5),
        Player("Kiki Rice","G","5-11",8.5,3.0,4.0,1.2),
        Player("Lexi Held","G","5-9",8.0,2.5,2.5,1.2),
        Player("Maria Conde","F","6-3",7.5,4.5,1.5,1.0),
        Player("Nikolina Milic","C","6-3",7.0,5.5,1.0,0.3),
        Player("Teonni Key","F","6-4",6.5,5.0,1.0,0.3),
        Player("Mariella Fasoula","C","6-4",6.0,4.5,0.5,0.5),
        Player("Laura Juškaitė","F","6-4",5.5,4.0,1.0,0.5),
        Player("Charlise Dunn","G","6-2",5.0,3.0,2.0,0.8),
        Player("Saffron Shiels","G","6-2",4.5,2.5,1.5,0.6),
    ]),
    "WAS": ("Washington Mystics", [
        Player("Kiki Iriafen","F","6-3",15.5,8.0,2.5,0.8),
        Player("Sonia Citron","G","6-1",14.0,5.5,3.5,1.5),
        Player("Lucy Olsen","G","5-10",13.5,3.5,4.5,2.2),
        Player("Lauren Betts","C","6-7",13.0,7.5,1.5,0.3),
        Player("Shakira Austin","C","6-5",11.5,7.0,2.0,0.4),
        Player("Cotie McMahon","G","6-0",10.5,4.0,3.0,1.5),
        Player("Darianna Littlepage-Buggs","GF","6-1",9.5,5.0,2.5,1.0),
        Player("Rori Harmon","G","5-6",9.0,3.5,5.0,1.2),
        Player("Michaela Onyenwere","F","6-0",8.5,4.0,1.5,1.0),
        Player("Georgia Amoore","G","5-6",8.0,2.5,4.5,1.8),
        Player("Angela Dugalić","F","6-4",7.5,4.5,1.5,0.5),
        Player("Cassandre Prosper","G","6-3",6.5,4.0,1.5,0.5),
        Player("Alicia Florez Getino","G","5-9",6.0,2.5,3.0,1.0),
        Player("Alex Wilson","G","5-9",5.5,2.0,2.5,0.8),
    ]),
}

print("\n" + "═"*80)
print("  FULL LEAGUE TC POWER RANKINGS — May 14, 2026")
print("═"*80)
print(f"\n  {'Rank':<5} {'Abbr':<5} {'Team':<26} {'TC PTS':>8} {'TC LINE':>9} {'EDGE':>7} {'OUT':>4} {'Q':>3}")
print(f"  {'─'*70}")

rank = 1
all_team_data = []

# Active games first
for abbr, (name, players) in [
    ("NYL", ("New York Liberty", NYL.players)),
    ("PDX", ("Portland Fire", PDX.players)),
    ("MIN", ("Minnesota Lynx", MIN.players)),
    ("DAL", ("Dallas Wings", DAL.players)),
]:
    t = Team(abbr, name, players)
    tc = t.tc_total()
    line = t.tc_line()
    edge = tc - line
    out_count = sum(1 for p in t.players if p.status == "OUT")
    q_count = sum(1 for p in t.players if p.status == "Q")
    all_team_data.append((tc, abbr, name, tc, line, edge, out_count, q_count))

for abbr, (name, players) in TEAMS_ALL.items():
    t = Team(abbr, name, players)
    tc = t.tc_total()
    line = t.tc_line()
    edge = tc - line
    out_count = sum(1 for p in t.players if p.status == "OUT")
    q_count = sum(1 for p in t.players if p.status == "Q")
    all_team_data.append((tc, abbr, name, tc, line, edge, out_count, q_count))

all_team_data.sort(key=lambda x: x[2], reverse=True)
for tc_val, abbr, name, tc, line, edge, out_count, q_count in all_team_data:
    print(f"  {rank:<5} {abbr:<5} {name:<26} {tc:>8.1f} {line:>9} {edge:>7.1f} {out_count:>4} {q_count:>3}")
    rank += 1

print(f"\n  TC prop formula: each player stat PTS/REB/AST/3PM × 0.85. TC does NOT apply to team/game totals.")
print(f"  Q Factor: × 0.55 | OUT = 0")