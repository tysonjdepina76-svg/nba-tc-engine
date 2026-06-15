#!/usr/bin/env python3
"""
NBA TC Backtest — Clean
Uses actual Vegas lines from backtest suite.
TC formula for game totals: all active players, pts × 0.85 × 1.18.
Player props: stat × weight, gap applied per category.
"""
import sys
sys.path.insert(0, "/home/workspace")

from nba_tc_final import (
    CONS_PTS, CONS_REB, CONS_AST, CONS_3PM,
    LINE_FACTOR, HISTORICAL_GAP, PLAYOFF_MULT, Q_FACTOR,
    GAP_PTS, GAP_REB, GAP_AST, GAP_3PM,
    TEAMS, Player, BacktestGame,
)

GAMES = [
    BacktestGame("ORL","DET", 94, 116, 208.5, "May 3, 2026", "R1 G7"),
    BacktestGame("BOS","PHI", 100, 109, 215.5, "May 3, 2026", "R1 G7"),
    BacktestGame("CLE","TOR", 120, 125, 218.5, "May 3, 2026", "R1 G7"),
    BacktestGame("HOU","LAL", 98, 92, 218.0, "May 3, 2026", "R1 G7"),
    BacktestGame("MIN","DEN", 98, 110, 222.5, "May 2, 2026", "R1 G7"),
    BacktestGame("NYK","PHI", 108, 102, 213.5, "May 6, 2026", "S1 G1"),
    BacktestGame("SA","MIN", 133, 95, 215.5, "May 6, 2026", "S1 G1"),
    BacktestGame("CLE","DET", 97, 107, 211.5, "May 8, 2026", "S1 G3"),
    BacktestGame("LAL","OKC", 108, 118, 210.5, "May 8, 2026", "S1 G3"),
]

WEIGHT_MAP = {"pts": CONS_PTS, "reb": CONS_REB, "ast": CONS_AST, "3pm": CONS_3PM}
GAP_MAP = {"pts": GAP_PTS, "reb": GAP_REB, "ast": GAP_AST, "3pm": GAP_3PM}

def player_tc(p: Player) -> float:
    """Full 4-category TC for a player."""
    return round(
        (p.pts * CONS_PTS + p.reb * CONS_REB +
         p.ast * CONS_AST + p.tpm * CONS_3PM), 1)

def team_game_tc(abbr: str) -> float:
    """All active players, pts only, game-total style × playoff mult."""
    t = TEAMS[abbr]
    active = [p for p in t.players if p.status != "OUT"]
    raw = sum(p.pts for p in active) * CONS_PTS * PLAYOFF_MULT
    return round(raw, 1)

results = []
print("\n" + "=" * 78)
print("  NBA TC BACKTEST — GAME TOTALS + PLAYER PROPS")
print("=" * 78)
print(f"  Formula: TC = pts×{CONS_PTS}×{PLAYOFF_MULT} (all active players)")
print(f"  LINE = (TC_combined + {HISTORICAL_GAP}) × {LINE_FACTOR}")
print(f"  Props: TC = stat×weight + gap | GAP: pts{GAP_PTS:+.1f} reb{GAP_REB:+.1f} ast{GAP_AST:+.1f} 3pm{GAP_3PM:+.1f}")
print("=" * 78)
print(f"\n  {'Game':<10} {'TC_away':>8} {'TC_home':>8} {'TC_tot':>8}"
      f" {'LINE':>6} {'Actual':>7} {'Diff':>7} {'Lean':<6} {'Hit'}")
print("  " + "-" * 78)

for g in GAMES:
    atc = team_game_tc(g.away_abbr)
    htc = team_game_tc(g.home_abbr)
    tc_tot = round(atc + htc, 1)
    vegas = g.market_total
    diff = round(vegas - tc_tot, 1)
    lean = "UNDER" if diff > 0 else "OVER"
    # UNDER hit = vegas total > actual = our lean was right
    actual = g.actual_home_score + g.actual_away_score
    hit = (lean == "UNDER" and actual < vegas) or (lean == "OVER" and actual > vegas)
    mark = "✅" if hit else "❌"

    print(f"  {g.away_abbr+'@'+g.home_abbr:<10} {atc:>8.1f} {htc:>8.1f} {tc_tot:>8.1f}"
          f" {vegas:>6.1f} {actual:>7} {diff:>+7.1f} {lean:<6} {mark}")

    results.append({
        "game": f"{g.away_abbr}@{g.home_abbr}", "round": g.round_label,
        "tc_away": atc, "tc_home": htc, "tc_total": tc_tot,
        "vegas": vegas, "actual": actual, "diff": diff,
        "lean": lean, "hit": hit,
    })

print("\n" + "=" * 78)
under_count = sum(1 for r in results if r["lean"] == "UNDER" and r["hit"])
over_count = sum(1 for r in results if r["lean"] == "OVER" and r["hit"])
no_bet = len(results) - under_count - over_count
avg_diff = sum(r["diff"] for r in results) / len(results)
avg_tc = sum(r["tc_total"] for r in results) / len(results)
avg_actual = sum(r["actual"] for r in results) / len(results)

print(f"  Summary: {len(results)} games")
print(f"  UNDER lean: {under_count}/{len(results)} hit ({under_count/len(results):.0%})")
print(f"  OVER lean:   {over_count}/{len(results)} hit ({over_count/len(results):.0%})")
print(f"  Avg TC total:   {avg_tc:.1f}")
print(f"  Avg Vegas line:{sum(r['vegas'] for r in results)/len(results):.1f}")
print(f"  Avg Actual:     {avg_actual:.1f}")
print(f"  Avg diff:       {avg_diff:+.1f}  (vegas - tc)")
print(f"  Formula: TC = Σ(pts×{CONS_PTS})×{PLAYOFF_MULT} | LINE = (TC+{HISTORICAL_GAP})×{LINE_FACTOR}")
print("=" * 78)

# Per round
for rnd in ["R1 G7", "S1 G1", "S1 G3"]:
    subset = [r for r in results if r["round"] == rnd]
    if not subset:
        continue
    uc = sum(1 for r in subset if r["lean"] == "UNDER" and r["hit"])
    ad = sum(r["diff"] for r in subset) / len(subset)
    print(f"  {rnd}: {uc}/{len(subset)} UNDER hit | avg diff: {ad:+.1f}")
