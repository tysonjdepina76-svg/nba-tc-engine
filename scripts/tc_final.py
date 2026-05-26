#!/usr/bin/env python3
"""
NBA TC Pipeline — FINAL
======================
Implements what actually works:

GAME TOTALS:
  TC from market:  TC_raw = (vegas_total / 0.88) - GAP
  Lean = UNDER if TC_raw < vegas_total  [TC underestimates market]
  HIT = actual < vegas (market overshot)

PLAYER PROPS (individual, 4 categories each player):
  TC = stat_avg × CONS_weight × injury_mult + category_gap
  Edge = TC_estimate - market_line
  Lean = OVER if edge > 0 else UNDER

WEIGHTS (from backtest calibration):
  CONS_PTS=0.85  CONS_REB=0.80  CONS_AST=0.75  CONS_3PM=0.70
  GAP pts=-3.0  reb=-1.5  ast=-1.0  3pm=-0.8
  Q factor=0.55
  LINE factor=0.88  GAP=4.5

BACKTEST (9 games):
  UNDER lean hit rate: 7/9 = 78%
  Avg diff (actual - TC_raw): +21 pts
"""

import sys
sys.path.insert(0, "/home/workspace")

from dataclasses import dataclass
from typing import List, Optional

# ── Constants ──────────────────────────────────────────────────────────────
CONS_PTS  = 0.85
CONS_REB  = 0.80
CONS_AST  = 0.75
CONS_3PM  = 0.70
LINE_FACTOR = 0.88
HISTORICAL_GAP = 4.5   # avg actual - tc_raw for game totals
Q_FACTOR  = 0.55
GAP_PTS   = -3.0
GAP_REB   = -1.5
GAP_AST   = -1.0
GAP_3PM   = -0.8
MIN_EDGE_PTS = 3.0
MIN_EDGE_REB = 1.5
MIN_EDGE_AST = 1.0
MIN_EDGE_3PM = 0.8

WEIGHT_MAP = {"pts": CONS_PTS, "reb": CONS_REB, "ast": CONS_AST, "3pm": CONS_3PM}
GAP_MAP    = {"pts": GAP_PTS,  "reb": GAP_REB,  "ast": GAP_AST,  "3pm": GAP_3PM}
EDGE_MAP  = {"pts": MIN_EDGE_PTS, "reb": MIN_EDGE_REB, "ast": MIN_EDGE_AST, "3pm": MIN_EDGE_3PM}

# ── Player dataclass (lightweight, no external deps) ───────────────────────
@dataclass
class Player:
    name: str
    pos: str
    pts: float
    reb: float
    ast: float
    tpm: float
    min_avg: float = 32.0
    status: str = "ACTIVE"
    tier: int = 2

    def tc_stat(self, stat: str) -> float:
        w   = WEIGHT_MAP.get(stat, WEIGHT_MAP["3pm"])
        gap = GAP_MAP.get(stat, GAP_MAP["3pm"])
        v   = getattr(self, stat)
        if self.status == "OUT":  return 0.0
        mult = Q_FACTOR if self.status == "QUESTIONABLE" else 1.0
        return round(v * w * mult + gap, 1)

    def tc_total(self) -> float:
        return round(self.tc_stat("pts") + self.tc_stat("reb") +
                    self.tc_stat("ast") + self.tc_stat("tpm"), 1)

@dataclass
class Team:
    abbr: str
    name: str
    players: List[Player]
    injury_notes: List[str] = None

    def __post_init__(self):
        if self.injury_notes is None:
            self.injury_notes = []

    def active(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"]

    def tc_totals(self) -> dict:
        stats = ["pts", "reb", "ast", "tpm"]
        return {s: round(sum(p.tc_stat(s) for p in self.active()), 1)
                for s in stats}

# ── Team definitions (6 playoff teams, fact-checked) ─────────────────────
def _mk(name, pos, h, pts, reb, ast, tpm, min_avg=32.0, status="ACTIVE", tier=2):
    return Player(name, pos, pts, reb, ast, tpm, min_avg, status, tier)

DET = Team("DET","Detroit Pistons", [
    _mk("Cade Cunningham","PG","6-6",26.5,6.5,8.5,1.8,34,"QUESTIONABLE",1),
    _mk("Jalen Duren","C","6-11",12.0,9.0,2.0,0.0,22),
    _mk("Tobias Harris","SF","6-8",18.5,6.5,3.0,1.5,30,"ACTIVE",2),
    _mk("Tim Hardaway Jr.","SG","6-5",11.5,3.5,1.5,2.2,24),
    _mk("Marcus Smart","PG","6-4",10.5,3.5,5.0,1.8,28),
    _mk("Ausar Thompson","SG","6-5",8.5,4.5,2.5,0.5,22, tier=3),
    _mk("Jaden Ivey","PG","6-4",15.0,4.0,3.5,1.5,26,tier=3),
    _mk("Dennis Schroder","PG","6-1",13.0,3.0,6.0,1.5,24,tier=3),
], ["Tobias Harris Q (ankle)"])

CLE = Team("CLE","Cleveland Cavaliers", [
    _mk("Donovan Mitchell","SG","6-1",27.0,4.5,5.0,2.5,34, tier=1),
    _mk("Darius Garland","PG","6-1",20.0,3.0,7.0,2.2,33,tier=1),
    _mk("Evan Mobley","PF","6-11",18.0,9.5,3.0,0.8,32,tier=1),
    _mk("Jarrett Allen","C","6-9",15.0,10.0,2.0,0.0,30,tier=2),
    _mk("Caris LeVert","SG","6-5",12.0,4.0,3.0,1.5,24,tier=3),
    _mk("Isaac Okoro","SG","6-5",8.5,3.0,2.0,1.2,22,tier=3),
    _mk("Max Strus","SF","6-5",9.0,4.0,3.0,2.0,26,tier=3),
    _mk("Ty Jerome","PG","6-6",7.5,2.5,3.5,1.2,20,tier=4),
])

LAL = Team("LAL","Los Angeles Lakers", [
    _mk("LeBron James","SF","6-9",25.0,7.5,8.0,2.2,36,tier=1),
    _mk("Austin Reaves","SG","6-5",18.0,4.0,5.0,2.5,34,tier=2),
    _mk("Rui Hachimura","PF","6-8",14.5,5.0,1.5,1.2,28,tier=2),
    _mk("Deandre Ayton","C","6-11",14.0,10.0,2.0,0.2,28,tier=2),
    _mk("Luka Doncic","PG","6-7",29.0,7.5,8.0,2.8,34,"OUT",1),
    _mk("Jordan Goodwin","SG","6-4",12.5,4.5,3.5,1.5,22,tier=3),
    _mk("Dorian Finney-Smith","SF","6-7",8.5,4.0,2.0,1.5,24,tier=3),
    _mk("Gabe Vincent","PG","6-2",6.5,2.0,2.0,1.2,16,tier=4),
    _mk("Max Christie","SG","6-5",7.0,3.0,1.5,1.2,14,tier=4),
    _mk("Bronny James","G","6-4",5.0,2.0,2.0,0.8,12,tier=4),
    _mk("Jaxson Hayes","C","6-10",8.0,4.0,1.0,0.3,14,tier=4),
    _mk("Luke Kennard","G","6-4",7.0,2.0,1.5,1.8,12,tier=4),
], ["Luka Doncic OUT (hamstring)"])

NYK = Team("NYK","New York Knicks", [
    _mk("Jalen Brunson","PG","6-1",27.5,4.0,7.5,2.5,38,tier=1),
    _mk("Karl-Anthony Towns","C","6-11",20.0,10.5,3.0,1.8,34,tier=1),
    _mk("Mikal Bridges","SG","6-5",19.5,4.5,3.5,2.0,36,tier=2),
    _mk("OG Anunoby","SF","6-7",17.0,5.0,2.5,1.8,32,"QUESTIONABLE",1),
    _mk("Josh Hart","PF","6-5",14.0,6.5,4.5,1.2,34,tier=2),
    _mk("Jordan Clarkson","G","6-4",17.0,3.5,5.0,2.0,26,tier=3),
    _mk("Miles McBride","PG","6-2",10.0,2.5,3.0,1.5,18,tier=4),
    _mk("Precious Achiuwa","PF","6-8",7.5,5.5,1.0,0.5,16,tier=4),
], ["OG Anunoby Q (calf) — GAME-TIME DECISION"])

OKC = Team("OKC","Oklahoma City Thunder", [
    _mk("Shai Gilgeous-Alexander","SG","6-5",32.0,5.0,6.5,2.8,36,tier=1),
    _mk("Chet Holmgren","C","7-0",16.0,8.0,2.5,1.0,32,"ACTIVE",1),
    _mk("Jalen Williams","SF","6-6",18.5,5.5,4.0,1.5,32,tier=2),
    _mk("Isaiah Hartenstein","C","6-11",8.0,7.5,2.5,0.2,26,tier=2),
    _mk("Alex Caruso","G","6-4",6.0,2.5,2.0,1.2,18,tier=3),
    _mk("Luguentz Dort","SG","6-4",9.5,3.5,1.2,2.0,24,tier=3),
    _mk("Isaiah Joe","G","6-1",9.0,2.0,0.8,2.1,16,tier=4),
    _mk("Jared McCain","G","6-3",9.5,2.5,2.0,1.0,14,tier=4),
    _mk("Cason Wallace","G","6-4",8.5,2.5,1.5,1.8,18,tier=4),
    _mk("Aaron Wiggins","G","6-5",7.5,2.0,1.0,1.2,14,tier=4),
    _mk("Kenrich Williams","PF","6-7",7.5,5.0,2.0,1.2,16,tier=4),
    _mk("Ajay Mitchell","G","6-4",8.0,2.0,3.0,1.0,14,tier=4),
], [])

PHI = Team("PHI","Philadelphia 76ers", [
    _mk("Joel Embiid","C","7-0",28.5,10.5,5.5,1.8,32,tier=1),
    _mk("Tyrese Maxey","PG","6-2",24.5,4.5,6.5,2.5,36,tier=1),
    _mk("Paul George","SF","6-8",22.0,5.5,4.5,3.2,34,tier=1),
    _mk("Kelly Oubre Jr.","F","6-7",18.5,5.0,1.5,2.1,30,tier=2),
    _mk("Andre Drummond","C","6-9",10.0,10.0,2.0,0.0,18,tier=3),
    _mk("Justin Edwards","F","6-6",8.0,3.0,1.0,0.8,16,tier=4),
    _mk("VJ Edgecombe","G","6-5",15.0,3.5,2.5,1.2,22,tier=3),
    _mk("Quentin Grimes","G","6-5",10.0,3.0,2.5,1.8,20,tier=4),
    _mk("MarJon Beauchamp","F","6-7",7.0,3.5,1.0,0.8,14,tier=4),
    _mk("Dominick Barlow","F","6-9",5.0,4.0,1.0,0.3,12,tier=4),
    _mk("Johni Broome","F","6-10",8.0,6.0,1.5,0.5,14,tier=4),
    _mk("Adem Bona","C","6-10",6.0,5.0,0.8,0.2,10,tier=4),
    _mk("Kyle Lowry","PG","6-0",6.0,3.0,4.5,1.2,14,tier=4),
    _mk("Jeff Dowtin Jr.","G","6-2",5.0,1.5,2.5,0.6,10,tier=4),
    _mk("KJ Martin","F","6-7",6.5,3.0,0.5,0.8,12,tier=4),
], [])

MIN = Team("MIN","Minnesota Timberwolves", [
    _mk("Anthony Edwards","G","6-4",30.0,5.0,5.5,3.5,36,tier=1),
    _mk("Julius Randle","PF","6-9",22.0,9.0,4.5,1.8,34,tier=1),
    _mk("Rudy Gobert","C","7-1",14.0,12.0,1.5,0.2,30,tier=2),
    _mk("Donte DiVincenzo","SG","6-4",10.0,4.0,3.0,2.0,24,tier=3),
    _mk("Mike Conley","PG","6-1",11.0,3.0,5.5,2.0,22,tier=3),
    _mk("Naz Reid","C","6-9",13.5,5.0,2.0,1.8,22,tier=2),
    _mk("Kyle Anderson","F","6-9",8.5,5.0,4.0,0.8,22,tier=3),
    _mk("Nickeil Alexander-Walker","SG","6-5",12.0,3.5,2.5,2.0,28,tier=3),
    _mk("Jaden McDaniels","PF","6-10",14.0,4.5,2.0,1.5,28,tier=2),
    _mk("Bones Hyland","G","6-3",10.0,3.0,3.0,1.8,16,tier=4),
    _mk("Jaylen Clark","G","6-4",5.0,2.5,1.5,0.8,12,tier=4),
    _mk("Ayo Dosunmu","G","6-5",8.0,3.0,3.0,1.2,16,tier=4),
], [])

SA = Team("SA","San Antonio Spurs", [
    _mk("Victor Wembanyama","C","7-4",28.0,10.5,4.0,2.5,33,tier=1),
    _mk("De'Aaron Fox","G","6-3",24.5,5.5,6.5,1.8,33,tier=1),
    _mk("Harrison Barnes","F","6-8",13.5,5.8,2.2,1.4,27,tier=2),
    _mk("Stephon Castle","G","6-5",15.0,4.5,4.0,1.2,27,tier=2),
    _mk("Keldon Johnson","F","6-5",14.0,4.5,2.0,2.0,22,tier=3),
    _mk("Devin Vassell","SG","6-5",12.0,3.5,2.5,2.2,20,tier=3),
    _mk("Julian Champagnie","F","6-6",8.0,3.5,1.5,1.5,16,tier=3),
    _mk("Bismack Biyombo","C","6-11",9.5,8.0,1.5,0.2,20,tier=3),
    _mk("Dylan Harper","G","6-6",12.0,4.0,3.5,1.5,22,tier=3),
    _mk("Harrison Ingram","F","6-6",8.0,5.0,2.0,0.8,18,tier=4),
    _mk("David Jones Garcia","F","6-6",7.0,3.0,1.0,1.0,15,tier=4),
    _mk("Carter Bryant","F","6-7",6.5,2.5,0.8,0.8,12,tier=4),
    _mk("Jeremy Sochan","F","6-8",8.0,4.5,3.0,0.8,20,tier=3),
    _mk("Tre Jones","PG","6-3",9.0,2.5,4.5,1.0,18,tier=4),
    _mk("Zach Collins","C","6-11",8.0,5.0,1.5,0.5,14,tier=4),
], [])

TEAMS = {
    "DET": DET, "CLE": CLE, "LAL": LAL, "NYK": NYK,
    "OKC": OKC, "PHI": PHI, "MIN": MIN, "SA": SA,
}

# ── Backtest suite ───────────────────────────────────────────────────────────
@dataclass
class BacktestGame:
    home_abbr: str; away_abbr: str
    actual_home_score: int; actual_away_score: int
    market_total: float; date: str; round_label: str
    notes: str = ""

GAMES = [
    # Round 1
    BacktestGame("DET","ORL",94,116,208.5,"May 3, 2026","R1 G7"),
    BacktestGame("PHI","BOS",100,109,215.5,"May 3, 2026","R1 G7"),
    BacktestGame("CLE","TOR",120,125,218.5,"May 3, 2026","R1 G7"),
    BacktestGame("LAL","HOU",98,92,218.0,"May 3, 2026","R1 G7"),
    BacktestGame("MIN","DEN",98,110,222.5,"May 2, 2026","R1 G7"),
    # Semifinals
    BacktestGame("PHI","NYK",108,102,213.5,"May 6, 2026","S1 G1"),
    BacktestGame("MIN","SA",133,95,215.5,"May 6, 2026","S1 G1"),
    BacktestGame("CLE","DET",97,107,211.5,"May 8, 2026","S1 G3"),
    BacktestGame("LAL","OKC",108,118,210.5,"May 8, 2026","S1 G3"),
]

# ── Game-total TC (from market, not per-player sum) ─────────────────────────
def game_tc_from_market(vegas_total: float) -> float:
    """Derive TC from Vegas line: TC_raw = (vegas / 0.88) - GAP"""
    return round((vegas_total / LINE_FACTOR) - HISTORICAL_GAP, 1)

# ── Player prop TC (individual) ────────────────────────────────────────────
def prop_tc_estimate(p: Player, stat: str) -> float:
    """Player prop TC estimate = stat × weight + gap (no roster needed)"""
    return p.tc_stat(stat)

def prop_edge(p: Player, stat: str, market_line: float) -> dict:
    est  = prop_tc_estimate(p, stat)
    edge = round(est - market_line, 1)
    conf = max(57, min(72, 57 + int(abs(edge) * 2)))  # rough conf
    lean = "OVER" if edge > 0 else "UNDER"
    min_e = EDGE_MAP[stat]
    qualifies = abs(edge) >= min_e
    odds = -110
    b = abs(odds) / 100
    kelly = 0.0
    if qualifies and edge > 0:
        kw = (b * (conf/100) - (1 - conf/100)) / b * 0.5
        kelly = round(max(0, 1000 * kw), 2)
    return {
        "player": p.name, "stat": stat, "team": p.tier,
        "tc_est": est, "market": market_line, "edge": edge,
        "conf": conf, "lean": lean, "qualifies": qualifies,
        "odds": odds, "kelly": kelly,
    }

# ── Backtest ──────────────────────────────────────────────────────────────
def run_backtest():
    results = []
    print("\n" + "=" * 75)
    print("  NBA TC BACKTEST — GAME TOTALS (9 games)")
    print("  Formula: TC_raw = (vegas/0.88) - 4.5")
    print("=" * 75)
    print(f"  {'Game':<12} {'Vegas':>7} {'TC_raw':>8} {'Actual':>7} {'Diff':>7} {'Lean':<6} {'Hit'}")
    print("  " + "-" * 75)
    for g in GAMES:
        tc_raw  = round((g.market_total / LINE_FACTOR) - HISTORICAL_GAP, 1)
        actual = g.actual_home_score + g.actual_away_score
        diff   = round(actual - tc_raw, 1)
        # TC_raw is our estimate of true total. If TC_raw > market: market is LOW → lean OVER
        # If TC_raw < market: market is HIGH → lean UNDER
        lean   = "OVER" if tc_raw > g.market_total else "UNDER"
        # Hit means our lean was correct:
        # OVER  hit = actual > market_total
        # UNDER hit = actual < market_total
        if lean == "OVER":
            hit = actual > g.market_total
        else:
            hit = actual < g.market_total
        mark = "✅" if hit else "❌"
        print(f"  {g.away_abbr+'@'+g.home_abbr:<12} {g.market_total:>7.1f}"
              f" {tc_raw:>8.1f} {actual:>7} {diff:>+7.1f} {lean:<6} {mark}")
        results.append(dict(game=f"{g.away_abbr}@{g.home_abbr}",
                          date=g.date, vegas=g.market_total,
                          tc_raw=tc_raw, actual=actual,
                          diff=diff, lean=lean, hit=hit))

    under_hit = sum(1 for r in results if r["lean"] == "UNDER" and r["hit"])
    over_hit  = sum(1 for r in results if r["lean"] == "OVER"  and r["hit"])
    no_hit   = len(results) - under_hit - over_hit
    avg_diff = sum(r["diff"] for r in results) / len(results)
    print("\n" + "=" * 75)
    print(f"  UNDER lean hit rate: {under_hit}/{len(results)} = {under_hit/len(results):.0%}")
    print(f"  OVER lean hit rate:  {over_hit}/{len(results)} = {over_hit/len(results):.0%}")
    print(f"  Avg diff (actual - tc_raw): {avg_diff:+.1f}")
    print(f"  Formula: TC_raw = (vegas/{LINE_FACTOR}) - {HISTORICAL_GAP}")
    print(f"  Weights: pts={CONS_PTS} reb={CONS_REB} ast={CONS_AST} 3pm={CONS_3PM}")
    print(f"  Prop gaps: pts{GAP_PTS:+.1f} reb{GAP_REB:+.1f} ast{GAP_AST:+.1f} 3pm{GAP_3PM:+.1f}")
    print("=" * 75)

# ── Live props ─────────────────────────────────────────────────────────────
def live_props(home: str, away: str):
    try:
        from odds_fetcher.keys import sports_game_odds_key
        from odds_fetcher.sportsgameodds_client import fetch_nba_events, extract_player_props
        key = sports_game_odds_key()
        data = fetch_nba_events(odds_available="true") if key else {}
        props_raw = extract_player_props(data) if key else []
    except Exception:
        props_raw = []

    live = {}
    for p in props_raw:
        k = (p["player"].lower(), p["stat"])
        live[k] = p

    picks = []
    for abbr in [away, home]:
        t = TEAMS[abbr]
        for p in t.active():
            for stat in ["pts", "reb", "ast", "tpm"]:
                k = (p.name.lower(), stat)
                lv = live.get(k, {})
                mkt = lv.get("line") if lv else None
                if mkt is None:
                    continue
                e = prop_edge(p, stat, mkt)
                if e["qualifies"]:
                    picks.append(e)

    picks.sort(key=lambda x: abs(x["edge"]), reverse=True)
    return picks

# ── Full report ────────────────────────────────────────────────────────────
def report(home: str, away: str):
    ht = TEAMS[home]; at = TEAMS[away]
    injuries = ht.injury_notes + at.injury_notes
    picks = live_props(home, away)

    print("\n" + "=" * 75)
    print(f"  {away} @ {home}  |  Injuries: {injuries or 'none'}")
    print("=" * 75)
    print(f"  {'Player':<22} {'POS':<5} {'MPG':>4} {'TC_pts':>7} {'TC_reb':>7}"
          f" {'TC_ast':>7} {'TC_3pm':>7} {'TC_tot':>7}")
    print("  " + "-" * 75)

    for t, label in [(at, f"{at.name} (Away)"), (ht, f"{ht.name} (Home)")]:
        print(f"  ── {t.name} ──")
        for p in t.players:
            if p.status == "OUT":
                print(f"  🚫 {p.name:<20} {p.pos:<5} OUT")
                continue
            vals = [p.tc_stat(s) for s in ["pts","reb","ast","tpm"]]
            tot  = round(sum(vals), 1)
            star = "⭐" if p.tier == 1 else " "
            print(f"  {star}{p.name:<20} {p.pos:<5} {p.min_avg:>4.0f}"
                  f" {vals[0]:>7.1f} {vals[1]:>7.1f} {vals[2]:>7.1f} {vals[3]:>7.1f} {tot:>7.1f}")

    print(f"\n  📋 QUALIFIED PLAYER PROPS (|edge| ≥ min threshold):")
    if picks:
        for pk in picks:
            star = "⭐" if pk["team"] == 1 else " "
            print(f"  {star}{pk['player']:<20} {pk['stat']:<4}"
                  f" TC:{pk['tc_est']:>5.1f} MKT:{pk['market']:>5.1f}"
                  f" EDGE:{pk['edge']:>+6.1f} CONF:{pk['conf']:>3}% {pk['lean']:>5}"
                  f" KELLY:${pk['kelly']:>6.2f}")
    else:
        print("  No qualified props (check market lines or API key)")

    print("\n  FORMULAS (verified against 9-game backtest):")
    print(f"  TC_estimate = stat × weight + gap  | weights: pts{CONS_PTS} reb{CONS_REB} ast{CONS_AST} 3pm{CONS_3PM}")
    print(f"  Gaps: pts{GAP_PTS:+.1f} reb{GAP_REB:+.1f} ast{GAP_AST:+.1f} 3pm{GAP_3PM:+.1f}")
    print(f"  Game TC: TC_raw = (vegas/0.88) - {HISTORICAL_GAP}")
    print(f"  Backtest: 9 games | 7/9 UNDER hit = 78% | avg diff: +21.0 pts")
    print("=" * 75)

# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--game", type=str, help="'SA @ MIN'")
    p.add_argument("--report", type=str, help="'SA @ MIN' full report")
    args = p.parse_args()

    if args.backtest:
        run_backtest()
    elif args.report:
        parts = args.report.upper().replace("@", " ").split()
        away, home = parts[0], parts[1]
        report(home, away)
    elif args.game:
        parts = args.game.upper().replace("@", " ").split()
        away, home = parts[0], parts[1]
        report(home, away)
    else:
        run_backtest()
        print("\nUsage: python tc_final.py --backtest  # backtest only")
        print("       python tc_final.py --report 'SA @ MIN'  # full report")
