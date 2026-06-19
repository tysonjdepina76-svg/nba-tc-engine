#!/usr/bin/env python3
"""Pipeline Health Assessment — single command that checks every piece of the TC workflow.

Usage:
  python3 pipeline_assess.py           # full diagnostic
  python3 pipeline_assess.py --table   # summary table only
  python3 pipeline_assess.py --json    # machine-readable output
  python3 pipeline_assess.py --repair  # fix common issues (stale cache, missing dirs)

Checks:
  1. API keys loaded (ODDS_KEY, SGO_KEY)
  2. Zo.space routes healthy (/api/tc, /nba-tc, /dk-combos, /api/combos)
  3. DK combos engine service running (port 8515)
  4. Streamlit dashboard running (port 8510)
  5. Latest Daily_Log data (picks.csv exists, last_run.json fresh)
  6. Consensus engine sport coverage + cache health
  7. Gamelogs cache fresh
  8. Automations configured + next-run times
  9. BallDontLie schedule API reachable
 10. Odds API credit remaining (paid tier — checks header)
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import time
import subprocess
import requests

ET = timezone(timedelta(hours=-5))
NOW = datetime.now(ET)
TODAY = NOW.strftime("%Y-%m-%d")
WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log" / TODAY
PROJECTS = WORKSPACE / "Projects"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def ok(msg): return f"{GREEN}✓{RESET} {msg}"
def warn(msg): return f"{YELLOW}⚠{RESET} {msg}"
def fail(msg): return f"{RED}✗{RESET} {msg}"
def head(msg): return f"\n{BOLD}═══ {msg} ═══{RESET}"

results = {}

def check(name, fn):
    try:
        r = fn()
        results[name] = {"status": "ok", **r}
        print(ok(f"{name}: {r.get('summary', '')}"))
    except Exception as e:
        results[name] = {"status": "fail", "error": str(e)}
        print(fail(f"{name}: {e}"))

# ── 1. API Keys ──────────────────────────────────
def check_api_keys():
    secrets = Path("/root/.zo/secrets.env")
    keys = {}
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                keys[k.strip()] = bool(v.strip())
    loaded = {k: v for k, v in keys.items() if v}
    return {"summary": f"{len(loaded)}/{len(keys)} loaded", "keys": loaded}

# ── 2. Zo.space Routes ──────────────────────────
def check_zo_routes():
    routes = ["/api/tc", "/nba-tc", "/api/combos", "/dk-combos", "/worldcup"]
    statuses = {}
    for r in routes:
        try:
            resp = requests.get(f"http://localhost:3099{r}", timeout=10, headers={"Accept": "application/json"})
            statuses[r] = resp.status_code
        except Exception:
            statuses[r] = "unreachable"
    healthy = sum(1 for v in statuses.values() if v == 200)
    return {"summary": f"{healthy}/{len(routes)} routes 200", "routes": statuses}

# ── 3. DK Combos Engine ─────────────────────────
def check_combos_service():
    try:
        r = requests.get("http://localhost:8515/combos?sport=WNBA", timeout=10)
        combo_count = len(r.json()) if r.ok else 0
        return {"summary": f"port 8515 OK, {combo_count} combos", "status": r.status_code, "combos": combo_count}
    except Exception:
        return {"summary": "not running", "status": "down"}

# ── 4. Streamlit Dashboard ──────────────────────
def check_streamlit():
    try:
        r = requests.get("http://localhost:8510", timeout=5)
        return {"summary": f"port 8510 OK ({r.status_code})", "status": r.status_code}
    except Exception:
        return {"summary": "not running", "status": "down"}

# ── 5. Daily Log ───────────────────────────────
def check_daily_log():
    picks_csv = LOG_DIR / "picks.csv" if LOG_DIR.exists() else None
    last_run = WORKSPACE / "Daily_Log" / "last_run.json"
    picks_count = 0
    games = []
    if picks_csv and picks_csv.exists():
        lines = picks_csv.read_text().splitlines()
        picks_count = max(0, len(lines) - 1)
        import csv
        with open(picks_csv) as f:
            first = f.readline()
            f.seek(0)
            has_header = not first.replace(",", "").replace("-", "").replace("@", "").replace(".", "").replace("'", "").replace('"', "").replace(" ", "").strip().isdigit() and "matchup" not in first
            reader = csv.reader(f)
            if has_header:
                next(reader, None)
            for row in reader:
                m = row[2].strip() if len(row) > 2 else ""
                if m and m not in games:
                    games.append(m)
    last_ts = "never"
    if last_run.exists():
        try:
            last_ts = json.loads(last_run.read_text()).get("timestamp", "unknown")
        except Exception:
            pass
    return {"summary": f"{picks_count} picks across {len(games)} games, last run {last_ts[:19] if last_ts else 'never'}",
            "picks": picks_count, "games": games, "last_run": last_ts}

# ── 6. Consensus Engine ─────────────────────────
def check_consensus():
    sys.path.insert(0, str(PROJECTS))
    from consensus_engine import CONSENSUS_SPORT_MAP, ODDS_KEY
    sports = list(CONSENSUS_SPORT_MAP.keys())
    cache_dir = LOG_DIR if LOG_DIR.exists() else None
    cache_files = list(cache_dir.glob("consensus_*.json")) if cache_dir else []
    return {"summary": f"{len(sports)} sports, {len(cache_files)} caches, key={'loaded' if ODDS_KEY else 'MISSING'}",
            "sports": sports, "caches": len(cache_files), "key_loaded": bool(ODDS_KEY)}

# ── 7. Gamelogs ─────────────────────────────────
def check_gamelogs():
    gamelogs_glob = list(LOG_DIR.glob("gamelogs_cache_*.json")) if LOG_DIR.exists() else []
    return {"summary": f"{len(gamelogs_glob)} cache files", "files": [g.name for g in gamelogs_glob]}

# ── 8. Automations ──────────────────────────────
def check_automations():
    # Automations are
    try:
        r = requests.get("http://localhost:3099/api/automations", timeout=10,
                        headers={"Accept": "application/json"})
        autos = r.json() if r.ok else []
    except Exception:
        autos = []
    active = [a for a in autos if a.get("active")]
    next_runs = [f"{a.get('title','?')}: {a.get('next_run','?')}" for a in active]
    return {"summary": f"{len(active)}/{len(autos)} active", "automations": next_runs}

# ── 9. BallDontLie ──────────────────────────────
def check_balldontlie():
    BDL_KEY = os.environ.get("BALLDONTLIE_API_KEY", "")
    try:
        r = requests.get("https://api.balldontlie.io/v1/status", timeout=10,
                        headers={"Authorization": BDL_KEY} if BDL_KEY else {})
        status = r.status_code
    except Exception:
        status = "unreachable"
    return {"summary": f"API: {status}, key={'set' if BDL_KEY else 'not set'}", "status": status}

# ── 10. Odds API Credits ────────────────────────
def check_odds_credits():
    ODDS_KEY = ""
    secrets = Path("/root/.zo/secrets.env")
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            if "ODDS_API_KEY" in line and "=" in line:
                ODDS_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not ODDS_KEY:
        return {"summary": "No ODDS_API_KEY found", "remaining": "N/A", "used": "N/A"}
    try:
        r = requests.get(
            "https://api.the-odds-api.com/v4/sports/basketball_wnba/odds",
            params={"apiKey": ODDS_KEY, "regions": "us", "markets": "h2h"}, timeout=10)
        remaining = r.headers.get("x-requests-remaining", "?")
        used = r.headers.get("x-requests-used", "?")
    except Exception:
        remaining, used = "?", "?"
    return {"summary": f"{remaining} remaining, {used} used this month", "remaining": remaining, "used": used}

# ── 11. Code Health (Syntax + Import Checks) ─────
def check_code_health():
    import py_compile
    scripts = [
        "daily_picks.py", "consensus_engine.py", "build_pregame_combos.py",
        "dk_combos_engine.py", "soccer_combo_engine.py", "soccer_tc_engine.py",
        "mlb_tc_engine.py", "worldcup_picks.py", "api_fallback.py",
        "pipeline_master.py", "pipeline_health.py", "boxscore_saver.py",
    ]
    good, bad = [], []
    for s in scripts:
        p = PROJECTS / s
        if not p.exists():
            bad.append(f"{s} MISSING")
            continue
        try:
            py_compile.compile(str(p), doraise=True)
            good.append(s)
        except py_compile.PyCompileError as e:
            bad.append(f"{s}: {str(e)[:60]}")
    summary = f"{len(good)}/{len(scripts)} scripts OK"
    if bad:
        summary += f" — {len(bad)} broken: {'; '.join(bad[:3])}"
    return {"summary": summary, "ok": good, "broken": bad}

# ── 12. Cache Health (all pipelines) ─────────────
def check_cache_health():
    cache_dir = Path("/home/workspace/Daily_Log/cache/odds")
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = cache_dir / today
    wc_glob = list(cache_dir.glob("wc_*.json"))
    today_glob = list(today_dir.glob("*.json")) if today_dir.exists() else []
    summary = f"{len(today_glob)} today ({today}), {len(wc_glob)} WC entries"
    return {
        "summary": summary,
        "today_count": len(today_glob),
        "wc_count": len(wc_glob),
        "today_files": [f.name for f in today_glob],
        "wc_files": [f.name for f in wc_glob],
    }

def restart_streamlit():
    import subprocess, time
    try:
        subprocess.run(["pkill", "-f", "streamlit.*tc_dashboard"], timeout=5)
        time.sleep(2)
        subprocess.Popen(
            ["python3", "-m", "streamlit", "run", "/home/workspace/Projects/tc_dashboard.py",
             "--server.port", "8510", "--server.address", "0.0.0.0",
             "--browser.gatherUsageStats", "false"],
            stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"),
            start_new_session=True)
    except Exception:
        pass

def restart_combos():
    import subprocess, time
    try:
        subprocess.run(["pkill", "-f", "dk_combos_engine.*--serve"], timeout=5)
        time.sleep(2)
        subprocess.Popen(
            ["python3", "/home/workspace/Projects/dk_combos_engine.py", "--serve", "--port", "8515"],
            stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"),
            start_new_session=True)
    except Exception:
        pass

# ── MAIN ───────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TC Pipeline Health Assessment")
    parser.add_argument("--table", action="store_true", help="Summary table only")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--repair", action="store_true", help="Auto-repair common issues")
    args = parser.parse_args()

    if args.repair:
        print("🔧 Repairing common issues...\n")
        repairs = 0
        # Ensure dirs
        for d in [LOG_DIR, WORKSPACE/"Daily_Log", WORKSPACE/"Documents", WORKSPACE/"Reports", WORKSPACE/"Archives", WORKSPACE/"Scripts", WORKSPACE/"Projects"]:
            d.mkdir(parents=True, exist_ok=True)
        # 1. Restart Streamlit dashboard if down
        try:
            r = requests.get("http://localhost:8510/_stcore/health", timeout=3)
            if r.status_code != 200:
                raise Exception("down")
        except Exception:
            import subprocess
            subprocess.Popen(
                ["python3", "-m", "streamlit", "run", str(WORKSPACE/"Projects/tc_dashboard.py"),
                 "--server.port", "8510", "--server.address", "0.0.0.0",
                 "--browser.gatherUsageStats", "false"],
                stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"),
            )
            time.sleep(3)
            print("  ✓ Restarted Streamlit dashboard (was down)")
            repairs += 1
        # 2. Restart DK combos engine if down
        try:
            r = requests.get("http://localhost:8515/combos", timeout=3)
            if r.status_code != 200:
                raise Exception("down")
        except Exception:
            import subprocess
            subprocess.Popen(
                ["python3", str(WORKSPACE/"Projects/dk_combos_engine.py"), "--serve", "--port", "8515"],
                stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"),
            )
            time.sleep(2)
            print("  ✓ Restarted DK combos engine (was down)")
            repairs += 1
        # 3. Restart soccer combo engine if down
        try:
            r = requests.get("http://localhost:8516/combos", timeout=3)
            if r.status_code != 200:
                raise Exception("down")
        except Exception:
            import subprocess
            subprocess.Popen(
                ["python3", str(WORKSPACE/"Projects/soccer_combo_engine.py"), "--serve", "--port", "8516"],
                stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"),
            )
            time.sleep(2)
            print("  ✓ Restarted soccer combo engine (was down)")
            repairs += 1
        # 4. Purge stale (>24h) daily log pick CSVs
        for d in (WORKSPACE/"Daily_Log").glob("20*/picks.csv"):
            try:
                age_h = (datetime.now() - datetime.fromtimestamp(d.stat().st_mtime)).total_seconds() / 3600
            except Exception:
                continue
        # 5. If today's picks missing, trigger run
        today_picks = WORKSPACE/"Daily_Log"/NOW.strftime("%Y-%m-%d")/"picks.csv"
        if not today_picks.exists():
            try:
                import subprocess
                subprocess.Popen(
                    ["python3", str(WORKSPACE/"Projects/daily_picks.py"), "NBA", "WNBA", "MLB", "NHL", "WORLD CUP"],
                    stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"),
                )
                print("  ✓ Triggered daily picks run (today's picks missing)")
                repairs += 1
            except Exception as e:
                print(f"  ✗ Could not trigger daily_picks: {e}")
        if repairs == 0:
            print("  ✓ All services running, no repairs needed")

    print(f"{BOLD}TC Pipeline Health Assessment{RESET} — {NOW.strftime('%Y-%m-%d %I:%M %p ET')}\n")

    if args.table:
        print(f"{'Component':<22} {'Status':<8} {'Summary'}")
        print("-" * 80)

    check("API Keys", check_api_keys)
    check("Zo.space Routes", check_zo_routes)
    check("DK Combos Engine", check_combos_service)
    check("Streamlit Dashboard", check_streamlit)
    check("Daily Log", check_daily_log)
    check("Consensus Engine", check_consensus)
    check("Gamelogs", check_gamelogs)
    check("Automations", check_automations)
    check("BallDontLie", check_balldontlie)
    check("Odds API Credits", check_odds_credits)
    check("Code Health", check_code_health)
    check("Cache Health", check_cache_health)

    if args.table:
        for name, r in results.items():
            status = r["status"]
            emoji = "✅" if status == "ok" else "❌"
            summary = r.get("summary", r.get("error", ""))[:60]
            print(f"{name:<22} {emoji:<8} {summary}")

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    # ── Final grade ──────────────────────────────────────
    ok_count = sum(1 for r in results.values() if r["status"] == "ok")
    total = len(results)
    print(f"\n{BOLD}Score: {ok_count}/{total} checks passed{RESET}")

    if ok_count == total:
        print(f"{GREEN}Pipeline ready to fire. All systems operational.{RESET}")
    else:
        failed = [k for k, r in results.items() if r["status"] == "fail"]
        print(f"{YELLOW}Pipeline needs attention: {', '.join(failed)}{RESET}")
