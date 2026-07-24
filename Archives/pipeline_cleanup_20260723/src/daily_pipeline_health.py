"""
Daily pipeline health check & gap detector.
Run: python3 -m src.daily_pipeline_health
"""
import os, sys, json, sqlite3
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path("/home/workspace/Projects")
DAILY_LOG = Path("/home/workspace/Daily_Log")
PICKS_DB = Path("/home/workspace/Projects/data/picks.db")
ET = ZoneInfo("America/New_York")

REQUIRED_SERVICES = {
    "tc-api": 8000,
    "streamlit": 8510,
}

# Files that must exist and be non-empty for a healthy pipeline
REQUIRED_FILES = [
    "Projects/daily_picks.py",
    "Projects/generate_projections.py",
    "Projects/tc_math.py",
    "Projects/gen_wnba_today.py",
    "Projects/src/free_api_aggregator.py",
    "Projects/src/adapters/free_api_aggregator.py",
    "Projects/src/api_cap_tracker.py",
]

SPORTS = ["mlb", "wnba"]


def check_services():
    """Check if required TCP services are listening."""
    import socket
    results = {}
    for name, port in REQUIRED_SERVICES.items():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        try:
            s.connect(("127.0.0.1", port))
            results[name] = f"UP (:{port})"
        except Exception:
            results[name] = f"DOWN (:{port})"
        finally:
            s.close()
    return results


def check_required_files():
    """Verify all required source files exist."""
    results = {}
    for f in REQUIRED_FILES:
        p = Path("/home/workspace") / f
        if p.exists() and p.stat().st_size > 0:
            results[f] = "OK"
        elif p.exists():
            results[f] = "EMPTY"
        else:
            results[f] = "MISSING"
    return results


def check_todays_projections(today_str):
    """Check if today's projection files exist and have real players."""
    results = {}
    d = DAILY_LOG / today_str
    if not d.exists():
        results["projection_dir"] = "MISSING"
        return results
    results["projection_dir"] = "EXISTS"

    for sport in SPORTS:
        proj = d / f"proj_{sport.upper()}_{today_str}.json"
        per_game = list(d.glob(f"proj_{sport.upper()}_*.json"))

        if proj.exists():
            try:
                data = json.loads(proj.read_text())
                n = len(data.get("players", []))
                results[f"{sport}_combined"] = f"{n} players"
            except Exception:
                results[f"{sport}_combined"] = "CORRUPT"
        elif per_game:
            total = 0
            for pg in per_game:
                try:
                    data = json.loads(pg.read_text())
                    total += len(data.get("players", []))
                except Exception:
                    pass
            results[f"{sport}_per_game"] = f"{len(per_game)} files, ~{total} players"
        else:
            results[f"{sport}_projections"] = "NONE"

    return results


def check_picks_count():
    """Count today's picks from DB."""
    today = date.today().isoformat()
    try:
        conn = sqlite3.connect(str(PICKS_DB))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT sport, COUNT(*) as cnt FROM picks WHERE date = ? GROUP BY sport", (today,))
        rows = {r["sport"]: r["cnt"] for r in c.fetchall()}
        conn.close()
        return rows if rows else {"picks": "NONE"}
    except Exception as e:
        return {"picks": f"ERROR: {e}"}


def check_free_api_aggregator_wired():
    """Verify free_api_aggregator is imported and used."""
    issues = []
    # Check daily_picks.py
    dp = Path("/home/workspace/Projects/daily_picks.py")
    if dp.exists():
        txt = dp.read_text()
        if "free_api_aggregator" not in txt:
            issues.append("daily_picks.py: NOT wired to free_api_aggregator")
    # Check generate_projections.py
    gp = Path("/home/workspace/Projects/generate_projections.py")
    if gp.exists():
        txt = gp.read_text()
        if "free_api_aggregator" not in txt and "roster_loader" not in txt:
            issues.append("generate_projections.py: NOT wired to free API sources")
    return issues if issues else ["ALL WIRED"]


def check_uncapped_api_calls():
    """Scan Python files for uncapped external HTTP calls."""
    import subprocess
    issues = []
    # Find all Python files hitting ESPN, statsapi, etc WITHOUT cap_check
    py_files = subprocess.run(
        ["grep", "-rl", "requests.get\|urllib", "/home/workspace/Projects/src/",
         "/home/workspace/Projects/api/"],
        capture_output=True, text=True
    ).stdout.strip().split("\n")

    for f in py_files:
        if not f or "__pycache__" in f or ".pyc" in f:
            continue
        try:
            content = Path(f).read_text()
            has_request = "requests.get" in content or "urllib" in content
            has_cap = "cap_check" in content
            has_free_api = "free_api_aggregator" in content
            if has_request and not has_cap and not has_free_api:
                issues.append(f"{f}: uncapped external call")
        except Exception:
            pass

    return issues if issues else ["ALL CAPPED"]


def run_health():
    today_str = date.today().isoformat()
    now = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S %Z")

    report = {
        "timestamp": now,
        "date": today_str,
        "services": check_services(),
        "required_files": check_required_files(),
        "projections": check_todays_projections(today_str),
        "picks_today": check_picks_count(),
        "free_api_wired": check_free_api_aggregator_wired(),
        "uncapped_calls": check_uncapped_api_calls(),
    }

    # Determine overall status
    issues = 0
    for s in report["services"].values():
        if s.startswith("DOWN"):
            issues += 1
    for f in report["required_files"].values():
        if f != "OK":
            issues += 1
    report["overall"] = "HEALTHY" if issues == 0 else f"{issues} ISSUES"

    return report


if __name__ == "__main__":
    report = run_health()
    print(json.dumps(report, indent=2, default=str))
