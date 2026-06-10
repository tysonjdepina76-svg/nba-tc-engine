#!/usr/bin/env python3
"""TC m"""
import json, csv, sys, os, glob
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, "/home/workspace/Projects")
from tc_math import project_pra, project_pr, project_pa, ceiling_recommend
from datetime import datetime

PROJ_DIR = Path("/home/workspace/Daily_Log")
REPORTS = Path("/home/workspace/Reports")
LEAGUE = {"WNBA": "basketball/wnba", "NBA": "basketball/nba"}

def find_proj(sport, away, home, dates):
    for d in dates:
        for p in PROJ_DIR.glob(str(d) + "/proj_*" + away + "_at_" + home + ".json"):
            head = p.read_text()[:200].upper()
            if sport == "WNBA" and "WNBA" in head:
                return p
            if sport == "NBA" and "NBA" in head:
                return p
    return None

def load_proj_means(proj_path):
    if not proj_path:
        return {}
    d = json.loads(proj_path.read_text())
    out = {}
    for side in ("away", "home"):
        for cat in ("starters", "bench"):
            for p in d.get(side, {}).get(cat, {}).get("players", []):
                nm = (p.get("name") or "").lower().strip()
                if nm:
                    out[nm] = {"pts": p.get("pts", 0) or 0, "reb": p.get("reb", 0) or 0, "ast": p.get("ast", 0) or 0}
    return out

DATES = ["2026-06-04", "2026-06-05", "2026-06-06", "2026-06-07", "2026-06-08", "2026-06-09", "2026-06-10"]
audit_rows = []
for csv_path in sorted(REPORTS.glob("boxscore_combo_backtest_*.csv")):
    for r in csv.DictReader(open(csv_path)):
        game = r["game"]
        sport = r["sport"]
        away, home = game.split("@")
        player = r["player"]
        ctype = r["combo_type"]
        dk_line = float(r["line"])
        side = r["side"]
        actual = float(r["actual"])
        hit = (r["hit"] == "True")
        proj_path = find_proj(sport, away, home, DATES)
        means = load_proj_means(proj_path)
        mp = means.get(player.lower().strip())
        if not mp:
            continue
        tc_pra = project_pra(mp["pts"], mp["reb"], mp["ast"], "ACTIVE", sport)
        tc_pr = project_pr(mp["pts"], mp["reb"], "ACTIVE", sport)
        tc_pa = project_pa(mp["pts"], mp["ast"], "ACTIVE", sport)
        tc_proj = {"PRA": tc_pra, "PR": tc_pr, "PA": tc_pa}[ctype]
        tc_pick = "Over" if tc_proj > dk_line else "Under"
        correct = (tc_pick == side and hit)
        gap = round(actual - tc_proj, 2)
        rec = ceiling_recommend(tc_proj, dk_line, side="Over")
        audit_rows.append({"sport": sport, "game": game, "player": player, "combo_type": ctype, "dk_line": dk_line, "side": side, "tc_proj": tc_proj, "tc_pick": tc_pick, "actual": actual, "gap": gap, "correct": correct, "ceiling_rec": rec})

if not audit_rows:
    print("NO AUDIT ROWS")
    sys.exit(0)

stamp = datetime.now().strftime("%Y%m%d_%H%M")
csv_out = REPORTS / ("tc_math_audit_" + stamp + ".csv")
with open(csv_out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
    w.writeheader()
    w.writerows(audit_rows)
print("wrote", csv_out, "rows:", len(audit_rows))
total = len(audit_rows)
hits = sum(1 for r in audit_rows if r["correct"])
print("Total:", total, "hits:", hits, "HR:", round(100*hits/total, 1), "%")
under_picks = [r for r in audit_rows if r["tc_pick"] == "Under"]
print("TC picked UNDER:", len(under_picks), "of which correct:", sum(1 for r in under_picks if r["correct"]), "HR:", round(100*sum(1 for r in under_picks if r["correct"])/len(under_picks), 1) if under_picks else 0, "%")
print("mean gap (actual - tc_proj):", round(sum(r["gap"] for r in audit_rows)/total, 2))
print("ceiling rec dist:", {k: sum(1 for r in audit_rows if r["ceiling_rec"] == k) for k in set(r["ceiling_rec"] for r in audit_rows)})