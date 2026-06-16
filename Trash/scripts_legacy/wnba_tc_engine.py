"""
WNBA TC ENGINE — Triple Conservative Betting Model

Adapted from nba_tc_engine.py for women's basketball.
Same TC math, WNBA-specific rosters and factors.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

CONS_PTS = 0.85
CONS_REB = 0.12
CONS_AST = 0.10
CONS_3PM = 0.08
LINE_FACTOR = 0.88
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
MIN_EDGE = 1.0

@dataclass
class Player:
    name: str
    pos: str
    ht: str
    ppg: float
    rpg: float
    apg: float
    tpm: float
    status: str = "ACTIVE"

    def tc_pts(self) -> float:
        if self.status == "OUT":
            return self.ppg * OUT_FACTOR
        if self.status == "Q":
            return self.ppg * Q_FACTOR
        base = (self.ppg * CONS_PTS +
                self.rpg * CONS_REB +
                self.apg * CONS_AST +
                self.tpm * CONS_3PM)
        return round(base, 1)

    def tc_line(self) -> int:
        return round(self.tc_pts() * LINE_FACTOR)

    def tc_edge(self) -> float:
        return round(self.tc_pts() - self.tc_line(), 1)


@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]
    injury_notes: List[str] = None

    @property
    def starters(self) -> List[Player]:
        return self.players[:5]

    @property
    def bench(self) -> List[Player]:
        return self.players[5:]

    @property
    def bench_total(self) -> float:
        return sum(p.tc_pts() for p in self.bench)

    @property
    def tc_team_total(self) -> float:
        return sum(p.tc_pts() for p in self.players)

    def summary(self) -> Dict[str, Any]:
        return {
            "team": self.abbr,
            "starters": [{"name": p.name, "pos": p.pos, "tc_pts": p.tc_pts(),
                          "tc_line": p.tc_line(), "edge": p.tc_edge(),
                          "status": p.status}
                         for p in self.starters],
            "bench_total": round(self.bench_total, 1),
            "tc_team_total": round(self.tc_team_total, 1),
            "injuries": self.injury_notes or [],
        }


# ── TEAMS ─────────────────────────────────────────────────────────────────────

LVA = Team("LVA", "Las Vegas Aces", [
    # STARTERS
    Player("A'ja Wilson",     "F", "6-4", 45.0, 9.0, 4.0, 1.0, "ACTIVE"),
    Player("Chelsea Gray",   "G", "5-11",14.5, 4.0, 5.5, 1.2, "ACTIVE"),
    Player("Kia Wilson",     "G", "5-10", 9.5, 3.0, 4.5, 1.0, "ACTIVE"),
    Player("Tiffany Hayes",  "G", "5-10", 9.5, 3.0, 3.5, 0.9, "ACTIVE"),
    Player("Kenyon Carter Jr","F","6-2",  8.5, 4.0, 2.5, 0.5, "ACTIVE"),
    # BENCH
    Player("Chennedy Carter", "G", "5-9", 18.0, 4.5, 3.0, 1.8, "ACTIVE"),
    Player("Kelsey Plum",    "G", "5-9", 12.5, 2.5, 3.5, 2.0, "ACTIVE"),
    Player("Jackie Lou",     "F", "6-2", 10.5, 5.5, 1.5, 0.8, "ACTIVE"),
    Player("Sydney Colson",  "G", "5-8",  5.5, 2.0, 3.0, 0.6, "ACTIVE"),
    Player("Sydny Weaver",   "C", "6-5",  7.5, 5.0, 1.0, 0.0, "Q"),
    Player("Rabiya Mateo",   "F", "6-3",  6.5, 4.0, 1.0, 0.5, "ACTIVE"),
], ["Chennedy Carter (knee) — OUT", "Sydny Weaver (ankle) — Q"])

CT = Team("CT", "Connecticut Sun", [
    # STARTERS
    Player("Tyasha Harris",       "G", "5-10",13.5, 3.5, 5.5, 1.2, "ACTIVE"),
    Player("DiJonai Carrington",  "G", "6-0", 14.0, 4.5, 3.0, 1.0, "ACTIVE"),
    Player("Olivia Odogbo",      "F", "6-3", 10.5, 6.0, 2.5, 0.8, "ACTIVE"),
    Player("Brionna Jones",      "C", "6-3", 12.0, 7.0, 2.0, 0.5, "ACTIVE"),
    Player("Kyara Liggins",      "F", "6-2",  8.5, 5.0, 1.5, 0.6, "ACTIVE"),
    # BENCH
    Player("Saniya Rivers",      "G", "5-11", 9.5, 3.5, 3.0, 1.2, "ACTIVE"),
    Player("Kiki Easter",        "F", "6-4",  8.0, 5.5, 1.5, 0.4, "ACTIVE"),
    Player("Diamond Miller",     "G", "5-11", 7.5, 3.0, 2.5, 0.9, "ACTIVE"),
    Player("Megan Bing",         "C", "6-5",  6.5, 4.5, 1.0, 0.0, "ACTIVE"),
    Player("Jasmine Nwang",      "G", "5-9",  5.5, 2.0, 2.0, 0.7, "ACTIVE"),
    Player("Marina Hernandez",   "F", "6-3",  5.0, 3.5, 1.0, 0.3, "ACTIVE"),
], ["Sun short-handed — multiple players out", "Carrington (ankle) — Q"])

WAS = Team("WAS", "Washington Mystics", [
    # STARTERS
    Player("Sonia Citron",      "G", "6-0", 30.0, 5.0, 3.5, 3.0, "ACTIVE"),
    Player("Brittany Sykes",    "G", "5-9", 15.0, 4.0, 5.5, 1.0, "ACTIVE"),
    Player("Ariel Atkins",      "G", "5-11",12.0, 3.5, 3.0, 1.5, "OUT"),
    Player("Shakira Austin",    "C", "6-5", 14.5, 8.0, 3.0, 0.5, "ACTIVE"),
    Player("Keishna Murray",    "F", "6-2", 10.5, 5.5, 2.0, 0.8, "ACTIVE"),
    # BENCH
    Player("Kelsey Mitchell",   "G", "5-8", 24.0, 3.5, 2.5, 2.5, "ACTIVE"),
    Player("Mathilde Reding",   "F", "6-3",  8.5, 4.5, 1.5, 0.8, "ACTIVE"),
    Player("Emma Roderique",   "G", "5-10", 6.5, 2.5, 3.5, 0.7, "ACTIVE"),
    Player("Jacie Lamm",       "C", "6-4",  7.0, 5.0, 1.0, 0.0, "ACTIVE"),
    Player("Miya Davidson",     "F", "6-2",  5.5, 3.5, 1.0, 0.5, "ACTIVE"),
    Player("Aliyah Boston",     "C", "6-4",  9.0, 4.0, 2.0, 0.5, "Q"),
], ["Aliyah Boston — Q (lower leg)", "Ariel Atkins (concussion) — OUT"])

IND = Team("IND", "Indiana Fever", [
    # STARTERS
    Player("Caitlin Clark",       "G", "6-0", 32.0, 5.0, 8.0, 7.0, "ACTIVE"),
    Player("Kelsey Mitchell",     "G", "5-8", 24.0, 3.5, 2.5, 2.5, "ACTIVE"),
    Player("Aliyah Boston",       "C", "6-4",  9.0, 4.0, 2.0, 0.5, "Q"),
    Player("NaLyssa Smith",       "F", "6-2", 11.0, 6.5, 2.0, 0.5, "ACTIVE"),
    Player("Lexie Hull",         "G", "5-11", 8.0, 3.5, 3.0, 1.2, "ACTIVE"),
    # BENCH
    Player("Myisha Hines-Allen",  "F", "6-2", 10.5, 5.5, 2.0, 0.8, "ACTIVE"),
    Player("Cotie McMahon",      "G", "6-1", 13.0, 5.0, 2.0, 1.0, "ACTIVE"),
    Player("Kristine Anigwe",    "C", "6-4",  8.5, 6.0, 1.0, 0.0, "ACTIVE"),
    Player("Erica Wheeler",      "G", "5-6", 10.0, 2.5, 5.5, 1.5, "ACTIVE"),
    Player("Kaitlyn Zaragoza",   "F", "6-3",  6.5, 4.0, 1.5, 0.5, "ACTIVE"),
    Player("Shakira Austin",      "C", "6-5",14.5, 8.0, 3.0, 0.5, "ACTIVE"),
], ["Aliyah Boston — Q (lower leg, did not finish)", "Clark (leg) — active, full game"])

LAS = Team("LAS", "Los Angeles Sparks", [
    # STARTERS
    Player("Kelsey Plum",         "G", "5-9", 25.0, 4.0, 9.0, 2.5, "ACTIVE"),
    Player("Nneka Ogwumike",      "F", "6-2", 20.0, 8.5, 2.5, 1.0, "ACTIVE"),
    Player("Dearica Hamby",       "F", "6-2", 19.0, 7.0, 3.0, 1.0, "ACTIVE"),
    Player("Erica Wheeler",       "G", "5-6", 10.0, 2.5, 7.0, 1.5, "ACTIVE"),
    Player("Layshia Clarendon",   "G", "5-11", 9.5, 3.5, 5.5, 1.2, "ACTIVE"),
    # BENCH
    Player("Rickea Jackson",      "F", "6-3", 15.5, 6.0, 2.0, 1.0, "ACTIVE"),
    Player("Elizabeth Williams",  "C", "6-5",  9.0, 5.5, 2.0, 0.5, "ACTIVE"),
    Player("Brittany Sykes",      "G", "5-9", 12.0, 3.5, 4.0, 0.8, "ACTIVE"),
    Player("Aerial Powers",       "F", "6-1", 10.5, 4.5, 2.0, 0.8, "ACTIVE"),
    Player("Jazmine Montaque",   "G", "5-10", 6.5, 2.5, 3.0, 0.7, "ACTIVE"),
    Player("Ariel Atkins",        "G", "5-11",12.0, 3.5, 3.0, 1.5, "OUT"),
], ["Ariel Atkins (concussion) — OUT", "Wheeler (wrist) — Q"])

TOR = Team("TOR", "Toronto Tempo", [
    # STARTERS
    Player("Katherine Plouffe",  "F", "6-2", 18.5, 7.5, 4.0, 2.0, "ACTIVE"),
    Player("Megan Laizer",        "C", "6-5", 14.0, 8.5, 2.5, 0.5, "ACTIVE"),
    Player("Cassidy MihARA",      "G", "5-10",13.5, 4.0, 5.5, 1.8, "ACTIVE"),
    Player("Jaylyne Widener",     "G", "5-9", 11.0, 3.5, 4.0, 1.5, "ACTIVE"),
    Player("Olga Osimani",        "F", "6-3", 10.5, 6.0, 2.0, 0.8, "ACTIVE"),
    # BENCH
    Player("Sylvia F + 9",        "G", "5-8", 27.0, 4.5, 3.0, 3.0, "ACTIVE"),
    Player("Natalia Mike",        "F", "6-2", 12.0, 5.5, 2.0, 0.8, "ACTIVE"),
    Player("Christina Brown",     "G", "5-10", 9.5, 3.5, 4.5, 1.2, "ACTIVE"),
    Player("Paige Gait",          "C", "6-4",  8.5, 5.0, 1.5, 0.0, "ACTIVE"),
    Player("Aaliyah Garner",     "F", "6-1",  7.5, 4.0, 1.5, 0.6, "ACTIVE"),
    Player("Teanna Lewis",        "G", "5-8",  6.0, 2.5, 3.0, 0.8, "ACTIVE"),
], ["Tempo (0-3) — building roster early season", "No major injuries reported"])

TEAMS = {
    "LVA": LVA, "CT": CT, "WAS": WAS,
    "IND": IND, "LAS": LAS, "TOR": TOR,
}


def project_wnba_game(home_abbr: str, away_abbr: str,
                       market_total: float = 168.0,
                       market_spread: float = None,
                       series: str = "", game_time: str = "TBD",
                       bankroll: float = 1000.0) -> Dict[str, Any]:
    """Project a WNBA game with TC model."""
    home = TEAMS[home_abbr]
    away = TEAMS[away_abbr]

    tc_home = home.tc_team_total
    tc_away = away.tc_team_total
    tc_combined = tc_home + tc_away

    edge_total = tc_combined - market_total

    spread_pick, spread_line, total_lean = None, None, None
    if market_spread is not None:
        if tc_home > tc_away:
            spread_pick = home_abbr
            spread_line = -abs(market_spread)
        else:
            spread_pick = away_abbr
            spread_line = abs(market_spread)

    if tc_combined < market_total - 3:
        total_lean = "UNDER"
    elif tc_combined > market_total + 3:
        total_lean = "OVER"

    return {
        "matchup": f"{away_abbr} @ {home_abbr}",
        "series": series,
        "game_time": game_time,
        "market_total": market_total,
        "tc_combined": round(tc_combined, 1),
        "edge": round(edge_total, 1),
        "lean": total_lean,
        "home": home.summary(),
        "away": away.summary(),
        "system": {
            "CONS_PTS": CONS_PTS, "LINE_FACTOR": LINE_FACTOR,
            "Q_FACTOR": Q_FACTOR, "OUT_FACTOR": OUT_FACTOR,
            "MIN_EDGE": MIN_EDGE,
        },
    }


if __name__ == "__main__":
    import json

    print("=" * 60)
    print("WNBA TC PROJECTIONS — May 16, 2026")
    print("=" * 60)

    games = [
        ("LVA", "CT",  195.5, -6.5,  "Aces lead series 2-0"),
        ("WAS", "IND", 170.5, None,   "Mystics at Fever — OT thriller rematch"),
        ("LAS", "TOR", 167.5, -5.5,   "Sparks seek 2-0; Tempo still searching"),
    ]

    for home, away, total, spread, note in games:
        proj = project_wnba_game(home, away, market_total=total, market_spread=spread)
        print(f"\n{'─'*60}")
        print(f"  {proj['away']['team']} @ {proj['home']['team']}  |  {note}")
        print(f"  Market Total: {total}  |  TC Combined: {proj['tc_combined']}  |  Edge: {proj['edge']}  |  Lean: {proj['lean']}")
        print(f"  Spread: {spread} → pick {proj.get('spread_pick','N/A')}")
        for side, label in [("home","HOME"), ("away","AWAY")]:
            s = proj[side]
            print(f"\n  [{label}] {s['team']}  TC={s['tc_team_total']}")
            print(f"  {'Name':<22} {'Pos':<4} {'TC pts':>7} {'TC Line':>8} {'Edge':>6} {'Status':<6}")
            for p in s["starters"]:
                flag = "⚠️Q" if p["status"]=="Q" else ("❌OUT" if p["status"]=="OUT" else "")
                print(f"  {p['name']:<22} {p['pos']:<4} {p['tc_pts']:>7.1f} {p['tc_line']:>8} {p['edge']:>6.1f} {flag}")
            print(f"  {'Bench Total':<22} {'':<4} {s['bench_total']:>7.1f}")
            if s["injuries"]:
                print(f"  ⚠️  {s['injuries'][0]}")
        print()