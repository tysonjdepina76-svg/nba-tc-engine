#!/usr/bin/env python3
"""TC math audit: use real proj_WNBA_*.json rolling avgs as TC inputs, then grade the TC pick against real DK combo closing lines from boxscore_combo_backtest_*.csv."""
import json, csv, sys, os, glob
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, "/home/workspace/Projects")
from tc_math import project_pra, project_pr, project_pa

PROJ_DIR = Path("/home/workspace/Daily_Log")
REPORTS = Path("/home/workspace/Reports")

def find_proj(sport, away, home, dates):
    a = away.upper()
    h = home.upper()
    for d in dates:
        for fp in PROJ_DIR.glob(str(d) + "/proj_*" + a + "_at_" + h + ".json"):
            return fp
        for fp in PROJ_DIR.glob(str(d) + "/proj_*" + a[:2] + "_at_" + h + ".json"):
            return fp
        for fp in PROJ_DIR.glob(str(d) + "/proj_*" + a + "_at_" + h[:2] + ".json"):
            return fp
        for fp in PROJ_DIR.glob(str(d) + "/proj_*" + a[:2] + "_at_" + h[:2] + ".json"):
            return fp
        for fp in PROJ_DIR.glob(str(d) + "/proj_*_" + a + "_at_" + h + ".json"):
            head = fp.read_text()[:200].upper()
            if sport.upper() in head:
                return fp
    return None

def load_proj_means(proj_path):
    if not proj_path or not proj_path.exists():
        return {}
    d = json.loads(proj_path.read_text())
    out = {}
    for side in ("away", "home"):
        for cat in ("starters", "bench"):
            for p in d.get(side, {}).get(cat, {}).get("players", []):
                nm = (p.get("name") or "").lower().strip()
                if nm:
                    out[nm] = {"pts": p.get("tc_pts", 0) or p.get("pts", 0) or 0, "reb": p.get("tc_reb", 0) or p.get("reb", 0) or 0, "ast": p.get("tc_ast", 0) or p.get("ast", 0) or 0}
    return out

def load_boxscore_actuals(date_str, away, home, sport):
    LEAGUE = {"WNBA": "basketball/wnba", "NBA": "basketball/nba"}
    import requests
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/" + LEAGUE[sport] + "/scoreboard", params={"dates": date_str}, timeout=15)
        d = r.json()
        target_eid = None
        for ev in d.get("events", []):
            comp = ev.get("competitions", [{}])[0]
            cs = comp.get("competitors", [])
            a = next((c["team"]["abbreviation"] for c in cs if c.get("homeAway") == "away"), "")
            h = next((c["team"]["abbreviation"] for c in cs if c.get("homeAway") == "home"), "")
            if a == away and h == home:
                target_eid = ev["id"]
                break
        if not target_eid:
            return {}
        r2 = requests.get("https://site.api.espn.com/apis/site/v2/sports/" + LEAGUE[sport] + "/summary", params={"event": target_eid}, timeout=15)
        sd = r2.json()
        out = {}
        for grp in sd.get("boxscore", {}).get("players", []):
            for s in grp.get("statistics", []):
                keys = s.get("keys", [])
                if "points" not in keys:
                    continue
                i_pts = keys.index("points")
                i_reb = keys.index("rebounds") if "rebounds" in keys else -1
                i_ast = keys.index("assists") if "assists" in keys else -1
                for ath in s.get("athletes", []):
                    nm = (ath.get("athlete", {}).get("displayName") or "").lower().strip()
                    raw = ath.get("stats", [])
                    def to_int(x):
                        try: return int(x)
                        except: return 0
                    out[nm] = {"pts": to_int(raw[i_pts]) if i_pts >= 0 and i_pts < len(raw) else 0, "reb": to_int(raw[i_reb]) if i_reb >= 0 and i_reb < len(raw) else 0, "ast": to_int(raw[i_ast]) if i_ast >= 0 and i_ast < len(raw) else 0}
        return out
    except Exception:
        return {}

dates = ["2026-06-04","2026-06-05","2026-06-06","2026-06-07","2026-06-08","2026-06-09","2026-06-10"]
audit_rows = []
for csv_path in sorted(glob.glob(str(REPORTS / "boxscore_combo_backtest_*.csv"))):
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            game = r["game"]
            sport = r["sport"]
            away, home = game.split("@")
            player = r["player"]
            ctype = r["combo_type"]
            dk_line = float(r["line"])
            side = r["side"]
            hit_str = r["hit"]
            actual = float(r["actual"])
            proj_path = find_proj(sport, away, home, dates)
            means = load_proj_means(proj_path)
            mp = means.get(player.lower().strip())
            if not mp:
                continue
            tc_pra = project_pra(mp["pts"], mp["reb"], mp["ast"], "ACTIVE", sport)
            tc_pr = project_pr(mp["pts"], mp["reb"], "ACTIVE", sport)
            tc_pa = project_pa(mp["pts"], mp["ast"], "ACTIVE", sport)
            tc_proj = {"PRA": tc_pra, "PR": tc_pr, "PA": tc_pa}[ctype]
            tc_pick = "Over" if tc_proj > dk_line else "Under"
            correct = (tc_pick == side and hit_str == "True")
            gap = round(actual - tc_proj, 2)
            audit_rows.append({"sport": sport, "game": game, "player": player, "combo_type": ctype, "dk_line": dk_line, "side": side, "tc_proj": tc_proj, "tc_pick": tc_pick, "actual": actual, "gap": gap, "correct": correct, "proj_file": str(proj_path) if proj_path else "NONE"})

if not audit_rows:
    print("NO AUDIT ROWS")
    sys.exit(0)
from datetime import datetime
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
by_pick = defaultdict(lambda: [0,0])
by_type = defaultdict(lambda: [0,0])
by_sport = defaultdict(lambda: [0,0])
for r in audit_rows:
    by_pick[r["tc_pick"]][0] += 1
    by_pick[r["tc_pick"]][1] += int(r["correct"])
    by_type[r["combo_type"]][0] += 1
    by_type[r["combo_type"]][1] += int(r["correct"])
    by_sport[r["sport"]][0] += 1
    by_sport[r["sport"]][1] += int(r["correct"])
print("by pick:", {k: (v[0], v[1], round(100*v[1]/v[0],1) if v[0] else 0) for k,v in by_pick.items()})
print("by type:", {k: (v[0], v[1], round(100*v[1]/v[0],1) if v[0] else 0) for k,v in by_type.items()})
print("by sport:", {k: (v[0], v[1], round(100*v[1]/v[0],1) if v[0] else 0) for k,v in by_sport.items()})
print("avg gap (actual - tc_proj):", round(sum(r["gap"] for r in audit_rows)/total, 2))
