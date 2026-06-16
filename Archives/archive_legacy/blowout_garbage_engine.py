"""
BLOWOUT TC ENGINE
================
Integrates into /api/tc as ?mode=blowout
or standalone via: python3 blowout_garbage_engine.py --game NYK CLE --margin 16

Key mechanics:
- Blowout threshold: Q4 margin ≥ 15  (CLE@NYK G2 was +16)
- Starter degradation: −4 min in blowout  (37.5 → 33.5 min)
- Bench degradation:  −9.5 min in blowout  (18.6 → 9.1 min)
- Bench 3PT multiplier GC: 1.49×  (G2 bench shot 5 more 3PM in 9.1 min = efficient garbage)
- Live prop scanner: scans bench UNDER edges when blowout is live
"""

import json, urllib.request
from dataclasses import dataclass, field
from typing import Optional

# ── Series data from CLE@NYK (3 games) ──────────────────────────────────────
MARGINS   = {401873341: 11, 401873342: 16, 401873343: 26}
BLOWOUT_M = 15   # margin threshold

SERIES_DATA = {
    # event_id: { date, away, home, margin, blowout, period_scores, players }
    "401873341": {
        "date": "2026-05-20", "away": "CLE", "home": "NYK",
        "margin": 11, "blowout": False, "type": "close",
        "period_scores": {"CLE": [25, 24, 28, 27], "NYK": [26, 28, 30, 31]},
    },
    "401873342": {
        "date": "2026-05-22", "away": "CLE", "home": "NYK",
        "margin": 16, "blowout": True, "type": "blowout",
        "period_scores": {"CLE": [28, 30, 35, 19], "NYK": [28, 31, 22, 28]},
        "garbage_notes": "CLE bench 18.6 min → 9.1 min; NYK bench 17.3 min → 12.0 min",
    },
    "401873343": {
        "date": "2026-05-24", "away": "CLE", "home": "NYK",
        "margin": 26, "blowout": True, "type": "blowout",
        "period_scores": {"CLE": [32, 35, 26, 14], "NYK": [36, 38, 27, 21]},
        "garbage_notes": "CLE starters rested Q4; NYK deep bench got run",
    },
}

# ── Minute degradation model ───────────────────────────────────────────────────
BASE_MIN_STARTER      = 36.0
BASE_MIN_BENCH_STARTER = 18.6   # bench avg in close games (G1)
BASE_MIN_DEEP_BENCH    = 10.0   # deep bench

BLOWOUT_STARTER_LOSS  = 4.0     # min lost when game blows out
BLOWOUT_BENCH_LOSS    = 9.5     # min lost for non-garbage bench
BLOWOUT_DEEP_BENCH_GAIN = 5.0  # min gained for deep bench in blowout

# Bench 3PM efficiency jump in blowout (G2: 4 bench 3PM in 9.1 min)
TPM_per_min_normal  = 0.20    # normal bench 3PM rate
TPM_per_min_blowout = 0.55    # garbage-time bench 3PM rate (1.49× boost)

STAT_DEG = {"pts": 0.85, "reb": 0.80, "ast": 0.65, "tpm": 0.80, "stl": 0.60, "blk": 0.70}
STAT_BLOWOUT_HEAVY = {"pts": 0.80, "reb": 0.75, "ast": 0.60, "tpm": 0.65, "stl": 0.55, "blk": 0.65}

# ── Models ────────────────────────────────────────────────────────────────────────
@dataclass
class Player:
    name: str; pos: str; ht: str
    pts: float; reb: float; ast: float; tpm: float; stl: float; blk: float
    status: str = "ACTIVE"; role: str = "BENCH"
    tc_pts: float = 0; tc_reb: float = 0; tc_ast: float = 0
    tc_3pm: float = 0; tc_stl: float = 0; tc_blk: float = 0
    line_pts: float = 0; line_reb: float = 0; line_ast: float = 0
    line_3pm: float = 0; line_stl: float = 0; line_blk: float = 0
    garbage_min: float = None; garbage_pts: float = 0; edge: float = 0
    is_garbage: bool = False
    actual_pts: float = 0; actual_min: float = 0
    _extra: dict = field(default_factory=dict)

    def __post_init__(self):
        for s in ["pts","reb","ast","tpm","stl","blk"]:
            tc = getattr(self, s) * 0.85
            ln = int(tc * 0.88)
            setattr(self, f"tc_{s if s!='tpm' else '3pm'}", round(tc, 1))
            setattr(self, f"line_{s if s!='tpm' else '3pm'}", ln)

    def project(self, margin: float, period: int = 4):
        is_blowout = margin >= BLOWOUT_M

        if self.role == "START":
            min_loss = BLOWOUT_STARTER_LOSS if is_blowout else 0
            adj_min = max(20, 36 - min_loss)
            factor = (adj_min / 36.0) * 0.80
            self.garbage_min = round(adj_min, 1)
            tc_adj = round(self.tc_pts * factor, 1)
            self.garbage_pts = tc_adj
            line_adj = max(1, int(tc_adj * 0.88))
            self.edge = round(tc_adj - line_adj, 1)
            return tc_adj

        elif self.role == "BENCH":
            season_avg = self.pts   # base season average

            if is_blowout and period == 4:
                # Degraded bench in blowout Q4
                # G2 data: Dean Wade 9.1 min actual → 2 3PM, 3 pts
                adj_min = min(18.0, 9.1 + 4.0)   # base 9.1 + up to 4 extra
                # PTS production: 36% of base TC in garbage Q4 (2.3/6.4 = 36%)
                pts_factor = 0.36
                base_pts = self.tc_pts * pts_factor
                extra_min = adj_min - 9.1
                extra_pts = extra_min * 0.44   # 0.44 pts/min in extended garbage
                tc_adj = round(base_pts + extra_pts, 1)
                # Market line for garbage: season avg * 0.85 (typical sportsbook floor)
                mkt_line = int(season_avg * 0.85)
                # Edge: positive = our proj is above market (OVER lean)
                #       negative = our proj is below market (UNDER lean)
                self.edge = round(tc_adj - mkt_line, 1)
                self.garbage_min = adj_min
                self.garbage_pts = tc_adj
                self.market_line = mkt_line
                self.is_garbage = True
                return tc_adj

            else:
                adj_min = self.garbage_min if self.garbage_min is not None else BASE_MIN_BENCH_STARTER
                factor = 0.85 if is_blowout else 1.0
                self.garbage_min = round(adj_min, 1)
                tc_adj = round(self.tc_pts * factor, 1)
                self.garbage_pts = tc_adj
                line_adj = max(1, int(tc_adj * 0.88))
                self.edge = round(tc_adj - line_adj, 1)
                return tc_adj

        else:
            adj_min = BASE_MIN_DEEP_BENCH
            factor = 0.75 if is_blowout else 0.90
            self.garbage_min = round(adj_min, 1)
            tc_adj = round(self.tc_pts * factor, 1)
            self.garbage_pts = tc_adj
            line_adj = max(1, int(tc_adj * 0.88))
            self.edge = round(tc_adj - line_adj, 1)
            return tc_adj

# ── Backtest engine ────────────────────────────────────────────────────────────
def build_roster(role="BENCH", n=5):
    return [
        Player("Tyler Dorsey",    "G", "6-5",  7.2, 3.1, 1.4, 2.0, 0.5, 0.1, role=role),
        Player("Craig",          "F", "6-5",  7.5, 4.2, 2.0, 1.9, 0.7, 0.2, role=role),
        Player("Wesley Matthews","G", "6-5",  5.5, 2.4, 1.3, 1.6, 0.4, 0.2, role=role),
        Player("Robin",          "C", "6-11", 9.0, 5.5, 0.8, 0.0, 0.3, 0.8, role=role),
        Player("Moritz",         "F", "6-11", 3.5, 2.5, 0.6, 0.9, 0.2, 0.3, role=role),
    ]

CLE_STARTERS = [
    Player("Darius Garland",    "G",  "6-1", 18.0, 2.7, 6.5, 2.4, 0.9, 0.2, role="START"),
    Player("Donovan Mitchell",  "G",  "6-1", 22.0, 4.4, 4.8, 2.8, 1.6, 0.4, role="START"),
    Player("Max Strus",        "F",  "6-5", 12.0, 4.7, 3.5, 3.0, 0.7, 0.3, role="START"),
    Player("Evan Mobley",       "F",  "6-11",16.0,8.5,3.0,1.0,0.7,1.4, role="START"),
    Player("Jarrett Allen",     "C",  "6-9", 14.0,7.2,2.0,0.2,0.6,1.2, role="START"),
]
CLE_BENCH = [
    # Only players who got real minutes in G2 blowout
    Player("Dean Wade",        "F",  "6-9",  5.3, 3.6, 1.1, 1.2, 0.6, 0.4, role="BENCH", garbage_min=9.1),
    Player("Isaac Okoro",      "G",  "6-5",  7.2, 3.3, 2.2, 0.8, 0.8, 0.2, role="BENCH", garbage_min=5.0),
    Player("Ty Jerome",        "G",  "6-5",  8.0, 2.5, 3.5, 2.0, 0.5, 0.1, role="BENCH", garbage_min=8.0),
    Player("Tristan Enaruna",  "F",  "6-9",  5.5, 3.3, 1.0, 0.8, 0.4, 0.2, role="BENCH", garbage_min=5.5),
    Player("Jaylon Tyson",     "G",  "6-5",  6.5, 2.5, 2.0, 1.5, 0.5, 0.2, role="BENCH", garbage_min=6.5),
]

NYK_STARTERS = [
    Player("Jalour Brunson",    "G",  "6-2", 26.0,3.2,5.9,2.2,0.9,0.2, role="START"),
    Player("Solomon Hill",      "F",  "6-6", 7.5, 5.0,2.5,1.2,0.8,0.3, role="START"),
    Player("OG Anunoby",       "F",  "6-7", 16.0,4.5,2.0,2.2,1.2,0.5, role="START"),
    Player("Julius Randle",    "F",  "6-8", 22.0,8.0,5.0,1.9,0.6,0.5, role="START"),
    Player("Karl-Anthony Towns","C",  "7-0", 24.0,10.0,3.5,1.8,0.6,1.3, role="START"),
]
NYK_BENCH = [
    Player("Miles McBride",    "G",  "6-2", 11.0,2.5,3.5,2.8,0.9,0.2, role="BENCH", garbage_min=8.5),
    Player("Jacob Topp",       "F",  "6-9", 5.0, 3.5,1.0,1.2,0.3,0.3, role="BENCH", garbage_min=6.0),
    Player(" Cameron",        "G",  "6-3", 8.0, 2.0,2.5,2.0,0.4,0.1, role="BENCH", garbage_min=4.0),
    Player("Jerome",          "C",  "6-11",5.0,4.0,1.5,0.0,0.2,0.8, role="BENCH", garbage_min=4.5),
    Player("Robinson",         "F",  "6-9", 4.5, 3.0,1.0,0.8,0.2,0.3, role="BENCH", garbage_min=3.0),
]

def tc_combined(team):
    return round(sum(getattr(p,'tc_pts',0) for p in team), 1)

def project_game(away_players, home_players, margin, period=4):
    is_blowout = margin >= BLOWOUT_M
    for p in away_players + home_players:
        p.project(margin, period)

    a_tc = tc_combined(away_players)
    h_tc = tc_combined(home_players)
    a_line = int(a_tc * 0.88)
    h_line = int(h_tc * 0.88)
    a_edge = round(a_tc - a_line, 1)
    h_edge = round(h_tc - h_line, 1)
    combined = a_tc + h_tc
    line = int(combined * 0.88)
    edge = round(combined - line, 1)

    signal = ("UNDER" if edge < -3.0 else "OVER" if edge > 3.0 else "PASS")
    return {
        "away_tc": a_tc, "away_line": a_line, "away_edge": a_edge,
        "home_tc": h_tc, "home_line": h_line, "home_edge": h_edge,
        "combined_tc": combined, "market_line": line, "edge": edge,
        "signal": signal,
        "type": ("BLOWOUT" if is_blowout else "CLOSE"),
        "period": period, "margin": margin,
    }

def garbage_candidates(bench_players, margin):
    is_blowout = margin >= BLOWOUT_M
    if not is_blowout:
        return []
    candidates = []
    for p in bench_players:
        p.project(margin, 4)
        candidates.append({
            "player": p.name, "pos": p.pos, "role": "GARBAGE",
            "tc_pts": round(p.garbage_pts, 1),
            "market_line": p.market_line if hasattr(p, 'market_line') and p.market_line else max(1, int(p.line_pts * 0.85)),
            "edge": p.edge,
            "garbage_min": p.garbage_min,
            "blowout_edge_shaved": round(p.tc_pts - p.garbage_pts, 1),
            "verdict": ("STRONG UNDER" if p.edge <= -3 else "LEAN UNDER" if p.edge < 0 else "NO BET"),
        })
    candidates.sort(key=lambda x: x["edge"])
    return candidates

def run_backtest():
    results = []
    all_garbage = []

    for event_id, gd in SERIES_DATA.items():
        margin = abs(MARGINS[int(event_id)])
        away = CLE_STARTERS + CLE_BENCH if gd["away"] == "CLE" else NYK_STARTERS + NYK_BENCH
        home = NYK_STARTERS + NYK_BENCH if gd["home"] == "NYK" else CLE_STARTERS + CLE_BENCH

        proj = project_game(away, home, margin)
        gc = garbage_candidates([p for p in home + away if p.role == "BENCH"], margin)

        results.append({
            "game": gd["date"],
            "matchup": f"{gd['away']}@{gd['home']}",
            "margin": margin,
            **proj,
            "garbage_candidates": gc,
        })
        all_garbage.extend([{**g, "game": gd["date"]} for g in gc])

    print(f"\n{'='*60}")
    print(f"CLE@NYK BLOWOUT BACKTEST — {len(results)} games")
    print(f"{'='*60}")
    for r in results:
        mt = r["type"][0]
        gc = r["garbage_candidates"]
        print(f"\n  {r['matchup']} {r['game']}  [margin={r['margin']}] {mt}")
        print(f"    COMBINED TC={r['combined_tc']}  LINE={r['market_line']}  EDGE={r.get('edge',0)} → {r['signal']}")
        if gc:
            print(f"    GARBAGE PROPS ({len(gc)} legs):")
            for g in gc:
                print(f"      {g['player']:<20} TC={g['tc_pts']:>5}  LINE={g.get('market_line',g.get('line_pts',0))}  EDGE={g['edge']:>+5}  → {g['verdict']}")
        else:
            print(f"    No garbage props")

    print(f"\n{'-'*60}")
    print(f"STACKED GARBAGE LEGS across series: {len(all_garbage)}")
    for ag in all_garbage:
        print(f"  {ag['game']}  {ag['player']:<20} {ag['role']}  MIN={ag['garbage_min']}  TC={ag['tc_pts']}  LINE={ag.get('market_line',ag.get('line_pts',0))}  EDGE={ag['edge']:>+5}  → {ag['verdict']}")

    under_legs = [g for g in all_garbage if "UNDER" in g["verdict"]]
    print(f"\n  UNDER legs: {len(under_legs)}/{len(all_garbage)}")
    return results

# ── Live prop scanner ────────────────────────────────────────────────────────
def scan_live_garbage_props(margin, bench_players):
    """
    Called during a live game when Q4 margin ≥ 15.
    Returns 4-6 leg UNDER parlay of bench players whose TC was shaved hardest.
    """
    is_blowout = margin >= BLOWOUT_M
    if not is_blowout:
        return {"mode": "normal", "blowout": False, "legs": []}

    legs = []
    for p in bench_players:
        p.project(margin, 4)
        if p.edge < 0:
            legs.append({
                "player": p.name, "pos": p.pos, "stat": "PTS",
                "tc_proj": round(p.garbage_pts, 1),
                "market_line": p.market_line,
                "edge": p.edge,
                "garbage_min": p.garbage_min,
                "verdict": "UNDER",
            })

    legs.sort(key=lambda x: x["edge"])
    best = legs[:6]
    total_edge = round(sum(x["edge"] for x in best), 1)
    return {
        "mode": "GARBAGE",
        "blowout": True,
        "margin": margin,
        "legs": best,
        "legs_count": len(best),
        "combined_edge": total_edge,
        "strategy": "stack bench UNDER — game pace slowed + defense relaxed = lower 4Q totals",
    }

if __name__ == "__main__":
    import sys
    if "--game" in sys.argv:
        idx = sys.argv.index("--game")
        team = sys.argv[idx+1]
        margin = int(sys.argv[sys.argv.index("--margin")+1]) if "--margin" in sys.argv else 16
        bench = NYK_BENCH if team == "NYK" else CLE_BENCH
        print(f"\n=== {team} LIVE GARBAGE PROP SCAN — margin={margin} ===\n")
        result = scan_live_garbage_props(margin, bench)
        print(f"Mode: {result['mode']}")
        print(f"Blowout: {result['blowout']}")
        for leg in result["legs"]:
            print(f"  {leg['player']:<20} TC={leg['tc_proj']:>5}  LINE={leg['market_line']}  EDGE={leg['edge']:>+5}  MIN={leg['garbage_min']}")
        print(f"\n  Combined edge: {result['combined_edge']}  |  Legs: {result['legs_count']}")
    else:
        run_backtest()
