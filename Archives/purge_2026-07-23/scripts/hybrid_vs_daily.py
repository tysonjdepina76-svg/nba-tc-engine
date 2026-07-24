"""Compare hybrid_tc_engine picks against the 2026-07-13 daily CSV."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, "/home/workspace/Projects")
from hybrid_tc_engine import generate_pick, build_combos, ml_probability, ml_to_american, spread_pick, total_pick, backtest, hit_rate

CSV_PATH = "/home/workspace/Daily_Log/2026-07-13/picks.csv"


def main() -> None:
    if not Path(CSV_PATH).exists():
        print(f"CSV not found: {CSV_PATH}")
        return
    rows = []
    with open(CSV_PATH) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    by_matchup: dict = {}
    for r in rows:
        m = r["matchup"]
        by_matchup.setdefault(m, {"away": None, "home": None, "players": []})
        if r.get("player") and r.get("market_line"):
            # crude team split: first 2 letters of team column = team abbr
            t = r.get("team", "?")
            by_matchup[m]["players"].append({
                "player": r["player"],
                "team": t,
                "stat": r["stat"],
                "market_line": float(r["market_line"]) if r["market_line"] else None,
            })
    print(f"Matchups found: {len(by_matchup)}")
    for m, info in by_matchup.items():
        print(f"  {m}: {len(info['players'])} players")

    # Re-run hybrid engine on same players (using same line as proxy for "recent mean")
    picks = []
    for m, info in by_matchup.items():
        for p in info["players"]:
            if p["market_line"] is None or p["market_line"] <= 0:
                continue
            # Use market line as recent baseline + small noise to simulate real variance
            recent = [p["market_line"] * 0.95, p["market_line"] * 1.02, p["market_line"] * 1.05, p["market_line"] * 0.98, p["market_line"] * 1.00]
            pick = generate_pick(p["player"], p["team"], recent, p["market_line"], p["stat"], "wnba", m)
            if pick:
                picks.append(pick)
    print(f"\n=== HYBRID ENGINE OUTPUT: {len(picks)} picks ===")
    for p in sorted(picks, key=lambda x: -abs(x["edge"]))[:15]:
        print(f"{p['player']:<22} {p['stat']:<5} {p['direction']:<6} line={p['market_line']:<6} proj={p['proj']:<6} edge={p['edge']*100:>6.2f}% [{p['signal']}]")
    print(f"\n=== COMBOS (top 5) ===")
    for c in build_combos(picks, min_legs=2, max_legs=3, top_n=5):
        legs = " + ".join(f"{x['player']} {x['stat']} {x['direction']}" for x in c["legs"])
        print(f"[{c['size']}-leg {c['matchup']}] avg edge {c['avg_edge_pct']:.2f}% :: {legs}")

    # ML/spread/total model per game
    print(f"\n=== GAME MARKETS ===")
    for m, info in by_matchup.items():
        # crude projection: sum of starter points projections (placeholder)
        ml = ml_probability(82, 78)  # demo
        print(f"{m}: ML home {ml[0]*100:.1f}% ({-110:+d}) / away {ml[1]*100:.1f}% ({110:+d})")


if __name__ == "__main__":
    main()
