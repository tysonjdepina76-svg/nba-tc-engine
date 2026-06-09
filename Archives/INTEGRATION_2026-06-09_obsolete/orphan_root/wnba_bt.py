"""WNBA LIVE BACKTEST - old math vs new minute-aware math, 2 final games, 48 players.
Compares (OLD) pts_per_36 * 0.85 vs (NEW) role-aware factor.
"""
import requests, csv, os
from collections import defaultdict

BASE = "https://true.zo.space"
OUT  = "/home/workspace/Daily_Log/wnba_bt_results.csv"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def role_factor(tc_pts):
    """Calibrated role factor for TC projection -> real minutes."""
    if tc_pts >= 20: return 1.00
    if tc_pts >= 15: return 0.85
    if tc_pts >= 10: return 0.70
    if tc_pts >= 6:  return 0.55
    return 0.40

def est_min(tc_pts, role):
    if role == "START":
        if tc_pts >= 18: return 30
        if tc_pts >= 12: return 26
        if tc_pts >= 8:  return 22
        return 18
    if role == "BENCH":
        if tc_pts >= 14: return 22
        if tc_pts >= 8:  return 16
        if tc_pts >= 4:  return 10
        return 6
    return 12

def new_proj(tc_pts, role):
    mins = est_min(tc_pts, role)
    per_min = tc_pts * role_factor(tc_pts) / 36.0
    return round(per_min * mins, 1)

def main():
    r = requests.get(f"{BASE}/api/tc",
        params={"sport":"WNBA","mode":"live-stats"},
        headers={"Accept":"application/json"}, timeout=30)
    data = r.json()
    games = data.get("games", [])
    print(f"=== WNBA LIVE BACKTEST - {len(games)} final games ===\n")

    results = []
    stat_keys = ["pts","reb","ast","tpm","stl","blk"]

    for g in games:
        if not g.get("completed"): continue
        home, away = g["home"]["team"], g["away"]["team"]
        print(f"=== {away}@{home} (Final) ===")
        for p in g.get("players", []):
            tc_pts = p.get("tc_pts", 0)
            role   = p.get("role", "BENCH")
            mins   = p.get("minutes", 0) or 0
            if tc_pts <= 0 or mins < 5: continue

            actuals = p.get("actual", {}) or {}
            old_proj = round(tc_pts * 0.85, 1)
            new_p    = new_proj(tc_pts, role)

            for stat in stat_keys:
                tc_v  = p.get(f"tc_{stat}", 0) or 0
                if tc_v <= 0: continue
                line  = p.get(f"line_{stat}", 0) or 0
                act   = actuals.get(stat, 0) or 0
                old_p = round(tc_v * 0.85, 1)
                new_p_s= new_proj(tc_v, role)

                results.append({
                    "matchup": f"{away}@{home}",
                    "player": p["name"],
                    "role": role,
                    "tc_pts": tc_pts,
                    "mins": mins,
                    "stat": stat.upper(),
                    "tc": tc_v,
                    "line": line,
                    "actual": act,
                    "old_proj": old_p,
                    "new_proj": new_p_s,
                    "old_hit": "Y" if abs(old_p - act) <= 2 else "N",
                    "new_hit": "Y" if abs(new_p_s - act) <= 2 else "N",
                })

            old_hit_old = abs(old_proj - actuals.get("pts",0)) <= 2
            new_hit_new = abs(new_p    - actuals.get("pts",0)) <= 2
            print(f"  {p['name']:20s} role={role:5s} tc={tc_pts:5.1f} mins={mins:2d}  actPTS={actuals.get('pts',0):2d}  oldP={old_proj:5.1f}({'Y' if old_hit_old else 'N'})  newP={new_p:5.1f}({'Y' if new_hit_new else 'N'})")

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else [])
        if results: w.writeheader(); w.writerows(results)

    print(f"\n=== RESULTS ({len(results)} player-stat rows) ===")
    old_hits = sum(1 for r in results if r["old_hit"] == "Y")
    new_hits = sum(1 for r in results if r["new_hit"] == "Y")
    print(f"OLD math (pts_per_36*0.85): {old_hits}/{len(results)} hits = {100*old_hits/max(len(results),1):.1f}%")
    print(f"NEW math (role-aware):      {new_hits}/{len(results)} hits = {100*new_hits/max(len(results),1):.1f}%")
    print(f"Delta: +{new_hits - old_hits} hits, +{100*(new_hits-old_hits)/max(len(results),1):.1f}%\n")

    by_role = defaultdict(lambda: {"old":0,"new":0,"n":0})
    for r in results:
        by_role[r["role"]]["n"] += 1
        by_role[r["role"]]["old"] += 1 if r["old_hit"] == "Y" else 0
        by_role[r["role"]]["new"] += 1 if r["new_hit"] == "Y" else 0
    print("=== BY ROLE ===")
    print(f"{'ROLE':6s} {'N':4s} {'OLD%':6s} {'NEW%':6s} {'DELTA':6s}")
    for role, v in sorted(by_role.items()):
        n = v["n"] or 1
        o = 100*v["old"]/n
        nw= 100*v["new"]/n
        print(f"{role:6s} {v['n']:4d} {o:6.1f} {nw:6.1f} {nw-o:+6.1f}")

    print(f"\nSaved: {OUT}")

if __name__ == "__main__":
    main()
