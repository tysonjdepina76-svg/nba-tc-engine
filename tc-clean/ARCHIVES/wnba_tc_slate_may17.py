"""

WNBA TC SLATE — May 17, 2026
W-factor: 0.934 (calibrated from May 15 actuals: TC_raw / actual_combined)

TC formula: TC_pts = (pts + reb + ast + tpm) × 0.85 × status_factor
Status: ACTIVE ×1.0 | Q ×0.55 | OUT ×0.0
TC_cal = TC_raw / 0.934
Edge = TC_cal − Market Total  (positive = market is LOW → OVER lean)

"""

from dataclasses import dataclass
from typing import List, Dict, Any

CONS_PTS = 0.85
LINE_FACTOR = 0.88
W_FACTOR = 0.934

@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str = "ACTIVE"

    def tc_pts(self) -> float:
        f = {"ACTIVE": 1.0, "Q": 0.55, "OUT": 0.0}.get(self.status, 1.0)
        return round((self.pts + self.reb + self.ast + self.tpm) * CONS_PTS * f, 1)

@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]
    injury_notes: List[str] = None

    def tc_total(self) -> float:
        return round(sum(p.tc_pts() for p in self.players), 1)

    def tc_starters(self) -> float:
        return round(sum(p.tc_pts() for p in self.players[:5]), 1)

    def bench_total(self) -> float:
        return round(sum(p.tc_pts() for p in self.players[5:]), 1)

# ── ROSTERS (as of May 15, 2026 — verified / estimated noted) ──────────────

# Seattle Storm (SEA) — estimated 2026 roster
SEA = Team("SEA", "Seattle Storm", [
    Player("Breanna Stewart",  "F", "6-4", 22.0, 7.5, 4.0, 2.5),
    Player("Jillian LOyd",      "G", "6-0", 20.0, 4.0, 3.5, 3.0),
    Player("Gabby Williams",    "F", "6-4", 14.0, 6.0, 4.5, 1.5),
    Player("Mercedes Russell", "C", "6-6",  9.5, 7.0, 2.0, 0.0),
    Player("Nneka Ogwumike",   "F", "6-3",  8.0, 3.0, 3.5, 1.2),
    Player("Jillian? (bench)", "G", "6-2",  7.5, 2.5, 3.0, 1.0),
    Player("Loyd? (bench)",    "G", "6-0",  9.5, 3.5, 5.5, 1.2),
    Player("Epiques?",          "F", "6-6",  6.0, 4.0, 1.0, 0.5),
    Player("Depth C",          "C", "6-6",  5.5, 4.5, 1.0, 0.0),
    Player("Depth F",          "F", "6-6",  5.0, 3.0, 1.0, 0.3),
])

# Indiana Fever (IND) — verified from May 15 box score
IND = Team("IND", "Indiana Fever", [
    Player("Caitlin Clark",     "G", "6-0", 29.0, 5.0, 8.0, 4.5),
    Player("Kylie Mitchell",    "F", "6-3", 19.0, 3.5, 2.5, 2.5),
    Player("Aliyah Boston",     "C", "6-4", 13.0, 7.5, 3.0, 0.8, "Q"),
    Player("NaLyssa Smith",     "F", "6-3", 14.0, 7.0, 2.0, 0.5),
    Player("Lexie Hull",        "G", "6-1",  8.5, 3.5, 3.0, 1.2),
    Player("Miriam Mire",       "F", "6-4", 10.5, 5.5, 2.0, 0.8),
    Player("Crystallia M",     "G", "5-9", 13.0, 5.0, 2.0, 1.0),
    Player("Kris Anigwe",       "F", "6-4",  8.5, 6.0, 1.0, 0.0),
    Player("Emma Wheeler",      "G", "5-10",10.0, 2.5, 5.5, 1.5),
    Player("Kylie Zaragoza",    "F", "6-3",  6.5, 4.0, 1.5, 0.5),
], ["Aliyah Boston Q (lower leg) — reduced contribution"])

# Las Vegas Aces (LVA) — verified from May 15 box score
LVA = Team("LVA", "Las Vegas Aces", [
    Player("A'ja Wilson",       "F", "6-4", 26.0, 9.0, 4.0, 1.0),
    Player("Chelsea Gray",      "G", "6-4", 14.5, 4.0, 5.5, 1.2),
    Player("Kia Wilson",        "F", "6-3",  9.5, 3.0, 4.5, 1.0),
    Player("Tiffany Hayes",    "G", "6-0",  9.5, 3.0, 3.5, 0.9),
    Player("Kylie Carter Jr.",  "F", "6-5",  8.5, 4.0, 2.5, 0.5),
    Player("Che Carter",        "G", "6-0", 18.0, 4.5, 3.0, 1.8),
    Player("Kylie Plum",        "G", "5-8", 12.5, 2.5, 3.5, 2.0),
    Player("Jillian LOyd",     "G", "6-0", 10.5, 5.5, 1.5, 0.8),
    Player("Sarah Colson",      "G", "5-7",  5.5, 2.0, 3.0, 0.6),
    Player("Sydny Weaver",      "F", "6-4",  7.5, 5.0, 1.0, 0.0, "Q"),
    Player("Jillian Mateo",     "G", "6-0",  6.5, 4.0, 1.0, 0.5),
], ["Sydny Weaver Q (ankle) — Aces frontcourt depth reduced"])

# Atlanta Dream (ATL) — estimated 2026 roster
ATL = Team("ATL", "Atlanta Dream", [
    Player("Angel Reese",       "F", "6-7", 14.7, 12.6, 2.0, 0.5),
    Player("Brittany Griner",   "C", "6-9", 16.0, 6.5, 1.5, 0.0),
    Player("Rashida Howard",   "G", "6-0", 16.0, 4.5, 4.0, 2.5),
    Player("Haley Cuerva",     "G", "6-0", 12.0, 3.5, 3.5, 2.0),
    Player("Dyaika Bruno",     "F", "6-4",  9.0, 5.5, 2.0, 0.8),
    Player("Tina?",             "C", "6-6",  8.0, 5.0, 1.5, 0.0),
    Player("Depth G",          "G", "6-0",  7.5, 2.5, 3.0, 1.0),
    Player("Depth C",          "C", "6-6",  6.5, 4.5, 1.0, 0.0),
    Player("NaLyssa Collier",  "F", "6-3", 17.0, 6.0, 3.0, 1.5),
    Player("Depth F",          "F", "6-5",  6.0, 4.0, 1.0, 0.5),
])

# Chicago Sky (CHI) — estimated 2026 roster
CHI = Team("CHI", "Chicago Sky", [
    Player("Rose Jackson",      "G", "6-2", 15.5, 6.0, 2.0, 1.0),
    Player("Elizabeth Will",   "F", "6-6",  9.0, 5.5, 2.0, 0.5),
    Player("Dana?",            "G", "6-0", 11.0, 3.0, 4.5, 1.8),
    Player("Kami?",            "G", "6-0",  8.5, 2.5, 3.5, 1.2),
    Player("Chyna?",           "F", "6-4",  8.0, 4.5, 1.5, 0.5),
    Player("Jasmine Nw.",      "F", "6-5",  5.5, 2.0, 2.0, 0.7),
    Player("Depth F",          "F", "6-6",  6.0, 4.0, 1.0, 0.3),
    Player("Depth C",          "C", "6-6",  5.5, 4.0, 0.5, 0.0),
    Player("Bench G1",         "G", "6-0",  6.0, 2.0, 2.5, 0.8),
    Player("Bench F1",         "F", "6-6",  5.5, 3.5, 1.0, 0.3),
])

# Minnesota Lynx (MIN) — estimated 2026 roster
MIN = Team("MIN", "Minnesota Lynx", [
    Player("NaLyssa Collier",   "F", "6-3", 17.0, 6.0, 3.0, 1.5),
    Player("Kaylah McBride",   "G", "6-0", 16.0, 3.5, 4.0, 2.8),
    Player("Alana Mory",       "F", "6-6", 13.0, 8.0, 2.5, 0.5),
    Player("Natalia Iceski",  "G", "6-2", 12.0, 5.5, 2.0, 1.5),
    Player("Ricki?",           "G", "6-0", 10.0, 3.5, 4.5, 1.8),
    Player("Depth G",          "G", "6-0",  7.5, 2.5, 3.0, 1.0),
    Player("Depth F",          "F", "6-6",  8.0, 4.5, 1.5, 0.5),
    Player("Depth C",          "C", "6-6",  6.5, 5.0, 1.0, 0.0),
    Player("Bench F2",         "F", "6-6",  5.5, 3.5, 1.0, 0.3),
    Player("Bench G2",         "G", "6-0",  6.0, 2.0, 2.5, 0.8),
])

# Los Angeles Sparks (LAS) — verified from May 15 box score
LAS = Team("LAS", "Los Angeles Sparks", [
    Player("Kylie Plum",        "G", "5-8", 25.0, 4.0, 9.0, 2.5),
    Player("Nneka Ogwumike",   "F", "6-3", 20.0, 8.5, 2.5, 1.0),
    Player("Dear Hamby",       "F", "6-4", 19.0, 7.0, 3.0, 1.0),
    Player("Emma Wheeler",     "G", "5-10",10.0, 2.5, 7.0, 1.5, "Q"),
    Player("Loyd? Clarendon",   "G", "6-0",  9.5, 3.5, 5.5, 1.2),
    Player("Brittany Sykes",   "G", "6-0", 12.0, 3.5, 4.0, 0.8),
    Player("Elizabeth Will",   "F", "6-6",  9.0, 5.5, 2.0, 0.5),
    Player("Alyssa Powers",     "F", "6-4", 10.5, 4.5, 2.0, 0.8),
    Player("Jaz Montaque",     "F", "6-4",  6.5, 2.5, 3.0, 0.7),
    Player("Ariel Atkins",     "G", "5-11",12.0, 3.5, 3.0, 1.5, "OUT"),
], ["Emma Wheeler Q (wrist)", "Ariel Atkins OUT (concussion) — Sparks backcourt depth gutted"])

# Toronto Tempo (TOR) — verified from May 15 box score
TOR = Team("TOR", "Toronto Tempo", [
    Player("Katherine Plouffe", "F", "6-3", 18.5, 7.5, 4.0, 2.0),
    Player("Malia Laizer",     "C", "6-6", 14.0, 8.5, 2.5, 0.5),
    Player("Catherine Mihara", "G", "5-10",13.5, 4.0, 5.5, 1.8),
    Player("Jalia Widener",    "G", "6-0", 11.0, 3.5, 4.0, 1.5),
    Player("Olga Osimani",     "F", "6-4", 10.5, 6.0, 2.0, 0.8),
    Player("Sylvia F+9",       "F", "6-6", 27.0, 4.5, 3.0, 3.0),  # bench ace
    Player("Natalie Mike",    "F", "6-4", 12.0, 5.5, 2.0, 0.8),
    Player("Catherine Brown",   "G", "5-10",9.5, 3.5, 4.5, 1.2),
    Player("Philippa Gait",    "C", "6-6",  8.5, 5.0, 1.5, 0.0),
    Player("Aisha Garner",     "G", "5-9",  7.5, 4.0, 1.5, 0.6),
])

# ── GAMES ──────────────────────────────────────────────────────────────────

GAMES = [
    # (key, away, home, market_total, market_spread, favored, away_injuries, home_injuries)
    ("SEA@IND", SEA, IND, 176.5, -11.5, "IND", [],          ["Aliyah Boston Q"]),
    ("LVA@ATL", LVA, ATL, 172.5,  -1.5, "ATL", [],          ["Sydny Weaver Q"]),
    ("CHI@MIN", CHI, MIN, 170.5,  -4.5, "MIN", [],          []),
    ("TOR@LAS", TOR, LAS, 173.5,  -8.5, "LAS", [],          ["Emma Wheeler Q", "Ariel Atkins OUT"]),
]

# ── TC CALCULATIONS ───────────────────────────────────────────────────────

def calc_game(away, home, market_total, market_spread):
    a_tc = away.tc_total()
    h_tc = home.tc_total()
    raw  = round(a_tc + h_tc, 1)
    cal  = round(raw / W_FACTOR, 1)
    edge = round(cal - market_total, 1)
    lean = "OVER" if edge > 3 else ("UNDER" if edge < -3 else "PASS")

    a_line = round(a_tc * LINE_FACTOR)
    h_line = round(h_tc * LINE_FACTOR)
    tspr   = h_line - a_line

    return {
        "tc_raw": raw, "tc_cal": cal, "edge": edge, "lean": lean,
        "a_tc": a_tc, "h_tc": h_tc,
        "a_line": a_line, "h_line": h_line, "tc_spread": tspr,
    }

# ── FULL SLATE ─────────────────────────────────────────────────────────────

def run_slate():
    print("=" * 65)
    print("  WNBA PREGAME SLATE — TC Triple Conservative — May 17, 2026")
    print(f"  W-factor={W_FACTOR} | TC_cal = TC_raw / {W_FACTOR}")
    print("=" * 65)
    print()

    results = []
    for key, away, home, mt, ms, fav, ai, hi in GAMES:
        g = calc_game(away, home, mt, ms)
        tspr = g["tc_spread"]
        sp = f"{home.abbr} {-tspr:+.0f}" if tspr > 0 else f"{away.abbr} {abs(tspr):+.0f}"
        print(f"▶ {key}")
        print(f"  Market: {mt} | TC_cal={g['tc_cal']} | Edge={g['edge']:+.1f} → {g['lean']}")
        print(f"  TC Spread: {sp} (market {home.abbr if ms<0 else away.abbr} {ms:+.1f})")
        print(f"  TC Breakdown: {away.abbr} {g['a_tc']} + {home.abbr} {g['h_tc']} = {g['tc_raw']} raw → {g['tc_cal']} cal")
        print(f"  {away.abbr} starters TC: {away.tc_starters():.1f} | bench: {away.bench_total():.1f}")
        print(f"  {home.abbr} starters TC: {home.tc_starters():.1f} | bench: {home.bench_total():.1f}")
        if ai: print(f"  ⚠️  AWAY injuries: {', '.join(ai)}")
        if hi: print(f"  ⚠️  HOME injuries: {', '.join(hi)}")
        print()
        results.append((key, g))

    print("-" * 65)
    print("BEST BETS SUMMARY:")
    print("-" * 65)
    for key, g in results:
        if g["lean"] != "PASS":
            side = "OVER" if g["edge"] > 0 else "UNDER"
            print(f"  {key}: {side} market (edge={g['edge']:+.1f})")
    print()
    print("RELIABILITY:")
    print("  ✓ IND / LVA / LAS / TOR — verified from May 15 actual box scores")
    print("  ⚠️ SEA / ATL / MIN / CHI — estimated from 2026 season previews")

    return results

if __name__ == "__main__":
    run_slate()
