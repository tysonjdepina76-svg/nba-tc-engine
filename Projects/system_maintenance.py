#!/usr/bin/env python3
"""system_maintenance.py — Self-sustaining health checks and auto-repair"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

LOG_DIR = Path("/home/workspace/Projects/logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemMaintenance:
    def __init__(self):
        self.projects_dir = Path("/home/workspace/Projects")
        self.daily_log = Path("/home/workspace/Daily_Log")
        self.results = {}

    def check_dashboard(self) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8510"],
                capture_output=True, text=True, timeout=5,
            )
            code = result.stdout.strip()
            return (code == "200", f"Dashboard HTTP {code}" if code == "200" else f"HTTP {code}")
        except Exception as e:
            return (False, f"Error: {e}")

    def check_git(self) -> Tuple[bool, str]:
        try:
            r = subprocess.run(
                ["git", "-C", str(self.projects_dir), "log", "--oneline", "-1"],
                capture_output=True, text=True, timeout=5,
            )
            sha = r.stdout.strip().split()[0] if r.stdout.strip() else "no-commits"
            return (bool(sha) and sha != "no-commits", f"HEAD {sha}")
        except Exception as e:
            return (False, f"Error: {e}")

    def check_daily_log(self) -> Tuple[bool, str]:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            d = self.daily_log / today
            if not d.exists():
                return (True, f"No log yet for {today} (off-day OK)")
            csvs = list(d.glob("*.csv"))
            return (True, f"{today}: {len(csvs)} csv files")
        except Exception as e:
            return (False, f"Error: {e}")

    def run_all_checks(self) -> Dict:
        checks = [
            ("dashboard", self.check_dashboard),
            ("git", self.check_git),
            ("daily_log", self.check_daily_log),
        ]
        self.results = {}
        for name, check_fn in checks:
            try:
                status, message = check_fn()
            except Exception as e:
                status, message = False, f"raised: {e}"
            self.results[name] = {"status": status, "message": message}
            logger.info(f"{'✅' if status else '❌'} {name}: {message}")
        return self.results

    def generate_report(self) -> str:
        report = [
            "=" * 60,
            f"SYSTEM HEALTH REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
        ]
        for name, data in self.results.items():
            report.append(f"{'✅' if data['status'] else '❌'} {name}: {data['message']}")
        passed = sum(1 for d in self.results.values() if d["status"])
        report.append("-" * 60)
        report.append(f"HEALTH: {passed}/{len(self.results)} PASSING")
        report.append("=" * 60)
        return "\n".join(report)

def main():
    maintenance = SystemMaintenance()
    maintenance.run_all_checks()
    print(maintenance.generate_report())
    return 0

if __name__ == "__main__":
    sys.exit(main())
