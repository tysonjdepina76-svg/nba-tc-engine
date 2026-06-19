#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
TC Pipeline Master — Self-Healing Daily Runner
================================================
One command that runs every check, repairs issues, generates picks/combos
for ALL sports, purges old files, saves, and generates a daily report.

Covers:
  WNBA, MLB, WORLD CUP — consensus lines, TC projections, DK combos
  Soccer stats: Goals, Assists, Shots, SOT, Corners, Tackles, Fouls, Cards, Passes
  Dashboard: Streamlit (8510), DK Combos (8515), Soccer Combos (8516)

Usage:
  python3 /home/workspace/Projects/pipeline_master.py
  python3 /home/workspace/Projects/pipeline_master.py --quick     # skip slow APIs
  python3 /home/workspace/Projects/pipeline_master.py --sports NBA,WNBA
  python3 /home/workspace/Projects/pipeline_master.py --dry-run   # check only, no repairs

Output:
  /home/workspace/Daily_Log/YYYY-MM-DD/picks.csv
  /home/workspace/Daily_Log/YYYY-MM-DD/combos_*.json
  /home/workspace/Daily_Log/YYYY-MM-DD/combos_*.md
  /home/workspace/Daily_Log/last_run.json
  /home/workspace/Daily_Log/pipeline_health.json
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# ── Config ──────────────────────────────────────────────────
ET = timezone(timedelta(hours=-5))
NOW = datetime.now(ET)
TODAY_STR = NOW.strftime("%Y-%m-%d")
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M:%S ET")

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
TODAY_DIR = LOG_DIR / TODAY_STR
PROJ_DIR = WORKSPACE / "Projects"
SECRETS_FILE = Path("/root/.zo/secrets.env")

API_BASE = os.environ.get("API_BASE", "https://true.zo.space")
ALL_SPORTS = ["WNBA", "MLB", "WORLD CUP"]

# NBA and NHL are gated behind disabled flag in /api/tc + /api/dk-lines.
# To reactivate: remove the gate from those routes, then add back to this list.

LOG = []  # [(timestamp, level, source, message)]

def log(level: str, source: str, msg: str):
    entry = (datetime.now(ET).strftime("%H:%M:%S"), level, source, msg)
    LOG.append(entry)
    emoji = {"OK":"✅","WARN":"⚠️","FAIL":"❌","INFO":"ℹ️","FIX":"🔧"}.get(level, "  ")
    print(f"  {emoji} [{entry[0]}] {source}: {msg}")

def load_secrets() -> dict:
    secrets = {}
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            secrets[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in secrets.items():
        os.environ[k] = v  # FORCE overwrite so empty/rotated env vars can't shadow secrets.env
    return secrets

# ── 1. SELF-CHECK: API Keys ─────────────────────────────────
def check_api_keys(secrets: dict) -> bool:
    required = {
    }
    all_ok = True
    for key, name in required.items():
        val = secrets.get(key, "")
        if val and len(val) > 8:
            log("OK", "API_KEY", f"{name}: {val[:4]}...{val[-4:]}")
        else:
            log("FAIL", "API_KEY", f"{name}: MISSING")
            all_ok = False
    return all_ok

# ── 2. SELF-CHECK: External APIs ────────────────────────────
def check_external_apis(secrets: dict, quick: bool = False) -> dict:
    status = {}
    if quick:
        return status

    # ESPN
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard", timeout=10)
        status["espn"] = r.ok
        log("OK" if r.ok else "FAIL", "ESPN", f"HTTP {r.status_code}")
    except Exception as e:
        status["espn"] = False
        log("FAIL", "ESPN", str(e)[:80])

    # The Odds API
    if odds_key:
        try:
            r = requests.get("https://api.the-odds-api.com/v4/sports/basketball_wnba/odds",\
                params={"apiKey": odds_key, "regions": "us", "markets": "h2h"}, timeout=10)
            ok = r.ok or r.status_code == 422
            detail = f"HTTP {r.status_code}"
            remaining = r.headers.get("x-requests-remaining", "?")
            detail += f" ({remaining} req left)"
            log("OK" if ok else "WARN", "Odds API", detail)
        except Exception as e:
            log("FAIL", "Odds API", str(e)[:80])

    # SportsGameOdds — check with WNBA (NBA/NHL off-season, SGO returns 503 for them)
    if sgo_key:
        try:
            r = requests.get("https://api.sportsgameodds.com/v2/events?leagueID=WNBA",
                           headers={"x-api-key": sgo_key}, timeout=10)
            status["sgo"] = r.ok
            log("OK" if r.ok else "FAIL", "SGO", f"HTTP {r.status_code}")
        except Exception as e:
            status["sgo"] = False
            log("FAIL", "SGO", str(e)[:80])

    return status

# ── 3. SELF-CHECK: Zo.Space Routes ──────────────────────────
def check_zo_routes(quick: bool = False) -> dict:
    routes = {
        "/api/tc": "TC Projections API",
        "/nba-tc": "NBA TC Dashboard",
        "/api/combos": "Combos API",
        "/worldcup": "World Cup Dashboard",
    }
    status = {}
    if quick:
        return status

    for path, name in routes.items():
        try:
            r = requests.get(f"{API_BASE}{path}", timeout=20, headers={"Accept": "application/json"})
            status[path] = r.ok
            log("OK" if r.ok else "FAIL", name, f"HTTP {r.status_code}")
        except Exception as e:
            status[path] = False
            log("FAIL", name, str(e)[:60])
    return status

# ── 4. SELF-CHECK: Local Services ────────────────────────────
def check_local_services(quick: bool = False) -> dict:
    services = {
        "streamlit": (8510, "Streamlit Dashboard"),
        "dk_combos": (8515, "DK Combos Engine"),
        "soccer_combos": (8516, "Soccer Combo Engine"),
    }
    status = {}
    for name, (port, label) in services.items():
        try:
            r = requests.get(f"http://localhost:{port}", timeout=5)
            status[name] = r.ok
            log("OK" if r.ok else "WARN", label, f"port {port} HTTP {r.status_code}")
        except Exception:
            status[name] = False
            log("WARN", label, f"port {port} DOWN")
    return status

# ── 5. AUTO-REPAIR: Restart Dead Services ────────────────────
def repair_services(service_status: dict) -> int:
    fixed = 0

    if not service_status.get("streamlit"):
        log("FIX", "Streamlit", "Restarting on port 8510...")
        try:
            subprocess.run(["pkill", "-f", "streamlit.*tc_dashboard"], timeout=5)
            time.sleep(2)
            subprocess.Popen(
                ["python3", "-m", "streamlit", "run",
                 str(PROJ_DIR / "tc_dashboard.py"),
                 "--server.port", "8510", "--server.address", "0.0.0.0",
                 "--server.headless", "true",
                 "--browser.gatherUsageStats", "false"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            time.sleep(3)
            fixed += 1
            log("OK", "Streamlit", "Restarted")
        except Exception as e:
            log("FAIL", "Streamlit", f"Could not restart: {e}")

    if not service_status.get("dk_combos"):
        log("FIX", "DK Combos", "Restarting on port 8515...")
        try:
            subprocess.run(["pkill", "-f", "dk_combos_engine.*--serve"], timeout=5)
            time.sleep(2)
            subprocess.Popen(
                ["python3", str(PROJ_DIR / "dk_combos_engine.py"), "--serve", "--port", "8515"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            time.sleep(2)
            fixed += 1
            log("OK", "DK Combos", "Restarted")
        except Exception as e:
            log("FAIL", "DK Combos", f"Could not restart: {e}")

    if not service_status.get("soccer_combos"):
        log("FIX", "Soccer Combos", "Restarting on port 8516...")
        try:
            subprocess.run(["pkill", "-f", "soccer_combo_engine.*--serve"], timeout=5)
            time.sleep(2)
            subprocess.Popen(
                ["python3", str(PROJ_DIR / "soccer_combo_engine.py"), "--serve", "--port", "8516"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            time.sleep(2)
            fixed += 1
            log("OK", "Soccer Combos", "Restarted")
        except Exception as e:
            log("FAIL", "Soccer Combos", f"Could not restart: {e}")

    return fixed

# ── 6. CORE: Run Daily Picks ─────────────────────────────────
def run_daily_picks(sports: List[str]) -> bool:
    log("INFO", "DailyPicks", f"Running for: {', '.join(sports)}")
    try:
        result = subprocess.run(
            ["python3", str(PROJ_DIR / "daily_picks.py")] + sports,
            capture_output=True, text=True, timeout=300, cwd=str(WORKSPACE))
        if result.returncode == 0:
            log("OK", "DailyPicks", f"Completed ({len(result.stdout.splitlines())} lines)")
            return True
        else:
            last_lines = "\n".join(result.stderr.splitlines()[-5:])
            log("FAIL", "DailyPicks", f"Exit {result.returncode}: {last_lines[:200]}")
            return False
    except subprocess.TimeoutExpired:
        log("FAIL", "DailyPicks", "Timed out after 300s")
        return False
    except Exception as e:
        log("FAIL", "DailyPicks", str(e)[:120])
        return False

# ── 7. CORE: Build Pregame Combos ────────────────────────────
def run_build_combos() -> bool:
    log("INFO", "Combos", "Building pregame combos...")
    try:
        result = subprocess.run(
            ["python3", str(PROJ_DIR / "build_pregame_combos.py")],
            capture_output=True, text=True, timeout=300, cwd=str(WORKSPACE))
        if result.returncode == 0:
            log("OK", "Combos", "Completed")
            return True
        else:
            last_lines = "\n".join(result.stderr.splitlines()[-5:])
            log("WARN", "Combos", f"Exit {result.returncode}: {last_lines[:200]}")
            return False
    except subprocess.TimeoutExpired:
        log("FAIL", "Combos", "Timed out")
        return False
    except Exception as e:
        log("FAIL", "Combos", str(e)[:120])
        return False

# ── 8. CORE: Run Soccer/WC Engine ────────────────────────────
def run_soccer_engine() -> bool:
    log("INFO", "Soccer", "Running soccer TC engine...")
    try:
        result = subprocess.run(
            ["python3", str(PROJ_DIR / "soccer_tc_engine.py")],
            capture_output=True, text=True, timeout=180, cwd=str(WORKSPACE))
        if result.returncode == 0:
            log("OK", "Soccer", "Completed")
            return True
        else:
            last_lines = "\n".join(result.stderr.splitlines()[-5:])
            log("WARN", "Soccer", f"Exit {result.returncode}: {last_lines[:200]}")
            return False
    except subprocess.TimeoutExpired:
        log("FAIL", "Soccer", "Timed out")
        return False
    except Exception as e:
        log("FAIL", "Soccer", str(e)[:120])
        return False

# ── 9. INTEGRITY: Verify Output Files ────────────────────────
def verify_outputs() -> dict:
    """Check that today's output files exist and have content."""
    files = {
        "picks_csv": TODAY_DIR / "picks.csv",
        "picks_json": TODAY_DIR / "picks.json",
        "last_run": LOG_DIR / "last_run.json",
        "slate_nba": TODAY_DIR / "slate_NBA.json",
        "slate_wnba": TODAY_DIR / "slate_WNBA.json",
    }
    status = {}
    for name, path in files.items():
        if path.exists():
            size = path.stat().st_size
            status[name] = size > 10  # at least 10 bytes
            log("OK" if size > 10 else "WARN", name, f"{size} bytes")
        else:
            status[name] = False
            log("WARN", name, "MISSING")
    return status

# ── 10. PURGE: Clean Old/Duplicate Files ─────────────────────
def purge_old_files() -> int:
    """Remove old cache, stale logs, and duplicate archive files. Return count purged."""
    purged = 0
    now_ts = time.time()

    # Purge stale consensus caches (>48h)
    for cache_file in LOG_DIR.glob("*/consensus_*.json"):
        try:
            age_h = (now_ts - cache_file.stat().st_mtime) / 3600
            if age_h > 48:
                cache_file.unlink()
                purged += 1
        except Exception:
            pass

    # Purge old live_props CSVs (>7 days)
    live_dir = LOG_DIR / "live_props"
    if live_dir.exists():
        for f in live_dir.glob("*.csv"):
            try:
                age_d = (now_ts - f.stat().st_mtime) / 86400
                if age_d > 7:
                    f.unlink()
                    purged += 1
            except Exception:
                pass

    # Purge old halftime/final JSONs (>14 days)
    for subdir in ["halftime", "final"]:
        d = LOG_DIR / subdir
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    age_d = (now_ts - f.stat().st_mtime) / 86400
                    if age_d > 14:
                        f.unlink()
                        purged += 1
                except Exception:
                    pass

    # Purge root workspace stale .py/.md files (>60 days)
    for f in WORKSPACE.iterdir():
        if f.is_file() and f.suffix in (".py", ".md", ".csv"):
            try:
                age_d = (now_ts - f.stat().st_mtime) / 86400
                if age_d > 60:
                    f.unlink()
                    purged += 1
            except Exception:
                pass

    # Purge empty date dirs in Daily_Log
    for d in LOG_DIR.iterdir():
        if d.is_dir() and len(d.name) == 10 and d.name[4] == "-":
            try:
                contents = list(d.iterdir())
                if not contents:
                    d.rmdir()
                    purged += 1
            except Exception:
                pass

    if purged > 0:
        log("FIX", "Purge", f"Removed {purged} stale/empty files")
    else:
        log("OK", "Purge", "Nothing to purge — workspace clean")
    return purged

# ── 11. SAVE: Write Summary Report ───────────────────────────
def write_summary(all_ok: List[str], warnings: List[str], failures: List[str],
                  purged: int, services_fixed: int):
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "local_time": TIMESTAMP,
        "status": "HEALTHY" if not failures else "DEGRADED" if not warnings else "UNHEALTHY",
        "checks_passed": len(all_ok),
        "warnings": len(warnings),
        "failures": len(failures),
        "services_repaired": services_fixed,
        "files_purged": purged,
        "all_ok": all_ok,
        "warnings_list": warnings,
        "failures_list": failures,
        "log": [{"time": t, "level": l, "source": s, "msg": m} for t, l, s, m in LOG],
    }

    # Save to Daily_Log
    (LOG_DIR / "pipeline_health.json").write_text(json.dumps(summary, indent=2))

    # Save today's run log
    today_log = TODAY_DIR / "pipeline_run.json"
    today_log.write_text(json.dumps(summary, indent=2))

    # Generate markdown report
    md_lines = [
        f"# TC Pipeline Daily Report — {TODAY_STR}",
        "",
        f"**Status**: {'🟢 HEALTHY' if not failures else '🔴 UNHEALTHY' if failures else '🟡 DEGRADED'}",
        f"**Time**: {TIMESTAMP}",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Checks Passed | {len(all_ok)} |",
        f"| Warnings | {len(warnings)} |",
        f"| Failures | {len(failures)} |",
        f"| Services Repaired | {services_fixed} |",
        f"| Files Purged | {purged} |",
        "",
    ]
    if all_ok:
        md_lines.append("## ✅ Passed")
        for item in all_ok:
            md_lines.append(f"- {item}")
        md_lines.append("")
    if warnings:
        md_lines.append("## ⚠️ Warnings")
        for item in warnings:
            md_lines.append(f"- {item}")
        md_lines.append("")
    if failures:
        md_lines.append("## ❌ Failures")
        for item in failures:
            md_lines.append(f"- {item}")
        md_lines.append("")

    md_lines.append("## Execution Log")
    md_lines.append("| Time | Level | Component | Message |")
    md_lines.append("|---|---|---|---|")
    for t, l, s, m in LOG[-30:]:  # last 30 entries
        md_lines.append(f"| {t} | {l} | {s} | {m} |")

    report_path = TODAY_DIR / "pipeline_report.md"
    report_path.write_text("\n".join(md_lines))

    log("OK", "Report", f"Saved to {report_path}")
    return summary

# ── 12. PUSH: Git Commit + Push ──────────────────────────────
def git_push() -> bool:
    """Commit and push changes if git is set up."""
    try:
        # Check if git repo
        result = subprocess.run(["git", "rev-parse", "--git-dir"],
                              capture_output=True, text=True, cwd=str(WORKSPACE), timeout=5)
        if result.returncode != 0:
            log("WARN", "Git", "Not a git repo — skipping push")
            return False

        # Stage daily log
        subprocess.run(["git", "add", "Daily_Log/"], capture_output=True,
                      cwd=str(WORKSPACE), timeout=10)
        subprocess.run(["git", "add", "Projects/"], capture_output=True,
                      cwd=str(WORKSPACE), timeout=10)

        # Check if anything to commit
        status = subprocess.run(["git", "status", "--porcelain"],
                              capture_output=True, text=True, cwd=str(WORKSPACE), timeout=5)
        if not status.stdout.strip():
            log("INFO", "Git", "Nothing to commit")
            return True

        # Commit
        msg = f"TC pipeline auto-run {TODAY_STR} — daily picks + combos + health check"
        subprocess.run(["git", "commit", "-m", msg], capture_output=True,
                      cwd=str(WORKSPACE), timeout=10)

        # Push
        push_result = subprocess.run(["git", "push"], capture_output=True, text=True,
                                    cwd=str(WORKSPACE), timeout=30)
        if push_result.returncode == 0:
            log("OK", "Git", "Pushed successfully")
            return True
        else:
            log("WARN", "Git", f"Push failed: {push_result.stderr[:100]}")
            return False
    except Exception as e:
        log("WARN", "Git", f"Error: {str(e)[:100]}")
        return False

# ── MAIN ─────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="TC Pipeline Master — Self-Healing Daily Runner")
    parser.add_argument("--quick", action="store_true", help="Skip slow HTTP checks")
    parser.add_argument("--dry-run", action="store_true", help="Check only, no repairs or runs")
    parser.add_argument("--sports", default="WNBA,MLB,WORLD CUP",
                       help="Comma-separated sports list (e.g. WNBA,MLB,WORLD CUP). NBA and NHL are currently gated.")
    parser.add_argument("--no-push", action="store_true", help="Skip git push")
    parser.add_argument("--skip-combos", action="store_true", help="Skip combo building")
    args = parser.parse_args()

    sports_list = [s.strip() for s in args.sports.split(",") if s.strip()]
    quick = args.quick
    dry_run = args.dry_run

    print("=" * 60)
    print(f"  TC PIPELINE MASTER — Self-Healing Daily Runner")
    print(f"  {TIMESTAMP}")
    print(f"  Sports: {', '.join(sports_list)}")
    if dry_run:
        print("  MODE: DRY RUN (check only)")
    if quick:
        print("  MODE: QUICK (skip slow APIs)")
    print("=" * 60)

    all_ok = []
    warnings = []
    failures = []
    services_fixed = 0
    purged = 0

    # ── PHASE 1: Load & Check ───────────────────────────────
    print("\n── PHASE 1: Self-Check ──")
    secrets = load_secrets()
    log("OK", "Secrets", f"{len(secrets)} keys loaded" if secrets else "No secrets file")

    check_api_keys(secrets)
    check_external_apis(secrets, quick)
    check_zo_routes(quick)
    svc_status = check_local_services(quick)

    # ── PHASE 2: Auto-Repair ─────────────────────────────────
    if not dry_run:
        print("\n── PHASE 2: Auto-Repair ──")
        services_fixed = repair_services(svc_status)

    # ── PHASE 3: Run Pipeline ────────────────────────────────
    if not dry_run:
        print("\n── PHASE 3: Pipeline Execution ──")

        # Ensure today's log dir exists
        TODAY_DIR.mkdir(parents=True, exist_ok=True)

        # Run daily picks
        picks_ok = run_daily_picks(sports_list)
        if picks_ok:
            all_ok.append("Daily Picks: all sports generated")
        else:
            failures.append("Daily Picks: failed")

        # Build combos
        if not args.skip_combos:
            combos_ok = run_build_combos()
            if combos_ok:
                all_ok.append("Pregame Combos: built")
            else:
                warnings.append("Pregame Combos: issues (see log)")

        # Soccer engine (if World Cup in sports)
        if "WORLD CUP" in sports_list:
            soccer_ok = run_soccer_engine()
            if soccer_ok:
                all_ok.append("Soccer TC Engine: completed")
            else:
                warnings.append("Soccer TC Engine: issues (see log)")

    # ── PHASE 4: Verify & Purge ─────────────────────────────
    print("\n── PHASE 4: Verify & Clean ──")
    outputs = verify_outputs()
    for name, ok in outputs.items():
        if ok:
            all_ok.append(f"Output '{name}': present")
        else:
            warnings.append(f"Output '{name}': missing or empty")

    purged = purge_old_files()
    if purged > 0:
        all_ok.append(f"Purge: {purged} files removed")

    # ── PHASE 5: Save & Push ─────────────────────────────────
    if not dry_run:
        print("\n── PHASE 5: Save & Push ──")
        summary = write_summary(all_ok, warnings, failures, purged, services_fixed)

        if not args.no_push:
            git_push()

    # ── FINAL SUMMARY ────────────────────────────────────────
    print("\n" + "=" * 60)
    if not failures:
        print(f"  🟢 PIPELINE HEALTHY — {len(all_ok)} checks passed")
    elif not failures:
        print(f"  🟡 PIPELINE DEGRADED — {len(warnings)} warnings")
    else:
        print(f"  🔴 PIPELINE UNHEALTHY — {len(failures)} failures")
    print(f"  ✅ Passed: {len(all_ok)}  ⚠️ Warnings: {len(warnings)}  ❌ Failures: {len(failures)}")
    print(f"  🔧 Services repaired: {services_fixed}  🗑️ Files purged: {purged}")
    print("=" * 60)

    if failures:
        print("\n  Failures:")
        for f in failures:
            print(f"    ❌  {f}")

    # Return exit code for automation
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
