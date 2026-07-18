#!/usr/bin/env python3
"""
Self-healing module – fixes common issues detected by health checks.
Each repair function returns (success: bool, message: str).
"""
import json
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime

from config import (
    OUTPUT_FILE, HEALTH_FILE, DB_PATH, CACHE_DIR,
    LOG_FILE, CRON_LOG
)
from alert import send_alert

REPAIR_LOG = "repair_report.json"


def repair_output_file() -> tuple:
    """Create a default pipeline_output.json if missing or corrupt."""
    path = Path(OUTPUT_FILE)
    if path.exists():
        try:
            with open(path, "r") as f:
                json.load(f)
            return True, "Output file exists and is valid."
        except json.JSONDecodeError:
            pass

    default_data = {
        "timestamp": datetime.now().isoformat(),
        "games": {"mlb": [], "wnba": []},
        "player_props": [],
        "summary": {"total_games": 0, "total_props": 0, "mlb_games": 0, "wnba_games": 0}
    }
    try:
        with open(path, "w") as f:
            json.dump(default_data, f, indent=2)
        return True, f"Created fresh {OUTPUT_FILE}"
    except Exception as e:
        return False, f"Failed to create output file: {e}"


def repair_cache_directory() -> tuple:
    """Create cache directory if missing."""
    path = Path(CACHE_DIR)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True, f"Cache directory {CACHE_DIR} ensured."
    except Exception as e:
        return False, f"Failed to create cache dir: {e}"


def repair_database() -> tuple:
    """Recreate database schema if DB is missing or corrupt."""
    from storage import init_db
    try:
        init_db()
        return True, f"Database {DB_PATH} initialised/verified."
    except Exception as e:
        return False, f"Database repair failed: {e}"


def repair_dependencies() -> tuple:
    """Attempt to install missing packages via pip."""
    required = ["requests", "streamlit", "plotly", "pandas"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)

    if not missing:
        return True, "All packages installed."

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        return True, f"Installed missing packages: {', '.join(missing)}"
    except Exception as e:
        return False, f"Failed to install packages: {e}"


def repair_environment() -> tuple:
    """Check and report missing environment variables. Does not auto-set them."""
    required_vars = ["ODDS_API_KEY", "SLACK_WEBHOOK_URL"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if not missing:
        return True, "All required env vars set."
    return False, f"Missing env vars: {', '.join(missing)}. Please set them."


# Map health check names to repair functions
REPAIR_MAP = {
    "file_age": repair_output_file,
    "schema": repair_output_file,
    "dependencies": repair_dependencies,
    "cache": repair_cache_directory,
    "database": repair_database,
}


def run_repairs(health_results: dict) -> dict:
    """
    Run repairs for each failed check.
    Returns a report dict with actions taken.
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "actions": [],
        "success": True
    }

    for check_name, check_data in health_results.get("checks", {}).items():
        if check_data.get("status") == "FAIL":
            repair_func = REPAIR_MAP.get(check_name)
            if repair_func:
                success, msg = repair_func()
                report["actions"].append({
                    "check": check_name,
                    "repair_attempted": True,
                    "success": success,
                    "message": msg
                })
                if not success:
                    report["success"] = False
            else:
                report["actions"].append({
                    "check": check_name,
                    "repair_attempted": False,
                    "success": False,
                    "message": "No repair defined for this check."
                })
                report["success"] = False

    # Save report
    with open(REPAIR_LOG, "w") as f:
        json.dump(report, f, indent=2)

    # Send alert with summary
    if report["actions"]:
        summary = f"Repair run: {len(report['actions'])} actions. Success: {report['success']}"
        send_alert(f"🛠️ {summary}\nDetails: {json.dumps(report['actions'], indent=2)}",
                   severity="WARNING" if report["success"] else "CRITICAL")

    return report
