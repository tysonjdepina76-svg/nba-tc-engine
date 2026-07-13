"""
Performance monitoring and alerting.
"""

import json
import os
from datetime import datetime
from typing import Dict
from sources.utils.logging import get_logger

logger = get_logger(__name__)

class PerformanceMonitor:
    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self.alerts = []
        self.thresholds = {
            "api_latency_ms": 500,
            "fetch_timeout": 10,
            "cache_hit_rate": 0.6,
            "error_rate": 0.05
        }

    def track_metric(self, name: str, value: float) -> None:
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
        self._check_alert(name, value)

    def _check_alert(self, name: str, value: float) -> None:
        threshold = self.thresholds.get(name)
        if threshold and value > threshold:
            alert = {
                "name": name,
                "value": value,
                "threshold": threshold,
                "timestamp": datetime.now().isoformat()
            }
            self.alerts.append(alert)
            logger.warning(f"Alert: {name} = {value} > {threshold}")
            self._send_alert(alert)

    def _send_alert(self, alert: Dict) -> None:
        alert_file = "/home/workspace/Projects/logs/alerts.log"
        os.makedirs(os.path.dirname(alert_file), exist_ok=True)
        with open(alert_file, "a") as f:
            f.write(json.dumps(alert) + "\n")

    def get_report(self) -> Dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics,
            "alerts": self.alerts[-10:],
            "alert_count": len(self.alerts)
        }
