import json
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime
from pipeline.config import OUTPUT_FILE, HEALTH_FILE, DB_PATH, CACHE_DIR, LOG_FILE, CRON_LOG, ODDS_API_KEY, SLACK_WEBHOOK_URL
from pipeline.alert import send_alert

REPAIR_LOG = "repair_report.json"


def repair_output_file() -> tuple:
    path = Path(OUTPUT_FILE)
    if path.exists():
        try:
            with open(path) as f:
                json.load(f)
            return True, "Output file is valid."
        except json.JSONDecodeError:
            pass

    default_data = {
        "timestamp": datetime.now().isoformat(),
        "games": {"mlb": [], "wnba": []},
        "player_props": [],
        "summary": {"total_games": 0, "total_props": 0, "mlb_games": 0, "wnba_games": 0},
    }
    try:
        with open(path, "w") as f:
            json.dump(default_data, f, indent=2)
        return True, f"Created fresh {OUTPUT_FILE}"
    except Exception as e:
        return False, f"Failed: {e}"


def repair_cache_directory() -> tuple:
    path = Path(CACHE_DIR)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True, f"Cache dir {CACHE_DIR} ensured."
    except Exception as e:
        return False, f"Failed: {e}"


def repair_database() -> tuple:
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, league TEXT, player TEXT, team TEXT, stat TEXT,
                tc_projection REAL, market_line REAL, edge REAL,
                direction TEXT, reason TEXT, matchup TEXT, period TEXT, signal TEXT
            )
        """)
        conn.commit()
        conn.close()
        return True, f"Database {DB_PATH} initialised."
    except Exception as e:
        return False, f"Database repair failed: {e}"


def repair_dependencies() -> tuple:
    required = ["requests", "streamlit", "plotly", "pandas", "sports-skills"]
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
        return True, f"Installed: {', '.join(missing)}"
    except Exception as e:
        return False, f"Failed: {e}"


def repair_environment() -> tuple:
    required_vars = ["ODDS_API_KEY", "SLACK_WEBHOOK_URL"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if not missing:
        return True, "All required env vars set."
    return False, f"Missing: {', '.join(missing)}. Set in .env or secrets."


REPAIR_MAP = {
    "file_age": repair_output_file,
    "schema": repair_output_file,
    "dependencies": repair_dependencies,
    "cache": repair_cache_directory,
    "database": repair_database,
}


def run_repairs(health_results: dict) -> dict:
    report = {
        "timestamp": datetime.now().isoformat(),
        "actions": [],
        "success": True,
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
                    "message": msg,
                })
                if not success:
                    report["success"] = False
            else:
                report["actions"].append({
                    "check": check_name,
                    "repair_attempted": False,
                    "success": False,
                    "message": "No repair defined.",
                })
                report["success"] = False

    with open(REPAIR_LOG, "w") as f:
        json.dump(report, f, indent=2)

    if report["actions"]:
        summary = f"Repair: {len(report['actions'])} actions. Success: {report['success']}"
        send_alert(f"\U0001f6e0 {summary}\n{json.dumps(report['actions'], indent=2)}",
                   severity="WARNING" if report["success"] else "CRITICAL")

    return report
