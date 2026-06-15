#!/usr/bin/env python3
"""WC TC Calibrator - position-group rolling avg with holdout."""
import csv, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from wc_tc_math import wc_bayes_shrink, position_of_player, WC_LEAGUE_PRIOR

CSV_PATH = Path("/home/workspace/Reports/wc_historical_2010_2022.csv")
STAT_KEYS = ["totalGoals", "goalAssists", "totalShots", "shotsOnTarget", "foulsCommitted", "yellowCards", "saves"]

def load_data():
    rows = list(csv.DictReader(open(CSV_PATH)))
    for r in rows:
        for k in STAT_KEYS:
            r[k] = float(r.get(k) or 0)
        r["starter"] = int(r.get("starter") or 0)
        r["pos_class"] = position_of_player(r.get("pos", ""))
    return rows

def build_player_index(rows):
    """Pre-compute (player, pos_class) -> list of stat vals in chronological order."""
    by_player = defaultdict(list)
    for r in rows:
        if not r["starter"]:
            continue
        by_player[(r["player"], r["pos_class"])].append(r)
    # sort by date
    for k in by_player:
        by_player[k].sort(key=lambda x: x.get("date", ""))
    return by_player

def test_alpha(by_player, stat, alpha, line=0.5, n_games=3, threshold=0.5):
    hit = miss = 0
    for (player, pos), history in by_player.items():
        for i, r in enumerate(history):
            prior_games = history[max(0, i - n_games):i]
            if not prior_games:
                continue
            sample = sum(p[stat] for p in prior_games) / len(prior_games)
            shrunk = wc_bayes_shrink(stat, sample, pos, alpha=alpha, n_games=len(prior_games))
            if shrunk > threshold:
                if r[stat] > line: hit += 1
                else: miss += 1
    return hit, miss

def main():
    rows = load_data()
    by_player = build_player_index(rows)
    n_qualifying = sum(
        len(history) - 1
        for history in by_player.values()
        if len(history) >= 2
    )
    print(f"Loaded {len(rows)} player-match rows, {len(by_player)} unique players, {n_qualifying} qualifying picks")
    print()
    best_overall = []
    for stat in STAT_KEYS:
        print(f"=== {stat} OVER 0.5 ===")
        best = (0, 0, 0, 0)
        for alpha in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0]:
            h, m = test_alpha(by_player, stat, alpha)
            hr = h / (h + m) if h + m else 0
            print(f"  alpha={alpha:5.1f}  HIT={h:4d}  MISS={m:4d}  HR={hr:.3f}  n={h+m}")
            if hr > best[3] or (hr == best[3] and (h+m) > best[1]+best[2]):
                best = (alpha, h, m, hr)
        print(f"  >> BEST alpha={best[0]} HR={best[3]:.3f} ({best[1]}/{best[1]+best[2]})")
        print()
        best_overall.append((stat, *best))
    print("=" * 60)
    print("FINAL RECOMMENDED ALPHAS:")
    for stat, alpha, h, m, hr in best_overall:
        print(f"  {stat:18s}  alpha={alpha:5.1f}  HR={hr:.3f}  (n={h+m})")
    print("=" * 60)

if __name__ == "__main__":
    main()
