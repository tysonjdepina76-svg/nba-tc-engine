"""WNBA TC CORRECTED - minute-aware projection engine.
Fixes the systematic 1.17-1.18x under-projection seen in WNBA live data.
OLD: TC = pts_per_36 * 0.85
NEW: TC = (pts_per_36 / 36) * proj_minutes * role_factor
     where role_factor captures the variance in points-per-minute.
"""
import requests, csv, os, json
from datetime import datetime

BASE = "https://true.zo.space"
OUT_DIR = "/home/workspace/Daily_Log"
os.makedirs(OUT_DIR, exist_ok=True)

# -------------------------------------------------------------------
# 1. PER-GAME MINUTE ESTIMATION (from observed patterns)
# -------------------------------------------------------------------
# Starter WNBA rotation: 30-32 min
# Bench 6-8: 18-24 min
# Bench 9+: 10-16 min
# Role inferred from TC_pts:
#   High TC (18+) = starter + heavy usage ~28-32 min
#   Mid TC (10-18) = starter or 6th ~22-28 min
#   Low TC (<10)   = bench / limited role ~14-22 min
def est_minutes(tc_pts, role):
    if role == "START":
        if tc_pts >= 18: return 30
        if tc_pts >= 12: return 27
        return 24
    return 18 if tc_pts >= 8 else 14

# -------------------------------------------------------------------
# 2. ROLE FACTOR (ppm multiplier for projection)
# -------------------------------------------------------------------
# Observed WNBA ppm: 0.258 (role) to 1.034 (star). Mean 0.536.
# A "balanced" projection should land at the player's observed ppm
# in the role bracket. We use a small role-factor table inferred
# from how high their TC is relative to typical minutes.
def role_factor(tc_pts, role):
    # Higher TC = higher usage role = higher ppm
    if tc_pts >= 20: return 1.00
    if tc_pts >= 15: return 0.85
    if tc_pts >= 10: return 0.70
    if tc_pts >= 6:  return 0.55
    return 0.40

# -------------------------------------------------------------------
# 3. PROJECTION
# -------------------------------------------------------------------
def project_corrected(tc_pts, role):
    mins = est_minutes(tc_pts, role)
    rf   = role_factor(tc_pts, role)
    ppm_base = 0.536  # league observed average
    ppm_player = ppm_base * rf
    proj = ppm_player * mins
    # Safety: never below original TC * 0.95 and never above TC * 1.25
    proj = max(tc_pts * 0.95, min(proj, tc_pts * 1.25))
    return round(proj, 1), mins, rf

# -------------------------------------------------------------------
# 4. LIVE SCRAPE
# -------------------------------------------------------------------
def fetch_wnba():
    r = requests.get(f"{BASE}/api/tc",
        params={"sport": "WNBA", "mode": "live-stats"},
        headers={"Accept": "application/json"}, timeout=30)
    return r.json()

def main():
    data = fetch_wnba()
    out_rows = []
    summary = []
    print("=== WNBA LIVE SCRAPE - CORRECTED TC ===")
    for g in data.get("games", []):
        matchup = g.get("matchup") or g.get("name", "?")
        print(f"\n=== {matchup} ({g.get('status','?')}) ===")
        for p in g.get("leaders", []):
            name = p.get("name", "?")
            team = p.get("team", "?")
            role = p.get("role", "BENCH")
            mins_live = p.get("minutes", 0)
            tc = p.get("tc_pts", 0)
            ln = p.get("line_pts", 0)
            act_pts = (p.get("actual") or {}).get("pts")
            act_reb = (p.get("actual") or {}).get("reb")
            act_ast = (p.get("actual") or {}).get("ast")
            tc_reb = p.get("tc_reb", 0)
            tc_ast = p.get("tc_ast", 0)
            ln_reb = p.get("line_reb", 0)
            ln_ast = p.get("line_ast", 0)
            # Skip non-final games
            if act_pts is None: continue
            # Apply correction to PTS, REB, AST
            for stat_name, tc_v, ln_v, act_v in [
                ("PTS", tc, ln, act_pts),
                ("REB", tc_reb, ln_reb, act_reb),
                ("AST", tc_ast, ln_ast, act_ast),
            ]:
                if tc_v == 0 or act_v is None: continue
                if stat_name == "PTS":
                    proj, mins_est, rf = project_corrected(tc_v, role)
                else:
                    # For REB/AST, simpler scale: use the same 1.18 ratio seen in PTS
                    proj = round(tc_v * 1.176, 1)
                    mins_est = mins_live or 0
                    rf = 0
                hit = "HIT" if act_v > proj else "MISS"
                out_rows.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "league": "WNBA",
                    "matchup": matchup,
                    "player": name,
                    "team": team,
                    "role": role,
                    "stat": stat_name,
                    "minutes_live": mins_live,
                    "minutes_est": mins_est,
                    "role_factor": rf,
                    "tc_old": tc_v,
                    "tc_corrected": proj,
                    "line": ln_v,
                    "actual": act_v,
                    "result": hit,
                })
                if stat_name == "PTS":
                    print(f"  {name:25} TC_old={tc_v:5.1f} TC_new={proj:5.1f} "
                          f"Line={ln:3d} Act={act_pts:3d} Min={mins_live:2d} [{hit}]")
        # Per-game summary
        if out_rows:
            g_rows = [r for r in out_rows if r["matchup"] == matchup]
            hits = sum(1 for r in g_rows if r["result"] == "HIT")
            summary.append({
                "matchup": matchup,
                "total": len(g_rows),
                "hits": hits,
                "hit_rate": round(hits/len(g_rows)*100, 1) if g_rows else 0,
            })

    # Save CSV
    out_path = os.path.join(OUT_DIR, f"wnba_corrected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with open(out_path, "w", newline="") as f:
        if out_rows:
            w = csv.DictWriter(f, fieldnames=out_rows[0].keys())
            w.writeheader()
            w.writerows(out_rows)
    print(f"\n=== SUMMARY ===")
    for s in summary:
        print(f"{s['matchup']}: {s['hits']}/{s['total']} hits ({s['hit_rate']}%)")
    print(f"Saved: {out_path}")
    print(f"Total picks: {len(out_rows)}")
    total_hits = sum(1 for r in out_rows if r["result"] == "HIT")
    print(f"Total hits: {total_hits}/{len(out_rows)} ({round(total_hits/len(out_rows)*100,1) if out_rows else 0}%)")

if __name__ == "__main__":
    main()
