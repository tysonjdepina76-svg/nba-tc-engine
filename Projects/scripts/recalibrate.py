import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

DAILY = Path("/home/workspace/Daily_Log")
dates = sorted([d for d in DAILY.iterdir() if d.is_dir()])
print(f"Scanning {len(dates)} daily logs...", file=sys.stderr)

rows = []
for d in dates:
    fp = d / "graded_picks.csv"
    if not fp.exists():
        continue
    try:
        df = pd.read_csv(fp)
        if "result" not in df.columns:
            continue
        df = df[df["result"].isin(["H", "M"])]
        if df.empty:
            continue
        df["date"] = d.name
        rows.append(df)
    except Exception:
        continue

if not rows:
    print("No graded picks found.")
    sys.exit(0)

all_df = pd.concat(rows, ignore_index=True)
print(f"Total graded picks: {len(all_df)}")
print(f"Date range: {all_df['date'].min()} → {all_df['date'].max()}")
print(f"Leagues: {sorted(all_df['league'].dropna().unique())}")
print()
all_df["win"] = (all_df["result"] == "H").astype(int)

print("=== HIT RATE BY LEAGUE ===")
gb_l = all_df.groupby("league").agg(n=("win", "count"), hits=("win", "sum"))
gb_l["hit_rate"] = (gb_l["hits"] / gb_l["n"] * 100).round(1)
print(gb_l.to_string())
print()

print("=== HIT RATE BY STAT ===")
gb_s = all_df.groupby("stat").agg(n=("win", "count"), hits=("win", "sum"))
gb_s["hit_rate"] = (gb_s["hits"] / gb_s["n"] * 100).round(1)
gb_s = gb_s.sort_values("n", ascending=False)
print(gb_s.to_string())
print()

print("=== HIT RATE BY DIRECTION ===")
gb_d = all_df.groupby("direction").agg(n=("win", "count"), hits=("win", "sum"))
gb_d["hit_rate"] = (gb_d["hits"] / gb_d["n"] * 100).round(1)
print(gb_d.to_string())
print()

print("=== HIT RATE BY ROLE ===")
gb_r = all_df.groupby("role").agg(n=("win", "count"), hits=("win", "sum"))
gb_r["hit_rate"] = (gb_r["hits"] / gb_r["n"] * 100).round(1)
print(gb_r.to_string())
print()

print("=== HIT RATE BY EDGE BUCKET ===")
all_df["edge_bucket"] = pd.cut(all_df["edge"], bins=[-999, 1, 2, 3, 5, 999], labels=["<1", "1-2", "2-3", "3-5", "5+"])
gb_e = all_df.groupby("edge_bucket", observed=False).agg(n=("win", "count"), hits=("win", "sum"))
gb_e["hit_rate"] = (gb_e["hits"] / gb_e["n"] * 100).round(1)
print(gb_e.to_string())
print()

print("=== HIT RATE BY SOURCE ===")
gb_src = all_df.groupby("source").agg(n=("win", "count"), hits=("win", "sum"))
gb_src["hit_rate"] = (gb_src["hits"] / gb_src["n"] * 100).round(1)
print(gb_src.to_string())
print()

print("=== LAST 7 DAYS ===")
recent = all_df[all_df["date"] >= (datetime.now() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")]
if not recent.empty:
    print(f"  n={len(recent)}, hits={recent['win'].sum()}, hit_rate={recent['win'].mean()*100:.1f}%")
else:
    print("  No recent data")
print()

print("=== KEY CALIBRATION SIGNALS ===")
overall = all_df["win"].mean() * 100
print(f"  Overall hit rate: {overall:.1f}% (target: 55%+, break-even at ~52.4% on -110 odds)")
print(f"  Profitable sports (>52.4%): {(gb_l['hit_rate'] > 52.4).sum()}/{len(gb_l)}")
print(f"  Profitable stats (>52.4%): {(gb_s['hit_rate'] > 52.4).sum()}/{len(gb_s)}")
worst_league = gb_l.sort_values("hit_rate").head(3)
print(f"  Worst 3 leagues (raise threshold or drop):")
for l, r in worst_league.iterrows():
    print(f"    {l}: {r['hit_rate']:.1f}% (n={r['n']})")
