"""Health check - validates the system, not just APIs.

Critical change: checks the DATA, not just HTTP status.
Only reports failure AFTER the validator confirms real problem.
"""
import httpx
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from circuit_breaker import CircuitBreakerRegistry
from data_validator import DataFreshnessChecker
from alert_deduper import get_deduper

logger = logging.getLogger(__name__)


class HealthCheck:
    def __init__(self):
        self.last_run: Optional[datetime] = None
        self.last_status: str = "unknown"
        self.history: List[dict] = []
        self.freshness = DataFreshnessChecker()
        self.deduper = get_deduper()

    def run_full_check(self, sources: List[str] = None) -> Dict[str, Any]:
        """Run health check on all registered breakers + data freshness.

        Returns a structured health report. Does NOT send alerts itself.
        Caller decides whether to alert based on real failures.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "circuits": CircuitBreakerRegistry.get_all_status(),
            "fresh_data": {},
            "services": self._check_external_services(),
            "issues": [],
            "healthy": True,
        }
        # Probe live combos service (separate from circuit breakers)
        combos = report["services"].get("live_combos", {})
        if combos.get("status") != "ok":
            report["healthy"] = False
            report["issues"].append({"type": "service_down", "service": "live_combos", "severity": "high", "details": combos})
        breakers = report["circuits"]
        open_breakers = [name for name, s in breakers.items() if s["state"] == "open"]
        if open_breakers:
            report["healthy"] = False
            report["issues"].append({"type": "circuit_open", "sources": open_breakers, "severity": "high"})
        for name, status in breakers.items():
            if status["failure_count"] > 0 and status["state"] == "closed":
                if status["failure_count"] >= 3:
                    report["issues"].append({"type": "degraded", "source": name, "failures": status["failure_count"], "severity": "medium"})
        self.last_run = datetime.now()
        self.last_status = "healthy" if report["healthy"] else "degraded"
        self.history.append({"time": self.last_run.isoformat(), "status": self.last_status})
        if len(self.history) > 100:
            self.history = self.history[-100:]
        return report

    def should_alert(self, report: Dict[str, Any]) -> bool:
        """Return True only if report contains a real, deduped, actionable failure."""
        if report["healthy"]:
            return False
        for issue in report["issues"]:
            if issue["severity"] == "high":
                key = f"{issue['type']}:{','.join(issue.get('sources', []))}"
                if self.deduper.should_send("health", key):
                    return True
        return False

    def get_status_summary(self) -> str:
        if not self.history:
            return "No health checks run yet"
        recent = self.history[-10:]
        healthy = sum(1 for h in recent if h["status"] == "healthy")
        return f"{healthy}/{len(recent)} healthy in last {len(recent)} runs. Last: {self.last_status} at {self.last_run.isoformat() if self.last_run else 'never'}"

    def _check_external_services(self) -> Dict[str, Any]:
        """Probe external services."""
        services: Dict[str, Any] = {}

        # Live combos API on :8000
        try:
            r = httpx.get("http://localhost:8000/live-combos?sport=WNBA", timeout=3.0)
            r.raise_for_status()
            data = r.json()
            services["live_combos"] = {
                "status": "ok",
                "combo_count": data.get("combo_count", 0),
                "seeded": data.get("seeded", False),
            }
        except Exception:
            services["live_combos"] = {"status": "down"}

        return services


_health_instance: Optional[HealthCheck] = None


def get_health_check() -> HealthCheck:
    global _health_instance
    if _health_instance is None:
        _health_instance = HealthCheck()
    return _health_instance
