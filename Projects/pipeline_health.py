#!/usr/bin/env python3
"""TC Pipeline Health Check — full diagnostic + maintenance tool.

Tests every component of the Triple Conservative sports betting pipeline:
  API keys → Odds feeds → ESPN rosters → Route endpoints → Daily logs → Combos

Usage:
  python3 pipeline_health.py            # full diagnostic
  python3 pipeline_health.py --purge    # archive old logs (keeps last 7 days)
  python3 pipeline_health.py --test     # test only (no maintenance)
  python3 pipeline_health.py --report   # generate markdown report
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
PROJ_DIR = WORKSPACE / "Projects"
SECRETS_FILE = "/root/.zo/secrets.env"
SPACE_BASE = "http://localhost:3099"

# ── Color helpers ──────────────────────────────────────────────────
G = "\033[32m"; R = "\033[31m"; Y = "\033[33m"; B = "\033[34m"; C = "\033[36m"; X = "\033[0m"
def ok(s): return f"{G}✓{X} {s}"
def fail(s): return f"{R}✗{X} {s}"
def warn(s): return f"{Y}⚠{X} {s}"
def info(s): return f"{B}ℹ{X} {s}"
def header(s): return f"\n{C}{'='*60}{X}\n{C}  {s}{X}\n{C}{'='*60}{X}"

# ── Secrets loader ─────────────────────────────────────────────────
def load_secrets():
    secrets = {}
    try:
        raw = Path(SECRETS_FILE).read_text()
        for line in raw.split("\n"):
            m = re.match(r'^\s*export\s+(\w+)\s*=\s*["\']?([^"\'#\s]+)', line)
            if m:
                secrets[m.group(1)] = m.group(2)
    except Exception:
        pass
    # also check env
    for key in ["ODDS_API_KEY", "Theoddsapi", "SPORTSGAMEODDS_API_KEY", "SportsDataIo"]:
        if key not in secrets and os.environ.get(key):
            secrets[key] = os.environ[key]
    return secrets

# ── API tests ──────────────────────────────────────────────────────
def test_odds_api(key):
    try:
        req = urllib.request.Request(
            f"https://api.the-odds-api.com/v4/sports/?apiKey={key}",
            headers={"User-Agent": "TC-HealthCheck/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
            return True, f"{len(data)} sports available"
    except Exception as e:
        return False, str(e)[:80]

def test_sgo_api(key):
    try:
        req = urllib.request.Request(
            "https://api.sportsgameodds.com/v2/events?leagueID=NBA",
            headers={"X-Api-Key": key, "Accept": "application/json", "User-Agent": "TC-HealthCheck/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
            if data.get("success") == False:
                return False, data.get("error", "unknown SGO error")[:80]
            return True, f"{len(data.get('data',[]))} NBA events"
    except Exception as e:
        return False, str(e)[:80]

def test_espn_endpoint():
    try:
        req = urllib.request.Request(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
            events = data.get("events", [])
            return True, f"{len(events)} WNBA games on scoreboard"
    except Exception as e:
        return False, str(e)[:80]

def test_space_route(path, desc=""):
    try:
        req = urllib.request.Request(
            f"{SPACE_BASE}{path}",
            headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
            if "error" in data:
                return False, f"route error: {data['error']}"
            return True, f"responded ({desc})"
    except Exception as e:
        return False, str(e)[:80]

# ── WNBA game test ─────────────────────────────────────────────────
def test_wnba_games():
    """Get today's WNBA schedule from Odds API."""
    secrets = load_secrets()
    odds_key = secrets.get("Theoddsapi") or secrets.get("ODDS_API_KEY", "")
    if not odds_key:
        return []
    try:
        req = urllib.request.Request(
            f"https://api.the-odds-api.com/v4/sports/basketball_wnba/odds?apiKey={odds_key}&regions=us&markets=h2h,spreads,totals&bookmakers=draftkings&oddsFormat=american",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            events = json.load(r)
            games = []
            for ev in events:
                games.append({
                    "away": ev.get("away_team", "?"),
                    "home": ev.get("home_team", "?"),
                    "commence": ev.get("commence_time", ""),
                })
            return games
    except Exception:
        return []

# ── Log analysis ───────────────────────────────────────────────────
def analyze_logs():
    if not LOG_DIR.exists():
        return {"dirs": 0, "files": 0, "date_range": "none", "stale_dirs": []}
    
    date_dirs = []
    stale_dirs = []
    now = datetime.now(timezone.utc)
    
    for entry in sorted(LOG_DIR.iterdir()):
        if not entry.is_dir():
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2})$", entry.name)
        if not m:
            continue
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age = (now - dt).days
            file_count = len(list(entry.iterdir()))
            date_dirs.append((entry.name, file_count, age))
            if age > 7:
                stale_dirs.append(entry.name)
        except ValueError:
            pass
    
    total_files = sum(d[1] for d in date_dirs)
    
    return {
        "dirs": len(date_dirs),
        "files": total_files,
        "date_range": f"{date_dirs[0][0]} → {date_dirs[-1][0]}" if date_dirs else "none",
        "stale_dirs": stale_dirs,
        "by_date": date_dirs,
    }

# ── Pipeline scripts check ─────────────────────────────────────────
def check_pipeline_scripts():
    scripts = {
        "daily_picks.py": "Daily pick capture (NBA+WNBA)",
        "tc_math.py": "TC math engine (CONS, bayesShrink)",
        "wnba_pipeline_v2.py": "WNBA backtest pipeline",
        "dk_combos_engine.py": "DK combo lines from SGO",
        "build_pregame_combos.py": "Pregame combo builder",
        "reconcile_picks_vs_box.py": "Live boxscore reconciliation",
        "recompute_bayes.py": "Bayesian recomputation",
    }
    results = {}
    for script, desc in scripts.items():
        path = PROJ_DIR / script
        results[script] = {
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else 0,
            "desc": desc,
        }
    return results

# ── Services check ─────────────────────────────────────────────────
def check_services():
    """Check if Streamlit dashboard is running."""
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8510"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "200"
    except Exception:
        return False

# ── MAIN ───────────────────────────────────────────────────────────
def main():
    args = set(sys.argv[1:])
    do_purge = "--purge" in args
    do_report = "--report" in args
    
    print(header("TC PIPELINE HEALTH CHECK"))
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"  Host: true.zo.computer")
    
    # 1. API Keys
    print(header("1. API KEYS"))
    secrets = load_secrets()
    
    odds_key = secrets.get("Theoddsapi") or secrets.get("ODDS_API_KEY", "")
    sgo_key = secrets.get("SPORTSGAMEODDS_API_KEY") or secrets.get("SportsDataIo", "")
    
    print(f"  The Odds API: {'found' if odds_key else fail('MISSING')} ({odds_key[:8]}...{odds_key[-4:] if len(odds_key)>12 else ''})")
    print(f"  SportsGameOdds: {'found' if sgo_key else fail('MISSING')} ({sgo_key[:8]}...{sgo_key[-4:] if len(sgo_key)>12 else ''})")
    
    # 2. API Connectivity
    print(header("2. API CONNECTIVITY"))
    
    if odds_key:
        ok1, msg1 = test_odds_api(odds_key)
        print(f"  Odds API: {ok(msg1) if ok1 else fail(msg1)}")
    else:
        print(f"  Odds API: {fail('no key — SKIPPED')}")
    
    if sgo_key:
        ok2, msg2 = test_sgo_api(sgo_key)
        print(f"  SGO API: {ok(msg2) if ok2 else fail(msg2)}")
    else:
        print(f"  SGO API: {fail('no key — SKIPPED')}")  
    
    ok3, msg3 = test_espn_endpoint()
    print(f"  ESPN API: {ok(msg3) if ok3 else fail(msg3)}")
    
    # 3. Route Endpoints
    print(header("3. ROUTE ENDPOINTS (zo.space)"))
    
    ok4, msg4 = test_space_route("/api/tc?diag=1", "diag")
    print(f"  /api/tc (diag): {ok(msg4) if ok4 else fail(msg4)}")
    
    ok5, msg5 = test_space_route("/api/tc?sport=WNBA&away=WSH&home=NY", "WNBA WSH@NY")
    if ok5:
        try:
            req = urllib.request.Request(f"{SPACE_BASE}/api/tc?sport=WNBA&away=WSH&home=NY", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
                dk_total = d.get("dk_total")
                valid_props = len(d.get("valid_props", []))
                players_away = d.get("roster_counts", {}).get("away_active", 0)
                players_home = d.get("roster_counts", {}).get("home_active", 0)
                print(f"    → DK total: {dk_total} | Valid props: {valid_props} | Rosters: {players_away}+{players_home} active players")
        except Exception:
            print(f"    → response received but parse failed")
    else:
        print(f"  /api/tc (WNBA): {fail(msg5)}")
    
    ok6, msg6 = test_space_route("/api/tc?mode=live-stats&sport=WNBA", "live-stats WNBA")
    print(f"  /api/tc (live-stats): {ok(msg6) if ok6 else fail(msg6)}")
    
    # 4. WNBA Slate
    print(header("4. WNBA SLATE (from Odds API)"))
    games = test_wnba_games()
    if games:
        for g in games:
            ts = g.get("commence", "")[:16].replace("T", " ")
            print(f"  {g['away']} @ {g['home']}  |  {ts}")
    else:
        print(f"  {fail('No WNBA games returned')}")
    
    # 5. Pipeline Scripts
    print(header("5. PIPELINE SCRIPTS"))
    scripts = check_pipeline_scripts()
    for name, info in scripts.items():
        status = ok(f"{info['size']:,} bytes") if info["exists"] else fail("MISSING")
        print(f"  {name}: {status} — {info['desc']}")
    
    # 6. Daily Logs
    print(header("6. DAILY LOGS"))
    logs = analyze_logs()
    print(f"  Date dirs: {logs['dirs']} ({logs['files']} files)  |  Range: {logs['date_range']}")
    if logs["stale_dirs"]:
        print(f"  {warn(f'{len(logs["stale_dirs"])} stale dirs (>7 days): {logs["stale_dirs"]}')}")
    
    for name, count, age in logs.get("by_date", []):
        bar = "█" * min(count, 20)
        age_tag = f" ({age}d ago)" if age > 0 else " (today)"
        print(f"    {name}: {count:3d} files {bar}{age_tag}")
    
    # 7. Services
    print(header("7. SERVICES"))
    dash_ok = check_services()
    print(f"  Streamlit (8510): {ok('running') if dash_ok else warn('not running')}")
    
    # 8. Combos
    print(header("8. COMBOS STATUS"))
    combo_files = list(LOG_DIR.glob("*/combos_*.json"))
    md_files = list(LOG_DIR.glob("*/combos_*.md"))
    print(f"  Combo JSONs: {len(combo_files)} files")
    print(f"  Combo Markdowns: {len(md_files)} files")
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = LOG_DIR / today
    today_combo_files = list(today_dir.glob("combos_*.json"))
    today_combo_md_files = list(today_dir.glob("combos_*.md"))
    print(f"  Today's Combo JSONs: {len(today_combo_files)} files")
    print(f"  Today's Combo Markdowns: {len(today_combo_md_files)} files")
    
    # ── Purge if requested ──────────────────────────────────────────
    if do_purge and logs["stale_dirs"]:
        print(header("PURGE: ARCHIVING STALE LOGS"))
        archive_dir = LOG_DIR / "_archive"
        archive_dir.mkdir(exist_ok=True)
        for stale in logs["stale_dirs"]:
            src = LOG_DIR / stale
            dst = archive_dir / stale
            if dst.exists():
                print(f"  {warn(f'{stale} already archived — skipping')}")
                continue
            import shutil
            shutil.move(str(src), str(dst))
            print(f"  {ok(f'Moved {stale} → _archive/')}")
        print(f"  {ok('Purge complete')}")
    
    # ── Report file ─────────────────────────────────────────────────
    if do_report:
        report_path = LOG_DIR / f"pipeline_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        lines = []
        lines.append("# TC Pipeline Health Report")
        lines.append(f"**Generated:** {datetime.now().isoformat()}")
        lines.append("")
        lines.append("## API Keys")
        lines.append(f"- The Odds API: `{odds_key[:8]}...` {'✓' if odds_key else '✗ MISSING'}")
        lines.append(f"- SportsGameOdds: `{sgo_key[:8]}...` {'✓' if sgo_key else '✗ MISSING'}")
        lines.append("")
        lines.append("## API Connectivity")
        lines.append(f"- Odds API: {'✓' if ok1 else '✗'} {msg1}")
        lines.append(f"- SGO API: {'✓' if ok2 else '✗'} {msg2}")
        lines.append(f"- ESPN API: {'✓' if ok3 else '✗'} {msg3}")
        lines.append("")
        lines.append("## Route Endpoints")
        lines.append(f"- /api/tc diag: {'✓' if ok4 else '✗'}")
        lines.append(f"- /api/tc WNBA: {'✓' if ok5 else '✗'}")
        lines.append(f"- /api/tc live-stats: {'✓' if ok6 else '✗'}")
        lines.append("")
        lines.append("## WNBA Slate")
        for g in games:
            lines.append(f"- {g['away']} @ {g['home']}")
        if not games:
            lines.append("- No games returned")
        lines.append("")
        lines.append("## Logs")
        lines.append(f"- {logs['dirs']} date dirs, {logs['files']} files, range {logs['date_range']}")
        if logs["stale_dirs"]:
            lines.append(f"- {len(logs['stale_dirs'])} stale dirs: {', '.join(logs['stale_dirs'])}")
        lines.append("")
        lines.append("## Pipeline Scripts")
        for name, info in scripts.items():
            lines.append(f"- `{name}`: {'✓' if info['exists'] else '✗'} — {info['desc']}")
        
        report_path.write_text("\n".join(lines))
        print(f"\n  {ok(f'Report saved: {report_path}')}")
    
    print(header("DIAGNOSTIC COMPLETE"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
