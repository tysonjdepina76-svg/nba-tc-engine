#!/usr/bin/env python3
"""TC Pipeline Health Check — run locally to audit the entire system.

Checks:
  1. API key presence (secrets file)
  2. External connectivity (SGO, Odds API, ESPN) with actual auth
  3. zo.space routes (/api/tc, /api/combos, /api/dk-lines)
  4. Local services (Streamlit, DK Combos Engine)
  5. Pipeline scripts (presence check)
  6. Daily log freshness
  7. NFL engine status
  8. Workspace cleanliness (>30 day stale files)

Usage:
  python3 /home/workspace/Projects/pipeline_health.py
  python3 /home/workspace/Projects/pipeline_health.py --json   # machine-readable
  python3 /home/workspace/Projects/pipeline_health.py --quick  # skip slow HTTP checks
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SECRETS_FILE = "/root/.zo/secrets.env"
WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
PROJ_DIR = WORKSPACE / "Projects"

ALL_GOOD = []
WARNINGS = []
FAILURES = []

def load_secrets():
    secrets = {}
    try:
        for line in Path(SECRETS_FILE).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                secrets[k.strip()] = v.strip()
    except Exception:
        pass
    return secrets

def check(label, ok, detail="", warn=False):
    status = "✅" if ok else "⚠️" if warn else "❌"
    msg = f"  {status} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if ok:
        ALL_GOOD.append(label)
    elif warn:
        WARNINGS.append(f"{label}: {detail}")
    else:
        FAILURES.append(f"{label}: {detail}")

def main():
    json_out = "--json" in sys.argv
    quick = "--quick" in sys.argv

    if not json_out:
        print("=" * 60)
        print("  TC PIPELINE HEALTH CHECK")
        print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 60)

    secrets = load_secrets()

    # ── 1. API KEYS ──
    if not json_out:
        print("\n── API Keys ──")
    key_checks = {
        "ODDS_API_KEY": "The Odds API (ga",
        "SPORTS_DATA_API_KEY": "SportsData.io ($99/mo NFL)"}
    for name, desc in key_checks.items():
        val = secrets.get(name, "")
        if val and len(val) > 5:
            masked = val[:4] + "..." + val[-4:]
            check(f"{name} ({desc})", True, masked)
        else:
            check(f"{name} ({desc})", False, "MISSING from secrets file")

    # ── 2. EXTERNAL CONNECTIVITY ──
    if not quick and not json_out:
        print("\n── External APIs ──")

    if not quick:
        import requests

        # ESPN
        try:
            r = requests.get(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
                timeout=10,
            )
            check("ESPN API", r.ok, f"HTTP {r.status_code}")
        except Exception as e:
            check("ESPN API", False, str(e)[:80])

        # The Odds API — use correct /odds/ endpoint
        if odds_key:
            try:
                r = requests.get(
                    params={ "regions": "us", "markets": "h2h"},
                    timeout=10,
                )
                ok = r.ok or r.status_code == 422
                detail = f"HTTP {r.status_code}"
                if r.status_code == 401:
                    detail += " — KEY EXPIRED/INVALID — all DK lines dead"
                elif r.status_code == 422:
                    detail += " (no games — OK)"
                check("The Odds API", ok, detail)
            except Exception as e:
                check("The Odds API", False, str(e)[:80])
        else:
            check("The Odds API", False, "No API key")

        # SportsGameOdds (NBA)
        if sgo_key:
            try:
                r = requests.get(
                    "https://api.sportsgameodds.com/v2/events?leagueID=NBA",
                    headers={"x-api-key": sgo_key},
                    timeout=10,
                )
                check("SportsGameOdds (NBA)", r.ok, f"HTTP {r.status_code}")
            except Exception as e:
                check("SportsGameOdds (NBA)", False, str(e)[:80])

            # WNBA tier check
            try:
                r2 = requests.get(
                    "https://api.sportsgameodds.com/v2/events?leagueID=WNBA",
                    headers={"x-api-key": sgo_key},
                    timeout=10,
                )
                data = r2.json()
                if data.get("success") is False and data.get("error"):
                    check("SportsGameOdds (WNBA)", False, data["error"], warn=True)
                elif r2.ok:
                    check("SportsGameOdds (WNBA)", True, f"HTTP {r2.status_code}")
                else:
                    check("SportsGameOdds (WNBA)", False, f"HTTP {r2.status_code}")
            except Exception as e:
                check("SportsGameOdds (WNBA)", False, str(e)[:80], warn=True)
        else:
            check("SportsGameOdds (NBA)", False, "No API key")

    # ── 3. ZO.SPACE ROUTES ──
    if not quick and not json_out:
        print("\n── Zo.Space Routes ──")

    if not quick:
        route_checks = [
            ("/api/tc (NBA)", "https://true.zo.space/api/tc?sport=NBA&mode=live-stats"),
            ("/api/tc (WNBA)", "https://true.zo.space/api/tc?sport=WNBA&mode=live-stats"),
            ("/api/daily-log", "https://true.zo.space/api/daily-log"),
            ("/api/combos", "https://true.zo.space/api/combos"),
            ("/api/dk-lines", "https://true.zo.space/api/dk-lines"),
        ]
        for name, url in route_checks:
            try:
                r = requests.get(url, headers={"Accept": "application/json"}, timeout=20)
                data = r.json()
                ok = not data.get("error") and r.ok
                check(name, ok, f"HTTP {r.status_code}" if ok else str(data.get("error", f"HTTP {r.status_code}"))[:60])
            except Exception as e:
                check(name, False, str(e)[:80])

    # ── 4. LOCAL SERVICES ──
    if not quick and not json_out:
        print("\n── Local Services ──")

    if not quick:
        # Streamlit
        streamlit_ok = False
        for port in [8507, 8510, 8501]:
            try:
                r = requests.get(f"http://localhost:{port}", headers={"x-api-key": ODDS_API_KEY}, timeout=5)
                check(f"Streamlit :{port}", True, f"HTTP {r.status_code}")
                streamlit_ok = True
                break
            except Exception:
                continue
        if not streamlit_ok:
            check("Streamlit", False, "Not running on any port")

        # DK Combos Engine
        try:
            r = requests.get(
                "https://dk-combos-engine-true.zocomputer.io/combos?sport=WNBA",
                timeout=10,
            )
            check("DK Combos Engine", r.ok, f"HTTP {r.status_code}")
        except Exception as e:
            check("DK Combos Engine", False, str(e)[:80])

    # ── 5. PIPELINE SCRIPTS ──
    if not json_out:
        print("\n── Pipeline Scripts ──")

    scripts = [
        "daily_picks.py",
        "consensus_engine.py",
        "build_pregame_combos.py",
    ]
    for s in scripts:
        p = PROJ_DIR / s
        check(s, p.exists(), "OK" if p.exists() else "MISSING")

    # ── 6. DAILY LOG FRESHNESS ──
    if not json_out:
        print("\n── Daily Log ──")

    last_run_file = LOG_DIR / "last_run.json"
    if last_run_file.exists():
        try:
            last = json.loads(last_run_file.read_text())
            ts = last.get("timestamp", "")[:19]
            games = last.get("games_logged", 0)
            picks = last.get("picks_logged", 0)
            errors = last.get("errors", [])
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(last["timestamp"])).total_seconds() / 3600
            fresh = age_h < 24
            detail = f"{ts} — {games} games, {picks} picks ({age_h:.1f}h ago)"
            if errors:
                detail += f" | {len(errors)} errors"
            check("Last run", fresh, detail, warn=not fresh)
        except Exception as e:
            check("Last run", False, str(e)[:80])
    else:
        check("Last run", False, "No last_run.json found")

    # Recent logs
    try:
        date_dirs = sorted(
            [d for d in LOG_DIR.iterdir() if d.is_dir() and len(d.name) == 10 and d.name[4] == "-"],
            reverse=True,
        )[:7]
        for d in date_dirs:
            files = list(d.iterdir())
            picks_file = d / "picks.json"
            if picks_file.exists():
                try:
                    picks = json.loads(picks_file.read_text())
                    n = len(picks) if isinstance(picks, list) else 0
                    check(f"  {d.name}", True, f"{n} picks, {len(files)} files")
                except Exception:
                    check(f"  {d.name}", True, f"{len(files)} files")
            else:
                check(f"  {d.name}", True, f"{len(files)} files (no picks)")
    except Exception as e:
        check("Daily log dirs", False, str(e)[:80])

    # ── 7. NFL ENGINE ──
    if not json_out:
        print("\n── NFL Engine ──")

    nfl_script = WORKSPACE / "Projects" / "sportsdata_nfl_engine.py"
    check("Engine script", nfl_script.exists(), "OK" if nfl_script.exists() else "MISSING")

    today = datetime.now().strftime("%Y-%m-%d")
    nfl_data = LOG_DIR / today / "nfl_full_2026REG_W1.json"
    if nfl_data.exists():
        try:
            data = json.loads(nfl_data.read_text())
            sd = data.get("sportsdata", {})
            games = len(sd.get("games", []))
            props = len(sd.get("props", []))
            check("W1 data pull", games > 0, f"{games} games, {props} props from SportsData.io")
        except Exception as e:
            check("W1 data pull", False, str(e)[:80])
    else:
        check("W1 data pull", False, "No NFL data file today", warn=True)

    # ── 8. WORKSPACE CLEANLINESS ──
    if not json_out:
        print("\n── Workspace Cleanliness ──")

    stale = []
    now = time.time()
    for f in WORKSPACE.iterdir():
        if f.is_file() and f.suffix in (".py", ".md", ".csv", ".json"):
            try:
                age_days = (now - f.stat().st_mtime) / 86400
                if age_days > 30:
                    stale.append(f.name)
            except Exception:
                pass

    if stale:
        check("Root workspace", False, f"{len(stale)} stale files: {', '.join(stale[:5])}")
    else:
        check("Root workspace", True, "Clean — no stale files")

    # ── 9. SUMMARY ──
    if not json_out:
        total = len(ALL_GOOD) + len(WARNINGS) + len(FAILURES)
        print("\n" + "=" * 60)
        if not FAILURES and not WARNINGS:
            print("  🟢 HEALTHY — All checks passed")
        elif not FAILURES and WARNINGS:
            print(f"  🟡 DEGRADED — {len(WARNINGS)} warning(s)")
        elif FAILURES:
            print(f"  🔴 UNHEALTHY — {len(FAILURES)} failure(s), {len(WARNINGS)} warning(s)")
        print(f"  ✅ {len(ALL_GOOD)} passed  |  ⚠️ {len(WARNINGS)} warnings  |  ❌ {len(FAILURES)} failures")
        if WARNINGS:
            print("\n  Warnings:")
            for w in WARNINGS:
                print(f"    ⚠️  {w}")
        if FAILURES:
            print("\n  Failures:")
            for f in FAILURES:
                print(f"    ❌  {f}")
        print("=" * 60)

    # JSON output
    if json_out:
        result = {
            "status": "HEALTHY" if not FAILURES else "DEGRADED" if not FAILURES else "UNHEALTHY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": len(ALL_GOOD),
            "warnings": len(WARNINGS),
            "failures": len(FAILURES),
            "warning_details": WARNINGS,
            "failure_details": FAILURES}
        if FAILURES:
            result["status"] = "UNHEALTHY"
        elif WARNINGS:
            result["status"] = "DEGRADED"
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
