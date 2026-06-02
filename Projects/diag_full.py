"""
Full system health diagnostic — System / Pipeline / Dashboard / Workspace
                              WNBA + NBA Finals rosters.
Outputs to /home/workspace/Daily_Log/health_YYYYMMDD_HHMMSS.txt
"""
import requests, json, os, csv, sys, shutil
from datetime import datetime
from pathlib import Path

WS   = Path("/home/workspace")
LOG  = WS / "Daily_Log"
LOG.mkdir(exist_ok=True)
ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
out  = LOG / f"health_{ts}.txt"
lines = []

def w(s=""): lines.append(s)

# ── 1. SYSTEM ───────────────────────────────────────────────────────────────
w("="*70); w(f"  SYSTEM HEALTH — {datetime.now().isoformat()}"); w("="*70)
import subprocess
def run(cmd): return subprocess.run(cmd, capture_output=True, text=True, shell=True).stdout
w(f"  Load: {run('uptime').strip()}")
df = run("df -h /home | tail -1 | awk '{print $4}'")
w(f"  Disk free: {df.strip()}")
mem = run("free -h | head -2 | tail -1 | awk '{print $3, $4}'")
w(f"  Memory: {mem.strip()}")

# ── 2. DASHBOARD ────────────────────────────────────────────────────────────
w(); w("="*70); w("  DASHBOARD HEALTH"); w("="*70)
ps = run("ps aux | grep 'streamlit run /home/workspace/SportsTC' | grep -v grep")
if ps:
    w("  ✅ Streamlit live: " + ps.split('\n')[0][:120])
else:
    w("  ❌ Streamlit NOT running")
code = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8507/")
w(f"  HTTP / : {code}  {'✅' if code.strip()=='200' else '❌'}")
# Check parlay tab code is present
app = WS / "SportsTC_Streamlit_App.py"
content = app.read_text() if app.exists() else ""
w(f"  App file: {app}  ({len(content):,} bytes)")
w(f"  Parlay tab code: {'✅ present' if 'with tab_parlay:' in content and 'st.markdown(\"### 💰 Parlay Builder' in content else '❌ MISSING'}")
w(f"  Top-8 Window code: {'✅ present' if 'Top 8 Window' in content else '❌ MISSING'}")
# Count tabs
import re
tabs = re.search(r"st\.tabs\(\[(.*?)\]\)", content, re.S)
if tabs:
    tab_count = len(re.findall(r'\"[^\"]+\"', tabs.group(1)))
    w(f"  Tabs in UI: {tab_count}")

# ── 3. PIPELINE / API ───────────────────────────────────────────────────────
w(); w("="*70); w("  WORKFLOW PIPELINE + API"); w("="*70)
try:
    r = requests.get("https://true.zo.space/api/tc", params={"sport":"WNBA","mode":"live-stats"}, timeout=10)
    w(f"  /api/tc WNBA live-stats: HTTP {r.status_code}  {'✅' if r.ok else '❌'}")
    if r.ok:
        d = r.json()
        games = d.get("games", [])
        w(f"  Games returned: {len(games)}")
except Exception as e:
    w(f"  ❌ API error: {e}")
try:
    r = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard", timeout=10)
    w(f"  ESPN NBA scoreboard: HTTP {r.status_code}  {'✅' if r.ok else '❌'}")
except Exception as e:
    w(f"  ❌ ESPN error: {e}")

# Daily Log health
w(f"  Daily_Log dir: {LOG}")
if LOG.exists():
    dates = sorted([d.name for d in LOG.iterdir() if d.is_dir()])
    w(f"  Date folders: {len(dates)} ({dates[-3:] if dates else 'none'})")
    lr = LOG / "last_run.json"
    if lr.exists():
        w(f"  last_run.json: ✅ ({(LOG / 'last_run.json').stat().st_size} bytes)")
    else:
        w("  last_run.json: ❌ missing")

# ── 4. WORKSPACE CLEANUP ────────────────────────────────────────────────────
w(); w("="*70); w("  WORKSPACE CLEANUP"); w("="*70)
# Find duplicate dashboard files
dash_copies = list(WS.rglob("SportsTC_Streamlit_App.py"))
w(f"  Dashboard file copies: {len(dash_copies)}")
for p in dash_copies:
    w(f"    - {p}  ({p.stat().st_size:,} bytes)  mtime={datetime.fromtimestamp(p.stat().st_mtime).strftime('%H:%M:%S')}")
# Find archive
arch = WS / "Archive"
if arch.exists():
    arch_subs = list(arch.iterdir())
    w(f"  Archive folders: {len(arch_subs)}")
    for a in arch_subs[-3:]:
        w(f"    - {a.name}  ({len(list(a.iterdir()))} files)")

# ── 5. ROSTERS — WNBA (15 teams) ────────────────────────────────────────────
w(); w("="*70); w("  WNBA ROSTERS (15 teams)"); w("="*70)
WNBA = {
    "ATL":20,"CHI":19,"CON":24,"DAL":22,"GS":21,"IND":23,"LV":17,
    "LA":15,"MIN":8,"NY":10,"PHX":9,"POR":11,"SEA":6,"TOR":5,"WSH":16,
}
roster_stats = {}
for abbr, tid in WNBA.items():
    try:
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{tid}/roster", timeout=10)
        if r.ok:
            players = r.json().get("athletes", [])
            roster_stats[abbr] = len(players)
            w(f"  ✅ {abbr}  {len(players)} players  (id={tid})")
        else:
            w(f"  ❌ {abbr}  HTTP {r.status_code}  (id={tid})")
            roster_stats[abbr] = 0
    except Exception as e:
        w(f"  ❌ {abbr}  ERROR {e}")
        roster_stats[abbr] = 0
w(f"  WNBA total: {sum(roster_stats.values())} players  ({sum(1 for v in roster_stats.values() if v>0)}/15 teams OK)")

# ── 6. ROSTERS — NBA Finals (4 teams) ───────────────────────────────────────
w(); w("="*70); w("  NBA FINALS ROSTERS — NYK vs SAS (plus OKC, BOS)"); w("="*70)

# CORRECT NBA ESPN team IDs (verified from /v2/teams endpoint)
NBA_FINALS = {
    "NY":  "18",   # New York Knicks
    "SA":  "24",   # San Antonio Spurs
    "OKC": "25",   # OKC Thunder
    "BOS": "2",    # Boston Celtics
}
# Use correct ESPN label list (verified from LeBron)
LBL = ["GP","GS","MIN","FG","FG%","3PT","3P%","FT","FT%","OR","DR","REB","AST","BLK","STL","PF","TO","PTS"]

def get_2025_stats(aid):
    try:
        r = requests.get(f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{aid}/stats?season=2025", timeout=10)
        if not r.ok: return None
        d = r.json()
        for cat in d.get("categories", []):
            if cat.get("name") != "averages": continue
            for row in cat.get("statistics", []):
                if (row.get("season") or {}).get("year") == 2025:
                    stats = row.get("stats", [])
                    if len(stats) < 18: return None
                    def f(idx, default=0.0):
                        v = stats[idx]
                        if v in (None,""): return default
                        s = str(v)
                        if "-" in s and s.replace("-","").replace(".","").isdigit():
                            return float(s.split("-")[0])  # 3PTM-3PTA -> 3PTM
                        try: return float(s)
                        except: return default
                    return {
                        "gp": int(f(0)), "gs": int(f(1)), "min": f(2),
                        "pts": f(17), "reb": f(12), "ast": f(13),
                        "stl": f(14), "blk": f(15), "3pm": f(6),
                    }
    except: pass
    return None

for abbr, tid in NBA_FINALS.items():
    try:
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{tid}/roster", timeout=10)
        if not r.ok:
            w(f"  ❌ {abbr}  HTTP {r.status_code}"); continue
        players = r.json().get("athletes", [])
        w(f"  ✅ {abbr}  {len(players)} players  (id={tid})")
        # Show top 5 by PTS
        w("     ── Top 5 by PTS (2025 season) ──")
        with_stats = []
        for p in players[:20]:  # cap to top 20 for speed
            aid = p.get("id")
            stats = get_2025_stats(aid)
            if stats and stats["gp"] > 0:
                with_stats.append((p.get("fullName") or p.get("displayName","?"), stats))
        with_stats.sort(key=lambda x: x[1]["pts"], reverse=True)
        for name, s in with_stats[:5]:
            w(f"       {name:<26} {s['gp']:>2}GP {s['min']:>5.1f}MIN  {s['pts']:>5.1f}PTS {s['reb']:>4.1f}REB {s['ast']:>4.1f}AST {s['3pm']:>4.1f}3PM")
    except Exception as e:
        w(f"  ❌ {abbr}  ERROR {e}")

# ── Save ────────────────────────────────────────────────────────────────────
out.write_text("\n".join(lines))
print("\n".join(lines))
print(f"\n\nSaved → {out}  ({out.stat().st_size:,} bytes)")
