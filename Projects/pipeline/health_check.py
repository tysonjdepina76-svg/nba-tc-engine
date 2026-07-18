import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import requests
from pipeline.config import OUTPUT_FILE, CACHE_DIR, MAX_DATA_AGE_SECONDS
from pipeline.repair import run_repairs


def check_file_age() -> tuple:
    path = Path(OUTPUT_FILE)
    if not path.exists():
        return False, f"File {OUTPUT_FILE} missing."
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age = (datetime.now() - mtime).total_seconds()
    if age > MAX_DATA_AGE_SECONDS:
        return False, f"Stale ({int(age)}s > {MAX_DATA_AGE_SECONDS}s)"
    return True, f"Fresh ({int(age)}s old)"


def validate_schema() -> tuple:
    path = Path(OUTPUT_FILE)
    if not path.exists():
        return False, "No file to validate."
    try:
        with open(path) as f:
            data = json.load(f)
        required = {"timestamp", "games", "player_props", "summary"}
        if all(k in data for k in required):
            return True, "Schema valid."
        return False, f"Missing keys: {required - set(data.keys())}"
    except Exception as e:
        return False, f"JSON error: {e}"


def check_dependencies() -> tuple:
    pkgs = ["requests", "streamlit", "plotly", "pandas"]
    missing = []
    for p in pkgs:
        try:
            __import__(p)
        except ImportError:
            missing.append(p)
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "All packages installed."


def check_network() -> tuple:
    endpoints = [
        ("MLB", "http://statsapi.mlb.com/api/v1/schedule?sportId=1"),
        ("ESPN", "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"),
    ]
    failed = []
    for name, url in endpoints:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                failed.append(f"{name} (HTTP {r.status_code})")
        except Exception as e:
            failed.append(f"{name} ({e})")
    if failed:
        return False, "; ".join(failed)
    return True, "All endpoints reachable."


def check_cache() -> tuple:
    path = Path(CACHE_DIR)
    if not path.exists():
        return False, f"Cache dir {CACHE_DIR} missing."
    test = path / ".health_test"
    try:
        test.touch()
        test.unlink()
        return True, "Cache writable."
    except Exception as e:
        return False, f"Cache error: {e}"


def run_health_checks() -> dict:
    return {
        "file_age": check_file_age(),
        "schema": validate_schema(),
        "dependencies": check_dependencies(),
        "network": check_network(),
        "cache": check_cache(),
    }


def evaluate_status(checks: dict) -> str:
    critical_checks = {"file_age", "schema", "dependencies"}
    for name in critical_checks:
        ok, _ = checks[name]
        if not ok:
            return "CRITICAL"
    if any(not ok for ok, _ in checks.values()):
        return "DEGRADED"
    return "OK"


def main(repair: bool = False) -> int:
    checks = run_health_checks()
    status = evaluate_status(checks)

    repair_report = None
    if repair and status != "OK":
        repair_report = run_repairs({
            "checks": {
                name: {"status": "PASS" if ok else "FAIL", "message": msg}
                for name, (ok, msg) in checks.items()
            }
        })
        checks = run_health_checks()
        status = evaluate_status(checks)

    output = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "checks": {
            name: {"status": "PASS" if ok else "FAIL", "message": msg}
            for name, (ok, msg) in checks.items()
        },
        "summary": {
            "total": len(checks),
            "passed": sum(1 for v in checks.values() if v[0]),
            "failed": sum(1 for v in checks.values() if not v[0]),
        },
        "repair_attempted": repair,
        "repair_report": repair_report,
    }

    with open("health_status.json", "w") as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))
    return 0 if status == "OK" else (1 if status == "DEGRADED" else 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    sys.exit(main(repair=args.repair))
