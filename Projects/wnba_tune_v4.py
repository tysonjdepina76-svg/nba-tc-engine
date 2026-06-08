#!/usr/bin/env python3
"""Per-stat alpha tuning: each stat may have different optimal shrinkage."""
import json
from collections import defaultdict
from pathlib import Path

ARCHIVE_ACTUALS = Path("/home/workspace/Daily_Log/wnba_pipeline_20260608_020106/actuals.json")
OUT_PATH = Path("/home/workspace/Archives/WNBA_Backtests/model_tuning_v4.json")

with open(ARCHIVE_ACTUALS) as f:
    raw = json.load(f)
all_players = list(raw.values())
by_player = defaultdict(list)
for r in all_players:
    by_player[(r["team"], r["name"])].append(r)

STAT_CONS = {"pts": 0.85, "reb": 0.85, "ast": 0.85, "stl": 0.80, "blk": 0.80, "tpm": 0.85}
STATS = ("pts", "reb", "ast", "stl", "blk", "tpm")
PUSH_WINDOW = 0.1
MIN_PRED = 0.5

def project_bayesian(others, stat, alpha):
    if not others: return None
    vals = [o[stat] for o in others]
    sample_mean = sum(vals) / len(vals)
    n = len(vals)
    prior = 0.5
    return round((sample_mean * n + prior * alpha) / (n + alpha) * STAT_CONS[stat], 2)

def grade(actual, pred):
    if abs(actual - pred) < PUSH_WINDOW:
        return "PUSH"
    return "HIT" if actual > pred else "MISS"

# Build per-stat leave-one-out projection dataset, varying alpha
print(f"{'Stat':<6} {'alpha':>6} {'Picks':>6} {'Hit':>5} {'Miss':>5} {'Push':>4} {'Hit%':>6}")
print("-" * 50)

best_per_stat = {}
for stat in STATS:
    rows = []
    for (team, name), recs in by_player.items():
        if len(recs) < 2: continue
        for i, r in enumerate(recs):
            others = [x for j, x in enumerate(recs) if j != i]
            pred = project_bayesian(others, stat, alpha=1.0)  # placeholder
            if pred is None or pred < MIN_PRED: continue
            rows.append({"actual": r[stat], "pred": pred, "stat": stat})

    best_hr = 0
    best_alpha = 1.0
    for alpha in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0]:
        h = m = p = 0
        for (team, name), recs in by_player.items():
            if len(recs) < 2: continue
            for i, r in enumerate(recs):
                others = [x for j, x in enumerate(recs) if j != i]
                pred = project_bayesian(others, stat, alpha=alpha)
                if pred is None or pred < MIN_PRED: continue
                g = grade(r[stat], pred)
                if g == "HIT": h += 1
                elif g == "MISS": m += 1
                else: p += 1
        hr = h / (h + m) * 100 if (h + m) else 0
        if alpha in [1.0, 2.0, 2.5, 3.0, 5.0]:
            print(f"{stat:<6} {alpha:>6.1f} {h+m+p:>6} {h:>5} {m:>5} {p:>4} {hr:>6.1f}")
        if hr > best_hr:
            best_hr = hr
            best_alpha = alpha
            best_picks = h + m
    best_per_stat[stat] = {"alpha": best_alpha, "hit_rate": best_hr, "picks": best_picks}
    print(f"  best {stat}: alpha={best_alpha} hit={best_hr:.1f}% picks={best_picks}\n")

# Combined model with per-stat alpha
print("=== Combined per-stat-alpha model ===")
total_h = total_m = total_p = 0
for (team, name), recs in by_player.items():
    if len(recs) < 2: continue
    for i, r in enumerate(recs):
        others = [x for j, x in enumerate(recs) if j != i]
        for stat in STATS:
            alpha = best_per_stat[stat]["alpha"]
            pred = project_bayesian(others, stat, alpha=alpha)
            if pred is None or pred < MIN_PRED: continue
            g = grade(r[stat], pred)
            if g == "HIT": total_h += 1
            elif g == "MISS": total_m += 1
            else: total_p += 1
hr = total_h / (total_h + total_m) * 100 if (total_h + total_m) else 0
print(f"Per-stat-alpha model: {total_h}/{total_h+total_m} = {hr:.1f}% ({total_p} pushes)")

out = {
    "methodology": f"per-stat alpha tuning, push_window={PUSH_WINDOW}, min_pred={MIN_PRED}",
    "best_per_stat": best_per_stat,
    "combined_picks": total_h + total_m + total_p,
    "combined_hr": hr,
}
with open(OUT_PATH, "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to {OUT_PATH}")
