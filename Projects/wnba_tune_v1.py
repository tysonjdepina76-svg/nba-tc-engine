#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

ARCHIVE_ACTUALS = Path("/home/workspace/Daily_Log/wnba_pipeline_20260608_020106/actuals.json")
OUT_PATH = Path("/home/workspace/Archives/WNBA_Backtests/model_tuning_v1.json")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(ARCHIVE_ACTUALS) as f:
    raw = json.load(f)
all_players = list(raw.values())
print(f"Loaded {len(all_players)} player-games")

by_player = defaultdict(list)
for r in all_players:
    by_player[(r["team"], r["name"])].append(r)

STAT_CONS = {"pts": 0.85, "reb": 0.85, "ast": 0.85, "stl": 0.80, "blk": 0.80, "tpm": 0.85}
STATS = ("pts", "reb", "ast", "stl", "blk", "tpm")

def project_baseline(others, stat):
    if not others: return None
    vals = [o[stat] for o in others]
    avg = sum(vals) / len(vals)
    return round(avg * STAT_CONS[stat], 2)

def project_bayesian(others, stat, alpha=1.5):
    if not others: return None
    vals = [o[stat] for o in others]
    sample_mean = sum(vals) / len(vals)
    n = len(vals)
    prior = 0.5
    shrunk = (sample_mean * n + prior * alpha) / (n + alpha)
    return round(shrunk * STAT_CONS[stat], 2)

def build_dataset(project_fn, **kwargs):
    rows = []
    for (team, name), recs in by_player.items():
        if len(recs) < 2: continue
        for i, r in enumerate(recs):
            others = [x for j, x in enumerate(recs) if j != i]
            for stat in STATS:
                pred = project_fn(others, stat, **kwargs)
                if pred is None: continue
                rows.append({"actual": r[stat], "pred": pred, "stat": stat, "team": team, "name": name})
    return rows

def grade(actual, pred, push_window=0.5):
    if abs(actual - pred) < push_window:
        return "PUSH"
    return "HIT" if actual > pred else "MISS"

def hit_rate(rows, push_window):
    h = m = p = 0
    for r in rows:
        g = grade(r["actual"], r["pred"], push_window)
        if g == "HIT": h += 1
        elif g == "MISS": m += 1
        else: p += 1
    total = h + m
    return (h, m, p, h / total * 100 if total else 0)

print("\n=== Bayesian alpha tuning ===")
best_alpha, best_hr, best_push = 1.5, 0, 0.5
results = []
for alpha in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]:
    rows = build_dataset(project_bayesian, alpha=alpha)
    for push in [0.1, 0.3, 0.5, 0.8, 1.0]:
        h, m, p, hr = hit_rate(rows, push)
        results.append({"model": f"bayes_a{alpha}_p{push}", "alpha": alpha, "push": push, "h": h, "m": m, "p": p, "hr": hr})
        if hr > best_hr:
            best_hr = hr
            best_alpha = alpha
            best_push = push
    print(f"  alpha={alpha:.1f} -> best push: {max([r for r in results if r['alpha']==alpha], key=lambda x: x['hr'])['hr']:.1f}%")

print(f"\nBest Bayesian: alpha={best_alpha} push={best_push} -> {best_hr:.1f}%")

print("\n=== A_baseline push-window sweep ===")
rows = build_dataset(project_baseline)
for push in [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]:
    h, m, p, hr = hit_rate(rows, push)
    results.append({"model": f"baseline_p{push}", "push": push, "h": h, "m": m, "p": p, "hr": hr})
    print(f"  push={push} -> {h}/{h+m} = {hr:.1f}%")

# Save
out = {
    "best_bayesian": {"alpha": best_alpha, "push": best_push, "hr": best_hr},
    "all_results": results,
}
with open(OUT_PATH, "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to {OUT_PATH}")
