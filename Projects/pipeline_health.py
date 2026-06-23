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
    odds_key = secrets.get("ODDS_API_KEY", "")
    sgo_key = secrets.get("SPORTSGAMEODDS_API_KEY", "")
    sdio_key = secrets.get("SPORTSDATAIO_API_KEY", "")
    sports_data_key = secrets.get("SPORTS_DATA_API_KEY", secrets.get("SPORTSDATAIO_API_KEY", ""))

    # ── 1. API KEYS ──
    if not json_out:
        print("\n── API Keys ──")
    key_checks = {
        "ODDS_API_KEY": "The Odds API (game lines — free tier, no player props)",
        "SPORTSGAMEODDS_API_KEY": "SportsGameOdds (NBA/WNBA player props — DEAD as of June 2026)",
        "SPORTSDATAIO_API_KEY": "SportsDataIO (MLB player props — Premium tier)"
    }
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

        # The Odds API — use correct /odds/?sport_key=... endpoint
        if odds_key:
            try:
                r = requests.get(
                    "https://api.theoddsapi.com/odds/?sport_key=basketball_wnba",
                    params={"apiKey": odds_key, "regions": "us", "markets": "h2h"},
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

        # SportsGameOdds (NBA) — DEAD as of June 2026
        if sgo_key:
            check("SportsGameOdds (NBA)", False, "DEAD — key expired or API changed", warn=True)
        # SportsDataIO — MLB player props (PAID tier)
        sportsdata_key = secrets.get("SPORTSDATAIO_API_KEY", "")
        if sportsdata_key:
            try:
                r = requests.get(
                    f"https://api.sportsdata.io/v3/mlb/odds/json/PlayerPropsByDate/{datetime.now().strftime('%Y-%m-%d')}",
                    headers={"Ocp-Apim-Subscription-Key": sportsdata_key},
                    timeout=10,
                )
                ok = r.ok
                props_count = len(r.json()) if ok else 0
                check("SportsDataIO (MLB props)", ok, f"{props_count} props" if ok else f"HTTP {r.status_code}")
            except Exception as e:
                check("SportsDataIO (MLB props)", False, str(e)[:80], warn=True)
        else:
            check("SportsDataIO (MLB props)", False, "No key in secrets", warn=True)

        # World Cup roster freshness
        roster_path = WORKSPACE / "Daily_Log" / "wc_team_rosters.json"
        if roster_path.exists():
            try:
                rosters = json.loads(roster_path.read_text())
                teams = len(rosters)
                age_h = (datetime.now() - datetime.fromtimestamp(roster_path.stat().st_mtime)).total_seconds() / 3600
                fresh = age_h < 168
                check("World Cup Rosters", fresh, f"{teams} teams ({age_h:.0f}h old)", warn=not fresh)
            except Exception as e:
                check("World Cup Rosters", False, str(e)[:80])
        else:
            check("World Cup Rosters", False, "No roster cache", warn=True)


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
                err_msg = data.get("error", "")
                ok = not err_msg and r.ok
                is_disabled = "disabled" in str(err_msg).lower() or "off-season" in str(err_msg).lower()
                detail = f"HTTP {r.status_code}" if ok else str(err_msg or f"HTTP {r.status_code}")[:60]
                check(name, ok, detail, warn=(not ok and is_disabled))
            except Exception as e:
                detail = str(e)[:80]
                is_nba_offseason = "NBA" in name and ("disabled" in detail.lower() or "off-season" in detail.lower())
                check(name, False, detail, warn=is_nba_offseason)

    # ── 4. LOCAL SERVICES ──
    if not quick and not json_out:
        print("\n── Local Services ──")

    if not quick:
        # Streamlit
        streamlit_ok = False
        for port in [8507, 8510, 8501]:
            try:
                r = requests.get(f"http://localhost:{port}", timeout=5)
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

    # ── 7a. DATA FRESHNESS — REAL CHECK (not just HTTP 200) ──
    if not json_out:
        print("\n── Data Freshness (real check) ──")

    if not quick:
        import urllib.request, urllib.parse

        def check_sport_data(sport: str, qparam: str, away: str = "NY", home: str = "LV"):
            # For WNBA + MLB + WC: hit the /api/tc route directly WITH matchup params
            if sport in ("WNBA", "MLB", "WORLD CUP"):
                try:
                    url = f"https://true.zo.space/api/tc?sport={urllib.parse.quote(qparam)}&away={away}&home={home}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as r:
                        data = json.loads(r.read().decode("utf-8", errors="ignore"))
                    vp = data.get("valid_props") or []
                    dk_total = data.get("dk_total") or data.get("odds", {}).get("total")
                    odds_src = data.get("odds", {}).get("ml_source", "none")
                    if len(vp) == 0:
                        check(f"{sport} valid_props", False, f"0 props — pipeline not generating data ({odds_src})")
                    else:
                        check(f"{sport} valid_props", True, f"{len(vp)} props, dk_total={dk_total}, source={odds_src[:50]}")
                except Exception as e:
                    check(f"{sport} valid_props", False, str(e)[:80])
                return
            # For WC/MLB: count valid props across all of today's games in the daily log
            try:
                from pathlib import Path
                import os
                if sport == "WORLD CUP":
                    date_compact = datetime.now(timezone.utc).strftime("%Y%m%d")
                    log_dir = Path(f"/home/workspace/Daily_Log/worldcup/{date_compact}")
                    if not log_dir.exists():
                        check(f"{sport} valid_props", False, "no daily log for today — run worldcup_picks.py")
                        return
                    matches_file = log_dir / "matches.json"
                    if not matches_file.exists():
                        check(f"{sport} valid_props", False, "matches.json missing for today")
                        return
                    md = json.loads(matches_file.read_text())
                    match_list = md.get("matches", []) if isinstance(md, dict) else md
                    total_props = 0
                    player_count = 0
                    for m in match_list:
                        pp = m.get("player_props", {}) or {}
                        player_count += len(pp)
                        for stats in pp.values():
                            total_props += len(stats)
                    if total_props == 0:
                        check(f"{sport} valid_props", False, f"0 props across {len(match_list)} matches — pipeline not generating data")
                    else:
                        check(f"{sport} valid_props", True, f"{total_props} props across {len(match_list)} matches · {player_count} players")
                elif sport == "MLB":
                    # Read today's picks.csv (multi-game aggregation)
                    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    picks_csv = Path(f"/home/workspace/Daily_Log/{today}/picks.csv")
                    if not picks_csv.exists():
                        check(f"{sport} valid_props", False, "no picks.csv for today — run daily_picks.py")
                        return
                    lines = picks_csv.read_text().strip().splitlines()
                    mlb_rows = [l for l in lines[1:] if ",MLB," in l]
                    mlb_valid = [l for l in mlb_rows if ",OVER," in l or ",UNDER," in l]
                    if len(mlb_valid) == 0:
                        check(f"{sport} valid_props", False, f"0 valid MLB props today")
                    else:
                        check(f"{sport} valid_props", True, f"{len(mlb_valid)} valid MLB props today")
                else:
                    check(f"{sport} valid_props", False, f"unknown sport {sport}")
            except Exception as e:
                check(f"{sport} valid_props", False, str(e)[:80])

        check_sport_data("WNBA", "WNBA", "NY", "LV")
        check_sport_data("MLB", "MLB", "NYY", "DET")
        check_sport_data("WORLD CUP", "WORLD CUP", "UZB", "POR")

        # Daily_Log freshness
        last_run = WORKSPACE / "Daily_Log" / "last_run.json"
        if last_run.exists():
            age_hr = (time.time() - last_run.stat().st_mtime) / 3600
            if age_hr > 6:
                check("Daily_Log freshness", False, f"last_run.json is {age_hr:.1f}hr old (>6hr threshold)")
            else:
                check("Daily_Log freshness", True, f"last_run.json is {age_hr:.1f}hr old")
        else:
            check("Daily_Log freshness", False, "last_run.json missing — daily_picks.py has not run today")


    # ── 7b. DASHBOARD WIRING CHECK — validate default matchups actually resolve ──
    if not quick and not json_out:
        print("\n── Dashboard Wiring ──")

    if not quick:
        # Issue #1: Dashboard default matchups must return real data
        dash_checks = [
            ("WNBA dashboard default (NY@LV)", "WNBA", "NY", "LV"),
            ("MLB dashboard default (NYY@DET)", "MLB", "NYY", "DET"),
            ("World Cup dashboard default (UZB@POR)", "WORLD CUP", "UZB", "POR"),
        ]
        for label, sport, away, home in dash_checks:
            try:
                u = f"https://true.zo.space/api/tc?sport={urllib.parse.quote(sport)}&away={away}&home={home}"
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = json.loads(r.read().decode("utf-8", errors="ignore"))
                err = data.get("error", "")
                vp = data.get("valid_props") or []
                signal = data.get("signal", "")
                if err:
                    check(label, False, f"API error: {err[:60]}")
                elif len(vp) == 0:
                    check(label, False, f"0 valid_props — dashboard would show blank ({signal})")
                else:
                    check(label, True, f"{len(vp)} props · {signal[:40]}")
            except Exception as e:
                check(label, False, str(e)[:80])

        # Issue #2: World Cup must be in TC projection mode (not worldcup-props book mode)
        try:
            u = "https://true.zo.space/api/tc?sport=WORLD%20CUP&away=UZB&home=POR"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                wc_data = json.loads(r.read().decode("utf-8", errors="ignore"))
            wc_signal = wc_data.get("signal", "")
            wc_vp = wc_data.get("valid_props") or []
            if not wc_data.get("error") and len(wc_vp) > 0:
                check("World Cup TC mode", True, f"{len(wc_vp)} props — dashboard renders stats")
            else:
                check("World Cup TC mode", False, f"{len(wc_vp)} props — check /api/tc routing")
        except Exception as e:
            check("World Cup TC mode", False, str(e)[:80])

        # Issue #3: MLB stat keys match between API output and dashboard labels
        # Verify a TK prop has tc_hits/tc_runs/etc (not tc_h/tc_r — the broken prefix)
        try:
            mlb_sample = None
            u = "https://true.zo.space/api/tc?sport=MLB&away=NYY&home=DET"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                mlb_sample = json.loads(r.read().decode("utf-8", errors="ignore"))
            vp = mlb_sample.get("valid_props") or []
            issue3_ok = any(
                p.get("stat", "").upper() in ("HITS", "RUNS", "HR", "RBI", "STRIKEOUTS", "TOTAL_BASES")
                for p in vp
            ) if vp else False
            if vp and issue3_ok:
                stat_labels = set(p.get("stat", "").upper() for p in vp[:20])
                check("MLB stat key mapping", True, f"stats: {', '.join(sorted(stat_labels)[:6])}")
            elif vp:
                stat_labels = set(p.get("stat", "").upper() for p in vp[:20])
                check("MLB stat key mapping", False, f"missing expected stat keys — found: {', '.join(sorted(stat_labels)[:6])}")
            else:
                check("MLB stat key mapping", False, "no props — cannot verify stat keys")
        except Exception as e:
            check("MLB stat key mapping", False, str(e)[:80])
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
