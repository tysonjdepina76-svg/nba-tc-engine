#!/usr/bin/env python3
"""
Pipeline Audit Tool — Complete System Analysis
Run: python3 /home/workspace/Projects/pipeline_audit.py
"""

import os
import sys
import sqlite3
import ast
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional

PROJECT_ROOT = Path("/home/workspace/Projects")
WORKSPACE = Path("/home/workspace")


class PipelineAudit:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "database": {},
            "adapters": {},
            "scripts": {},
            "dashboard": {},
            "api": {},
            "backtest": {},
            "cron": {},
            "imports": {},
            "cap_enforcement": {},
            "gaps": [],
            "warnings": [],
            "errors": [],
        }

    def run(self):
        print("=" * 70)
        print("PIPELINE AUDIT — %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S ET"))
        print("=" * 70)

        self.audit_database()
        self.audit_adapters()
        self.audit_cap_enforcement()
        self.audit_scripts()
        self.audit_dashboard()
        self.audit_api()
        self.audit_backtest()
        self.audit_cron()
        self.audit_imports()
        self.identify_gaps()
        self.generate_report()
        return self.results

    # ──────────────────── DATABASE ────────────────────

    def audit_database(self):
        print("\n[1/10] DATABASE AUDIT")
        db_candidates = [
            PROJECT_ROOT / "data" / "picks.db",
            WORKSPACE / "picks.db",
            WORKSPACE / "data" / "picks.db",
            PROJECT_ROOT / "picks.db",
        ]
        db_path = None
        for candidate in db_candidates:
            if candidate.exists():
                db_path = candidate
                break

        if not db_path:
            self.results["errors"].append("DB: picks.db not found in any expected location")
            print("  FAIL — picks.db not found")
            return

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        # picks schema
        cur.execute("PRAGMA table_info(picks)")
        cols = cur.fetchall()
        col_names = [c[1] for c in cols]

        # row counts
        cur.execute("SELECT COUNT(*) FROM picks")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT date) FROM picks")
        days = cur.fetchone()[0]

        cur.execute("SELECT MIN(date), MAX(date) FROM picks")
        dmin, dmax = cur.fetchone()

        # sport breakdown
        cur.execute("SELECT sport, COUNT(*) FROM picks GROUP BY sport")
        by_sport = {r[0]: r[1] for r in cur.fetchall()}

        # edge stats
        cur.execute("SELECT AVG(ABS(edge)), MAX(ABS(edge)), MIN(ABS(edge)) FROM picks")
        avg_e, max_e, min_e = cur.fetchone()

        # junk check: line=0 or edge=0 picks
        cur.execute("SELECT COUNT(*) FROM picks WHERE market_line = 0 OR edge = 0")
        junk = cur.fetchone()[0]

        conn.close()

        self.results["database"] = {
            "path": str(db_path),
            "tables": tables,
            "columns": col_names[:30],
            "total_picks": total,
            "days_covered": days,
            "date_range": (dmin, dmax),
            "by_sport": by_sport,
            "edge_avg": round(avg_e or 0, 2),
            "edge_max": round(max_e or 0, 2),
            "edge_min": round(min_e or 0, 2),
            "junk_rows": junk,
        }

        print("  DB: %s" % db_path)
        print("  Picks: %d across %d days [%s → %s]" % (total, days, dmin, dmax))
        print("  Sports: %s" % dict(by_sport))
        print("  Edge: avg %.1f%%, max %.1f%%, min %.1f%%" % (avg_e or 0, max_e or 0, min_e or 0))
        if junk > 0:
            print("  WARNING: %d junk rows (line=0 or edge=0)" % junk)
            self.results["warnings"].append("DB: %d junk rows" % junk)

    # ──────────────────── ADAPTERS ────────────────────

    def audit_adapters(self):
        print("\n[2/10] ADAPTERS AUDIT")
        adapters_dir = PROJECT_ROOT / "src" / "adapters"
        if not adapters_dir.exists():
            self.results["errors"].append("Adapters dir missing: src/adapters/")
            print("  FAIL — adapters directory not found")
            return

        py_files = [f for f in adapters_dir.glob("*.py") if not f.name.startswith("__")]
        adapter_data = {}

        for f in py_files:
            name = f.stem
            try:
                code = f.read_text()
                tree = ast.parse(code)

                funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                imports = []
                for n in ast.walk(tree):
                    if isinstance(n, ast.Import):
                        for alias in n.names:
                            imports.append(alias.name)
                    elif isinstance(n, ast.ImportFrom):
                        if n.module:
                            imports.append(n.module)

                # check for HTTP calls
                has_requests = "requests" in code
                has_http = any(k in code for k in ["urllib", "http.client", "httpx", "aiohttp"])
                has_curl = "subprocess" in code and ("curl" in code or "wget" in code)
                makes_external_calls = has_requests or has_http or has_curl

                # check for cap_check
                uses_cap_tracker = "cap_check" in code or "api_cap_tracker" in code

                adapter_data[name] = {
                    "path": str(f),
                    "functions": funcs,
                    "imports": imports[:15],
                    "lines": len(code.split("\n")),
                    "makes_external_calls": makes_external_calls,
                    "uses_cap_tracker": uses_cap_tracker,
                }
            except Exception as e:
                adapter_data[name] = {"path": str(f), "error": str(e)}

        uncapped = [n for n, d in adapter_data.items()
                    if d.get("makes_external_calls") and not d.get("uses_cap_tracker") and "error" not in d]

        self.results["adapters"] = {
            "total": len(adapter_data),
            "files": adapter_data,
            "uncapped_external_calls": uncapped,
        }

        print("  Adapters: %d" % len(adapter_data))
        for n, d in adapter_data.items():
            ext = "EXT" if d.get("makes_external_calls") else "---"
            cap = "CAPPED" if d.get("uses_cap_tracker") else "NO CAP"
            err = " ERROR" if "error" in d else ""
            print("    %-30s %s %s%s" % (n, ext, cap, err))
        if uncapped:
            print("  UNCAPPED: %s" % ", ".join(uncapped))
            self.results["warnings"].append("Uncapped external calls in: %s" % ", ".join(uncapped))

    # ──────────────────── CAP ENFORCEMENT ────────────────────

    def audit_cap_enforcement(self):
        print("\n[3/10] API CAP ENFORCEMENT")
        cap_file = PROJECT_ROOT / "src" / "api_cap_tracker.py"
        if not cap_file.exists():
            self.results["errors"].append("Cap tracker missing: src/api_cap_tracker.py")
            print("  FAIL — cap tracker not found")
            return

        code = cap_file.read_text()

        # extract DEFAULT_CAPS
        caps = {}
        if "DEFAULT_CAPS" in code:
            try:
                tree = ast.parse(code)
                for n in ast.walk(tree):
                    if isinstance(n, ast.Assign) and hasattr(n, 'targets') and len(n.targets) > 0:
                        if hasattr(n.targets[0], 'id') and n.targets[0].id == 'DEFAULT_CAPS':
                            if isinstance(n.value, ast.Dict):
                                for k, v in zip(n.value.keys, n.value.values):
                                    if isinstance(k, ast.Constant):
                                        mod = k.value
                                        if isinstance(v, ast.Dict):
                                            cap = {}
                                            for ck, cv in zip(v.keys, v.values):
                                                if isinstance(ck, ast.Constant) and isinstance(cv, ast.Constant):
                                                    cap[ck.value] = cv.value
                                            caps[mod] = cap
            except Exception:
                pass

        # find all callers of cap_check
        callers = []
        for root, dirs, files in os.walk(str(PROJECT_ROOT)):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "Archives", "archives")]
            for fn in files:
                if fn.endswith(".py"):
                    fp = Path(root) / fn
                    try:
                        fc = fp.read_text()
                        if "cap_check" in fc and "import" not in fc.split("cap_check")[0]:
                            pass  # may import it
                        if "cap_check(" in fc and "from" in fc and "api_cap_tracker" in fc:
                            callers.append(str(fp.relative_to(PROJECT_ROOT)))
                    except Exception:
                        pass

        # find ALL modules making HTTP calls that DON'T use cap_check
        http_users = []
        for root, dirs, files in os.walk(str(PROJECT_ROOT)):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "Archives", "archives")]
            for fn in files:
                if fn.endswith(".py"):
                    fp = Path(root) / fn
                    try:
                        fc = fp.read_text()
                        has_http = any(k in fc for k in ["requests.get", "requests.post", "urllib.request",
                                                          "httpx.get", "httpx.post"])
                        if has_http and "cap_check(" not in fc:
                            http_users.append(str(fp.relative_to(PROJECT_ROOT)))
                    except Exception:
                        pass

        # check live data state
        data_file = WORKSPACE / "data" / "api_caps.json"
        live_state = {}
        if data_file.exists():
            try:
                live_state = json.loads(data_file.read_text())
            except Exception:
                pass

        self.results["cap_enforcement"] = {
            "registered_modules": caps,
            "cap_check_callers": callers,
            "uncapped_http_modules": http_users,
            "live_state": live_state,
        }

        print("  Registered caps: %s" % dict(caps))
        print("  Callers using cap_check: %d" % len(callers))
        for c in callers:
            print("    %s" % c)
        if http_users:
            print("  UNCAPPED HTTP CALLERS: %d" % len(http_users))
            for u in http_users:
                print("    MISSING CAP: %s" % u)
            self.results["gaps"].append("%d modules make HTTP calls without cap_check" % len(http_users))

    # ──────────────────── SCRIPTS ────────────────────

    def audit_scripts(self):
        print("\n[4/10] SCRIPTS AUDIT")
        key_scripts = [
            "daily_picks.py", "gen_wnba_today.py", "tc_math.py",
            "tc_sports_dashboard.py", "backfill_projections.py",
            "tc_math_hybrid.py", "tc_math_master.py",
        ]
        script_data = {}

        for name in key_scripts:
            fp = PROJECT_ROOT / name
            if fp.exists():
                code = fp.read_text()
                has_main = 'if __name__' in code
                imports_sqlite = "sqlite3" in code
                imports_cap = "api_cap_tracker" in code or "cap_check" in code
                has_http = any(k in code for k in ["requests.", "urllib.", "httpx."])

                script_data[name] = {
                    "exists": True,
                    "lines": len(code.split("\n")),
                    "has_main_guard": has_main,
                    "has_sqlite": imports_sqlite,
                    "has_cap_tracker": imports_cap,
                    "has_external_http": has_http,
                }
            else:
                script_data[name] = {"exists": False}

        self.results["scripts"] = script_data

        for n, d in script_data.items():
            if d.get("exists"):
                cap = "CAP" if d["has_cap_tracker"] else "---"
                http = "HTTP" if d["has_external_http"] else "---"
                print("  %-35s %4d lines  %s  %s" % (n, d["lines"], cap, http))
            else:
                print("  %-35s MISSING" % n)

    # ──────────────────── DASHBOARD ────────────────────

    def audit_dashboard(self):
        print("\n[5/10] DASHBOARD AUDIT")
        dash = PROJECT_ROOT / "tc_sports_dashboard.py"
        if not dash.exists():
            self.results["warnings"].append("Dashboard file missing")
            print("  MISSING: tc_sports_dashboard.py")
            return

        code = dash.read_text()
        lines = len(code.split("\n"))

        # check for key features
        has_combos = "combo" in code.lower() and "parlay" in code.lower()
        has_betslip = "bet_slip" in code.lower() or "betslip" in code.lower()
        has_h2h = "h2h" in code.lower() or "head.to.head" in code.lower()
        has_live_odds = "live_odds" in code.lower() or "live_odds" in code
        has_sport_selector = any(k in code.lower() for k in ["sport_select", "league_select", "sport_filter"])

        self.results["dashboard"] = {
            "path": str(dash),
            "lines": lines,
            "features": {
                "combos": has_combos,
                "betslip": has_betslip,
                "h2h": has_h2h,
                "live_odds": has_live_odds,
                "sport_selector": has_sport_selector,
            },
        }

        print("  tc_sports_dashboard.py: %d lines" % lines)
        for feat, present in self.results["dashboard"]["features"].items():
            print("    %-20s %s" % (feat, "YES" if present else "NO"))

        missing = [f for f, p in self.results["dashboard"]["features"].items() if not p]
        if missing:
            self.results["gaps"].append("Dashboard missing features: %s" % ", ".join(missing))

    # ──────────────────── API ────────────────────

    def audit_api(self):
        print("\n[6/10] API AUDIT")
        api_file = PROJECT_ROOT / "api" / "main.py"
        if not api_file.exists():
            self.results["errors"].append("API main.py missing")
            print("  FAIL — api/main.py not found")
            return

        code = api_file.read_text()

        # find all endpoints
        endpoints = []
        try:
            tree = ast.parse(code)
            for n in ast.walk(tree):
                if isinstance(n, ast.FunctionDef):
                    for dec in n.decorator_list:
                        if isinstance(dec, ast.Call):
                            if hasattr(dec.func, 'attr') and dec.func.attr == 'get':
                                if hasattr(dec, 'args') and len(dec.args) > 0:
                                    if isinstance(dec.args[0], ast.Constant):
                                        endpoints.append(("GET", dec.args[0].value, n.name))
                            elif hasattr(dec.func, 'attr') and dec.func.attr in ('post', 'put'):
                                if hasattr(dec, 'args') and len(dec.args) > 0:
                                    if isinstance(dec.args[0], ast.Constant):
                                        endpoints.append((dec.func.attr.upper(), dec.args[0].value, n.name))
        except Exception:
            pass

        # check /combos endpoint does NOT reference WC
        combos_has_wc = False
        if "wc" in code.lower() and "combos" in code.lower():
            combos_has_wc = True

        self.results["api"] = {
            "path": str(api_file),
            "lines": len(code.split("\n")),
            "endpoints": endpoints,
            "combos_has_wc_ref": combos_has_wc,
        }

        print("  api/main.py: %d lines" % len(code.split("\n")))
        for method, path, func in endpoints:
            print("    %s %-20s → %s()" % (method, path, func))
        if combos_has_wc:
            print("  WARNING: combos section references WC (should be purged)")
            self.results["warnings"].append("api/main.py combos still references WC")

    # ──────────────────── BACKTEST ────────────────────

    def audit_backtest(self):
        print("\n[7/10] BACKTEST AUDIT")
        bt_dir = WORKSPACE / "Archives" / "backtests"
        reports_dir = WORKSPACE / "reports"

        backtest_files = []
        if bt_dir.exists():
            for f in bt_dir.rglob("*"):
                if f.is_file():
                    backtest_files.append(str(f.relative_to(bt_dir)))

        report_files = []
        if reports_dir.exists():
            for f in reports_dir.glob("*.md"):
                report_files.append(str(f.relative_to(WORKSPACE)))

        # check for most recent backtest
        latest = None
        if report_files:
            latest = sorted(report_files)[-1]

        self.results["backtest"] = {
            "archives_count": len(backtest_files),
            "report_files": report_files,
            "latest_report": latest,
        }

        print("  Archived backtests: %d files" % len(backtest_files))
        print("  Reports: %d" % len(report_files))
        if latest:
            print("  Latest: %s" % latest)

    # ──────────────────── CRON / AUTOMATIONS ────────────────────

    def audit_cron(self):
        print("\n[8/10] AUTOMATIONS AUDIT")
        # check crontab
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            cron_lines = [l.strip() for l in result.stdout.split("\n") if l.strip() and not l.startswith("#")]
        except Exception:
            cron_lines = []

        self.results["cron"] = {
            "cron_jobs": len(cron_lines),
            "entries": cron_lines[:20],
        }

        print("  Cron jobs: %d" % len(cron_lines))
        for line in cron_lines[:5]:
            print("    %s" % line[:100])

    # ──────────────────── IMPORTS ────────────────────

    def audit_imports(self):
        print("\n[9/10] IMPORT CHAIN AUDIT")
        self.results["imports"] = {}

        # trace daily_picks.py imports
        dp = PROJECT_ROOT / "daily_picks.py"
        if dp.exists():
            code = dp.read_text()
            imported = []
            try:
                tree = ast.parse(code)
                for n in ast.walk(tree):
                    if isinstance(n, ast.Import):
                        for alias in n.names:
                            imported.append(alias.name)
                    elif isinstance(n, ast.ImportFrom) and n.module:
                        imported.append(n.module)
            except Exception:
                pass

            dead = []
            for imp in imported:
                if imp.startswith("Projects."):
                    mod_path = imp.replace(".", "/") + ".py"
                    full = WORKSPACE / mod_path
                    if not full.exists():
                        dead.append(imp)

            self.results["imports"]["daily_picks_imports"] = imported[:30]
            self.results["imports"]["dead_imports"] = dead

            print("  daily_picks.py imports: %d modules" % len(imported))
            if dead:
                print("  DEAD IMPORTS: %s" % ", ".join(dead))
                self.results["gaps"].append("dead imports in daily_picks.py: %s" % ", ".join(dead))

    # ──────────────────── GAPS ────────────────────

    def identify_gaps(self):
        print("\n[GAP ANALYSIS]")
        gaps = self.results["gaps"]

        # 1. uncapped adapters
        uncapped = self.results["adapters"].get("uncapped_external_calls", [])
        if uncapped:
            gaps.append("Uncapped adapters: %s — add cap_check before all external calls" % ", ".join(uncapped))

        # 2. missing cap enforcement
        uncapped_http = self.results["cap_enforcement"].get("uncapped_http_modules", [])
        if uncapped_http:
            gaps.append("%d modules call HTTP without cap_check — wire api_cap_tracker" % len(uncapped_http))

        # 3. DB junk
        db = self.results["database"]
        if db.get("junk_rows", 0) > 0:
            gaps.append("DB has %d junk rows (line=0 or edge=0) — run clean_picks.py" % db["junk_rows"])

        # 4. edge quality
        if db.get("edge_avg", 0) < 5:
            gaps.append("Low average edge (%.1f%%) — projection engine may be flat-lining" % db.get("edge_avg", 0))

        # 5. single-sport DB
        if len(db.get("by_sport", {})) <= 1 and db.get("total_picks", 0) > 0:
            gaps.append("DB has only 1 sport — MLB pipeline may not be generating")

        # 6. stale DB
        try:
            from datetime import timedelta
            dmax = db.get("date_range", ("", ""))[1]
            if dmax:
                days_old = (datetime.now() - datetime.strptime(dmax, "%Y-%m-%d")).days
                if days_old > 3:
                    gaps.append("DB stale — last pick %d days ago (%s)" % (days_old, dmax))
        except Exception:
            pass

        # 7. dashboard feature gaps
        dash_missing = [f for f, p in self.results.get("dashboard", {}).get("features", {}).items() if not p]
        if dash_missing:
            gaps.append("Dashboard missing: %s" % ", ".join(dash_missing))

        # 8. live odds adapter
        adapters = self.results["adapters"].get("files", {})
        has_live_odds = "theoddsapi_adapter" in adapters
        if not has_live_odds:
            gaps.append("No TheOddsAPI live odds adapter — DK+FD odds comparison not possible")

        # deduplicate
        self.results["gaps"] = list(dict.fromkeys(gaps))

        print("  Found %d gaps" % len(self.results["gaps"]))
        for g in self.results["gaps"]:
            print("    GAP: %s" % g)

    # ──────────────────── REPORT ────────────────────

    def generate_report(self):
        print("\n" + "=" * 70)
        print("AUDIT REPORT")
        print("=" * 70)

        r = self.results

        db = r["database"]
        print("\n── DATABASE ──")
        if db:
            print("  Picks: %d | Days: %d | Sports: %s" % (
                db.get("total_picks", 0), db.get("days_covered", 0), db.get("by_sport", {})))
            print("  Edge: avg %.1f%% | max %.1f%% | Junk rows: %d" % (
                db.get("edge_avg", 0), db.get("edge_max", 0), db.get("junk_rows", 0)))
        else:
            print("  NO DATABASE")

        adapters = r["adapters"]
        print("\n── ADAPTERS ──")
        print("  Total: %d | Uncapped: %s" % (
            adapters.get("total", 0),
            ", ".join(adapters.get("uncapped_external_calls", [])) or "NONE"))

        cap = r["cap_enforcement"]
        print("\n── API CAPS ──")
        print("  Registered: %s" % (cap.get("registered_modules", {})))
        print("  Cap-aware callers: %d" % len(cap.get("cap_check_callers", [])))
        uncapped = cap.get("uncapped_http_modules", [])
        print("  Uncapped HTTP: %d %s" % (len(uncapped), uncapped[:5]))

        print("\n── SCRIPTS ──")
        for n, d in r.get("scripts", {}).items():
            status = "%d lines" % d["lines"] if d.get("exists") else "MISSING"
            print("  %-35s %s" % (n, status))

        dash = r["dashboard"]
        print("\n── DASHBOARD ──")
        if dash:
            print("  Lines: %d | Features: %s" % (dash.get("lines", 0),
                  {k: "Y" if v else "N" for k, v in dash.get("features", {}).items()}))

        api = r["api"]
        print("\n── API ──")
        if api:
            print("  Endpoints: %d" % len(api.get("endpoints", [])))
            for method, path, func in api.get("endpoints", [])[:10]:
                print("    %s %s" % (method, path))

        print("\n── GAPS (%d) ──" % len(r["gaps"]))
        for i, g in enumerate(r["gaps"], 1):
            print("  %d. %s" % (i, g))

        print("\n── WARNINGS (%d) ──" % len(r["warnings"]))
        for w in r["warnings"]:
            print("  ! %s" % w)

        print("\n── ERRORS (%d) ──" % len(r["errors"]))
        for e in r["errors"]:
            print("  X %s" % e)

        # write JSON
        out = WORKSPACE / "reports" / "pipeline_audit_%s.json" % datetime.now().strftime("%Y%m%d")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(r, f, indent=2, default=str)

        print("\n  Report saved: %s" % out)
        print("=" * 70)
        print("AUDIT COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    audit = PipelineAudit()
    audit.run()
