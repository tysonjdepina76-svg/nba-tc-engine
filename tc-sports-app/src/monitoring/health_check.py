"""
Health check orchestrator — runs all checks and aggregates results.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import logging

from src.monitoring.checks import api, data, system, gates

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self):
        self.results = {}
        self.critical_failures = []
        self.warnings = []

    def check_all(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {},
        }
        self._run_check("espn", api.check_espn)
        self._run_check("odds_api", api.check_odds_api)
        self._run_check("draftkings", api.check_draftkings)
        self._run_check("data_freshness", data.check_data_freshness)
        self._run_check("projections", data.check_projection_validity)
        self._run_check("disk_space", system.check_disk_space)
        self._run_check("dashboard", system.check_dashboard)
        self._run_check("circuit_breakers", gates.check_circuit_breakers)
        if self.critical_failures:
            self.results["status"] = "critical"
        elif self.warnings:
            self.results["status"] = "warning"
        self.results["critical_failures"] = self.critical_failures
        self.results["warnings"] = self.warnings
        self._log_results()
        return self.results

    def _run_check(self, name, check_func):
        try:
            result = check_func()
            self.results["checks"][name] = result
            status = result.get("status", "unknown")
            if status == "critical":
                self.critical_failures.append(name + ": " + result.get("message", "Unknown error"))
            elif status == "warning":
                self.warnings.append(name + ": " + result.get("message", "Warning"))
        except Exception as e:
            self.results["checks"][name] = {"status": "critical", "error": str(e)}
            self.critical_failures.append(name + ": " + str(e))

    def _log_results(self):
        log_dir = Path("/home/workspace/logs/health")
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / ("health_" + timestamp + ".json")
        try:
            log_file.write_text(json.dumps(self.results, indent=2))
        except Exception as e:
            logger.warning("Failed to write health log: " + str(e))
        try:
            cutoff = (datetime.now() - timedelta(days=30)).timestamp()
            for old_file in log_dir.glob("*.json"):
                if old_file.stat().st_mtime < cutoff:
                    old_file.unlink()
        except Exception:
            pass
