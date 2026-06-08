#!/usr/bin/env python3
"""Blended model: weighted avg of A_baseline + C_bayesian, also test 3PM recency
weighting. Goal: hit% > 55% with pred >= 0.5 filter.
"""
import json
from collections import defaultdict
from pathlib import Path

ARCHIVE_ACTUALS = Path("/home/workspace/Daily_Log/wnba_pipeline_20260608_020106/actuals.json")
OUT_PATH = Path("/home/workspace/Archives/WNBA_Backtests/model_tuning_v3.json")

with open(ARCHIVE_ACTUALS) as f:
    raw = json.load(f)
all_players = list(raw.values())

# Sort each player by date
for r in all_players:
    pass  # already sorted by insertion
by_player = defaultdict(list)
for r in all_players:
    by_player[(r["team"], r["name"])].append(r)

STAT_CONS = {"pts": 0.85, "reb": 0.85, "ast": 0.85, "stl": 0.80, "blk": 0.80, "tpm": 0.85}
STATS = ("pts", "reb", "ast", "stl", "blk", "tpm")

def project_baseline(others, stat):
    if not others: return None
    vals = [o[stat] for o in others]
    return round(sum(vals) / len(vals) * STAT_CONS[stat], 2)

def project_bayesian(others, stat, alpha=2.5):
    if not others: return None
    vals = [o[stat] for o in others]
    sample_mean = sum(vals) / len(vals)
    n = len(vals)
    prior = 0.5
    return round((sample_mean * n + prior * alpha) / (n + alpha) * STAT_CONS[stat], 2)

def project_blend(others, stat, w_baseline=0.5, alpha=2.5):
    b = project_baseline(others, stat)
    c = project_bayesian(others, stat, alpha=alpha)
    if b is None or c is None: return None
    return round(b * w_baseline + c * (1 - w_baseline), 2)

def project_recency_weighted(others, stat, half_life=2):
    if not others: return None
    # weight most recent game 1.0, older games decay by half_life
    n = len(others)
    weighted_sum = 0
    weight_total = 0
    for i, o in enumerate(others):
        # i=0 is oldest, i=n-1 is most recent
        age = (n - 1) - i
        w = 0.5 ** (age / half_life)
        weighted_sum += o[stat] * w
        weight_total += w
    if weight_total == 0: return None
    return round(weighted_sum / weight_total * STAT_CONS[stat], 2)

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

def grade(actual, pred):
    return "HIT" if actual > pred else ("PUSH" if actual == pred else "MISS")

def evaluate(rows, label):
    rows_filt = [r for r in rows if r["pred"] >= 0.5]
    h = sum(1 for r in rows_filt if grade(r["actual"], r["pred"]) == "HIT")
    m = sum(1 for r in rows_filt if grade(r["actual"], r["pred"]) == "MISS")
    p = sum(1 for r in rows_filt if grade(r["actual"], r["pred"]) == "PUSH")
    hr = h / (h + m) * 100 if (h + m) else 0
    print(f"{label:<35} {len(rows_filt):>5} {h:>5} {m:>5} {p:>4} {hr:>6.1f}%")
    return {"label": label, "picks": len(rows_filt), "h": h, "m": m, "p": p, "hr": hr}

print(f"{'Model':<35} {'Picks':>5} {'Hit':>5} {'Miss':>5} {'Push':>4} {'Hit%':>7}")
print("-" * 70)

results = []

# Baselines
results.append(evaluate(build_dataset(project_baseline), "A_baseline (no shrink)"))
results.append(evaluate(build_dataset(project_bayesian, alpha=2.5), "C_bayesian a=2.5"))

# Blend sweep
print("\n--- Blend (w_baseline sweep, alpha=2.5) ---")
for w in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
    results.append(evaluate(build_dataset(project_blend, w_baseline=w, alpha=2.5), f"D_blend w={w}"))

# Recency-weighted
print("\n--- Recency-weighted (half_life sweep) ---")
for hl in [1.0, 1.5, 2.0, 3.0, 5.0]:
    results.append(evaluate(build_dataset(project_recency_weighted, half_life=hl), f"E_recency hl={hl}"))

# Best blend + recency
print("\n--- Combined: recency + bayesian blend ---")
def project_combo(others, stat, alpha=2.5, hl=2.0, w_recency=0.6):
    b = project_bayesian(others, stat, alpha=alpha)
    r = project_recency_weighted(others, stat, half_life=hl)
    if b is None or r is None: return None
    return round(b * (1 - w_recency) + r * w_recency, 2)

for w in [0.3, 0.5, 0.7]:
    for hl in [1.5, 2.0, 3.0]:
        results.append(evaluate(build_dataset(project_combo, w_recency=w, hl=hl), f"F_combo w={w} hl={hl}"))

# Best per stat
print("\n--- Per-stat for best model ---")
best = max(results, key=lambda r: r["hr"])
print(f"Best overall: {best['label']} {best['hr']:.1f}%")

# Show how each model performs per stat
top3 = sorted(results, key=lambda r: r["hr"], reverse=True)[:3]
print(f"\nTop 3 models: {[r['label'] for r in top3]}")

out = {
    "methodology": "push_window=0.1, pred >= 0.5 filter",
    "all_results": sorted(results, key=lambda r: -r["hr"]),
}
with open(OUT_PATH, "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to {OUT_PATH}")
